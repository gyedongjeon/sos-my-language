"""The tutor's side of a spoken conversation: the next line, and a fix for what was just said."""

import string
from typing import Literal

from pydantic import BaseModel, Field

from .db import current_language
from .llm import complete, format_conversation, parse_json_reply
from .own_language import in_own_language
from .settings import feedback_language

SPEAKERS = {"tutor": "Tutor", "learner": "Learner"}


class Message(BaseModel):
    role: Literal["tutor", "learner"]
    text: str = Field(min_length=1)


class Correction(BaseModel):
    original: str = Field(description="The phrase or sentence the learner said, quoted as-is.")
    improved: str = Field(description="A more correct or natural way to say it, in the language being practised.")
    explanation: str = Field(description="Why the improved version is better.")


class TutorReply(BaseModel):
    reply: str = Field(min_length=1, description="The tutor's next line, in the language being practised.")
    correction: Correction | None = Field(
        default=None, description="The most valuable fix to the learner's latest message, or null."
    )


SYSTEM_PROMPT = """\
You are a friendly {target} conversation partner helping a non-native speaker practice
speaking. You are having a spoken conversation in this situation:
{situation}

You will get the conversation so far. The learner spoke their lines aloud; you see
speech-recognition transcripts. Punctuation, capitalization, and spelling were chosen by the
recognizer, not by the learner. Never correct punctuation, capitalization, or spelling, and
do not treat an obvious recognition error (a word that makes no sense where a
similar-sounding word would) as the learner's mistake.

reply: stay in the situation and respond to what the learner just said, then keep the
conversation going, usually with one question.{address} Keep it easy to follow by ear: one or two
short sentences in natural, everyday {target} at a level slightly above the learner's.
Plain text only, with no formatting, because it is read aloud to the learner as-is. Do not
correct the learner here.

correction: look only at the learner's latest message. If it has a grammar mistake, a wrong
word, or phrasing a fluent speaker would not use, give the single most valuable fix: quote
what they said, give the better version, and explain why in one or two sentences of
{language}. If it is
already fine, or the only difference would be punctuation or capitals, use null; do not
invent a problem. In "explanation", talk about what to say, not how to write it.

Write "explanation" in {language}, the learner's own language, whatever language the
conversation is in: the learner reads it in {language}, and {target} examples may be quoted
inside it. {only_quoted} Keep "reply", "original", and "improved" in {target}.

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""


def _spoken(text: str) -> list[str]:
    """The words of a sentence as they are heard: no punctuation at their edges, no capitals."""
    words = (word.strip(string.punctuation + "“”‘’…") for word in text.lower().replace("’", "'").split())
    return [word for word in words if word]


def tutor_reply(situation: str, messages: list[Message]) -> TutorReply:
    """Return the tutor's next line and a correction for the learner's latest message."""
    target, language = current_language(), feedback_language()
    system = SYSTEM_PROMPT.format(
        situation=situation,
        target=target.name,
        # The languages that have no rule for it leave no gap in the sentence.
        address=f" {target.address}" if target.address else "",
        language=language,
        only_quoted=target.only_quoted(language),
        schema=TutorReply.model_json_schema(),
    )
    reply = complete(
        system,
        format_conversation([(SPEAKERS[m.role], m.text) for m in messages]),
        max_tokens=4000,
        response_format={"type": "json_object"},
        # A short line needs little reasoning; keep the wait short.
        reasoning_effort="low",
    )
    result = parse_json_reply(reply, TutorReply)
    fix = result.correction
    if fix and _spoken(fix.original) == _spoken(fix.improved):
        # Only punctuation or capitals changed, which the learner cannot say.
        result.correction = None
    elif fix:
        fix.explanation = in_own_language(fix.explanation, language)
    return result
