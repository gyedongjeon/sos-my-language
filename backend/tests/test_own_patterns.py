"""A pattern of the learner's own, made from a sentence of a saved video."""

import json

import pytest

from app import patterns, videos
from app.llm import LLMError
from app.patterns import PATTERNS
from app.videos import Snippet

SENTENCE = "This is the closest I've ever gotten to a college graduation."
WRITTEN = {"pattern": "the closest I've ever + past participle + to …", "use": "Saying how near you came to something"}


@pytest.fixture
def line(client, monkeypatch):
    """A sentence of a saved video."""
    speech = [Snippet(0.0, 4.0, "Truth be told, I never graduated."), Snippet(4.0, 4.0, SENTENCE)]
    monkeypatch.setattr(videos, "_transcript", lambda video_id: (speech, "en", False))
    monkeypatch.setattr(videos, "_about", lambda video_id: ("Commencement address", "Stanford"))
    video = client.post("/api/videos", json={"url": "https://youtu.be/UF8uR6Z6KLc"}).json()
    return {**video["lines"][1], "video": video["id"]}


@pytest.fixture
def model(monkeypatch):
    """The model answers with `model.reply` and records what it was asked."""

    def complete(system, user, **params):
        complete.calls.append((system, user))
        return json.dumps(complete.reply)

    complete.reply, complete.calls = dict(WRITTEN), []
    monkeypatch.setattr(patterns, "complete", complete)
    return complete


def make(client, line: dict, phrase="the closest I've ever gotten to") -> dict:
    response = client.post("/api/patterns", json={"line": line["id"], "phrase": phrase})
    assert response.status_code == 201, response.text
    return response.json()


def test_built_in_patterns_are_not_the_learners_own(client):
    listed = client.get("/api/patterns").json()
    assert len(listed) == len(PATTERNS)
    assert all(p["custom"] is False and p["video"] is None for p in listed)


def test_a_pattern_is_made_from_the_marked_part_of_a_sentence(client, line, model):
    made = make(client, line)
    assert made["id"].startswith("own-") and made["level"] == "Yours" and made["custom"] is True
    assert (made["pattern"], made["use"]) == (WRITTEN["pattern"], WRITTEN["use"])
    # The sentence it was found in is its example, and it leads back to the video.
    assert made["example"] == SENTENCE
    assert (made["video"], made["position"]) == (line["video"], 1)
    assert made["sessions"] == 0
    _, user = model.calls[0]
    assert SENTENCE in user and "the closest I've ever gotten to" in user


def test_own_patterns_are_listed_after_the_built_in_ones(client, line, model):
    made = make(client, line)
    listed = client.get("/api/patterns").json()
    assert len(listed) == len(PATTERNS) + 1 and listed[-1] == made


def test_the_marked_part_must_be_in_the_sentence(client, line, model):
    body = {"line": line["id"], "phrase": "a phrase from somewhere else"}
    assert client.post("/api/patterns", json=body).status_code == 422
    assert client.post("/api/patterns", json={"line": line["id"], "phrase": " "}).status_code == 422
    assert client.post("/api/patterns", json={"line": 999, "phrase": "the closest"}).status_code == 404
    assert model.calls == []
    # Capitals and spacing do not matter.
    assert client.post("/api/patterns", json={"line": line["id"], "phrase": "THE  closest i've"}).status_code == 201


def test_the_same_pattern_is_not_saved_twice(client, line, model):
    first = make(client, line)
    again = client.post("/api/patterns", json={"line": line["id"], "phrase": "the closest I've ever"})
    assert again.status_code == 200 and again.json() == first
    assert len(client.get("/api/patterns").json()) == len(PATTERNS) + 1


def test_nothing_is_saved_when_the_pattern_cannot_be_written(client, line, monkeypatch):
    def fail(system, user, **params):
        raise LLMError("The LLM provider is not responding.")

    monkeypatch.setattr(patterns, "complete", fail)
    response = client.post("/api/patterns", json={"line": line["id"], "phrase": "the closest"})
    assert response.status_code == 502 and "not responding" in response.json()["detail"]
    assert len(client.get("/api/patterns").json()) == len(PATTERNS)


def test_an_own_pattern_is_practised_like_any_other(client, line, model):
    made = make(client, line)
    model.reply = {"note": "…", "items": [{"prompt": "가장 가까이 가 본 거예요.", "answer": "This is the closest I've ever come."}]}
    assert client.post(f"/api/patterns/{made['id']}/exercises").status_code == 200
    system, _ = model.calls[-1]
    # Its example shows the level; there is no CEFR level to name.
    assert WRITTEN["pattern"] in system and SENTENCE in system and "Yours" not in system
    saved = client.post(f"/api/patterns/{made['id']}/results", json={"correct": 1, "total": 1}).json()
    assert saved["sessions"] == 1 and saved["custom"] is True
    assert client.get("/api/patterns").json()[-1] == saved


def test_an_own_pattern_can_be_deleted_with_its_progress(client, line, model):
    made = make(client, line)
    client.post(f"/api/patterns/{made['id']}/results", json={"correct": 1, "total": 1})
    assert client.delete(f"/api/patterns/{made['id']}").status_code == 204
    assert len(client.get("/api/patterns").json()) == len(PATTERNS)
    assert client.post(f"/api/patterns/{made['id']}/exercises").status_code == 404
    # A pattern made again starts from nothing.
    assert make(client, line)["sessions"] == 0


def test_a_built_in_pattern_cannot_be_deleted(client):
    assert client.delete("/api/patterns/should-have").status_code == 403
    assert client.delete("/api/patterns/own-999").status_code == 404
    assert client.delete("/api/patterns/nope").status_code == 404


def test_an_own_pattern_stays_when_its_video_is_deleted(client, line, model):
    made = make(client, line)
    client.delete(f"/api/videos/{line['video']}")
    kept = client.get("/api/patterns").json()[-1]
    assert kept["id"] == made["id"] and kept["example"] == SENTENCE
    assert kept["video"] is None and kept["position"] is None
