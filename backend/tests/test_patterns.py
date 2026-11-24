"""Sentence patterns, grouped by CEFR level, practised by saying a sentence in English."""

import json
from collections import Counter

import pytest

from app import patterns
from app.llm import LLMError
from app.patterns import LEVELS, PATTERNS

EXERCISES = {
    "note": "과거의 일을 후회할 때 씁니다.",
    "items": [
        {"prompt": "더 일찍 떠났어야 했어.", "answer": "I should have left earlier."},
        {"prompt": "그에게 말했어야 했어.", "answer": "I should have told him."},
    ],
}
VERDICT = {"correct": False, "improved": "I should have left earlier.", "explanation": "have 뒤에는 과거분사를 씁니다."}
ATTEMPT = {"prompt": "더 일찍 떠났어야 했어.", "answer": "I should have left earlier.", "said": "I should have leave earlier."}


@pytest.fixture
def model(monkeypatch):
    """The model answers with `model.reply` and records what it was asked."""

    def complete(system, user, **params):
        complete.calls.append((system, user))
        return json.dumps(complete.reply)

    complete.reply, complete.calls = EXERCISES, []
    monkeypatch.setattr(patterns, "complete", complete)
    return complete


def test_every_pattern_is_complete_and_has_a_level():
    assert LEVELS == ["A1", "A2", "B1", "B2", "C1", "C2"]
    for pattern in PATTERNS:
        assert pattern.level in LEVELS, pattern.id
        assert pattern.pattern and pattern.use and pattern.example, pattern.id
    assert len({pattern.id for pattern in PATTERNS}) == len(PATTERNS)
    assert len({pattern.pattern for pattern in PATTERNS}) == len(PATTERNS)


def test_every_level_has_patterns():
    sizes = Counter(pattern.level for pattern in PATTERNS)
    assert set(sizes) == set(LEVELS)
    assert all(size >= 6 for size in sizes.values()), sizes


def test_patterns_are_listed_level_by_level_and_start_unpractised(client):
    listed = client.get("/api/patterns").json()
    assert len(listed) == len(PATTERNS)
    levels = [pattern["level"] for pattern in listed]
    assert levels == sorted(levels, key=LEVELS.index)
    first = listed[0]
    assert first["level"] == "A1" and first["pattern"] and first["use"] and first["example"]
    assert all(p["sessions"] == 0 and p["last_correct"] is None and p["practiced_at"] is None for p in listed)


def test_exercises_are_written_for_the_pattern_in_the_learners_language(client, model):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    response = client.post("/api/patterns/should-have/exercises")
    assert response.status_code == 200, response.text
    assert response.json() == EXERCISES
    system, _ = model.calls[0]
    assert "should have + past participle" in system and "Korean" in system and "B2" in system


def test_exercises_that_cannot_be_written_are_reported(client, monkeypatch):
    def fail(system, user, **params):
        raise LLMError("The LLM provider is not responding.")

    monkeypatch.setattr(patterns, "complete", fail)
    response = client.post("/api/patterns/should-have/exercises")
    assert response.status_code == 502 and "not responding" in response.json()["detail"]


def test_a_reply_without_exercises_is_reported(client, model):
    model.reply = {"note": "…", "items": []}
    assert client.post("/api/patterns/should-have/exercises").status_code == 502


def test_what_was_said_is_judged_by_the_model(client, model):
    model.reply = VERDICT
    response = client.post("/api/patterns/should-have/check", json=ATTEMPT)
    assert response.status_code == 200, response.text
    assert response.json() == VERDICT
    system, user = model.calls[0]
    assert "should have + past participle" in system
    assert all(text in user for text in ATTEMPT.values())


def test_the_model_answer_said_as_it_is_needs_no_model(client):
    # The LLM is not mocked here: reaching it would fail the test. Spoken, so punctuation,
    # capitals, and short forms do not matter.
    said = {**ATTEMPT, "answer": "I should have left earlier.", "said": "i should've left earlier"}
    assert client.post("/api/patterns/should-have/check", json=said).json() == {
        "correct": True,
        "improved": "I should have left earlier.",
        "explanation": None,
    }


def test_a_correct_sentence_needs_no_explanation(client, model):
    model.reply = {"correct": True, "improved": "I should have gone sooner.", "explanation": "Great!"}
    said = {**ATTEMPT, "said": "I should have gone sooner."}
    assert client.post("/api/patterns/should-have/check", json=said).json()["explanation"] is None


def test_a_judgement_that_fails_is_reported(client, monkeypatch):
    def fail(system, user, **params):
        raise LLMError("The LLM provider is not responding.")

    monkeypatch.setattr(patterns, "complete", fail)
    assert client.post("/api/patterns/should-have/check", json=ATTEMPT).status_code == 502
    assert client.post("/api/patterns/should-have/check", json={**ATTEMPT, "said": ""}).status_code == 422


def test_a_finished_round_is_recorded_with_the_pattern(client):
    assert client.post("/api/patterns/should-have/results", json={"correct": 3, "total": 5}).status_code == 200
    saved = client.post("/api/patterns/should-have/results", json={"correct": 5, "total": 5}).json()
    assert (saved["sessions"], saved["last_correct"], saved["last_total"]) == (2, 5, 5)
    assert saved["practiced_at"].endswith("Z")
    listed = {p["id"]: p for p in client.get("/api/patterns").json()}
    assert listed["should-have"] == saved
    assert listed["id-like"]["sessions"] == 0


def test_a_result_must_make_sense(client):
    for body in ({"correct": 6, "total": 5}, {"correct": -1, "total": 5}, {"correct": 0, "total": 0}):
        assert client.post("/api/patterns/should-have/results", json=body).status_code == 422


def test_an_unknown_pattern_is_not_found(client):
    assert client.post("/api/patterns/nope/exercises").status_code == 404
    assert client.post("/api/patterns/nope/check", json=ATTEMPT).status_code == 404
    assert client.post("/api/patterns/nope/results", json={"correct": 1, "total": 5}).status_code == 404
