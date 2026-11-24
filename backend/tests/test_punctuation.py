"""Automatic subtitles may come without punctuation; the model adds it, so they can be cut
into sentences, and a reply that changes the words is not used."""

import json

import pytest

from app import videos
from app.llm import LLMError
from app.videos import Snippet

# As YouTube's automatic subtitles sometimes are: no punctuation, few capitals.
AUTOMATIC = [
    Snippet(0.0, 4.0, "richard feynman was a leading"),
    Snippet(4.0, 4.0, "theoretical physicist who received a"),
    Snippet(8.0, 4.0, "nobel prize for his work let's start"),
]
PUNCTUATED = "Richard Feynman was a leading theoretical physicist who received a Nobel Prize for his work. Let's start!"


@pytest.fixture
def youtube(monkeypatch):
    """YouTube serves `youtube.speech` for every video, as automatic subtitles."""
    youtube.speech = AUTOMATIC
    monkeypatch.setattr(videos, "_transcript", lambda video_id: (youtube.speech, "en", True))
    monkeypatch.setattr(videos, "_about", lambda video_id: ("Feynman", "A channel"))
    return youtube


@pytest.fixture
def model(monkeypatch):
    """The model punctuates with `model.punctuated` and estimates every level at B1."""

    def complete(system, user, **params):
        if "punctuation" not in system:
            return json.dumps({"level": "B1"})
        complete.asked.append(user)
        return json.dumps({"text": complete.punctuated(user)})

    complete.punctuated, complete.asked = lambda text: PUNCTUATED, []
    monkeypatch.setattr(videos, "complete", complete)
    return complete


def add(client) -> list[dict]:
    response = client.post("/api/videos", json={"url": "https://youtu.be/aRlakaPVrEw"})
    assert response.status_code == 201, response.text
    return response.json()["lines"]


def test_automatic_subtitles_are_punctuated_and_cut_into_sentences(client, youtube, model):
    lines = add(client)
    assert [line["text"] for line in lines] == [
        "Richard Feynman was a leading theoretical physicist who received a Nobel Prize for his work.",
        "Let's start!",
    ]
    # Each word keeps the time of the subtitle line it was in.
    assert lines[0]["start"] == 0.0 and 8.0 < lines[1]["start"] < 12.0 and lines[1]["end"] == 12.0
    assert model.asked == ["richard feynman was a leading theoretical physicist who received a nobel prize for his work let's start"]


def test_words_the_model_changed_keep_their_own_spelling_with_its_punctuation(client, youtube, model):
    # The model "corrected" a word and added one, as it does with recognition errors.
    model.punctuated = lambda text: PUNCTUATED.replace("Feynman", "Feynmann").replace("work.", "work too.")
    lines = add(client)
    assert [line["text"] for line in lines] == [
        "Richard Feynman was a leading theoretical physicist who received a Nobel Prize for his work.",
        "Let's start!",
    ]


def test_a_reply_unlike_the_words_is_not_used(client, youtube, model):
    model.punctuated = lambda text: "Something else entirely."
    lines = add(client)
    assert [line["text"] for line in lines] == [snippet.text for snippet in AUTOMATIC]


def test_without_a_model_the_subtitles_are_kept_line_by_line(client, youtube, monkeypatch):
    def fail(system, user, **params):
        raise LLMError("No model is configured.")

    monkeypatch.setattr(videos, "complete", fail)
    assert [line["text"] for line in add(client)] == [snippet.text for snippet in AUTOMATIC]


def test_subtitles_with_punctuation_are_not_sent(client, youtube, model):
    youtube.speech = [Snippet(0.0, 3.0, "Stop, no entry."), Snippet(3.0, 3.0, "I stood still.")]
    assert [line["text"] for line in add(client)] == ["Stop, no entry.", "I stood still."]
    assert model.asked == []


def test_long_subtitles_are_punctuated_a_part_at_a_time(client, youtube, model):
    # Each part is cut at a subtitle line; each line here ends one sentence.
    youtube.speech = [Snippet(i * 3.0, 3.0, f"this is sentence number {i}") for i in range(3 * videos.PART // 5)]
    model.punctuated = lambda text: " ".join(
        f"{words[0].capitalize()} {' '.join(words[1:])}." for words in _fives(text.split())
    )
    lines = add(client)
    assert len(lines) == len(youtube.speech) and lines[1]["text"] == "This is sentence number 1."
    assert len(model.asked) > 1 and all(len(part.split()) <= videos.PART for part in model.asked)


def test_a_part_the_model_changed_is_kept_as_it_was_and_the_others_are_used(client, youtube, model):
    youtube.speech = [Snippet(i * 3.0, 3.0, f"this is sentence number {i}") for i in range(3 * videos.PART // 5)]

    def all_but_the_first(text):
        words = text.split()
        if words[-1] == str(videos.PART // 5 - 1):
            return "Something else entirely."
        return " ".join(f"{w[0].capitalize()} {' '.join(w[1:])}." for w in _fives(words))

    model.punctuated = all_but_the_first
    lines = add(client)
    first = videos.PART // 5
    # The part the model changed stays line by line, as subtitles without punctuation are kept.
    assert [line["text"] for line in lines[:first]] == [f"this is sentence number {i}" for i in range(first)]
    assert lines[first]["text"] == f"This is sentence number {first}."
    assert len(lines) == len(youtube.speech)


def _fives(words: list[str]) -> list[list[str]]:
    return [words[i : i + 5] for i in range(0, len(words), 5)]
