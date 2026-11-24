"""Health check, seeded topics, transcription, and serving the built frontend."""

from app import main
from app.db import SEED_TOPICS, init_db
from app.paths import FRONTEND_DIST
from app.transcribe import Transcript


def build_frontend() -> None:
    (FRONTEND_DIST / "assets").mkdir(parents=True)
    (FRONTEND_DIST / "index.html").write_text("<title>index</title>")
    (FRONTEND_DIST / "assets" / "app.js").write_text("console.log('app')")


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_topics_are_seeded_once(client):
    init_db()
    topics = client.get("/api/topics").json()
    assert sorted(t["title"] for t in topics) == sorted(title for title, *_ in SEED_TOPICS)
    assert all(t["situation"] and t["opener"] for t in topics)


def test_transcript_comes_with_how_clearly_it_was_spoken(client, monkeypatch):
    monkeypatch.setattr(main, "transcribe", lambda audio: Transcript("I went to the beach.", 82, ["beach"], 110))
    response = client.post("/api/transcribe", files={"file": ("speech.webm", b"audio", "audio/webm")})
    assert response.json() == {
        "text": "I went to the beach.",
        "clarity": 82,
        "unclear_words": ["beach"],
        "words_per_minute": 110,
    }


def test_transcription_failure_is_reported(client, monkeypatch):
    def fail(audio):
        raise ValueError("not audio")

    monkeypatch.setattr(main, "transcribe", fail)
    response = client.post("/api/transcribe", files={"file": ("speech.webm", b"x", "audio/webm")})
    assert response.status_code == 502
    assert "not audio" in response.json()["detail"]


def test_frontend_is_not_served_before_it_is_built(client):
    assert client.get("/").status_code == 404


def test_built_files_are_served(client):
    build_frontend()
    assert client.get("/").text == "<title>index</title>"
    assert client.get("/assets/app.js").text == "console.log('app')"


def test_client_side_routes_get_the_index_page(client):
    build_frontend()
    assert client.get("/topics/2").text == "<title>index</title>"


def test_unknown_api_paths_are_not_answered_with_the_index_page(client):
    build_frontend()
    assert client.get("/api/nope").status_code == 404


def test_files_outside_the_build_folder_are_not_served(client):
    build_frontend()
    (FRONTEND_DIST.parent / "secret.txt").write_text("secret")
    response = client.get("/..%2Fsecret.txt")
    assert "secret" not in response.text
