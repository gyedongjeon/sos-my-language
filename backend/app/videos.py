"""Videos to study with: a YouTube video is watched in its own player; its subtitles are kept
here, cut into sentences, so each sentence can be listened to on its own."""

import json
import re
import sqlite3
import string
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from html import unescape

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
    YouTubeTranscriptApiException,
)

from .corrections import Heard, _words
from .db import current_language, get_connection
from .languages import LEVELS
from .llm import LLMError, complete, parse_json_reply

router = APIRouter(prefix="/api")

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
# Path prefixes under which youtube.com names a video: /embed/<id>, /shorts/<id>, /live/<id>.
PATH_KINDS = {"embed", "shorts", "live", "v"}

# What subtitles carry besides speech: [Music], speaker arrows, music notes.
NOISE = re.compile(r"\[[^\]]*\]|>>|♪|♫")
# One or two words in brackets are a stage direction, such as (Laughter) or (Gelächter), when
# only the first letter is a capital; anything else in brackets was said.
BRACKETED = re.compile(r"\(([^\W\d_]{2,}(?: [^\W\d_]+)?)\)")
SENTENCE_END = re.compile(r"[.!?][\"'”’)\]]*$")
# Subtitles with fewer sentence ends than one in this many words were written without
# punctuation (typical of automatic ones), so they cannot be cut into sentences.
WORDS_PER_END = 40
# A silence of this many seconds between two subtitle lines ends a sentence left without a full stop.
PAUSE = 1.5
# A sentence longer than this is cut at its next comma, and at the hard limit without one.
LONG, TOO_LONG = 40, 60
# Subtitles without punctuation are punctuated by the model this many words at a time, at most,
# a few parts at once.
PART = 300
PARALLEL = 4


class NoSubtitles(Exception):
    """Raised with a user-facing message when a video's subtitles cannot be had."""


@dataclass(frozen=True)
class Snippet:
    """One subtitle line as YouTube shows it."""

    start: float
    duration: float
    text: str
    # Left without punctuation in subtitles that were punctuated: it ends a sentence of its own,
    # as each line does in subtitles without any punctuation.
    unpunctuated: bool = False


class Line(BaseModel):
    """One sentence of a video, with the part of the video in which it is said (in seconds)."""

    start: float
    end: float
    text: str


class SavedLine(Line):
    """A sentence of a saved video, and how the learner has done at shadowing it."""

    id: int
    # How often it was shadowed, and the best score so far (0-100); None before the first try.
    shadowed: int = 0
    best: int | None = None


class Said(BaseModel):
    text: str = Field(min_length=1, description="What the learner said, as transcribed.")


class ShadowedWord(BaseModel):
    text: str
    heard: bool


class Shadowed(BaseModel):
    """How one try at saying a sentence after the video went."""

    # The share of the sentence's words that were heard, 0-100.
    accuracy: int
    # The sentence word by word, as it is written, with whether each was heard.
    words: list[ShadowedWord]
    shadowed: int
    best: int


class Hit(BaseModel):
    """A sentence found in the saved subtitles."""

    id: int
    # The saved video it is in (our id and YouTube's), and where.
    video: int
    video_id: str
    title: str
    position: int
    start: float
    text: str


class VideoSummary(BaseModel):
    id: int
    # YouTube's own id of the video, which its player is given.
    video_id: str
    title: str
    channel: str
    # The language code of the subtitles, and whether YouTube made them automatically.
    language: str
    generated: bool
    added_at: str
    sentences: int
    # The CEFR level of what is said in it, A1 to C2; None while it has none.
    level: str | None = None


class Video(BaseModel):
    id: int
    video_id: str
    title: str
    channel: str
    language: str
    generated: bool
    added_at: str
    level: str | None = None
    lines: list[SavedLine]


class NewVideo(BaseModel):
    url: str


class Level(BaseModel):
    level: str | None


class Estimate(BaseModel):
    level: str = Field(description="The CEFR level a learner needs to follow the video: A1, A2, B1, B2, C1 or C2.")


LEVEL_PROMPT = """\
You are a teacher of {target} choosing videos for learners. You get sentences taken from the
start, the middle, and the end of a video's subtitles, and how fast it is spoken. Estimate the
CEFR level a learner needs to follow the video by ear and to repeat its sentences: A1, A2, B1,
B2, C1 or C2. Go by the vocabulary, the length and build of the sentences, how much is idiom or
specialist language, and the speed: around 120 words a minute is slow and clear, 150 is
ordinary speech, and 180 or more is fast. Dialect or strongly regional speech makes a video harder.

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""

# How much of the subtitles the model reads to estimate a level, in characters.
SAMPLE = 2400


def _take(stretch: list[Line], limit: int, from_end: bool = False) -> str:
    """As many whole sentences of a stretch as fit the limit, from its start or up to its end."""
    picked: list[str] = []
    for line in reversed(stretch) if from_end else stretch:
        if sum(map(len, picked)) + len(line.text) > limit:
            break
        picked.append(line.text)
    return " ".join(reversed(picked) if from_end else picked)


def _sample(lines: list[Line]) -> str:
    """Sentences from all through a video, and its speed, for estimating its level."""
    words = sum(len(line.text.split()) for line in lines)
    # From the first word to the last, pauses included: the pace a listener has to keep up with.
    spoken = lines[-1].end - lines[0].start if lines else 0
    speed = f"Spoken at about {round(words / spoken * 60)} words a minute." if spoken > 0 else ""
    third, limit = max(1, len(lines) // 3), SAMPLE // 3
    parts = [
        _take(lines[:third], limit),
        _take(lines[third : 2 * third], limit),
        _take(lines[2 * third :], limit, from_end=True),
    ]
    return f"{speed}\n\n" + "\n…\n".join(part for part in parts if part)


def _estimate(lines: list[Line]) -> str | None:
    """The level the model gives a video; None when its answer is not a level. Raises LLMError
    when the model cannot be asked."""
    reply = complete(
        LEVEL_PROMPT.format(target=current_language().name, schema=Estimate.model_json_schema()),
        _sample(lines),
        max_tokens=1000,
        response_format={"type": "json_object"},
        reasoning_effort="low",
    )
    level = parse_json_reply(reply, Estimate).level.strip().upper()
    return level if level in LEVELS else None


def video_id_of(url: str) -> str | None:
    """The video a YouTube link leads to, or None when it is not a link to a YouTube video."""
    parts = urllib.parse.urlsplit(url.strip())
    host = (parts.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    path = [part for part in parts.path.split("/") if part]
    found = None
    if host == "youtu.be" and path:
        found = path[0]
    elif host in ("youtube.com", "youtube-nocookie.com", "music.youtube.com"):
        if path[:1] == ["watch"]:
            found = urllib.parse.parse_qs(parts.query).get("v", [None])[0]
        elif len(path) >= 2 and path[0] in PATH_KINDS:
            found = path[1]
    return found if found and VIDEO_ID.fullmatch(found) else None


def _stage_direction(found: re.Match) -> str:
    words = found[1]
    return " " if words[0].isupper() and words[1:].replace(" ", "").islower() else found[0]


def _clean(text: str) -> str:
    return " ".join(BRACKETED.sub(_stage_direction, NOISE.sub(" ", unescape(text))).split())


class Punctuated(BaseModel):
    text: str = Field(min_length=1, description="The same words, with punctuation and capitals.")


PUNCTUATION_PROMPT = """\
You get a stretch of automatic {target} subtitles: the words that were said, with no punctuation
and few capitals. Add the punctuation (full stops, commas, question marks, exclamation marks)
and the capitals that a careful transcript would have, so that it can be cut into sentences.

Keep every word exactly as it is and in the same order: do not add, remove, join, split,
correct, or translate any word, even one that looks wrong. Change only capitals and the marks
attached to the words. The stretch may begin or end in the middle of a sentence; leave it open
there.

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""

# What may stand around a word besides its letters: compared without it, words are the same.
MARKS = string.punctuation + "„“”‚‘’…–—«»"
# The model's reply is used for a part when at least this share of the part's words are found in
# it unchanged. The model tends to correct recognition errors ("there" to "their") however it is
# told not to; those words keep their own spelling and take the model's marks.
MATCHED = 0.9


def _bare(word: str) -> str:
    return word.strip(MARKS).casefold()


def _trailing(written: str) -> str:
    """The marks after a word: "soon." gives "."."""
    return written[len(written.rstrip(MARKS)) :]


def _marked(word: str, written: str) -> str:
    """A word as it was said, with the capital and the marks after it that the model gave it."""
    bare = word.rstrip(MARKS) or word
    if written[:1].isupper():
        bare = bare[:1].upper() + bare[1:]
    return bare + _trailing(written)


def _carry(words: list[str], written: list[str]) -> list[str] | None:
    """The words with the punctuation and capitals of the model's version of them; None when it
    is too unlike them to tell which mark belongs to which word."""
    said, wrote = [_bare(w) for w in words], [_bare(w) for w in written]
    matcher = SequenceMatcher(None, said, wrote, autojunk=False)
    if sum(block.size for block in matcher.get_matching_blocks()) < MATCHED * len(words):
        return None
    result = list(words)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                result[i1 + k] = _marked(words[i1 + k], written[j1 + k])
        elif j2 > j1:
            # Words joined, split, added, or dropped: the marks after the last of the model's
            # words go after the last word said there.
            last = i2 - 1 if i2 > i1 else i1 - 1
            if last >= 0:
                result[last] = (result[last].rstrip(MARKS) or result[last]) + _trailing(written[j2 - 1])
    return result


def _punctuate_part(words: list[str], target: str) -> list[str] | None:
    """The words with punctuation and capitals, or None when the model's reply cannot be used.
    `target` is the name of the language they are in."""
    try:
        reply = complete(
            PUNCTUATION_PROMPT.format(target=target, schema=Punctuated.model_json_schema()),
            " ".join(words),
            max_tokens=8000,
            response_format={"type": "json_object"},
            reasoning_effort="low",
            timeout=60,
        )
        written = parse_json_reply(reply, Punctuated).text.split()
    except LLMError:
        return None
    # A dash or a quotation mark on its own belongs to no word.
    return _carry(words, [word for word in written if _bare(word)])


def punctuate(snippets: list[Snippet]) -> list[Snippet]:
    """Subtitles without punctuation, such as some of YouTube's automatic ones, punctuated by the
    model; each subtitle line keeps its words and its time. A part whose words the model changed,
    and every part when no model can be asked, is kept as it was. Punctuated subtitles are
    returned as they are."""
    texts = [_clean(snippet.text) for snippet in snippets]
    words = [word for text in texts for word in text.split()]
    if not words or sum(1 for word in words if SENTENCE_END.search(word)) * WORDS_PER_END >= len(words):
        return snippets
    # Asked for here: the parts are punctuated on other threads.
    target = current_language().name
    # Parts end with a subtitle line, so each line's words come back from one part.
    parts: list[list[int]] = [[]]
    size = 0
    for i, text in enumerate(texts):
        count = len(text.split())
        if parts[-1] and size + count > PART:
            parts.append([])
            size = 0
        parts[-1].append(i)
        size += count
    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        written = list(
            pool.map(lambda part: _punctuate_part([w for i in part for w in texts[i].split()], target), parts)
        )
    if all(punctuated is None for punctuated in written):
        return snippets
    result = list(snippets)
    for part, punctuated in zip(parts, written, strict=True):
        if punctuated is None:
            for i in part:
                result[i] = replace(snippets[i], unpunctuated=True)
            continue
        at = 0
        for i in part:
            count = len(texts[i].split())
            result[i] = Snippet(snippets[i].start, snippets[i].duration, " ".join(punctuated[at : at + count]))
            at += count
    return result


def sentences(snippets: list[Snippet]) -> list[Line]:
    """Cut subtitles into sentences. A subtitle line breaks where it fits on the screen, not
    where a sentence ends, so the lines are joined and cut again at the sentence ends; a
    word's time is taken from how far into its line it stands."""
    abbreviations = current_language().abbreviations
    kept = [(snippet, _clean(snippet.text)) for snippet in snippets]
    kept = [(snippet, text) for snippet, text in kept if text]
    # (word, the time it is said at, the time its subtitle line ends)
    words: list[tuple[str, float, float]] = []
    # The words after which a sentence ends whatever they are: the last of an unpunctuated line.
    line_ends: set[int] = set()
    for i, (snippet, text) in enumerate(kept):
        end = snippet.start + snippet.duration
        if i + 1 < len(kept) and snippet.start < kept[i + 1][0].start < end:
            # Automatic subtitles stay on screen while the next line is already spoken.
            end = kept[i + 1][0].start
        at = 0
        for word in text.split():
            at = text.index(word, at)
            words.append((word, snippet.start + (end - snippet.start) * at / len(text), end))
            at += len(word)
        if snippet.unpunctuated:
            line_ends.add(len(words) - 1)
    ends = sum(1 for word, _, _ in words if SENTENCE_END.search(word))
    if ends * WORDS_PER_END < len(words):
        return [
            Line(start=snippet.start, end=words_end, text=text)
            for (snippet, text), words_end in zip(kept, _line_ends(kept), strict=True)
        ]

    lines: list[Line] = []
    current: list[tuple[str, float, float]] = []
    for at, word in enumerate(words):
        if current and word[1] - current[-1][2] >= PAUSE:
            lines.append(Line(start=current[0][1], end=current[-1][2], text=" ".join(w for w, _, _ in current)))
            current = []
        current.append(word)
        text = word[0]
        full = bool(SENTENCE_END.search(text)) and text.lower() not in abbreviations
        if full or at in line_ends or len(current) >= TOO_LONG or (len(current) >= LONG and text.endswith(",")):
            lines.append(Line(start=current[0][1], end=current[-1][2], text=" ".join(w for w, _, _ in current)))
            current = []
    if current:
        lines.append(Line(start=current[0][1], end=current[-1][2], text=" ".join(w for w, _, _ in current)))
    for line, following in zip(lines, lines[1:], strict=False):
        # A sentence ends where the next one starts, unless a pause comes first.
        if following.start > line.start:
            line.end = min(line.end, following.start)
    return lines


def _line_ends(kept: list[tuple[Snippet, str]]) -> list[float]:
    ends = []
    for i, (snippet, _) in enumerate(kept):
        end = snippet.start + snippet.duration
        if i + 1 < len(kept) and snippet.start < kept[i + 1][0].start < end:
            end = kept[i + 1][0].start
        ends.append(end)
    return ends


def _transcript(video_id: str) -> tuple[list[Snippet], str, bool]:
    """A video's subtitles in the language being practised: the lines, their language code, and
    whether they were made automatically. Subtitles written by a person are preferred."""
    language = current_language()
    try:
        track = YouTubeTranscriptApi().list(video_id).find_transcript(language.subtitles)
        fetched = track.fetch()
    except (NoTranscriptFound, TranscriptsDisabled) as e:
        raise NoSubtitles(f"This video has no {language.name} subtitles.") from e
    except VideoUnavailable as e:
        raise NoSubtitles("This video does not exist or is not available.") from e
    except YouTubeTranscriptApiException as e:
        raise NoSubtitles(f"The subtitles could not be read from YouTube ({type(e).__name__}). Try again later.") from e
    except Exception as e:
        # Offline, or YouTube answered with something the library does not expect.
        raise NoSubtitles(f"YouTube could not be reached: {e}") from e
    return [Snippet(s.start, s.duration, s.text) for s in fetched], track.language_code, track.is_generated


def _about(video_id: str) -> tuple[str, str]:
    """The title and the channel of a video, from YouTube's public embedding information;
    empty when it cannot be had, which does not keep the video from being saved."""
    watch = urllib.parse.quote(f"https://www.youtube.com/watch?v={video_id}", safe="")
    try:
        with urllib.request.urlopen(f"https://www.youtube.com/oembed?url={watch}&format=json", timeout=10) as reply:
            about = json.load(reply)
        return str(about.get("title") or "").strip(), str(about.get("author_name") or "").strip()
    except Exception:
        return "", ""


def _load(conn: sqlite3.Connection, where: str, value: object) -> Video | None:
    """A video saved for the language being practised, by one of its columns."""
    found = conn.execute(
        f"SELECT * FROM videos WHERE {where} = ? AND target = ?", (value, current_language().code)
    ).fetchone()
    if found is None:
        return None
    rows = conn.execute(
        "SELECT id, start, end, text, shadowed, best FROM video_lines WHERE video = ? ORDER BY position",
        (found["id"],),
    ).fetchall()
    return Video(**dict(found), lines=[SavedLine(**dict(row)) for row in rows])


@router.get("/videos", response_model=list[VideoSummary])
def list_videos() -> list[VideoSummary]:
    """The videos saved for the language being practised, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT v.*, COUNT(l.id) AS sentences
            FROM videos v LEFT JOIN video_lines l ON l.video = v.id
            WHERE v.target = ?
            GROUP BY v.id ORDER BY v.id DESC
            """,
            (current_language().code,),
        ).fetchall()
    return [VideoSummary(**dict(row)) for row in rows]


@router.post("/videos", response_model=Video, status_code=201)
def add_video(body: NewVideo, response: Response) -> Video:
    """Save a YouTube video to study with: its title and its subtitles, as sentences.
    The video itself is not downloaded; it is played by YouTube's player."""
    video_id = video_id_of(body.url)
    if video_id is None:
        raise HTTPException(status_code=422, detail="This is not a link to a YouTube video.")
    target = current_language()
    with get_connection() as conn:
        if saved := _load(conn, "video_id", video_id):
            response.status_code = 200
            return saved
    try:
        snippets, language, generated = _transcript(video_id)
    except NoSubtitles as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    lines = sentences(punctuate(snippets))
    if not lines:
        raise HTTPException(status_code=422, detail=f"This video has no {target.name} subtitles.")
    title, channel = _about(video_id)
    try:
        level = _estimate(lines)
    except LLMError:
        # No model, or it did not answer: the video is saved all the same, without a level.
        level = None
    with get_connection() as conn:
        created = conn.execute(
            "INSERT INTO videos (target, video_id, title, channel, language, generated, level)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (target.code, video_id, title or f"YouTube video {video_id}", channel, language, generated, level),
        )
        conn.executemany(
            "INSERT INTO video_lines (video, position, start, end, text) VALUES (?, ?, ?, ?, ?)",
            [(created.lastrowid, i, line.start, line.end, line.text) for i, line in enumerate(lines)],
        )
        return _load(conn, "id", created.lastrowid)


@router.get("/videos/{video}", response_model=Video)
def get_video(video: int) -> Video:
    with get_connection() as conn:
        found = _load(conn, "id", video)
    if found is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return found


@router.put("/videos/{video}/level", response_model=Video)
def set_level(video: int, body: Level) -> Video:
    """Set a video's level by hand, or clear it."""
    if body.level is not None and body.level not in LEVELS:
        raise HTTPException(status_code=422, detail=f"A level is one of {', '.join(LEVELS)}.")
    with get_connection() as conn:
        changed = conn.execute("UPDATE videos SET level = ? WHERE id = ?", (body.level, video))
        if changed.rowcount == 0:
            raise HTTPException(status_code=404, detail="Video not found")
        return _load(conn, "id", video)


@router.post("/videos/{video}/level", response_model=Video)
def estimate_level(video: int) -> Video:
    """Have a video's level estimated again from its subtitles."""
    found = get_video(video)
    try:
        level = _estimate(found.lines)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Could not estimate the level: {e}") from e
    if level is None:
        raise HTTPException(status_code=502, detail="Could not estimate the level: the model gave no level.")
    with get_connection() as conn:
        conn.execute("UPDATE videos SET level = ? WHERE id = ?", (level, video))
        return _load(conn, "id", video)


@router.delete("/videos/{video}", status_code=204)
def delete_video(video: int) -> Response:
    """Remove a saved video and its subtitles."""
    with get_connection() as conn:
        deleted = conn.execute("DELETE FROM videos WHERE id = ?", (video,))
    if deleted.rowcount == 0:
        raise HTTPException(status_code=404, detail="Video not found")
    return Response(status_code=204)


# The most sentences a search returns.
MAX_HITS = 50


@router.get("/video-lines", response_model=list[Hit])
def search_lines(q: str = Query(min_length=1, max_length=200)) -> list[Hit]:
    """The sentences of the videos saved for the language being practised that contain a word or
    phrase, newest video first."""
    phrase = " ".join(q.split())
    if not phrase:
        raise HTTPException(status_code=422, detail="Type a word or a phrase to look for.")
    # The phrase is looked for as it is: "%" and "_" are not wildcards here.
    escaped = phrase.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with get_connection() as conn:
        # SQLite ignores the case of ASCII letters only; "Ä" and "ä" are told apart.
        conn.create_function("casefold", 1, lambda text: text.casefold(), deterministic=True)
        rows = conn.execute(
            """
            SELECT l.id, l.video, v.video_id, v.title, l.position, l.start, l.text
            FROM video_lines l JOIN videos v ON v.id = l.video
            WHERE v.target = ? AND casefold(l.text) LIKE ? ESCAPE '\\'
            ORDER BY v.id DESC, l.position LIMIT ?
            """,
            (current_language().code, f"%{escaped}%", MAX_HITS),
        ).fetchall()
    return [Hit(**dict(row)) for row in rows]


def _not_heard(words: list[ShadowedWord], said: list[str]) -> str:
    """The words of a sentence that were not heard, each with what was heard in its place, if
    anything: 'Not heard: “gaps” (heard “guess”).' Words missed side by side are named together."""
    # Each word as spoken, with the written word it belongs to.
    spoken = [(word, i) for i, written in enumerate(words) for word in _words(written.text)]
    matcher = SequenceMatcher(None, [word for word, _ in spoken], said, autojunk=False)
    # The written words missed together, by the first of them, and what was heard instead.
    together: dict[int, int] = {}
    instead: dict[int, str] = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        missed = sorted({spoken[k][1] for k in range(i1, i2)} - {i for i, w in enumerate(words) if w.heard})
        if tag == "replace" and missed:
            instead[missed[0]] = " ".join(said[j1:j2])
            together.update((i, missed[0]) for i in missed)
    groups: dict[int, list[str]] = {}
    for i, word in enumerate(words):
        if not word.heard:
            groups.setdefault(together.get(i, i), []).append(word.text.strip(MARKS))
    named = [f"“{' '.join(group)}”" + (f" (heard “{instead[first]}”)" if first in instead else "") for first, group in groups.items()]
    return f"Not heard: {', '.join(named)}."


@router.post("/video-lines/{line}/attempts", response_model=Shadowed)
def shadow(line: int, body: Said) -> Shadowed:
    """Compare what the learner said after the video with the sentence, word by word."""
    with get_connection() as conn:
        found = conn.execute(
            "SELECT l.text, l.shadowed, l.best, v.title, v.target"
            " FROM video_lines l JOIN videos v ON v.id = l.video WHERE l.id = ?",
            (line,),
        ).fetchone()
        if found is None:
            raise HTTPException(status_code=404, detail="Sentence not found")
        said = Heard(_words(body.text))
        words, counted, heard_count = [], 0, 0
        for written in found["text"].split():
            # A short form is two words to say; a dash or a lone quotation mark is none.
            spoken = _words(written)
            heard = said.take(spoken)
            if spoken:
                counted += 1
                heard_count += heard
            words.append(ShadowedWord(text=written, heard=heard))
        accuracy = int(100 * heard_count / counted + 0.5) if counted else 0
        best = max(accuracy, found["best"] or 0)
        conn.execute("UPDATE video_lines SET shadowed = shadowed + 1, best = ? WHERE id = ?", (best, line))
        conn.execute(
            "INSERT INTO shadowing_attempts (target, line, sentence, said, accuracy) VALUES (?, ?, ?, ?, ?)",
            (found["target"], line, found["text"], body.text, accuracy),
        )
        if accuracy < 100:
            # Kept with the corrections; a new wrong try replaces the last one, to be practised again.
            conn.execute(
                """
                INSERT INTO shadowing_mistakes (target, line, title, said, improved, explanation)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (line) DO UPDATE SET
                    title = excluded.title, said = excluded.said, improved = excluded.improved, explanation = excluded.explanation,
                    practiced = 0, practiced_at = NULL, created_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                """,
                (found["target"], line, found["title"], body.text, found["text"], _not_heard(words, _words(body.text))),
            )
    return Shadowed(accuracy=accuracy, words=words, shadowed=found["shadowed"] + 1, best=best)
