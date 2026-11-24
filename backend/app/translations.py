"""The sentences of a saved video in the learner's own language, written by the model when the
learner asks for them and kept, so each sentence is translated once for each language."""

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import videos
from .db import get_connection
from .llm import LLMError, complete, parse_json_reply
from .settings import feedback_language

router = APIRouter(prefix="/api")

# How many sentences one request translates; the parts of a long video are asked for at once.
CHUNK = 40
PARALLEL = 4
# Sentences a request failed on or the model left out are asked for again, this many times in all.
ROUNDS = 2


class Translated(BaseModel):
    id: int
    text: str = Field(min_length=1)


class Translations(BaseModel):
    translations: list[Translated]


class LineTranslation(BaseModel):
    line: int
    text: str


class VideoTranslation(BaseModel):
    language: str
    lines: list[LineTranslation]
    # Sentences left without a translation after every round; asking again tries them again.
    missing: int = 0


PROMPT = """\
You translate the English subtitles of a video into {language} for a learner of English, who
reads them next to the English to understand what is said. You get the video's title and its
sentences in order, each after its number in square brackets. The sentences come from
subtitles, so a sentence may be cut short or run on into the next; translate each as it stands,
using the ones around it to get the meaning right.

Translate every sentence into natural {language}, keeping its meaning and its tone (casual or
formal); do not explain or add anything. Give each translation the number of its sentence.

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""


def _translate(language: str, title: str, part: list[videos.SavedLine]) -> dict[int, str]:
    """Translations of some sentences by their line id; a sentence the model left out is missing."""
    sentences = "\n".join(f"[{line.id}] {line.text}" for line in part)
    reply = complete(
        PROMPT.format(language=language, schema=Translations.model_json_schema()),
        f"Title: {title}\n\n{sentences}",
        max_tokens=8000,
        response_format={"type": "json_object"},
        reasoning_effort="low",
        timeout=60,
    )
    asked = {line.id for line in part}
    return {t.id: t.text.strip() for t in parse_json_reply(reply, Translations).translations if t.id in asked}


def _save(language: str, found: dict[int, str]) -> None:
    with get_connection() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO line_translations (line, language, text) VALUES (?, ?, ?)",
            [(line, language, text) for line, text in found.items()],
        )


@router.post("/videos/{video}/translations", response_model=VideoTranslation)
def translate(video: int) -> VideoTranslation:
    """Every sentence of a saved video in the learner's language. Sentences translated before
    are taken as they were kept; the others are sent to the model."""
    found = videos.get_video(video)
    language = feedback_language()
    if language.strip().lower() == "english":
        raise HTTPException(status_code=422, detail="The feedback language is English, so there is nothing to translate into.")
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT t.line, t.text FROM line_translations t JOIN video_lines l ON l.id = t.line
            WHERE l.video = ? AND t.language = ?
            """,
            (video, language),
        ).fetchall()
    kept = {row["line"]: row["text"] for row in rows}
    error: LLMError | None = None

    def run(part: list[videos.SavedLine]) -> dict[int, str]:
        nonlocal error
        try:
            written = _translate(language, found.title, part)
        except LLMError as e:
            error = e
            return {}
        # Kept part by part, so what was translated before a failure is not asked for again.
        _save(language, written)
        return written

    for _ in range(ROUNDS):
        missing = [line for line in found.lines if line.id not in kept]
        if not missing:
            break
        parts = [missing[i : i + CHUNK] for i in range(0, len(missing), CHUNK)]
        with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
            for written in pool.map(run, parts):
                kept.update(written)
    if error and not any(line.id in kept for line in found.lines):
        raise HTTPException(status_code=502, detail=f"Could not translate the sentences: {error}")
    return VideoTranslation(
        language=language,
        lines=[LineTranslation(line=line.id, text=kept[line.id]) for line in found.lines if line.id in kept],
        missing=sum(1 for line in found.lines if line.id not in kept),
    )
