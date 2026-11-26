"""A word the learner taps in a sentence, explained in their own language."""

import json

import pytest

from app import word_lookup
from app.llm import LLMError

CORTEX = {
    "lemma": "cortex",
    "phrase": "",
    "part_of_speech": "명사",
    "meaning": "피질, 대뇌 피질",
    "in_context": "여기서는 뇌의 바깥층을 말합니다.",
}
SENTENCE = "It involves activation and all four lobes of the cortex."


@pytest.fixture
def model(monkeypatch):
    """The model explains every word as `model.reply`."""

    def complete(system, user, **params):
        complete.calls.append((system, user))
        return json.dumps(complete.reply)

    complete.calls = []
    complete.reply = CORTEX
    monkeypatch.setattr(word_lookup, "complete", complete)
    return complete


def look_up(client, word="cortex", sentence=SENTENCE):
    return client.post("/api/lookup", json={"word": word, "sentence": sentence})


def test_a_tapped_word_is_explained_in_the_feedback_language(client, model):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    response = look_up(client)
    assert response.status_code == 200, response.text
    assert response.json() == {"word": "cortex", "saved": None, **CORTEX}
    system, user = model.calls[0]
    assert "Korean" in system and "English" in system
    # The sentence is sent with the word, so the meaning is the one it has there.
    assert "cortex" in user and SENTENCE in user


def test_a_lookup_is_kept_and_not_asked_for_again(client, model):
    first = look_up(client).json()
    assert look_up(client).json() == first
    assert len(model.calls) == 1


def test_a_word_is_asked_for_again_in_another_feedback_language(client, model):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    look_up(client)
    client.put("/api/settings", json={"feedback_language": "Japanese"})
    look_up(client)
    assert len(model.calls) == 2
    assert "Japanese" in model.calls[1][0]


def test_a_lookup_in_one_language_being_learned_is_not_used_for_another(client, model, german):
    look_up(client)
    assert "German" in model.calls[0][0]
    client.put("/api/language", json={"language": "en"})
    look_up(client)
    assert len(model.calls) == 2


def test_a_word_in_a_phrase_names_the_phrase(client, model):
    model.reply = {**CORTEX, "lemma": "fangen", "phrase": "anfangen"}
    response = look_up(client, "fängt", "Der Film fängt um acht an.")
    assert response.json()["phrase"] == "anfangen"


def test_a_failed_lookup_is_reported_and_not_kept(client, model, monkeypatch):
    def fail(system, user, **params):
        raise LLMError("The model is busy.")

    monkeypatch.setattr(word_lookup, "complete", fail)
    response = look_up(client)
    assert response.status_code == 502
    assert "The model is busy." in response.json()["detail"]
    monkeypatch.setattr(word_lookup, "complete", model)
    assert look_up(client).status_code == 200


def test_a_word_must_be_in_its_sentence(client, model):
    assert look_up(client, "brain").status_code == 422
    assert model.calls == []
