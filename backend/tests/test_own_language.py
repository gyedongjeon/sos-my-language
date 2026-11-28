"""A text for the learner is in the learner's own language. The model is asked for that, and at
times goes on in the language of the conversation all the same (about one correction in ten in
live runs with German); such a text is noticed by its script and written again."""

import json

import pytest

from app import conversation, own_language, patterns
from app.languages import LANGUAGES
from app.llm import LLMError

GERMAN = LANGUAGES["de"]
IN_GERMAN = "Kaffee ist maskulin, daher heißt es im Akkusativ 'einen Kaffee'."
IN_KOREAN = "Kaffee는 남성 명사라서 4격에서는 'einen Kaffee'라고 합니다."


@pytest.mark.parametrize(
    ("text", "language", "expected"),
    [
        (IN_KOREAN, "Korean", True),
        (IN_GERMAN, "Korean", False),
        ("「einen Kaffee」が正しいです。", "Japanese", True),
        (IN_GERMAN, "Japanese", False),
        ("应该说 'einen Kaffee'。", "Simplified Chinese", True),
        ("Нужно сказать 'einen Kaffee'.", "Russian", True),
        (IN_GERMAN, "Russian", False),
        # Languages written with the same letters as the one practised cannot be told apart.
        (IN_GERMAN, "Spanish", True),
        (IN_GERMAN, "English", True),
        ("", "Korean", True),
    ],
)
def test_a_text_is_known_by_its_script(text, language, expected):
    assert own_language.looks_written_in(text, language) is expected


@pytest.fixture
def model(monkeypatch):
    """Answers each request with the next of `model.replies`, and records what it was asked."""

    def complete(system, user, **params):
        complete.asked.append((system, user))
        reply = complete.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    complete.asked, complete.replies = [], []
    for module in (conversation, own_language, patterns):
        monkeypatch.setattr(module, "complete", complete)
    return complete


def test_a_text_in_the_learners_language_is_left_as_it_is(model, german):
    assert own_language.in_own_language(IN_KOREAN, "Korean") == IN_KOREAN
    assert model.asked == []


def test_a_text_in_the_language_practised_is_written_again(model, german):
    model.replies = [json.dumps({"text": IN_KOREAN})]
    assert own_language.in_own_language(IN_GERMAN, "Korean") == IN_KOREAN
    system, user = model.asked[0]
    assert "into Korean" in system and "German" in system and user == IN_GERMAN


ABOUT_KOREAN_IN_KOREAN = "'할 수 있어요'는 할 수 있는 것을 말할 때 써요."
ABOUT_KOREAN_IN_ENGLISH = "Say '할 수 있어요' when you talk about what you are able to do."


@pytest.mark.parametrize(
    ("text", "language", "expected"),
    [
        # Mostly in the letters of the language practised: not in one written in Latin letters.
        (ABOUT_KOREAN_IN_KOREAN, "English", False),
        (ABOUT_KOREAN_IN_KOREAN, "Spanish", False),
        # Quoting it is fine.
        (ABOUT_KOREAN_IN_ENGLISH, "English", True),
        ("「할 수 있어요」は能力を表します。", "Japanese", True),
        (ABOUT_KOREAN_IN_KOREAN, "Japanese", False),
        (ABOUT_KOREAN_IN_KOREAN, "Korean", True),
    ],
)
def test_a_text_in_the_letters_of_the_language_practised_is_known_when_it_has_its_own(korean, text, language, expected):
    assert own_language.looks_written_in(text, language) is expected


def test_an_explanation_in_korean_is_written_again_in_english(model, korean):
    model.replies = [json.dumps({"text": ABOUT_KOREAN_IN_ENGLISH})]
    assert own_language.in_own_language(ABOUT_KOREAN_IN_KOREAN, "English") == ABOUT_KOREAN_IN_ENGLISH
    assert "into English" in model.asked[0][0]


def test_a_text_that_cannot_be_written_again_is_kept(model, german):
    model.replies = [LLMError("The model is not responding.")]
    assert own_language.in_own_language(IN_GERMAN, "Korean") == IN_GERMAN
    # Still not in the learner's language: better the first text than none.
    model.replies = [json.dumps({"text": "Immer noch auf Deutsch."})]
    assert own_language.in_own_language(IN_GERMAN, "Korean") == IN_GERMAN


def say(client, text: str) -> int:
    topic = client.get("/api/topics").json()[0]["id"]
    started = client.post("/api/conversations", json={"topic_id": topic}).json()
    client.post(f"/api/conversations/{started['id']}/messages", json={"text": text})
    return started["id"]


def test_a_correction_explained_in_the_language_practised_is_explained_again(client, model, german):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    fix = {"original": "ein Kaffee", "improved": "einen Kaffee", "explanation": IN_GERMAN}
    model.replies = [json.dumps({"reply": "Sehr gerne.", "correction": fix}), json.dumps({"text": IN_KOREAN})]
    conversation_id = say(client, "Ich möchte ein Kaffee")
    reply = client.post(f"/api/conversations/{conversation_id}/reply").json()
    assert reply["correction"] == {**fix, "explanation": IN_KOREAN}
    # What is kept with the conversation is the explanation the learner can read.
    saved = client.get(f"/api/conversations/{conversation_id}").json()
    assert saved["messages"][1]["correction"]["explanation"] == IN_KOREAN


def test_a_correction_in_the_learners_language_costs_no_second_request(client, model, german):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    fix = {"original": "ein Kaffee", "improved": "einen Kaffee", "explanation": IN_KOREAN}
    model.replies = [json.dumps({"reply": "Sehr gerne.", "correction": fix})]
    client.post(f"/api/conversations/{say(client, 'Ich möchte ein Kaffee')}/reply")
    assert len(model.asked) == 1


def test_a_pattern_verdict_explained_in_the_language_practised_is_explained_again(client, model, german):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    verdict = {"correct": False, "improved": "Ich bleibe zu Hause, weil ich krank bin.", "explanation": IN_GERMAN}
    model.replies = [json.dumps(verdict), json.dumps({"text": IN_KOREAN})]
    attempt = {"prompt": "아파서 집에 있어요.", "answer": verdict["improved"], "said": "Ich bleibe zu Hause, weil ich bin krank."}
    checked = client.post("/api/patterns/weil/check", json=attempt).json()
    assert checked["explanation"] == IN_KOREAN
    assert client.get("/api/corrections").json()[0]["explanation"] == IN_KOREAN
