"""Corrections from saved conversations, practised by saying the better sentence aloud."""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from .conversation import _spoken
from .db import get_connection

router = APIRouter(prefix="/api")

# Short forms that are spelled differently from their words, and the ones that follow no rule.
IRREGULAR = {"won't": "will not", "can't": "can not", "cannot": "can not", "shan't": "shall not", "let's": "let us"}
ENDINGS = {"n't": " not", "'m": " am", "'re": " are", "'ve": " have", "'ll": " will"}
# After these words "'s" is "is" and "'d" is "would" far more often than anything else; after any
# other word "'s" is left alone, because it usually marks an owner ("my friend's car").
PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "that", "there", "here", "what", "who", "where", "how"}


# Speech recognition writes small numbers as figures or as words; both are heard the same.
NUMBERS = dict(
    zip(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
        "sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety".split(),
        [*map(str, range(21)), "30", "40", "50", "60", "70", "80", "90"],
        strict=True,
    )
)


class SavedCorrection(BaseModel):
    """A sentence to practise again: a correction made in a saved conversation, a sentence got
    wrong in pattern practice, or one of a video not said right after it. It also says how often
    it was practised since."""

    # "m" and the id of the learner's line it was made on, or "p" or "s" and the id of the mistake.
    id: str
    # Where it comes from: one of the three is set, or none for a sentence of a video since
    # deleted. `title` is the conversation's title, the pattern's formula, or the video's title.
    conversation_id: int | None = None
    pattern_id: str | None = None
    video: int | None = None
    # For a shadowing mistake: where the sentence stands in its video.
    position: int | None = None
    title: str
    # For a pattern mistake: the sentence that was to be said in English.
    prompt: str | None = None
    original: str
    improved: str
    explanation: str
    # How many times the better sentence was said correctly, and when it last was.
    practiced: int
    practiced_at: str | None


class AttemptRequest(BaseModel):
    text: str = Field(min_length=1, description="What the learner said, as transcribed.")


class Attempt(BaseModel):
    matched: bool
    # Words of the better sentence that were not heard, in its order.
    missing: list[str]
    practiced: int


def _words(text: str) -> list[str]:
    """The words of a sentence as heard: short forms spelled out, so "I'm" equals "I am", and
    small numbers as figures, so "three" equals "3"."""
    words: list[str] = []
    for word in _spoken(text):
        stem, apostrophe, ending = word.rpartition("'")
        if word in IRREGULAR:
            word = IRREGULAR[word]
        elif apostrophe and stem in PRONOUNS and ending in ("s", "d"):
            word = f"{stem} {'is' if ending == 's' else 'would'}"
        else:
            for short, full in ENDINGS.items():
                if word.endswith(short) and len(word) > len(short):
                    word = word.removesuffix(short) + full
                    break
        words.extend(NUMBERS.get(part, part) for part in word.split())
    return words


def _contains(said: list[str], wanted: list[str]) -> bool:
    """Whether the wanted words were said one after another, in order."""
    return any(said[i : i + len(wanted)] == wanted for i in range(len(said) - len(wanted) + 1))


def _missing(said: list[str], wanted: list[str]) -> list[str]:
    left = list(said)
    missing = []
    for word in wanted:
        if word in left:
            left.remove(word)
        else:
            missing.append(word)
    return missing


# Where each kind of correction is stored, by the letter its id starts with: the table, and the
# column that holds the better sentence.
KINDS = {
    "m": ("messages", "correction_improved"),
    "p": ("pattern_mistakes", "improved"),
    "s": ("shadowing_mistakes", "improved"),
}
NOW = "strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"


def _locate(correction_id: str) -> tuple[str, str, int]:
    """The table, the column of the better sentence, and the row a correction's id stands for."""
    kind, number = correction_id[:1], correction_id[1:]
    if kind not in KINDS or not number.isdecimal():
        raise HTTPException(status_code=404, detail="Correction not found")
    return (*KINDS[kind], int(number))


@router.get("/corrections", response_model=list[SavedCorrection])
def list_corrections() -> list[SavedCorrection]:
    """Every correction of the saved conversations, every sentence got wrong in pattern practice,
    and every sentence of a video not said right after it, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT 'm' || m.id AS id, m.conversation_id, NULL AS pattern_id, NULL AS video,
                   NULL AS position, c.title, NULL AS prompt,
                   m.correction_original AS original, m.correction_improved AS improved,
                   m.correction_explanation AS explanation, m.practiced, m.practiced_at,
                   COALESCE(m.corrected_at, c.started_at) AS made_at, m.id AS row
            FROM messages m JOIN conversations c ON c.id = m.conversation_id
            WHERE m.correction_improved IS NOT NULL AND m.dismissed = 0
            UNION ALL
            SELECT 'p' || id, NULL, pattern_id, NULL, NULL, pattern, prompt, said, improved, explanation,
                   practiced, practiced_at, created_at, id
            FROM pattern_mistakes
            UNION ALL
            SELECT 's' || s.id, NULL, NULL, l.video, l.position, s.title, NULL, s.said, s.improved,
                   s.explanation, s.practiced, s.practiced_at, s.created_at, s.id
            FROM shadowing_mistakes s LEFT JOIN video_lines l ON l.id = s.line
            ORDER BY made_at DESC, row DESC
            """
        ).fetchall()
    return [SavedCorrection(**{key: row[key] for key in row.keys() if key not in ("made_at", "row")}) for row in rows]


@router.post("/corrections/{correction_id}/attempts", response_model=Attempt)
def attempt(correction_id: str, body: AttemptRequest) -> Attempt:
    """Check what the learner said against the better sentence; a match is counted as practice."""
    table, improved, row_id = _locate(correction_id)
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {improved} AS improved, practiced FROM {table} WHERE id = ? AND {improved} IS NOT NULL", (row_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Correction not found")
        said, wanted = _words(body.text), _words(row["improved"])
        matched = _contains(said, wanted)
        if matched:
            conn.execute(f"UPDATE {table} SET practiced = practiced + 1, practiced_at = {NOW} WHERE id = ?", (row_id,))
    return Attempt(
        matched=matched,
        missing=[] if matched else _missing(said, wanted),
        practiced=row["practiced"] + matched,
    )


@router.delete("/corrections/{correction_id}", status_code=204)
def remove(correction_id: str) -> Response:
    """Take a correction off the list. One made in a conversation stays in that conversation."""
    table, improved, row_id = _locate(correction_id)
    with get_connection() as conn:
        if table == "messages":
            gone = conn.execute(
                f"UPDATE messages SET dismissed = 1 WHERE id = ? AND {improved} IS NOT NULL AND dismissed = 0",
                (row_id,),
            )
        else:
            gone = conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
    if gone.rowcount == 0:
        raise HTTPException(status_code=404, detail="Correction not found")
    return Response(status_code=204)


def keep_mistake(pattern_id: str, pattern: str, prompt: str, said: str, improved: str, explanation: str) -> None:
    """Keep a sentence got wrong in pattern practice. A new wrong try at the same sentence
    replaces what was said, and it has to be practised again."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO pattern_mistakes (pattern_id, pattern, prompt, said, improved, explanation)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (pattern_id, prompt) DO UPDATE SET
                pattern = excluded.pattern, said = excluded.said, improved = excluded.improved,
                explanation = excluded.explanation, practiced = 0, practiced_at = NULL,
                created_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """,
            (pattern_id, pattern, prompt, said, improved, explanation),
        )
