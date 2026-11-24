"""Sentence patterns, practised by saying a sentence shown in the learner's language in the
language being practised."""

from dataclasses import asdict

import sqlite3

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, model_validator

from .corrections import _words, keep_mistake
from .db import current_language, get_connection
from .languages import LEVELS, Pattern
from .llm import LLMError, complete, parse_json_reply
from .settings import feedback_language

router = APIRouter(prefix="/api")

# How many sentences one round of a pattern has.
ROUND = 5
# The level the learner's own patterns are listed under, and what their ids start with.
OWN_LEVEL = "Yours"
OWN_PREFIX = "own-"


def _built_in() -> dict[str, Pattern]:
    """The built-in patterns of the language being practised, by id."""
    return {pattern.id: pattern for pattern in current_language().patterns}


class PatternStatus(BaseModel):
    """A pattern and how the learner has done on it."""

    id: str
    level: str
    pattern: str
    use: str
    example: str
    # Finished rounds, and the score of the last one.
    sessions: int = 0
    last_correct: int | None = None
    last_total: int | None = None
    practiced_at: str | None = None
    # Made by the learner from a sentence of a video, and where that sentence is, while the
    # video is still saved.
    custom: bool = False
    video: int | None = None
    position: int | None = None


class NewPattern(BaseModel):
    # The sentence of a saved video the pattern was found in, and the part of it to practise.
    line: int
    phrase: str = Field(min_length=1, max_length=300)


class WrittenPattern(BaseModel):
    pattern: str = Field(min_length=1, description="The pattern as a formula.")
    use: str = Field(min_length=1, description="What it is used for.")


class Exercise(BaseModel):
    prompt: str = Field(min_length=1, description="The sentence to say, in the learner's language.")
    answer: str = Field(min_length=1, description="The sentence in the language being practised, using the pattern.")


class Exercises(BaseModel):
    note: str = Field(description="When the pattern is used, in the learner's language.")
    items: list[Exercise] = Field(min_length=1)


class Attempt(BaseModel):
    prompt: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    said: str = Field(min_length=1, description="What the learner said, as transcribed.")


class Verdict(BaseModel):
    correct: bool
    improved: str = Field(min_length=1, description="The sentence as it should be said, in the language being practised.")
    explanation: str | None = Field(default=None, description="What to change and why; null when correct.")


class Result(BaseModel):
    correct: int = Field(ge=0)
    total: int = Field(ge=1, le=50)

    @model_validator(mode="after")
    def not_more_than_all(self) -> "Result":
        if self.correct > self.total:
            raise ValueError("More correct sentences than sentences.")
        return self


EXERCISES_PROMPT = """\
You are a teacher of {target} preparing a speaking drill for a non-native speaker whose own
language is {language}. The drill practises one sentence pattern:

Pattern: {pattern}
Used for: {use}
Example: {example}
Level: {level}

Write {count} different sentences that each need this pattern. The learner sees a sentence in
{language} and says it in {target}.
- Everyday things a person might really say, each about a different situation and with a
  different subject or verb. Do not reuse the example.
- Keep the vocabulary and the rest of the grammar at {level} or below, so that the pattern is
  the only hard part.
- "answer" is the sentence in natural {target}, using the pattern. It is one sentence, short
  enough to say in one breath.
- "prompt" is the same sentence in natural {language}, as a native speaker would say it, not a
  word-for-word translation. {cue}
- "note" says in one or two sentences when this pattern is used. Write it in {language}, the
  learner's own language; {target} words may be quoted inside it.

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""

# With the language being practised as the learner's own there is nothing to translate from.
SAME_LANGUAGE_CUE = (
    'Because that language is {target}, write "prompt" as a short instruction in {target} that describes '
    'what to say without using the pattern\'s own words, such as "{example}"'
)

CHECK_PROMPT = """\
You are a teacher of {target} checking one sentence of a speaking drill. The learner, whose own
language is {language}, practises this sentence pattern:

Pattern: {pattern}
Used for: {use}
Level: {level}

You get the sentence the learner was shown, a model answer, and what the learner said. The
learner spoke; you see a speech-recognition transcript, so ignore punctuation, capitalization,
and spelling, and do not count an obvious recognition error (a word that makes no sense where
a similar-sounding word would) as a mistake.

correct: true when what the learner said means what the shown sentence means, uses the
pattern, and has no mistake in grammar or word choice that a fluent speaker would notice. It
does not have to match the model answer: other words and a different order are fine.
improved: the sentence as it should be said, in {target}. Stay as close to the learner's own
words as a correct sentence allows; when it was correct, repeat what the learner said. When
the learner said something that means something else than the shown sentence, give the model
answer instead.
explanation: when it was not correct, one or two sentences on what to change and why, talking
about what to say, not how to write it; when the meaning was different, say so first. When it
was correct, null. Write it in {language}, the learner's own language, whatever language the
sentence is in; {target} words may be quoted inside it. {only_quoted}

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""


PATTERN_PROMPT = """\
You are a teacher of {target}. A learner found a sentence in a video and marked the part of it
they want to be able to say themselves. Turn that part into a sentence pattern they can
practise with other sentences.

pattern: the pattern as a short formula, as a grammar book writes one: keep the words that
make the pattern, and put a slot where other words can go, named by what goes there, such as
{slots}. For example,
{example}. Name the slots in English. At most 12 words.
use: what the pattern is used for, in plain English, starting with a verb in -ing, such as
"Regretting something in the past". At most 12 words.

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""

OWN_SQL = """
    SELECT o.id, o.pattern, o.use, o.example, l.video, l.position
    FROM own_patterns o LEFT JOIN video_lines l ON l.id = o.line
"""


def _own(row: sqlite3.Row) -> tuple[Pattern, dict]:
    """An own pattern in the shape of a built-in one, and what only an own one has."""
    pattern = Pattern(f"{OWN_PREFIX}{row['id']}", OWN_LEVEL, row["pattern"], row["use"], row["example"])
    return pattern, {"custom": True, "video": row["video"], "position": row["position"]}


def _find(conn: sqlite3.Connection, pattern_id: str) -> tuple[Pattern, dict]:
    """A pattern by its id, built in or the learner's own, with the fields only an own one has."""
    if found := _built_in().get(pattern_id):
        return found, {}
    number = pattern_id.removeprefix(OWN_PREFIX)
    if pattern_id.startswith(OWN_PREFIX) and number.isdecimal():
        own = conn.execute(f"{OWN_SQL} WHERE o.id = ? AND o.target = ?", (int(number), current_language().code))
        if row := own.fetchone():
            return _own(row)
    raise HTTPException(status_code=404, detail="Pattern not found")


def _pattern(pattern_id: str) -> Pattern:
    with get_connection() as conn:
        return _find(conn, pattern_id)[0]


def _for_prompt(pattern: Pattern) -> dict:
    """A pattern's fields as the prompts name them. An own pattern has no CEFR level; its
    example sentence shows how hard it is."""
    level = f"CEFR level {pattern.level}" if pattern.level in LEVELS else "the level of the example sentence"
    return {**asdict(pattern), "level": level}


def _status(pattern: Pattern, progress: dict | None) -> PatternStatus:
    return PatternStatus(**asdict(pattern), **(progress or {}))


@router.get("/patterns", response_model=list[PatternStatus])
def list_patterns() -> list[PatternStatus]:
    """Every pattern of the language being practised, level by level, with the learner's
    progress on it."""
    language = current_language()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT pattern_id, sessions, last_correct, last_total, practiced_at FROM pattern_progress WHERE target = ?",
            (language.code,),
        ).fetchall()
        own = [_own(row) for row in conn.execute(f"{OWN_SQL} WHERE o.target = ? ORDER BY o.id", (language.code,))]
    progress = {row["pattern_id"]: {key: row[key] for key in row.keys() if key != "pattern_id"} for row in rows}
    return [_status(pattern, progress.get(pattern.id)) for pattern in language.patterns] + [
        _status(pattern, {**(progress.get(pattern.id) or {}), **extra}) for pattern, extra in own
    ]


@router.post("/patterns", response_model=PatternStatus, status_code=201)
def add_pattern(body: NewPattern, response: Response) -> PatternStatus:
    """Make a pattern of the learner's own from the marked part of a sentence of a saved video."""
    phrase = " ".join(body.phrase.split())
    target = current_language()
    with get_connection() as conn:
        line = conn.execute("SELECT text FROM video_lines WHERE id = ?", (body.line,)).fetchone()
    if line is None:
        raise HTTPException(status_code=404, detail="Sentence not found")
    if not phrase or phrase.lower() not in " ".join(line["text"].split()).lower():
        raise HTTPException(status_code=422, detail="Mark a part of the sentence itself.")
    try:
        reply = complete(
            PATTERN_PROMPT.format(
                target=target.name,
                slots=target.pattern_slots,
                example=target.pattern_example,
                schema=WrittenPattern.model_json_schema(),
            ),
            f"Sentence: {line['text']}\nMarked part: {phrase}",
            max_tokens=2000,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        written = parse_json_reply(reply, WrittenPattern)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Could not make the pattern: {e}") from e
    formula = " ".join(written.pattern.split())
    with get_connection() as conn:
        known = conn.execute(
            "SELECT id FROM own_patterns WHERE target = ? AND pattern = ?", (target.code, formula)
        ).fetchone()
        if known:
            response.status_code = 200
            number = known["id"]
        else:
            number = conn.execute(
                "INSERT INTO own_patterns (target, pattern, use, example, line) VALUES (?, ?, ?, ?, ?)",
                (target.code, formula, written.use.strip(), line["text"], body.line),
            ).lastrowid
        return _saved(conn, f"{OWN_PREFIX}{number}")


@router.delete("/patterns/{pattern_id}", status_code=204)
def delete_pattern(pattern_id: str) -> Response:
    """Remove a pattern of the learner's own, with its progress."""
    with get_connection() as conn:
        pattern, _ = _find(conn, pattern_id)
        if pattern_id in _built_in():
            raise HTTPException(status_code=403, detail="A built-in pattern cannot be removed.")
        conn.execute("DELETE FROM own_patterns WHERE id = ?", (int(pattern_id.removeprefix(OWN_PREFIX)),))
        conn.execute(
            "DELETE FROM pattern_progress WHERE target = ? AND pattern_id = ?", (current_language().code, pattern_id)
        )
    return Response(status_code=204)


def _saved(conn: sqlite3.Connection, pattern_id: str) -> PatternStatus:
    """A pattern with the learner's progress on it."""
    pattern, extra = _find(conn, pattern_id)
    row = conn.execute(
        "SELECT sessions, last_correct, last_total, practiced_at FROM pattern_progress"
        " WHERE target = ? AND pattern_id = ?",
        (current_language().code, pattern_id),
    ).fetchone()
    return _status(pattern, {**(dict(row) if row else {}), **extra})


@router.post("/patterns/{pattern_id}/exercises", response_model=Exercises)
def write_exercises(pattern_id: str) -> Exercises:
    """New sentences to say for one round of a pattern. They are not stored."""
    pattern = _pattern(pattern_id)
    target, language = current_language(), feedback_language()
    cue = SAME_LANGUAGE_CUE.format(target=target.name, example=target.instruction_example)
    system = EXERCISES_PROMPT.format(
        **_for_prompt(pattern),
        target=target.name,
        language=language,
        count=ROUND,
        cue=cue if target.is_named(language) else "",
        schema=Exercises.model_json_schema(),
    )
    try:
        reply = complete(system, f"Write the {ROUND} sentences.", max_tokens=4000, response_format={"type": "json_object"})
        written = parse_json_reply(reply, Exercises)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Could not write the sentences: {e}") from e
    written.items = written.items[:ROUND]
    return written


@router.post("/patterns/{pattern_id}/check", response_model=Verdict)
def check(pattern_id: str, body: Attempt) -> Verdict:
    """Judge what the learner said for one sentence of a round."""
    pattern = _pattern(pattern_id)
    if _words(body.said) == _words(body.answer):
        # The model answer itself, as heard: nothing to judge.
        return Verdict(correct=True, improved=body.answer)
    target, language = current_language(), feedback_language()
    system = CHECK_PROMPT.format(
        **_for_prompt(pattern),
        target=target.name,
        language=language,
        only_quoted=target.only_quoted(language),
        schema=Verdict.model_json_schema(),
    )
    user = f"Shown to the learner: {body.prompt}\nModel answer: {body.answer}\nThe learner said: {body.said}"
    try:
        reply = complete(
            system, user, max_tokens=2000, response_format={"type": "json_object"}, reasoning_effort="low"
        )
        verdict = parse_json_reply(reply, Verdict)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Could not check the sentence: {e}") from e
    if verdict.correct:
        verdict.explanation = None
    else:
        # Kept with the corrections, to be heard and said again later.
        keep_mistake(pattern.id, pattern.pattern, body.prompt, body.said, verdict.improved, verdict.explanation or "")
    return verdict


@router.post("/patterns/{pattern_id}/results", response_model=PatternStatus)
def save_result(pattern_id: str, body: Result) -> PatternStatus:
    """Record a finished round: how many of its sentences were right at the first try."""
    pattern = _pattern(pattern_id)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO pattern_progress (target, pattern_id, sessions, last_correct, last_total, practiced_at)
            VALUES (?, ?, 1, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            ON CONFLICT (target, pattern_id) DO UPDATE SET
                sessions = sessions + 1, last_correct = excluded.last_correct,
                last_total = excluded.last_total, practiced_at = excluded.practiced_at
            """,
            (current_language().code, pattern_id, body.correct, body.total),
        )
        return _saved(conn, pattern_id)
