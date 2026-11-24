"""User preferences stored in the database (single user, so one global set)."""

import os
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .db import get_connection
from .llm import LLMError, complete, llm_config

router = APIRouter(prefix="/api")


class Settings(BaseModel):
    # Language corrections are explained in, as an English name (e.g. "Korean").
    # None until the user (or the browser's language, on first visit) has chosen one.
    feedback_language: str | None = Field(default=None, min_length=1, max_length=40)


def _get(key: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def feedback_language() -> str:
    """The language to explain corrections in: the saved choice, else FEEDBACK_LANGUAGE, else English."""
    return _get("feedback_language") or os.environ.get("FEEDBACK_LANGUAGE", "").strip() or "English"


@router.get("/settings", response_model=Settings)
def get_settings() -> Settings:
    return Settings(feedback_language=_get("feedback_language"))


@router.put("/settings", response_model=Settings)
def save_settings(body: Settings) -> Settings:
    with get_connection() as conn:
        if body.feedback_language is None:
            conn.execute("DELETE FROM settings WHERE key = 'feedback_language'")
        else:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES ('feedback_language', ?)",
                (body.feedback_language.strip(),),
            )
    return get_settings()


class LLMSettings(BaseModel):
    # "<provider>/<model>" as named by LiteLLM; None when no model is configured.
    model: str | None
    # "app" when saved on the Settings page, "env" when it comes from the LLM_MODEL environment variable.
    source: Literal["app", "env"] | None
    # The key itself is never sent back to the page, only its last characters.
    key_hint: str | None


class LLMSettingsUpdate(BaseModel):
    model: str = Field(min_length=3, max_length=200, pattern=r"^[^/\s]+/\S+$")
    # Empty keeps the key that is already saved.
    api_key: str = Field(default="", max_length=500)


@router.get("/settings/llm", response_model=LLMSettings)
def get_llm_settings() -> LLMSettings:
    saved_model, saved_key = _get("llm_model"), _get("llm_api_key")
    if saved_model:
        return LLMSettings(model=saved_model, source="app", key_hint=saved_key[-4:] if saved_key else None)
    model, _ = llm_config()
    return LLMSettings(model=model or None, source="env" if model else None, key_hint=None)


@router.put("/settings/llm", response_model=LLMSettings)
def save_llm_settings(body: LLMSettingsUpdate) -> LLMSettings:
    key = body.api_key.strip()
    previous = _get("llm_model") or ""
    same_provider = previous.split("/")[0] == body.model.split("/")[0]
    # A saved key belongs to one provider, so it is kept only while the provider stays the same.
    if not key and not (same_provider and _get("llm_api_key")):
        raise HTTPException(status_code=422, detail="Enter the API key for this provider.")
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('llm_model', ?)", (body.model,))
        if key:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('llm_api_key', ?)", (key,))
    return get_llm_settings()


@router.delete("/settings/llm", response_model=LLMSettings)
def delete_llm_settings() -> LLMSettings:
    with get_connection() as conn:
        conn.execute("DELETE FROM settings WHERE key IN ('llm_model', 'llm_api_key')")
    return get_llm_settings()


@router.post("/settings/llm/test", status_code=204)
def test_llm_settings() -> None:
    """Send the configured model a one-line request, to check the model name and key."""
    try:
        complete("Reply with the single word OK.", "Say OK.", timeout=20, num_retries=0)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
