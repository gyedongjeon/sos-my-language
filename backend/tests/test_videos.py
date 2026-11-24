"""Videos to study with: a YouTube link is saved with its subtitles, cut into sentences."""

import pytest

from app import videos
from app.videos import Snippet, sentences, video_id_of

SPEECH = [
    Snippet(7.0, 3.0, "This program is brought to you\nby Stanford University."),
    Snippet(10.0, 4.0, "Thank you. I am honored to be with you today"),
    Snippet(14.0, 3.0, "at your commencement. [Applause]"),
    Snippet(20.0, 4.0, "Truth be told, I never graduated from college."),
]


@pytest.fixture
def youtube(monkeypatch):
    """YouTube has the subtitles `youtube.tracks[video id]` and the titles `youtube.titles`."""

    def transcript(video_id):
        transcript.asked.append(video_id)
        if video_id not in transcript.tracks:
            raise videos.NoSubtitles("This video has no English subtitles.")
        return transcript.tracks[video_id], "en", False

    transcript.tracks, transcript.asked = {"UF8uR6Z6KLc": SPEECH}, []
    transcript.titles = {"UF8uR6Z6KLc": ("Commencement address", "Stanford")}
    monkeypatch.setattr(videos, "_transcript", transcript)
    monkeypatch.setattr(videos, "_about", lambda video_id: transcript.titles.get(video_id, ("", "")))
    return transcript


def add(client, url="https://www.youtube.com/watch?v=UF8uR6Z6KLc") -> dict:
    response = client.post("/api/videos", json={"url": url})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=UF8uR6Z6KLc",
        "https://youtube.com/watch?feature=shared&v=UF8uR6Z6KLc&t=42s",
        "https://m.youtube.com/watch?v=UF8uR6Z6KLc",
        "https://youtu.be/UF8uR6Z6KLc?si=abc",
        "https://www.youtube.com/embed/UF8uR6Z6KLc",
        "https://www.youtube.com/shorts/UF8uR6Z6KLc",
        "https://www.youtube.com/live/UF8uR6Z6KLc?feature=share",
        "  https://www.youtube.com/watch?v=UF8uR6Z6KLc  ",
    ],
)
def test_the_video_is_found_in_every_kind_of_youtube_link(url):
    assert video_id_of(url) == "UF8uR6Z6KLc"


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/123456",
        "https://www.youtube.com/",
        "https://www.youtube.com/watch?v=short",
        "https://notyoutube.com/watch?v=UF8uR6Z6KLc",
        "UF8uR6Z6KLc",
        "",
    ],
)
def test_other_links_are_not_videos(url):
    assert video_id_of(url) is None


def test_subtitle_lines_are_joined_and_cut_into_sentences():
    lines = sentences(SPEECH)
    assert [line.text for line in lines] == [
        "This program is brought to you by Stanford University.",
        "Thank you.",
        "I am honored to be with you today at your commencement.",
        "Truth be told, I never graduated from college.",
    ]
    assert lines[0].start == 7.0 and lines[0].end == 10.0
    # A sentence that starts inside a subtitle line starts part of the way through it.
    assert 10.0 < lines[2].start < 14.0
    assert lines[1].end == lines[2].start
    # The pause before the next subtitle is not part of the sentence.
    assert lines[2].end == 17.0
    assert lines[3].start == 20.0 and lines[3].end == 24.0


def test_overlapping_subtitle_lines_do_not_make_sentences_overlap():
    rolling = [Snippet(0.0, 5.0, "I never graduated."), Snippet(2.0, 5.0, "This is the closest.")]
    first, second = sentences(rolling)
    assert first.end == 2.0 and second.start == 2.0


def test_subtitles_without_punctuation_are_kept_line_by_line():
    spoken = [Snippet(i * 3.0, 3.0, "so today i want to talk about something that matters") for i in range(8)]
    lines = sentences(spoken)
    assert len(lines) == 8
    assert lines[1].text == "so today i want to talk about something that matters"
    assert (lines[1].start, lines[1].end) == (3.0, 6.0)


def test_noise_in_subtitles_is_left_out():
    noisy = [Snippet(0.0, 2.0, "[Music]"), Snippet(2.0, 3.0, "&gt;&gt; Hello &amp; welcome. ♪")]
    assert [line.text for line in sentences(noisy)] == ["Hello & welcome."]


def test_a_very_long_sentence_is_cut_at_a_comma():
    endless = [Snippet(i * 4.0, 4.0, "and then we went on and on, " * 2) for i in range(12)] + [Snippet(48.0, 2.0, "The end.")]
    lines = sentences(endless)
    assert len(lines) > 2
    assert all(len(line.text.split()) <= 60 for line in lines)


def test_a_video_is_saved_with_its_title_and_sentences(client, youtube):
    added = add(client)
    assert added["video_id"] == "UF8uR6Z6KLc"
    assert (added["title"], added["channel"]) == ("Commencement address", "Stanford")
    assert added["language"] == "en" and added["generated"] is False
    assert added["added_at"].endswith("Z")
    assert [line["text"] for line in added["lines"]][1] == "Thank you."
    assert all(line["end"] > line["start"] for line in added["lines"])
    assert client.get(f"/api/videos/{added['id']}").json() == added


def test_videos_are_listed_newest_first_with_their_size(client, youtube):
    youtube.tracks["dQw4w9WgXcQ"] = [Snippet(0.0, 2.0, "Hello there.")]
    first, second = add(client), add(client, "https://youtu.be/dQw4w9WgXcQ")
    listed = client.get("/api/videos").json()
    assert [(v["id"], v["sentences"]) for v in listed] == [(second["id"], 1), (first["id"], 4)]
    assert "lines" not in listed[0]
    # No title could be found for the second one.
    assert listed[0]["title"] == "YouTube video dQw4w9WgXcQ"


def test_adding_a_video_again_opens_the_saved_one(client, youtube):
    first = add(client)
    again = client.post("/api/videos", json={"url": "https://youtu.be/UF8uR6Z6KLc"})
    assert again.status_code == 200 and again.json() == first
    assert youtube.asked == ["UF8uR6Z6KLc"]
    assert len(client.get("/api/videos").json()) == 1


def test_a_link_that_is_not_a_youtube_video_is_refused(client, youtube):
    response = client.post("/api/videos", json={"url": "https://vimeo.com/123456"})
    assert response.status_code == 422 and "YouTube" in response.json()["detail"]
    assert youtube.asked == []


def test_a_video_without_subtitles_is_reported_and_not_saved(client, youtube):
    response = client.post("/api/videos", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert response.status_code == 422 and "no English subtitles" in response.json()["detail"]
    youtube.tracks["dQw4w9WgXcQ"] = [Snippet(0.0, 2.0, "[Music]")]
    assert client.post("/api/videos", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).status_code == 422
    assert client.get("/api/videos").json() == []


def test_a_video_can_be_deleted_with_its_sentences(client, youtube):
    added = add(client)
    assert client.delete(f"/api/videos/{added['id']}").status_code == 204
    assert client.get(f"/api/videos/{added['id']}").status_code == 404
    assert client.delete(f"/api/videos/{added['id']}").status_code == 404
    from app.db import get_connection

    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM video_lines").fetchone()[0] == 0


def test_stage_directions_are_left_out():
    talk = [Snippet(0.0, 4.0, "So, you know -- (Laughter) you get started."), Snippet(4.0, 2.0, "(Applause) Thank you (all of you).")]
    assert [line.text for line in sentences(talk)] == ["So, you know -- you get started.", "Thank you (all of you)."]


def test_a_long_silence_ends_a_sentence_that_has_no_full_stop():
    intro = [Snippet(10.0, 4.0, "Please visit us at stanford.edu"), Snippet(22.0, 3.0, "Thank you. I am honored.")]
    lines = sentences(intro)
    assert [line.text for line in lines] == ["Please visit us at stanford.edu", "Thank you.", "I am honored."]
    assert lines[0].end == 14.0 and lines[1].start == 22.0
