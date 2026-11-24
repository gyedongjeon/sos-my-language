"""FastAPI entry point."""

import threading
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .corrections import router as corrections_router
from . import llm
from .db import init_db
from .history import router as history_router
from .models import router as models_router
from .paths import FRONTEND_DIST
from .patterns import router as patterns_router
from .settings import router as settings_router
from .similar_videos import router as similar_videos_router
from .speech import synthesize
from .topics import router as topics_router
from .transcribe import transcribe
from .translations import router as translations_router
from .videos import router as videos_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    # LiteLLM takes seconds to load; the app opens without waiting for it.
    threading.Thread(target=llm.load, daemon=True).start()
    yield


app = FastAPI(title="sos-my-language", lifespan=lifespan)
app.include_router(corrections_router)
app.include_router(history_router)
app.include_router(models_router)
app.include_router(patterns_router)
app.include_router(settings_router)
app.include_router(topics_router)
app.include_router(videos_router)
app.include_router(similar_videos_router)
app.include_router(translations_router)


class TranscriptResponse(BaseModel):
    text: str
    clarity: int | None
    unclear_words: list[str]
    words_per_minute: int | None


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Lets the desktop shell know the server is ready."""
    return {"status": "ok"}


@app.post("/api/transcribe", response_model=TranscriptResponse)
def transcribe_speech(file: UploadFile) -> TranscriptResponse:
    try:
        result = transcribe(file.file)
    except Exception as e:
        # Undecodable upload or a failed model download/load; report it to the UI.
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}") from e
    return TranscriptResponse(**asdict(result))


@app.post("/api/speech")
def speech(body: SpeechRequest) -> Response:
    try:
        audio = synthesize(body.text)
    except Exception as e:
        # Model still downloading, failed to load, or synthesis failed; the UI falls back to the browser voice.
        raise HTTPException(status_code=502, detail=f"Speech synthesis failed: {e}") from e
    return Response(content=audio, media_type="audio/wav")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str) -> FileResponse:
    """Serve the built frontend, so the whole app runs from this one server."""
    index = FRONTEND_DIST / "index.html"
    if path.startswith("api/") or not index.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    file = (FRONTEND_DIST / path).resolve()
    if file.is_file() and file.is_relative_to(FRONTEND_DIST.resolve()):
        return FileResponse(file)
    # Any other path is a client-side route; the Vue router takes it from here.
    return FileResponse(index)
