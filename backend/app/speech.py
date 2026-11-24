"""Local text-to-speech with Kokoro (kokoro-onnx); no API key, runs on this machine."""

import hashlib
import io
import os
import shutil
import ssl
import threading
import urllib.request
import wave

from dataclasses import dataclass

import certifi
import numpy as np
from kokoro_onnx import Kokoro

from .db import get_connection
from .downloads import Download
from .paths import DATA_DIR

TTS_DIR = DATA_DIR / "tts"
CACHE_DIR = TTS_DIR / "cache"
# Model files (~350 MB in total), downloaded on first use.
RELEASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")


@dataclass(frozen=True)
class Voice:
    id: str
    label: str


# Kokoro's English voices that sound natural, best first within each accent. All of them are in
# the one voices file, so choosing one downloads nothing. Another Kokoro voice can still be set
# with TTS_VOICE; its prefix gives the accent: "a" American, "b" British.
VOICES = {
    voice.id: voice
    for voice in (
        Voice("af_heart", "Heart · American · female"),
        Voice("af_bella", "Bella · American · female"),
        Voice("af_nicole", "Nicole · American · female · soft"),
        Voice("af_sarah", "Sarah · American · female"),
        Voice("am_michael", "Michael · American · male"),
        Voice("am_fenrir", "Fenrir · American · male"),
        Voice("am_puck", "Puck · American · male"),
        Voice("bf_emma", "Emma · British · female"),
        Voice("bf_isabella", "Isabella · British · female"),
        Voice("bm_george", "George · British · male"),
        Voice("bm_fable", "Fable · British · male"),
    )
}
DEFAULT_VOICE = "af_heart"

# Size of the two files of the pinned release, for showing download progress.
EXPECTED_BYTES = 325_532_387 + 28_214_398

_kokoro: Kokoro | None = None
_lock = threading.Lock()


def current_voice() -> str:
    """The voice chosen on the Settings page, else TTS_VOICE, else the default."""
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'voice'").fetchone()
    if row and row["value"] in VOICES:
        return row["value"]
    return os.environ.get("TTS_VOICE", "").strip() or DEFAULT_VOICE


def choose_voice(voice: str) -> None:
    """Keep a listed voice as the partner's."""
    if voice not in VOICES:
        raise ValueError(f"Unknown voice: {voice}")
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('voice', ?)", (voice,))


def _accent(voice: str) -> str:
    """The English the voice speaks, from its prefix: British for "b", else American."""
    return "en-gb" if voice.startswith("b") else "en-us"


def _is_downloaded() -> bool:
    return all((TTS_DIR / name).exists() for name in MODEL_FILES)


def _downloaded_bytes() -> int:
    """Bytes of the model files on disk, counting a file that is still being downloaded."""
    names = [candidate for name in MODEL_FILES for candidate in (name, f"{name}.part")]
    return sum((TTS_DIR / name).stat().st_size for name in names if (TTS_DIR / name).exists())


def _download_models() -> None:
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        path = TTS_DIR / name
        if not path.exists():
            # Download to a temporary name so an interrupted download is not reused.
            partial = path.with_suffix(path.suffix + ".part")
            # certifi's CA bundle: some Python installs ship without root certificates.
            tls = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(f"{RELEASE_URL}/{name}", context=tls) as response:
                with partial.open("wb") as out:
                    shutil.copyfileobj(response, out)
            partial.rename(path)


# The lambdas look the functions up when called, so tests can replace them.
model_download = Download(
    "voice",
    "Partner's voice",
    is_ready=lambda: _is_downloaded(),
    fetch=lambda: _download_models(),
    measure=lambda: _downloaded_bytes(),
    total=EXPECTED_BYTES,
)


def _get_kokoro() -> Kokoro:
    """Return the loaded voice model. Raises while its files are still being downloaded."""
    global _kokoro
    if _kokoro is None:
        if not _is_downloaded():
            # The download takes minutes, so it runs in the background instead of holding the
            # request; the caller reports the failure and the UI uses the browser voice meanwhile.
            model_download.start()
            raise RuntimeError("the voice model is still downloading")
        _kokoro = Kokoro(str(TTS_DIR / MODEL_FILES[0]), str(TTS_DIR / MODEL_FILES[1]))
    return _kokoro


def synthesize(text: str) -> bytes:
    """Return WAV audio of the text spoken in English."""
    voice = current_voice()
    # Questions repeat across sessions, so keep each rendered clip on disk.
    key = hashlib.sha256(f"{voice}\n{text}".encode()).hexdigest()
    cached = CACHE_DIR / f"{key}.wav"
    if cached.exists():
        return cached.read_bytes()

    # One synthesis at a time: the model is loaded once and shared.
    with _lock:
        samples, sample_rate = _get_kokoro().create(text, voice=voice, speed=1.0, lang=_accent(voice))

    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    audio = buffer.getvalue()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(audio)
    return audio
