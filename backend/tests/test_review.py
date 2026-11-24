"""A conversation can be wrapped up with a review of how it went."""

import json
import sqlite3

import pytest

from app import conversation, review
from app.db import DB_PATH, SEED_TOPICS, get_connection, init_db
from app.llm import LLMError

OPENER = SEED_TOPICS[0][2]
CORRECTION = {"original": "I go", "improved": "I went", "explanation": "Past tense."}
REVIEW = {
    "summary": "You kept the chat going and answered every question.",
    "strengths": ["You answered in full sentences."],
    "focus": ["Use the past tense for things that already happened."],
    "phrases": [{"english": "I ended up going to the beach.", "note": "For a plan that changed."}],
}


@pytest.fixture
def model(monkeypatch):
    """The model answers a turn with one correction, and a review request with `model.review`."""

    def reply(system, user, **params):
        return json.dumps({"reply": "Nice! Who did you go with?", "correction": CORRECTION})

    def write(system, user, **params):
        write.system, write.user = system, user
        return json.dumps(write.review)

    write.review = REVIEW
    monkeypatch.setattr(conversation, "complete", reply)
    monkeypatch.setattr(review, "complete", write)
    return write


def held(client, *said: str) -> int:
    """A saved conversation in which the learner said these lines."""
    started = client.post("/api/conversations", json={"topic_id": 1}).json()
    for text in said:
        assert client.post(f"/api/conversations/{started['id']}/messages", json={"text": text}).status_code == 201
        assert client.post(f"/api/conversations/{started['id']}/reply").status_code == 200
    return started["id"]


def test_a_conversation_has_no_review_until_it_is_asked_for(client, model):
    assert client.get(f"/api/conversations/{held(client, 'I go to the beach.')}").json()["review"] is None


def test_a_review_is_written_and_saved_with_the_conversation(client, model):
    conversation_id = held(client, "I go to the beach.")
    response = client.post(f"/api/conversations/{conversation_id}/review")
    assert response.status_code == 200
    assert response.json() == REVIEW
    assert client.get(f"/api/conversations/{conversation_id}").json()["review"] == REVIEW


def test_the_review_is_written_from_the_lines_and_their_corrections(client, model):
    client.post(f"/api/conversations/{held(client, 'I go to the beach.')}/review")
    assert model.user.splitlines() == [
        f"Tutor: {OPENER}",
        "Learner: I go to the beach.",
        '  (corrected: "I go" -> "I went")',
        "Tutor: Nice! Who did you go with?",
    ]


def test_the_review_is_written_in_the_feedback_language(client, model):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    client.post(f"/api/conversations/{held(client, 'I go to the beach.')}/review")
    assert "Korean" in model.system


def test_each_list_of_a_review_is_kept_short(client, model):
    model.review = {**REVIEW, "strengths": ["a", "b", "c", "d"], "focus": [], "phrases": []}
    written = client.post(f"/api/conversations/{held(client, 'I go to the beach.')}/review").json()
    assert written["strengths"] == ["a", "b", "c"]
    assert written["focus"] == [] and written["phrases"] == []


def test_a_conversation_in_which_nothing_was_said_cannot_be_reviewed(client, model):
    assert client.post(f"/api/conversations/{held(client)}/review").status_code == 409
    assert client.post("/api/conversations/999/review").status_code == 404


def test_a_review_that_cannot_be_written_is_reported_and_nothing_is_saved(client, model, monkeypatch):
    conversation_id = held(client, "I go to the beach.")

    def fail(system, user, **params):
        raise LLMError("The LLM provider is not responding.")

    monkeypatch.setattr(review, "complete", fail)
    response = client.post(f"/api/conversations/{conversation_id}/review")
    assert response.status_code == 502
    assert "not responding" in response.json()["detail"]
    assert client.get(f"/api/conversations/{conversation_id}").json()["review"] is None


def test_saying_more_drops_the_review_because_it_no_longer_covers_the_conversation(client, model):
    conversation_id = held(client, "I go to the beach.")
    client.post(f"/api/conversations/{conversation_id}/review")
    client.post(f"/api/conversations/{conversation_id}/messages", json={"text": "With my friend."})
    assert client.get(f"/api/conversations/{conversation_id}").json()["review"] is None


def test_a_database_from_before_reviews_gains_the_column(client):
    with get_connection() as conn:
        conn.execute("ALTER TABLE conversations DROP COLUMN review")
    init_db()
    with get_connection() as conn:
        assert "review" in [column[1] for column in conn.execute("PRAGMA table_info(conversations)")]
