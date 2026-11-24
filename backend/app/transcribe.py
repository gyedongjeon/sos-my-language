"""Local speech-to-text with Whisper (faster-whisper); no API key, audio stays on this machine."""

import os
import string
import threading
from dataclasses import dataclass, field
from typing import BinaryIO

from faster_whisper import WhisperModel
from faster_whisper.utils import _MODELS, download_model
from huggingface_hub import HfApi

from .db import current_language
from .downloads import Download
from .paths import DATA_DIR

# Kept with the app's other files instead of Hugging Face's shared cache in the home folder,
# so that removing the data folder removes the model too.
MODEL_DIR = DATA_DIR / "whisper"
# Words Whisper recognized with less confidence than this are reported as unclear.
UNCLEAR_BELOW = 0.5
MAX_UNCLEAR_WORDS = 8

# The loaded model and its name: another language may need another model.
_model: WhisperModel | None = None
_loaded: str | None = None
_lock = threading.Lock()


@dataclass
class Transcript:
    text: str
    # How confidently Whisper recognized the words, 0-100. This is a proxy for how clearly
    # they were pronounced, not a phonetic assessment. None when nothing was said.
    clarity: int | None = None
    unclear_words: list[str] = field(default_factory=list)
    words_per_minute: int | None = None


def _model_name() -> str:
    """The model that hears the language being practised, downloaded from Hugging Face on first
    use (~480 MB for the small ones): WHISPER_MODEL, else the language's own. An English-only
    model (".en") from the environment is used for English alone."""
    language = current_language()
    chosen = os.environ.get("WHISPER_MODEL", "").strip()
    if chosen.endswith(".en") and language.code != "en":
        chosen = ""
    return chosen or language.whisper_model


def _is_downloaded() -> bool:
    try:
        # Looks only at what is on disk; raises when a file of the model is missing.
        download_model(_model_name(), cache_dir=str(MODEL_DIR), local_files_only=True)
        return True
    except Exception:
        return False


def _downloaded_bytes() -> int:
    """Bytes on disk of the model that hears the language being practised, counting files that
    are still being downloaded. The models of the other languages are in the same folder and
    are left out."""
    name = _model_name()
    folder = MODEL_DIR / f"models--{_MODELS.get(name, name).replace('/', '--')}"
    # A model's files are links to where Hugging Face keeps them, in the model's own folder or
    # in one shared by all models; each file is followed to where it is and counted once.
    files = {os.path.realpath(os.path.join(at, file)) for at, _, names in os.walk(folder) for file in names}
    # A file on its way is not linked to yet. Only one model is downloaded at a time.
    files |= {
        os.path.realpath(os.path.join(at, file))
        for at, _, names in os.walk(MODEL_DIR)
        for file in names
        if file.endswith(".incomplete")
    }
    return sum(os.path.getsize(file) for file in files if os.path.isfile(file))


def _download() -> None:
    name = _model_name()
    try:
        # Only for showing progress, so a failure here does not stop the download.
        files = HfApi().model_info(_MODELS.get(name, name), files_metadata=True).siblings or []
        model_download.total = sum(file.size or 0 for file in files) or None
    except Exception:
        model_download.total = None
    download_model(name, cache_dir=str(MODEL_DIR))


# The lambdas look the functions up when called, so tests can replace them.
model_download = Download(
    "speech-to-text",
    "Speech recognition",
    is_ready=lambda: _is_downloaded(),
    fetch=lambda: _download(),
    measure=lambda: _downloaded_bytes(),
)


def _get_model() -> WhisperModel:
    global _model, _loaded
    # Downloading can take minutes, so it happens outside the lock that guards the model.
    model_download.wait()
    name = _model_name()
    with _lock:
        if _model is None or _loaded != name:
            # One model in memory at a time: the one of the language practised before is let go.
            _model = WhisperModel(name, device="cpu", compute_type="int8", download_root=str(MODEL_DIR))
            _loaded = name
        return _model


def transcribe(audio: BinaryIO) -> Transcript:
    """Transcribe an audio file and measure how clearly it was spoken."""
    language = current_language().code
    model = _get_model()
    # The model is not safe for concurrent use; requests are rare, so run one at a time.
    with _lock:
        # vad_filter drops silence, which otherwise makes Whisper invent text.
        segments, _ = model.transcribe(
            audio, language=language, vad_filter=True, word_timestamps=True
        )
        segments = list(segments)

    text = " ".join(segment.text.strip() for segment in segments).strip()
    words = [word for segment in segments for word in (segment.words or [])]
    if not words:
        return Transcript(text=text)

    clarity = round(100 * sum(w.probability for w in words) / len(words))
    unclear: list[str] = []
    for w in words:
        cleaned = w.word.strip().strip(string.punctuation)
        if w.probability < UNCLEAR_BELOW and cleaned and cleaned.lower() not in map(str.lower, unclear):
            unclear.append(cleaned)

    speaking_seconds = words[-1].end - words[0].start
    wpm = round(len(words) / speaking_seconds * 60) if speaking_seconds >= 5 else None
    return Transcript(text, clarity, unclear[:MAX_UNCLEAR_WORDS], wpm)
