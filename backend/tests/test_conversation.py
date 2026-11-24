"""The tutor's replies and corrections in a saved conversation, with the model's reply prepared by the test."""

import json

import pytest

from app import conversation
from app.db import SEED_TOPICS
from app.llm import LLMError

OPENER = SEED_TOPICS[0][2]
SAID = "I go to the beach yesterday."
CORRECTION = {
    "original": "I go to the beach yesterday.",
    "improved": "I went to the beach yesterday.",
    "explanation": "Use the past tense for yesterday.",
}


def say(client, text=SAID, topic_id=1) -> int:
    """Start a conversation on a topic, add what the learner said, and return its id."""
    conversation = client.post("/api/conversations", json={"topic_id": topic_id}).json()
    assert client.post(f"/api/conversations/{conversation['id']}/messages", json={"text": text}).status_code == 201
    return conversation["id"]


@pytest.fixture
def model(monkeypatch):
    """Records what is sent to the model and replies with `model.reply`."""

    def complete(system, user, **params):
        complete.system, complete.user = system, user
        if isinstance(complete.reply, Exception):
            raise complete.reply
        return complete.reply

    complete.reply = ""
    monkeypatch.setattr(conversation, "complete", complete)
    return complete


def test_tutor_replies_in_the_topic_situation_with_a_correction(client, model):
    model.reply = json.dumps({"reply": "Nice! Who did you go with?", "correction": CORRECTION})
    response = client.post(f"/api/conversations/{say(client)}/reply")
    assert response.json() == {"reply": "Nice! Who did you go with?", "correction": CORRECTION}
    assert SEED_TOPICS[0][1] in model.system
    assert model.user == f"Tutor: {OPENER}\nLearner: {SAID}"


def test_a_message_that_needs_no_fix_has_no_correction(client, model):
    model.reply = json.dumps({"reply": "Nice! Who did you go with?", "correction": None})
    assert client.post(f"/api/conversations/{say(client)}/reply").json()["correction"] is None


def test_corrections_are_explained_in_the_chosen_language(client, model):
    model.reply = json.dumps({"reply": "Nice!", "correction": None})
    client.put("/api/settings", json={"feedback_language": "Korean"})
    client.post(f"/api/conversations/{say(client)}/reply")
    assert 'Write "explanation" in Korean' in model.system


def test_reply_reports_a_model_failure(client, model):
    model.reply = LLMError("The LLM provider's rate limit was reached. Try again shortly.")
    response = client.post(f"/api/conversations/{say(client)}/reply")
    assert response.status_code == 502
    assert "rate limit" in response.json()["detail"]


def test_reply_in_the_wrong_shape_is_an_error(client, model):
    model.reply = json.dumps({"correction": None})
    response = client.post(f"/api/conversations/{say(client)}/reply")
    assert response.status_code == 502
    assert "unexpected format" in response.json()["detail"]


def test_a_fix_of_punctuation_only_is_dropped(client, model):
    # The learner spoke; punctuation and capitals come from speech recognition, not from them.
    fix = {"original": "I'm good and you", "improved": "I'm good, and you?", "explanation": "Add a question mark."}
    model.reply = json.dumps({"reply": "I'm doing well, thanks!", "correction": fix})
    response = client.post(f"/api/conversations/{say(client, "I'm good and you")}/reply")
    assert response.json() == {"reply": "I'm doing well, thanks!", "correction": None}


def test_the_model_is_told_the_learner_spoke(client, model):
    model.reply = json.dumps({"reply": "Nice!", "correction": None})
    client.post(f"/api/conversations/{say(client)}/reply")
    assert "Never correct punctuation" in model.system
