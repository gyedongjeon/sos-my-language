"""The learner can add topics of their own next to the built-in ones."""

import json
import sqlite3

import pytest

from app import conversation, topics
from app.db import DB_PATH, SEED_TOPICS, get_connection, init_db
from app.llm import LLMError

OWN = {
    "title": "Renting a car",
    "situation": "The tutor works at a car rental desk at the airport.",
    "opener": "Hello! Do you have a reservation with us?",
}


@pytest.fixture
def writer(monkeypatch):
    """The model writes `writer.opener` as a topic's opening line."""

    def complete(system, user, **params):
        complete.system, complete.user = system, user
        return json.dumps({"opener": complete.opener})

    complete.opener = "Hi there! How can I help you today?"
    monkeypatch.setattr(topics, "complete", complete)
    return complete


def add(client, **changes) -> dict:
    response = client.post("/api/topics", json={**OWN, **changes})
    assert response.status_code == 201, response.text
    return response.json()


def test_built_in_topics_are_not_the_learners_own(client):
    assert all(topic["custom"] is False for topic in client.get("/api/topics").json())


def test_a_topic_of_the_learners_own_is_added_after_the_built_in_ones(client):
    added = add(client)
    assert added == {"id": added["id"], **OWN, "custom": True, "category": None, "background": None}
    listed = client.get("/api/topics").json()
    assert len(listed) == len(SEED_TOPICS) + 1
    assert listed[-1] == added


def test_the_tutor_writes_the_opening_line_when_none_is_given(client, writer):
    added = add(client, opener="")
    assert added["opener"] == "Hi there! How can I help you today?"
    # It is written from the title and the situation.
    assert OWN["title"] in writer.user and OWN["situation"] in writer.user
    assert add(client, title="Another", opener=None)["opener"] == writer.opener


def test_no_model_is_needed_when_the_opening_line_is_given(client):
    # The LLM is not mocked here: reaching it would fail the test.
    assert add(client)["opener"] == OWN["opener"]


def test_a_topic_is_not_added_when_its_opening_line_cannot_be_written(client, monkeypatch):
    def fail(system, user, **params):
        raise LLMError("The LLM provider is not responding.")

    monkeypatch.setattr(topics, "complete", fail)
    response = client.post("/api/topics", json={**OWN, "opener": ""})
    assert response.status_code == 502
    assert "not responding" in response.json()["detail"]
    assert len(client.get("/api/topics").json()) == len(SEED_TOPICS)


def test_a_topic_needs_a_title_and_a_situation_and_a_title_of_its_own(client):
    assert client.post("/api/topics", json={**OWN, "title": "  "}).status_code == 422
    assert client.post("/api/topics", json={**OWN, "situation": ""}).status_code == 422
    add(client)
    assert client.post("/api/topics", json=OWN).status_code == 409
    assert client.post("/api/topics", json={**OWN, "title": SEED_TOPICS[0][0]}).status_code == 409


def test_what_was_typed_is_trimmed(client):
    added = add(client, title="  Renting a car ", situation=" At the desk. ", opener=" Hello! ")
    assert (added["title"], added["situation"], added["opener"]) == ("Renting a car", "At the desk.", "Hello!")


def test_a_conversation_can_be_held_on_an_own_topic(client, monkeypatch):
    added = add(client)
    monkeypatch.setattr(conversation, "complete", lambda system, user, **params: json.dumps({"reply": "Great!"}))
    started = client.post("/api/conversations", json={"topic_id": added["id"]}).json()
    assert started["messages"][0]["text"] == OWN["opener"]
    client.post(f"/api/conversations/{started['id']}/messages", json={"text": "Yes, I do."})
    assert client.post(f"/api/conversations/{started['id']}/reply").status_code == 200


def test_an_own_topic_can_be_deleted_and_its_conversations_stay(client, monkeypatch):
    added = add(client)
    monkeypatch.setattr(conversation, "complete", lambda system, user, **params: json.dumps({"reply": "Great!"}))
    started = client.post("/api/conversations", json={"topic_id": added["id"]}).json()
    client.post(f"/api/conversations/{started['id']}/messages", json={"text": "Yes, I do."})
    client.post(f"/api/conversations/{started['id']}/reply")

    assert client.delete(f"/api/topics/{added['id']}").status_code == 204
    assert len(client.get("/api/topics").json()) == len(SEED_TOPICS)
    kept = client.get(f"/api/conversations/{started['id']}").json()
    assert kept["topic_id"] is None and kept["title"] == OWN["title"]
    assert [c["id"] for c in client.get("/api/conversations").json()] == [started["id"]]


def test_a_built_in_topic_cannot_be_deleted(client):
    assert client.delete("/api/topics/1").status_code == 403
    assert client.delete("/api/topics/999").status_code == 404
    assert len(client.get("/api/topics").json()) == len(SEED_TOPICS)


def test_starting_the_app_again_leaves_an_own_topic_as_it_is(client):
    added = add(client)
    init_db()
    assert client.get("/api/topics").json()[-1] == added


def test_a_database_from_before_own_topics_gains_the_column(client):
    with get_connection() as conn:
        conn.execute("ALTER TABLE topics DROP COLUMN custom")
    init_db()
    with get_connection() as conn:
        assert "custom" in [column[1] for column in conn.execute("PRAGMA table_info(topics)")]
    assert all(topic["custom"] is False for topic in client.get("/api/topics").json())
