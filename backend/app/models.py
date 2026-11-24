"""The models the app downloads on first use, their download progress, and the partner's voice."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import speech, transcribe
from .db import learning_language

router = APIRouter(prefix="/api")


class ModelStatus(BaseModel):
    id: str
    label: str
    state: Literal["missing", "downloading", "ready", "error"]
    # Bytes on disk so far, and the expected size when it is known.
    downloaded: int
    total: int | None
    error: str | None


def _statuses() -> list[ModelStatus]:
    return [ModelStatus(**download.status()) for download in (transcribe.model_download, speech.model_download)]


@router.get("/models", response_model=list[ModelStatus])
def list_models() -> list[ModelStatus]:
    return _statuses()


@router.post("/models/download", response_model=list[ModelStatus])
def download_models() -> list[ModelStatus]:
    """Start downloading whatever is missing. The page calls this when it opens, so the models
    are usually there before the first recording needs them: the speech recognition and the
    voice of the language being practised. Nothing is downloaded before a language is chosen."""
    if learning_language():
        transcribe.model_download.start()
        speech.model_download.start()
    return _statuses()


class VoiceStatus(BaseModel):
    id: str
    label: str
    # Bytes to download the first time it is chosen, and whether it is already there.
    size: int
    downloaded: bool
    chosen: bool


class VoiceChoice(BaseModel):
    voice: str


def _voices() -> list[VoiceStatus]:
    chosen = speech.current_voice()
    return [
        VoiceStatus(id=v.id, label=v.label, size=v.size, downloaded=speech.is_downloaded(v.id), chosen=v.id == chosen)
        for v in speech.voices().values()
    ]


@router.get("/voices", response_model=list[VoiceStatus])
def list_voices() -> list[VoiceStatus]:
    """The voices the partner can speak the language being practised with, and which one it does."""
    return _voices()


@router.put("/voice", response_model=list[VoiceStatus])
def choose_voice(body: VoiceChoice) -> list[VoiceStatus]:
    """Have the partner speak with another voice; it is downloaded the first time."""
    try:
        speech.choose_voice(body.voice)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return _voices()
