"""A sentence not said right after a video is kept with the corrections, to be practised again,
and every try is logged, so the words often not heard can be looked at later."""

import pytest

from app import videos
from app.db import get_connection
from app.videos import Snippet

SPEECH = [
    Snippet(0.0, 4.0, "This makes you realize where you still have gaps."),
    Snippet(4.0, 4.0, "Write and speak at the same time."),
]


@pytest.fixture
def video(client, monkeypatch):
    monkeypatch.setattr(videos, "_transcript", lambda video_id: (SPEECH, "en", False))
    monkeypatch.setattr(videos, "_about", lambda video_id: ("How to learn", "A channel"))
    return client.post("/api/videos", json={"url": "https://youtu.be/UF8uR6Z6KLc"}).json()


def shadow(client, line: dict, said: str) -> dict:
    response = client.post(f"/api/video-lines/{line['id']}/attempts", json={"text": said})
    assert response.status_code == 200, response.text
    return response.json()


def corrections(client) -> list[dict]:
    return client.get("/api/corrections").json()


def test_a_sentence_not_said_right_is_listed_with_the_corrections(client, video):
    line = video["lines"][0]
    shadow(client, line, "This makes you realize where you still have guess")
    [mistake] = corrections(client)
    assert mistake["id"].startswith("s")
    assert (mistake["original"], mistake["improved"]) == (
        "This makes you realize where you still have guess",
        "This makes you realize where you still have gaps.",
    )
    # The word that was not heard, with what was heard in its place.
    assert mistake["explanation"] == "Not heard: “gaps” (heard “guess”)."
    # It names the video and the sentence it comes from.
    assert mistake["title"] == "How to learn"
    assert (mistake["video"], mistake["position"]) == (video["id"], 0)
    assert mistake["conversation_id"] is None and mistake["pattern_id"] is None
    assert mistake["practiced"] == 0


def test_words_left_out_are_named_without_anything_heard_in_their_place(client, video):
    shadow(client, video["lines"][1], "Write and speak at the time")
    assert corrections(client)[0]["explanation"] == "Not heard: “same”."


def test_a_sentence_said_right_is_not_listed(client, video):
    shadow(client, video["lines"][1], "write and speak at the same time")
    assert corrections(client) == []


def test_trying_the_same_sentence_again_keeps_one_entry_with_the_last_try(client, video):
    line = video["lines"][1]
    shadow(client, line, "Write and speak at the time")
    shadow(client, line, "Right and speak at the same time")
    [mistake] = corrections(client)
    assert mistake["original"] == "Right and speak at the same time"
    assert mistake["explanation"] == "Not heard: “Write” (heard “right”)."


def test_a_shadowing_mistake_is_practised_like_any_correction(client, video):
    shadow(client, video["lines"][1], "Write and speak at the time")
    mistake_id = corrections(client)[0]["id"]
    tried = client.post(f"/api/corrections/{mistake_id}/attempts", json={"text": "Write and speak at the same time."})
    assert tried.json()["matched"] is True
    assert corrections(client)[0]["practiced"] == 1
    assert client.delete(f"/api/corrections/{mistake_id}").status_code == 204
    assert corrections(client) == []


def test_a_mistake_outlives_its_video_without_a_link_to_it(client, video):
    shadow(client, video["lines"][1], "Write and speak at the time")
    assert client.delete(f"/api/videos/{video['id']}").status_code == 204
    [mistake] = corrections(client)
    assert (mistake["improved"], mistake["title"]) == ("Write and speak at the same time.", "How to learn")
    assert mistake["video"] is None and mistake["position"] is None
    tried = client.post(f"/api/corrections/{mistake['id']}/attempts", json={"text": "Write and speak at the same time"})
    assert tried.json()["matched"] is True


def test_every_try_is_logged_and_the_log_outlives_the_video(client, video):
    line = video["lines"][1]
    shadow(client, line, "Write and speak at the time")
    shadow(client, line, "Write and speak at the same time")
    client.delete(f"/api/videos/{video['id']}")
    with get_connection() as conn:
        logged = conn.execute("SELECT sentence, said, accuracy FROM shadowing_attempts ORDER BY id").fetchall()
    assert [tuple(row) for row in logged] == [
        ("Write and speak at the same time.", "Write and speak at the time", 86),
        ("Write and speak at the same time.", "Write and speak at the same time", 100),
    ]
