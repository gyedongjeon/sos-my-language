"""Local text-to-speech; no API key, runs on this machine. A voice is spoken by Kokoro
(kokoro-onnx), Piper (piper-tts), or Supertonic (supertonic): each language being taught lists
its own voices."""

import hashlib
import io
import os
import shutil
import ssl
import threading
import urllib.request
import wave

import certifi
import numpy as np
from kokoro_onnx import Kokoro
from piper import PiperVoice
from supertonic import TTS as Supertonic

from .db import current_language, get_connection
from .downloads import Download
from .languages import Voice
from .paths import DATA_DIR

TTS_DIR = DATA_DIR / "tts"
CACHE_DIR = TTS_DIR / "cache"
# Kokoro's model and its voices (~350 MB in total): two files that hold every Kokoro voice.
KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
KOKORO_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
# Piper's voices, pinned to a release of the collection; each voice has two files of its own.
PIPER_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
# Supertonic 3 (~400 MB), pinned to a commit of the archive its makers keep it in since they
# stopped working on it. Its files keep their folders under TTS_DIR / SUPERTONIC_DIR; every voice
# needs the six shared ones and the style file named after it.
SUPERTONIC_URL = "https://huggingface.co/supertone-oss-archive/supertonic-3/resolve/aafc6e32416a594460b32413efc49d7fe4ce6d46"
SUPERTONIC_DIR = "supertonic-3"
SUPERTONIC_FILES = (
    "onnx/duration_predictor.onnx",
    "onnx/text_encoder.onnx",
    "onnx/vector_estimator.onnx",
    "onnx/vocoder.onnx",
    "onnx/tts.json",
    "onnx/unicode_indexer.json",
)

_kokoro: Kokoro | None = None
_piper: dict[str, PiperVoice] = {}
_supertonic: Supertonic | None = None
_lock = threading.Lock()


def voices() -> dict[str, Voice]:
    """The voices of the language being practised, by id, the default first."""
    return {voice.id: voice for voice in current_language().voices}


def _setting() -> str:
    """Where the chosen voice is kept: each language has its own."""
    return f"voice:{current_language().code}"


def current_voice() -> str:
    """The voice chosen on the Settings page for the language being practised, else TTS_VOICE,
    else the language's default."""
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (_setting(),)).fetchone()
    if row and row["value"] in voices():
        return row["value"]
    return os.environ.get("TTS_VOICE", "").strip() or current_language().default_voice


def _voice(voice: str) -> Voice:
    """A voice by its id. One that is not listed (set with TTS_VOICE) is taken to be spoken by
    the same program as the language's own voices; its size is not known."""
    listed = voices()
    return listed.get(voice) or Voice(voice, voice, current_language().voices[0].engine, 0)


def choose_voice(voice: str) -> None:
    """Keep a listed voice as the partner's, and start downloading it if it is not there."""
    if voice not in voices():
        raise ValueError(f"Unknown voice: {voice}")
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (_setting(), voice))
    model_download.start()


def _accent(voice: str) -> str:
    """The English a Kokoro voice speaks, from its prefix: British for "b", else American."""
    return "en-gb" if voice.startswith("b") else "en-us"


def model_files(voice: str) -> tuple[str, ...]:
    """The files a voice needs, as they are named on disk under TTS_DIR."""
    engine = _voice(voice).engine
    if engine == "kokoro":
        return KOKORO_FILES
    if engine == "supertonic":
        return tuple(f"{SUPERTONIC_DIR}/{name}" for name in (*SUPERTONIC_FILES, f"voice_styles/{voice}.json"))
    return f"{voice}.onnx", f"{voice}.onnx.json"


def _file_url(voice: str, name: str) -> str:
    """Where a file of a voice is downloaded from. Piper's collection keeps "de_DE-thorsten-high"
    under de/de_DE/thorsten/high/."""
    engine = _voice(voice).engine
    if engine == "kokoro":
        return f"{KOKORO_URL}/{name}"
    if engine == "supertonic":
        return f"{SUPERTONIC_URL}/{name.removeprefix(SUPERTONIC_DIR + '/')}"
    locale, speaker, quality = voice.split("-", 2)
    return f"{PIPER_URL}/{locale.split('_')[0]}/{locale}/{speaker}/{quality}/{name}"


def is_downloaded(voice: str) -> bool:
    return all((TTS_DIR / name).exists() for name in model_files(voice))


def _is_downloaded() -> bool:
    return is_downloaded(current_voice())


def _downloaded_bytes() -> int:
    """Bytes of the voice's files on disk, counting a file that is still being downloaded."""
    names = [candidate for name in model_files(current_voice()) for candidate in (name, f"{name}.part")]
    return sum((TTS_DIR / name).stat().st_size for name in names if (TTS_DIR / name).exists())


def _download_models() -> None:
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    voice = current_voice()
    for name in model_files(voice):
        path = TTS_DIR / name
        if not path.exists():
            # Download to a temporary name so an interrupted download is not reused.
            partial = path.with_name(path.name + ".part")
            partial.parent.mkdir(parents=True, exist_ok=True)
            # certifi's CA bundle: some Python installs ship without root certificates.
            tls = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(_file_url(voice, name), context=tls) as response:
                with partial.open("wb") as out:
                    shutil.copyfileobj(response, out)
            partial.rename(path)


# The lambdas look the functions up when called, so tests can replace them. The voice, and so
# what there is to download, changes with the language being practised and the voice chosen.
model_download = Download(
    "voice",
    "Partner's voice",
    is_ready=lambda: _is_downloaded(),
    fetch=lambda: _download_models(),
    measure=lambda: _downloaded_bytes(),
    size=lambda: _voice(current_voice()).size or None,
)


def _require_files() -> None:
    """Raises while the voice's files are still being downloaded."""
    if not _is_downloaded():
        # The download takes minutes, so it runs in the background instead of holding the
        # request; the caller reports the failure and the UI uses the browser voice meanwhile.
        model_download.start()
        raise RuntimeError("the voice model is still downloading")


def _get_kokoro() -> Kokoro:
    """Return the loaded Kokoro model, which speaks with every Kokoro voice."""
    global _kokoro
    if _kokoro is None:
        _require_files()
        _kokoro = Kokoro(str(TTS_DIR / KOKORO_FILES[0]), str(TTS_DIR / KOKORO_FILES[1]))
    return _kokoro


def _get_piper(voice: str) -> PiperVoice:
    """Return a loaded Piper voice."""
    if voice not in _piper:
        _require_files()
        model, config = model_files(voice)
        _piper[voice] = PiperVoice.load(TTS_DIR / model, config_path=TTS_DIR / config)
    return _piper[voice]


def _get_supertonic() -> Supertonic:
    """Return the loaded Supertonic model, which speaks with every Supertonic voice."""
    global _supertonic
    if _supertonic is None:
        _require_files()
        _supertonic = Supertonic(model="supertonic-3", model_dir=TTS_DIR / SUPERTONIC_DIR, auto_download=False)
    return _supertonic


def _write(samples: np.ndarray, sample_rate: int, wav: wave.Wave_write) -> None:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)
    wav.writeframes((np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16).tobytes())


def _render(voice: str, text: str, wav: wave.Wave_write) -> None:
    """Write the text spoken by a voice into an open WAV file."""
    if _voice(voice).engine == "kokoro":
        samples, sample_rate = _get_kokoro().create(text, voice=voice, speed=1.0, lang=_accent(voice))
        _write(samples, sample_rate, wav)
    elif _voice(voice).engine == "supertonic":
        model = _get_supertonic()
        # Its style files are named like the voices; the language is the one being practised.
        samples, _ = model.synthesize(text, voice_style=model.get_voice_style(voice), lang=current_language().code)
        _write(samples[0], model.sample_rate, wav)
    else:
        _get_piper(voice).synthesize_wav(text, wav)


def synthesize(text: str) -> bytes:
    """Return WAV audio of the text spoken in the language being practised."""
    voice = current_voice()
    # Lines repeat across sessions, so keep each rendered clip on disk.
    key = hashlib.sha256(f"{voice}\n{text}".encode()).hexdigest()
    cached = CACHE_DIR / f"{key}.wav"
    if cached.exists():
        return cached.read_bytes()

    # Loaded first: a WAV file closed before anything was written to it raises.
    _require_files()
    buffer = io.BytesIO()
    # One synthesis at a time: a model is loaded once and shared.
    with _lock, wave.open(buffer, "wb") as wav:
        _render(voice, text, wav)
    audio = buffer.getvalue()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(audio)
    return audio
