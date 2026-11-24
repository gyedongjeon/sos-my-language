"""Videos like a saved one, suggested to study with next: the model thinks of searches, YouTube
is searched with yt-dlp, and only the videos found with English subtitles at a level near the
saved one's are suggested."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import videos
from .db import get_connection
from .llm import LLMError, complete, parse_json_reply
from .pattern_list import LEVELS

router = APIRouter(prefix="/api")

# How many videos each search brings, and how many of those found are checked for subtitles
# and a level: each check reads the subtitles and asks the model once.
PER_SEARCH = 8
MAX_CHECKED = 6
# Shorter videos are Shorts, too short to study with; longer ones are streams and lectures.
SHORTEST, LONGEST = 60, 60 * 60


class SearchFailed(Exception):
    """Raised with a user-facing message when YouTube cannot be searched."""


@dataclass(frozen=True)
class Found:
    """A video a YouTube search found; its length in seconds, when YouTube gives it."""

    video_id: str
    title: str
    channel: str
    duration: float | None


class Suggestion(BaseModel):
    video_id: str
    title: str
    channel: str
    duration: float | None
    # The level its subtitles were estimated at, and whether YouTube made them automatically.
    level: str
    generated: bool


class Searches(BaseModel):
    queries: list[str] = Field(description="Two or three YouTube searches, each a few words.")


SEARCH_PROMPT = """\
You help an English learner find YouTube videos to study with. You get the title and the
channel of a video they are studying, and sentences from it. Think of two or three YouTube
searches that find other videos like it: on the same subject or in the same kind of format
(a talk, an interview, a vlog, a lesson), spoken in English at a similar difficulty. Each
search is a few words, as a person would type it.

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""


def _search(query: str, count: int) -> list[Found]:
    """The videos YouTube finds for a search, without opening each of them."""
    import yt_dlp  # Imported here: it is slow to import and only needed for searching.

    options = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": "in_playlist"}
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            result = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
    except Exception as e:
        raise SearchFailed(f"YouTube could not be searched: {e}") from e
    return [
        Found(
            video_id=entry["id"],
            title=str(entry.get("title") or "").strip(),
            channel=str(entry.get("channel") or entry.get("uploader") or "").strip(),
            duration=entry.get("duration"),
        )
        for entry in (result or {}).get("entries") or []
        if entry and videos.VIDEO_ID.fullmatch(str(entry.get("id") or ""))
    ]


def _queries(video: videos.Video) -> list[str]:
    """The searches the model thinks of for videos like this one. Raises LLMError."""
    about = f"Title: {video.title}\nChannel: {video.channel or 'unknown'}\n\n"
    reply = complete(
        SEARCH_PROMPT.format(schema=Searches.model_json_schema()),
        about + videos._sample(video.lines),
        max_tokens=1000,
        response_format={"type": "json_object"},
        reasoning_effort="low",
    )
    return [query.strip() for query in parse_json_reply(reply, Searches).queries if query.strip()][:3]


def _check(found: Found) -> Suggestion | None:
    """The video as a suggestion, with its level; None when it has no English subtitles that
    can be read, or no level can be estimated for it."""
    try:
        snippets, _, generated = videos._transcript(found.video_id)
        lines = videos.sentences(snippets)
        level = videos._estimate(lines) if lines else None
    except (videos.NoSubtitles, LLMError):
        return None
    if level is None:
        return None
    return Suggestion(**found.__dict__, level=level, generated=generated)


def _distance(level: str | None, other: str) -> int:
    return 0 if level is None else abs(LEVELS.index(level) - LEVELS.index(other))


@router.post("/videos/{video}/suggestions", response_model=list[Suggestion])
def suggest(video: int) -> list[Suggestion]:
    """Videos like a saved one at a similar level (one level apart at most), nearest level first."""
    studied = videos.get_video(video)
    try:
        queries = _queries(studied)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Could not think of searches: {e}") from e
    with get_connection() as conn:
        seen = {row["video_id"] for row in conn.execute("SELECT video_id FROM videos")}
    candidates: list[Found] = []
    try:
        for query in queries:
            for found in _search(query, PER_SEARCH):
                short_or_long = found.duration is not None and not SHORTEST <= found.duration <= LONGEST
                if found.video_id not in seen and not short_or_long:
                    seen.add(found.video_id)
                    candidates.append(found)
    except SearchFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    with ThreadPoolExecutor(max_workers=MAX_CHECKED) as pool:
        checked = [s for s in pool.map(_check, candidates[:MAX_CHECKED]) if s]
    near = [s for s in checked if _distance(studied.level, s.level) <= 1]
    # sorted() keeps the order YouTube found them in among videos equally near.
    return sorted(near, key=lambda s: _distance(studied.level, s.level))
