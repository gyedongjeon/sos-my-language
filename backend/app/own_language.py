"""Texts for the learner are written by the model in the learner's own language. After lines in
the language being practised the model at times goes on in that language, whatever it is told;
such a text is noticed by its script, where the two languages are written differently, and
written again."""

import re

from pydantic import BaseModel, Field

from .db import current_language
from .llm import LLMError, complete, parse_json_reply

# A letter that only the language has, by the name the learner's language is saved under. A
# language written with Latin letters cannot be told from the one practised this way.
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_HAN = re.compile(r"[一-鿿]")
SCRIPTS = {
    "Korean": re.compile(r"[가-힣]"),
    "Japanese": re.compile(r"[぀-ヿ]"),
    "Simplified Chinese": _HAN,
    "Traditional Chinese": _HAN,
    "Russian": _CYRILLIC,
    "Ukrainian": _CYRILLIC,
    "Thai": re.compile(r"[฀-๿]"),
    "Hindi": re.compile(r"[ऀ-ॿ]"),
    "Bengali": re.compile(r"[ঀ-৿]"),
}


class Rewritten(BaseModel):
    text: str = Field(min_length=1, description="The same text, in the language asked for.")


PROMPT = """\
You get a short note that a teacher of {target} wrote for a learner. It should have been written
in {language}, the learner's own language. Translate it into {language}, keeping its meaning and
its length. Words and examples in {target} that the note quotes stay in {target}, in their
quotation marks.

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""


def looks_written_in(text: str, language: str) -> bool:
    """Whether a text can be in a language, going by its letters. True when that cannot be told."""
    script = SCRIPTS.get(language.strip())
    return script is None or not text.strip() or bool(script.search(text))


def in_own_language(text: str, language: str) -> str:
    """A text for the learner, written again in their language when it is in another. When that
    fails, the text as it was: better a note in the wrong language than none."""
    if looks_written_in(text, language):
        return text
    try:
        reply = complete(
            PROMPT.format(target=current_language().name, language=language, schema=Rewritten.model_json_schema()),
            text,
            max_tokens=2000,
            response_format={"type": "json_object"},
            reasoning_effort="low",
        )
        rewritten = parse_json_reply(reply, Rewritten).text.strip()
    except LLMError:
        return text
    return rewritten if looks_written_in(rewritten, language) else text
