"""Corrections from saved conversations can be practised by saying the better sentence aloud."""

import json
import sqlite3

import pytest

from app import conversation
from app.db import DB_PATH, SEED_TOPICS, get_connection, init_db

BEACH = {"original": "I go to the beach", "improved": "I went to the beach.", "explanation": "Past tense."}
EXCITED = {"original": "I am exciting", "improved": "I'm excited.", "explanation": "Use -ed for a feeling."}


@pytest.fixture
def tutor(monkeypatch):
    """The model answers every turn with `tutor.correction`."""

    def complete(system, user, **params):
        return json.dumps({"reply": "I see!", "correction": complete.correction})

    complete.correction = BEACH
    monkeypatch.setattr(conversation, "complete", complete)
    return complete


def held(client, tutor, *corrections, topic_id=1) -> int:
    """A saved conversation with one learner line for each given correction (None: a fine line)."""
    started = client.post("/api/conversations", json={"topic_id": topic_id}).json()
    for correction in corrections:
        tutor.correction = correction
        client.post(f"/api/conversations/{started['id']}/messages", json={"text": "Something I said."})
        assert client.post(f"/api/conversations/{started['id']}/reply").status_code == 200
    return started["id"]


def attempt(client, correction_id: int, text: str) -> dict:
    response = client.post(f"/api/corrections/{correction_id}/attempts", json={"text": text})
    assert response.status_code == 200, response.text
    return response.json()


def test_corrections_are_listed_newest_first_with_where_they_came_from(client, tutor):
    first = held(client, tutor, BEACH, None)
    second = held(client, tutor, EXCITED, topic_id=3)
    listed = client.get("/api/corrections").json()
    assert [(c["conversation_id"], c["title"], c["improved"]) for c in listed] == [
        (second, SEED_TOPICS[2][0], "I'm excited."),
        (first, SEED_TOPICS[0][0], "I went to the beach."),
    ]
    assert listed[1]["original"] == BEACH["original"] and listed[1]["explanation"] == BEACH["explanation"]
    assert all(c["practiced"] == 0 and c["practiced_at"] is None for c in listed)


def test_saying_the_better_sentence_counts_as_practice(client, tutor):
    held(client, tutor, BEACH)
    correction_id = client.get("/api/corrections").json()[0]["id"]
    # Spoken, so punctuation and capitals do not matter.
    result = attempt(client, correction_id, "i went to the beach")
    assert result["matched"] is True and result["missing"] == []
    assert result["practiced"] == 1
    assert attempt(client, correction_id, "I went to the beach!")["practiced"] == 2
    saved = client.get("/api/corrections").json()[0]
    assert saved["practiced"] == 2 and saved["practiced_at"].endswith("Z")


def test_the_better_sentence_may_be_part_of_what_was_said(client, tutor):
    held(client, tutor, BEACH)
    correction_id = client.get("/api/corrections").json()[0]["id"]
    assert attempt(client, correction_id, "Yesterday I went to the beach with my friend.")["matched"] is True


def test_a_sentence_said_differently_does_not_count_and_names_the_missing_words(client, tutor):
    held(client, tutor, BEACH)
    correction_id = client.get("/api/corrections").json()[0]["id"]
    result = attempt(client, correction_id, "I go to the beach.")
    assert result == {"matched": False, "missing": ["went"], "practiced": 0}
    # All the words, but not in that order.
    assert attempt(client, correction_id, "To the beach I went.") == {"matched": False, "missing": [], "practiced": 0}
    assert client.get("/api/corrections").json()[0]["practiced_at"] is None


def test_both_ways_of_saying_a_contraction_count(client, tutor):
    held(client, tutor, EXCITED)
    correction_id = client.get("/api/corrections").json()[0]["id"]
    assert attempt(client, correction_id, "I am excited.")["matched"] is True


def test_only_a_corrected_line_can_be_practised(client, tutor):
    held(client, tutor, None)
    with get_connection() as conn:
        fine = conn.execute("SELECT id FROM messages WHERE role = 'learner'").fetchone()["id"]
    assert client.post(f"/api/corrections/{fine}/attempts", json={"text": "Hello."}).status_code == 404
    assert client.post("/api/corrections/999/attempts", json={"text": "Hello."}).status_code == 404
    assert client.post(f"/api/corrections/{fine}/attempts", json={"text": ""}).status_code == 422


def test_deleting_a_conversation_removes_its_corrections(client, tutor):
    conversation_id = held(client, tutor, BEACH)
    client.delete(f"/api/conversations/{conversation_id}")
    assert client.get("/api/corrections").json() == []


def test_a_database_from_before_practice_gains_the_columns(client):
    with get_connection() as conn:
        conn.execute("ALTER TABLE messages DROP COLUMN practiced")
        conn.execute("ALTER TABLE messages DROP COLUMN practiced_at")
    init_db()
    with get_connection() as conn:
        columns = [column[1] for column in conn.execute("PRAGMA table_info(messages)")]
    assert "practiced" in columns and "practiced_at" in columns
