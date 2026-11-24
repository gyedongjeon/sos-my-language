"""A saved video has a CEFR level: estimated when it is added, and changeable by the learner."""

import json

import pytest

from app import videos
from app.llm import LLMError
from app.videos import Snippet

SPEECH = [Snippet(i * 4.0, 4.0, f"This is sentence number {i} of the speech, and it goes on.") for i in range(60)]


@pytest.fixture
def youtube(monkeypatch):
    """YouTube serves the same subtitles for every video."""
    monkeypatch.setattr(videos, "_transcript", lambda video_id: (SPEECH, "en", False))
    monkeypatch.setattr(videos, "_about", lambda video_id: (f"Video {video_id}", "A channel"))


@pytest.fixture
def model(monkeypatch):
    """The model estimates every video at `model.level`."""

    def complete(system, user, **params):
        complete.calls.append((system, user))
        return json.dumps({"level": complete.level})

    complete.level, complete.calls = "B2", []
    monkeypatch.setattr(videos, "complete", complete)
    return complete


def add(client, video_id="UF8uR6Z6KLc") -> dict:
    response = client.post("/api/videos", json={"url": f"https://youtu.be/{video_id}"})
    assert response.status_code == 201, response.text
    return response.json()


def test_the_level_of_a_video_is_estimated_when_it_is_added(client, youtube, model):
    added = add(client)
    assert added["level"] == "B2"
    assert client.get("/api/videos").json()[0]["level"] == "B2"
    system, user = model.calls[0]
    assert "CEFR" in system
    # The model reads sentences from all through the video and how fast it is spoken, not all of it.
    assert "sentence number 0 " in user and "sentence number 59 " in user
    assert "words a minute" in user and len(user) < 4000


def test_a_video_is_saved_without_a_level_when_it_cannot_be_estimated(client, youtube, monkeypatch):
    def fail(system, user, **params):
        raise LLMError("No model is configured.")

    monkeypatch.setattr(videos, "complete", fail)
    added = add(client)
    assert added["level"] is None and len(added["lines"]) == 60


def test_an_estimate_that_is_not_a_level_is_ignored(client, youtube, model):
    model.level = "Intermediate"
    assert add(client)["level"] is None


def test_the_learner_can_set_and_clear_the_level(client, youtube, model):
    added = add(client)
    changed = client.put(f"/api/videos/{added['id']}/level", json={"level": "C1"})
    assert changed.status_code == 200 and changed.json()["level"] == "C1"
    assert client.get(f"/api/videos/{added['id']}").json()["level"] == "C1"
    assert client.put(f"/api/videos/{added['id']}/level", json={"level": None}).json()["level"] is None
    assert client.put(f"/api/videos/{added['id']}/level", json={"level": "D1"}).status_code == 422
    assert client.put("/api/videos/999/level", json={"level": "C1"}).status_code == 404


def test_the_level_can_be_estimated_again(client, youtube, model):
    added = add(client)
    client.put(f"/api/videos/{added['id']}/level", json={"level": None})
    model.level = "B1"
    again = client.post(f"/api/videos/{added['id']}/level")
    assert again.status_code == 200 and again.json()["level"] == "B1"
    assert client.post("/api/videos/999/level").status_code == 404


def test_an_estimate_asked_for_reports_its_failure_and_keeps_the_level(client, youtube, model, monkeypatch):
    added = add(client)

    def fail(system, user, **params):
        raise LLMError("The LLM provider is not responding.")

    monkeypatch.setattr(videos, "complete", fail)
    response = client.post(f"/api/videos/{added['id']}/level")
    assert response.status_code == 502 and "not responding" in response.json()["detail"]
    assert client.get(f"/api/videos/{added['id']}").json()["level"] == "B2"