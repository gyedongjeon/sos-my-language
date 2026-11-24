"""A review of a finished conversation: how it went, and what to practice next."""

from pydantic import BaseModel, Field

from .conversation import SPEAKERS, Correction
from .llm import complete, parse_json_reply
from .settings import feedback_language

# A review is read at a glance after speaking; each of its lists is cut to this many items.
MAX_ITEMS = 3


class Phrase(BaseModel):
    english: str = Field(min_length=1, description="An expression that would have fit this conversation, in English.")
    note: str = Field(description="What it means or when to use it.")


class Review(BaseModel):
    summary: str = Field(min_length=1, description="Two or three sentences on how the conversation went.")
    strengths: list[str] = Field(default=[], description="What the learner did well.")
    focus: list[str] = Field(default=[], description="What to work on next.")
    phrases: list[Phrase] = Field(default=[], description="Expressions worth learning for this situation.")


SYSTEM_PROMPT = """\
You are a friendly English conversation partner. A non-native speaker has just finished
practising a spoken conversation with you in this situation:
{situation}

You will get the whole conversation. The learner spoke their lines aloud; you see
speech-recognition transcripts, so never comment on punctuation, capitalization, or spelling.
Under some of the learner's lines is the correction they were shown at the time.

Write a short review that the learner reads right after speaking. Talk to the learner as "you".
Be specific to what was actually said, and honest: praise only what was really done well.

summary: two or three sentences on how the conversation went as a whole.
strengths: up to {max_items} things you did well, each one short sentence that quotes or points
at something you said. Quote only your own words as you said them, never a corrected version.
focus: up to {max_items} things to work on next, most valuable first, each one short sentence.
Look for patterns across the conversation (a mistake made more than once, very short answers,
the same word used again and again) rather than repeating every correction one by one. Use an
empty list if there is nothing worth working on.
phrases: up to {max_items} natural English expressions you did not use but could have used in
this conversation. "english" is the expression as it would be said; "note" says what it means
or when to use it.

Write "summary", "strengths", "focus", and every "note" in {language}: the learner reads them
in {language}, and English examples may be quoted inside them. Keep "english" in English.

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""


def _transcript(lines: list[tuple[str, str, Correction | None]]) -> str:
    """The conversation as text, with each correction under the line it was made on."""
    text = []
    for role, said, fix in lines:
        text.append(f"{SPEAKERS[role]}: {said}")
        if fix:
            text.append(f'  (corrected: "{fix.original}" -> "{fix.improved}")')
    return "\n".join(text)


def write_review(situation: str, lines: list[tuple[str, str, Correction | None]]) -> Review:
    """Review a conversation given as (role, text, correction) lines in the order they were said."""
    system = SYSTEM_PROMPT.format(
        situation=situation, language=feedback_language(), max_items=MAX_ITEMS, schema=Review.model_json_schema()
    )
    reply = complete(
        system,
        _transcript(lines),
        max_tokens=4000,
        response_format={"type": "json_object"},
        # Written once, when the conversation is over, so a longer wait than a turn's is fine.
        timeout=60,
    )
    review = parse_json_reply(reply, Review)
    review.strengths = review.strengths[:MAX_ITEMS]
    review.focus = review.focus[:MAX_ITEMS]
    review.phrases = review.phrases[:MAX_ITEMS]
    return review
