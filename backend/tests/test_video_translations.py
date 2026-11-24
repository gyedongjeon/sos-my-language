"""The sentences of a saved video, translated into the learner's language when asked for."""

import json
import re

import pytest

from app import translations, videos
from app.db import get_connection
from app.llm import LLMError
from app.videos import Snippet

SPEECH = [
    Snippet(0.0, 3.0, "Good morning."),
    Snippet(3.0, 3.0, "Today we are talking about the weather."),
    Snippet(6.0, 3.0, "It has been raining for days."),
]


@pytest.fixture
def youtube(monkeypatch):
    """YouTube serves `youtube.speech` for every video."""

    def transcript(video_id):
        return youtube.speech, "en", False

    youtube.speech = SPEECH
    monkeypatch.setattr(videos, "_transcript", transcript)
    monkeypatch.setattr(videos, "_about", lambda video_id: ("The weather", "A channel"))
    return youtube


@pytest.fixture
def model(monkeypatch):
    """The model "translates" each numbered sentence it is sent as "<language>: <sentence>"."""

    def complete(system, user, **params):
        complete.calls.append((system, user))
        language = re.search(r"into (\w+)", system).group(1)
        found = re.findall(r"^\[(\d+)\] (.+)$", user, flags=re.MULTILINE)
        return json.dumps({"translations": [{"id": int(i), "text": f"{language}: {text}"} for i, text in found]})

    complete.calls = []
    monkeypatch.setattr(translations, "complete", complete)
    return complete


def add(client) -> dict:
    response = client.post("/api/videos", json={"url": "https://youtu.be/UF8uR6Z6KLc"})
    assert response.status_code == 201, response.text
    return response.json()


def translate(client, video: dict):
    return client.post(f"/api/videos/{video['id']}/translations")


def test_every_sentence_is_translated_into_the_feedback_language(client, youtube, model):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    video = add(client)
    response = translate(client, video)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "language": "Korean",
        "lines": [{"line": line["id"], "text": f"Korean: {line['text']}"} for line in video["lines"]],
        "missing": 0,
    }
    system, user = model.calls[0]
    # The title helps with what the sentences are about.
    assert "Korean" in system and "The weather" in user


def test_a_translation_is_kept_and_not_asked_for_again(client, youtube, model):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    video = add(client)
    first = translate(client, video).json()
    assert translate(client, video).json() == first
    assert len(model.calls) == 1


def test_another_feedback_language_is_translated_on_its_own(client, youtube, model):
    video = add(client)
    client.put("/api/settings", json={"feedback_language": "Korean"})
    translate(client, video)
    client.put("/api/settings", json={"feedback_language": "Japanese"})
    lines = translate(client, video).json()["lines"]
    assert all(line["text"].startswith("Japanese: ") for line in lines)
    assert len(model.calls) == 2


def test_a_long_video_is_translated_a_part_at_a_time(client, youtube, model):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    youtube.speech = [Snippet(i * 3.0, 3.0, f"This is sentence number {i}.") for i in range(2 * translations.CHUNK + 5)]
    video = add(client)
    lines = translate(client, video).json()["lines"]
    assert len(lines) == len(video["lines"])
    assert len(model.calls) == 3
    assert all(len(re.findall(r"^\[\d+\]", user, flags=re.MULTILINE)) <= translations.CHUNK for _, user in model.calls)


def test_a_sentence_left_out_by_the_model_is_asked_for_next_time(client, youtube, model, monkeypatch):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    video = add(client)
    first, *rest = video["lines"]

    def skip_the_first(system, user, **params):
        reply = json.loads(model(system, user, **params))
        # One sentence left out, and an id that was not asked for.
        reply["translations"] = [t for t in reply["translations"] if t["id"] != first["id"]] + [{"id": 999, "text": "?"}]
        return json.dumps(reply)

    monkeypatch.setattr(translations, "complete", skip_the_first)
    assert [line["line"] for line in translate(client, video).json()["lines"]] == [line["id"] for line in rest]
    monkeypatch.setattr(translations, "complete", model)
    model.calls.clear()
    assert len(translate(client, video).json()["lines"]) == 3
    # Only the missing sentence was sent.
    assert re.findall(r"^\[(\d+)\]", model.calls[0][1], flags=re.MULTILINE) == [str(first["id"])]


def test_a_part_that_failed_is_asked_for_again_at_once(client, youtube, model, monkeypatch):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    youtube.speech = [Snippet(i * 3.0, 3.0, f"This is sentence number {i}.") for i in range(2 * translations.CHUNK + 5)]
    video = add(client)
    failed = []

    def second_part_fails_once(system, user, **params):
        if "number 40." in user and not failed:
            failed.append(user)
            raise LLMError("The request timed out.")
        return model(system, user, **params)

    monkeypatch.setattr(translations, "complete", second_part_fails_once)
    found = translate(client, video).json()
    assert len(found["lines"]) == len(video["lines"]) and found["missing"] == 0


def test_a_sentence_left_out_by_the_model_is_asked_for_again_at_once(client, youtube, model, monkeypatch):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    video = add(client)
    first = video["lines"][0]

    def skip_the_first_once(system, user, **params):
        reply = json.loads(model(system, user, **params))
        if len(model.calls) == 1:
            reply["translations"] = [t for t in reply["translations"] if t["id"] != first["id"]]
        return json.dumps(reply)

    monkeypatch.setattr(translations, "complete", skip_the_first_once)
    found = translate(client, video).json()
    assert len(found["lines"]) == 3 and found["missing"] == 0
    # The second request asked only for the sentence left out.
    assert re.findall(r"^\[(\d+)\]", model.calls[1][1], flags=re.MULTILINE) == [str(first["id"])]


def test_sentences_still_not_translated_are_counted(client, youtube, model, monkeypatch):
    client.put("/api/settings", json={"feedback_language": "Korean"})
    youtube.speech = [Snippet(i * 3.0, 3.0, f"This is sentence number {i}.") for i in range(2 * translations.CHUNK + 5)]
    video = add(client)

    def second_part_always_fails(system, user, **params):
        if "number 40." in user:
            raise LLMError("The request timed out.")
        return model(system, user, **params)

    monkeypatch.setattr(translations, "complete", second_part_always_fails)
    response = translate(client, video)
    # What was translated is shown, and the rest is counted so it can be asked for again.
    assert response.status_code == 200
    found = response.json()
    assert len(found["lines"]) == translations.CHUNK + 5 and found["missing"] == translations.CHUNK


def test_a_translation_that_cannot_be_written_is_reported(client, youtube, monkeypatch):
    def fail(system, user, **params):
        raise LLMError("The LLM provider is not responding.")

    monkeypatch.setattr(translations, "complete", fail)
    client.put("/api/settings", json={"feedback_language": "Korean"})
    response = translate(client, add(client))
    assert response.status_code == 502 and "not responding" in response.json()["detail"]


def test_there_is_nothing_to_translate_into_english(client, youtube, model):
    client.put("/api/settings", json={"feedback_language": "English"})
    response = translate(client, add(client))
    assert response.status_code == 422 and "English" in response.json()["detail"]
    assert model.calls == []


def test_only_a_saved_video_is_translated(client, model):
    assert client.post("/api/videos/999/translations").status_code == 404


def test_deleting_a_video_deletes_its_translations(client, youtube, model):
    video = add(client)
    translate(client, video)
    client.delete(f"/api/videos/{video['id']}")
    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM line_translations").fetchone()[0] == 0
