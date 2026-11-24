"""Conversations are saved as they happen and can be looked at again."""

import json

import pytest

from app import conversation
from app.db import SEED_TOPICS, get_connection
from app.languages.english import ENGLISH
from app.llm import LLMError

TITLE, SITUATION = SEED_TOPICS[0][:2]
OPENER = ENGLISH.openers[TITLE]
CORRECTION = {"original": "I go", "improved": "I went", "explanation": "Past tense."}
DELIVERY = {"clarity": 82, "unclear_words": ["beach"], "words_per_minute": 110}


@pytest.fixture
def tutor(monkeypatch):
    """The model answers every turn with `tutor.reply` and `tutor.correction`."""

    def complete(system, user, **params):
        complete.user = user
        return json.dumps({"reply": complete.reply, "correction": complete.correction})

    complete.reply, complete.correction = "Nice! Who did you go with?", CORRECTION
    monkeypatch.setattr(conversation, "complete", complete)
    return complete


def start(client, topic_id=1) -> dict:
    response = client.post("/api/conversations", json={"topic_id": topic_id})
    assert response.status_code == 201
    return response.json()


def turn(client, conversation_id: int, text="I go to the beach.", delivery=None) -> None:
    body = {"text": text, "delivery": delivery}
    assert client.post(f"/api/conversations/{conversation_id}/messages", json=body).status_code == 201
    assert client.post(f"/api/conversations/{conversation_id}/reply").status_code == 200


def test_a_conversation_starts_with_the_topic_and_its_opening_line(client):
    started = start(client)
    assert started["topic_id"] == 1
    assert (started["title"], started["situation"]) == (TITLE, SITUATION)
    assert started["started_at"].endswith("Z")
    assert started["messages"] == [{"role": "tutor", "text": OPENER, "correction": None, "delivery": None}]


def test_a_conversation_needs_a_known_topic(client):
    assert client.post("/api/conversations", json={"topic_id": 999}).status_code == 404


def test_each_turn_is_saved_with_its_correction_and_how_it_was_spoken(client, tutor):
    started = start(client)
    turn(client, started["id"], delivery=DELIVERY)
    saved = client.get(f"/api/conversations/{started['id']}").json()
    assert saved["messages"][1:] == [
        {"role": "learner", "text": "I go to the beach.", "correction": CORRECTION, "delivery": DELIVERY},
        {"role": "tutor", "text": "Nice! Who did you go with?", "correction": None, "delivery": None},
    ]


def test_the_tutor_sees_the_whole_saved_conversation(client, tutor):
    started = start(client)
    turn(client, started["id"])
    turn(client, started["id"], text="With my friend.")
    assert tutor.user.splitlines() == [
        f"Tutor: {OPENER}",
        "Learner: I go to the beach.",
        "Tutor: Nice! Who did you go with?",
        "Learner: With my friend.",
    ]


def test_the_learner_and_the_tutor_take_turns(client, tutor):
    started = start(client)
    # Nothing was said yet, so there is nothing to reply to.
    assert client.post(f"/api/conversations/{started['id']}/reply").status_code == 409
    assert client.post(f"/api/conversations/{started['id']}/messages", json={"text": "Hello."}).status_code == 201
    # The tutor has not answered the last line yet.
    assert client.post(f"/api/conversations/{started['id']}/messages", json={"text": "Hello?"}).status_code == 409
    assert client.post(f"/api/conversations/{started['id']}/messages", json={"text": ""}).status_code == 422


def test_a_failed_reply_keeps_what_was_said_so_it_can_be_asked_for_again(client, tutor, monkeypatch):
    started = start(client)
    client.post(f"/api/conversations/{started['id']}/messages", json={"text": "I go to the beach."})

    def fail(system, user, **params):
        raise LLMError("The LLM provider is not responding.")

    with monkeypatch.context() as broken:
        broken.setattr(conversation, "complete", fail)
        assert client.post(f"/api/conversations/{started['id']}/reply").status_code == 502
    assert client.post(f"/api/conversations/{started['id']}/reply").status_code == 200
    roles = [m["role"] for m in client.get(f"/api/conversations/{started['id']}").json()["messages"]]
    assert roles == ["tutor", "learner", "tutor"]


def test_history_lists_conversations_newest_first_with_their_size(client, tutor):
    first, second = start(client), start(client, topic_id=3)
    turn(client, first["id"])
    tutor.correction = None
    turn(client, first["id"], text="With my friend.")
    turn(client, second["id"], text="A latte, please.")
    listed = client.get("/api/conversations").json()
    assert [(c["id"], c["title"], c["turns"], c["corrections"]) for c in listed] == [
        (second["id"], SEED_TOPICS[2][0], 1, 0),
        (first["id"], TITLE, 2, 1),
    ]
    assert all(c["started_at"].endswith("Z") for c in listed)


def test_a_conversation_in_which_nothing_was_said_is_not_listed(client):
    start(client)
    assert client.get("/api/conversations").json() == []


def test_a_conversation_can_be_deleted_with_its_messages(client, tutor):
    started = start(client)
    turn(client, started["id"])
    assert client.delete(f"/api/conversations/{started['id']}").status_code == 204
    assert client.get(f"/api/conversations/{started['id']}").status_code == 404
    assert client.get("/api/conversations").json() == []
    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def test_an_unknown_conversation_is_not_found(client):
    assert client.get("/api/conversations/999").status_code == 404
    assert client.delete("/api/conversations/999").status_code == 404
    assert client.post("/api/conversations/999/messages", json={"text": "Hello."}).status_code == 404
    assert client.post("/api/conversations/999/reply").status_code == 404
