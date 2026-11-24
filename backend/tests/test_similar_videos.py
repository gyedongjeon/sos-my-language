"""Videos like a saved one are suggested: the model thinks of searches, YouTube is searched, and
only the videos found with English subtitles at a level near the saved one's are kept."""

import json

import pytest

from app import similar_videos, videos
from app.llm import LLMError
from app.similar_videos import Found
from app.videos import Snippet

SAVED = "UF8uR6Z6KLc"


def speech(video_id: str) -> list[Snippet]:
    return [Snippet(i * 4.0, 4.0, f"Sentence {i} of {video_id} goes on.") for i in range(30)]


@pytest.fixture
def youtube(monkeypatch):
    """YouTube finds `youtube.results[query]`; the videos in `youtube.levels` have subtitles,
    which are estimated at that level."""

    def transcript(video_id):
        if video_id not in youtube.levels:
            raise videos.NoSubtitles("This video has no English subtitles.")
        return speech(video_id), "en", False

    def estimate(lines):
        return youtube.levels[lines[0].text.split()[3]]

    def search(query, count):
        youtube.searched.append(query)
        if youtube.down:
            raise similar_videos.SearchFailed("YouTube could not be searched: offline")
        return youtube.results.get(query, [])

    youtube.levels, youtube.results, youtube.searched, youtube.down = {SAVED: "B2"}, {}, [], False
    monkeypatch.setattr(videos, "_transcript", transcript)
    monkeypatch.setattr(videos, "_about", lambda video_id: (f"Video {video_id}", "A channel"))
    monkeypatch.setattr(videos, "_estimate", estimate)
    monkeypatch.setattr(similar_videos, "_search", search)
    return youtube


@pytest.fixture
def model(monkeypatch):
    """The model thinks of the searches `model.queries`."""

    def complete(system, user, **params):
        model.asked.append((system, user))
        return json.dumps({"queries": model.queries})

    model.queries, model.asked = ["habits talk", "motivation speech"], []
    monkeypatch.setattr(similar_videos, "complete", complete)
    return model


def found(video_id: str, duration: float | None = 600) -> Found:
    return Found(video_id=video_id, title=f"Found {video_id}", channel="Somebody", duration=duration)


def saved(client, video_id=SAVED) -> dict:
    response = client.post("/api/videos", json={"url": f"https://youtu.be/{video_id}"})
    assert response.status_code == 201, response.text
    return response.json()


def suggest(client, video: int):
    return client.post(f"/api/videos/{video}/suggestions")


def test_videos_found_by_the_models_searches_are_suggested_nearest_level_first(client, youtube, model):
    video = saved(client)
    youtube.levels.update({"aaaaaaaaaa1": "C1", "aaaaaaaaaa2": "B2", "aaaaaaaaaa3": "A1"})
    youtube.results = {
        "habits talk": [found("aaaaaaaaaa1"), found("aaaaaaaaaa3")],
        "motivation speech": [found("aaaaaaaaaa2"), found("nosubtitles")],
    }
    response = suggest(client, video["id"])
    assert response.status_code == 200, response.text
    assert [(s["video_id"], s["level"]) for s in response.json()] == [("aaaaaaaaaa2", "B2"), ("aaaaaaaaaa1", "C1")]
    assert response.json()[0] == {
        "video_id": "aaaaaaaaaa2",
        "title": "Found aaaaaaaaaa2",
        "channel": "Somebody",
        "duration": 600,
        "level": "B2",
        "generated": False,
    }
    assert youtube.searched == ["habits talk", "motivation speech"]
    system, user = model.asked[0]
    # The model reads what the video is and some of what is said in it.
    assert f"Video {SAVED}" in user and f"of {SAVED}" in user


def test_saved_videos_and_ones_found_twice_are_left_out(client, youtube, model):
    video = saved(client)
    youtube.levels.update({"aaaaaaaaaa1": "B2", "aaaaaaaaaa2": "B2"})
    saved(client, "aaaaaaaaaa2")
    youtube.results = {
        "habits talk": [found(SAVED), found("aaaaaaaaaa1")],
        "motivation speech": [found("aaaaaaaaaa1"), found("aaaaaaaaaa2")],
    }
    assert [s["video_id"] for s in suggest(client, video["id"]).json()] == ["aaaaaaaaaa1"]


def test_shorts_and_very_long_videos_are_left_out(client, youtube, model):
    video = saved(client)
    youtube.levels.update({"aaaaaaaaaa1": "B2", "aaaaaaaaaa2": "B2", "aaaaaaaaaa3": "B2"})
    youtube.results = {"habits talk": [found("aaaaaaaaaa1", 45), found("aaaaaaaaaa2", 4 * 3600), found("aaaaaaaaaa3", None)]}
    assert [s["video_id"] for s in suggest(client, video["id"]).json()] == ["aaaaaaaaaa3"]


def test_only_a_few_videos_are_checked(client, youtube, model):
    video = saved(client)
    many = [f"aaaaaaaaa{i:02d}" for i in range(20)]
    youtube.levels.update(dict.fromkeys(many, "B2"))
    youtube.results = {"habits talk": [found(video_id) for video_id in many]}
    assert len(suggest(client, video["id"]).json()) == similar_videos.MAX_CHECKED


def test_every_level_is_kept_for_a_video_without_one(client, youtube, model):
    video = saved(client)
    client.put(f"/api/videos/{video['id']}/level", json={"level": None})
    youtube.levels.update({"aaaaaaaaaa1": "A1", "aaaaaaaaaa2": "C2"})
    youtube.results = {"habits talk": [found("aaaaaaaaaa1"), found("aaaaaaaaaa2")]}
    assert [s["video_id"] for s in suggest(client, video["id"]).json()] == ["aaaaaaaaaa1", "aaaaaaaaaa2"]


def test_a_video_whose_level_cannot_be_estimated_is_left_out(client, youtube, model):
    video = saved(client)
    youtube.levels["aaaaaaaaaa1"] = None
    youtube.results = {"habits talk": [found("aaaaaaaaaa1")]}
    assert suggest(client, video["id"]).json() == []


def test_without_a_model_nothing_is_suggested(client, youtube, monkeypatch):
    video = saved(client)

    def fail(system, user, **params):
        raise LLMError("No model is configured.")

    monkeypatch.setattr(similar_videos, "complete", fail)
    response = suggest(client, video["id"])
    assert response.status_code == 502
    assert "No model is configured." in response.json()["detail"]
    assert youtube.searched == []


def test_a_failed_search_is_reported(client, youtube, model):
    video = saved(client)
    youtube.down = True
    response = suggest(client, video["id"])
    assert response.status_code == 502
    assert "YouTube could not be searched" in response.json()["detail"]


def test_an_unknown_video_has_no_suggestions(client, youtube, model):
    assert suggest(client, 999).status_code == 404
