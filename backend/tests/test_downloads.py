"""Model downloads: one background download per model, with a state the UI can show."""

import threading

import pytest

from app import speech, transcribe
from app.downloads import Download


class FakeModel:
    """A model whose download is controlled by the test."""

    def __init__(self, total=1000):
        self.ready = False
        self.bytes = 0
        self.fetches = 0
        self.started = threading.Event()
        self.release = threading.Event()
        self.fail_with: Exception | None = None
        self.download = Download(
            "fake", "Fake model", is_ready=lambda: self.ready, fetch=self.fetch, measure=lambda: self.bytes, total=total
        )

    def fetch(self):
        self.fetches += 1
        self.started.set()
        assert self.release.wait(5)
        if self.fail_with:
            raise self.fail_with
        self.ready = True

    def finish(self):
        self.release.set()
        self.download.wait()


def test_a_model_that_is_not_there_is_missing():
    assert FakeModel().download.status() == {
        "id": "fake",
        "label": "Fake model",
        "state": "missing",
        "downloaded": 0,
        "total": 1000,
        "error": None,
    }


def test_download_runs_in_the_background_and_reports_progress():
    model = FakeModel()
    model.download.start()
    assert model.started.wait(5)
    model.bytes = 250
    status = model.download.status()
    assert (status["state"], status["downloaded"], status["total"]) == ("downloading", 250, 1000)

    model.finish()
    status = model.download.status()
    assert (status["state"], status["downloaded"]) == ("ready", 1000)


def test_the_files_are_not_checked_while_they_are_being_downloaded():
    # Checking a model that is being written can wait for the download to finish (the Whisper
    # check does), which would freeze the progress display.
    model = FakeModel()
    checks = []
    model.download._is_ready = lambda: checks.append(1) or model.ready
    model.download.start()
    assert model.started.wait(5)
    checks.clear()

    assert model.download.status()["state"] == "downloading"
    model.download.start()
    assert checks == []
    model.finish()


def test_starting_again_while_it_runs_does_not_download_twice():
    model = FakeModel()
    model.download.start()
    model.download.start()
    model.finish()
    model.download.start()
    assert model.fetches == 1


def test_a_failed_download_is_reported_and_can_be_retried():
    model = FakeModel()
    model.fail_with = OSError("no route to host")
    model.download.start()
    model.release.set()
    with pytest.raises(RuntimeError, match="no route to host"):
        model.download.wait()
    status = model.download.status()
    assert (status["state"], status["error"]) == ("error", "no route to host")

    model.fail_with = None
    model.download.wait()
    assert model.download.status()["state"] == "ready"
    assert model.fetches == 2


def test_waiting_for_a_ready_model_does_not_download():
    model = FakeModel()
    model.ready = True
    model.download.wait()
    assert model.fetches == 0


def test_progress_without_a_known_size_reports_what_was_downloaded():
    model = FakeModel(total=None)
    model.bytes = 300
    assert model.download.status()["total"] is None
    model.ready = True
    assert model.download.status()["downloaded"] == 300


# --- The app's two models ---------------------------------------------------------------


@pytest.fixture
def downloads(monkeypatch):
    """Stand-ins for both real downloads: each "downloads" by creating its model files."""
    calls = []

    def voice():
        calls.append("voice")
        speech.TTS_DIR.mkdir(parents=True, exist_ok=True)
        for name in speech.MODEL_FILES:
            (speech.TTS_DIR / name).write_bytes(b"model")

    def whisper():
        calls.append("speech-to-text")
        transcribe.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        (transcribe.MODEL_DIR / "model.bin").write_bytes(b"x" * 10)
        monkeypatch.setattr(transcribe, "_is_downloaded", lambda: True)

    monkeypatch.setattr(speech, "_download_models", voice)
    monkeypatch.setattr(transcribe, "_download", whisper)
    return calls


def states(client):
    return {model["id"]: model["state"] for model in client.get("/api/models").json()}


def test_both_models_are_missing_on_a_fresh_install(client):
    models = client.get("/api/models").json()
    assert [(m["id"], m["label"], m["state"]) for m in models] == [
        ("speech-to-text", "Speech recognition", "missing"),
        ("voice", "Partner's voice", "missing"),
    ]


def test_asking_for_the_downloads_starts_both(client, downloads):
    assert client.post("/api/models/download").status_code == 200
    transcribe.model_download.wait()
    speech.model_download.wait()
    assert sorted(downloads) == ["speech-to-text", "voice"]
    assert states(client) == {"speech-to-text": "ready", "voice": "ready"}

    # Asking again changes nothing.
    client.post("/api/models/download")
    assert len(downloads) == 2


def test_voice_progress_counts_the_partly_downloaded_file(client):
    speech.TTS_DIR.mkdir(parents=True)
    (speech.TTS_DIR / "kokoro-v1.0.onnx.part").write_bytes(b"x" * 1234)
    voice = next(m for m in client.get("/api/models").json() if m["id"] == "voice")
    assert (voice["downloaded"], voice["total"]) == (1234, speech.EXPECTED_BYTES)


def test_speech_model_progress_counts_what_is_on_disk(client):
    (transcribe.MODEL_DIR / "blobs").mkdir(parents=True)
    (transcribe.MODEL_DIR / "blobs" / "abc.incomplete").write_bytes(b"x" * 4321)
    model = next(m for m in client.get("/api/models").json() if m["id"] == "speech-to-text")
    assert model["downloaded"] == 4321


def test_transcribing_waits_for_the_model_download(downloads, monkeypatch):
    loaded = []
    monkeypatch.setattr(transcribe, "WhisperModel", lambda name, **options: loaded.append(name) or object())
    monkeypatch.setattr(transcribe, "_model", None)
    transcribe._get_model()
    # The download finished before the model was loaded.
    assert downloads == ["speech-to-text"]
    assert loaded == ["small.en"]


def test_a_failed_model_download_is_shown_to_the_ui(client, monkeypatch):
    def fail():
        raise OSError("disk full")

    monkeypatch.setattr(speech, "_download_models", fail)
    client.post("/api/models/download")
    with pytest.raises(RuntimeError):
        speech.model_download.wait()
    voice = next(m for m in client.get("/api/models").json() if m["id"] == "voice")
    assert (voice["state"], voice["error"]) == ("error", "disk full")
