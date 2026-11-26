"""A word the learner taps in a sentence of the language being learned, explained in their own
language by the model. The sentence is sent with it, so the meaning given is the one the word
has there, and a word that is part of a phrase (a verb in two parts, an idiom) is explained as
that phrase. Each explanation is kept, so a word is looked up once in each sentence."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from .db import current_language, get_connection
from .llm import LLMError, complete, parse_json_reply
from .own_language import in_own_language
from .settings import feedback_language

router = APIRouter(prefix="/api")


class LookupRequest(BaseModel):
    word: str = Field(min_length=1, max_length=100)
    sentence: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def word_in_sentence(self):
        self.word, self.sentence = self.word.strip(), self.sentence.strip()
        if not self.word or self.word.lower() not in self.sentence.lower():
            raise ValueError("The word is not in the sentence.")
        return self


class Explained(BaseModel):
    lemma: str = Field(min_length=1)
    phrase: str
    part_of_speech: str
    meaning: str = Field(min_length=1)
    in_context: str


class WordLookup(Explained):
    word: str


PROMPT = """\
A learner of {target} reads a sentence in {target} and taps a word they do not know. Explain the
word to them in {language}, their own language, as a good learner's dictionary would, for the
meaning it has in that sentence.

- lemma: the word's dictionary form in {target}, as a dictionary lists it, with what a learner
  needs to use it that the language has: for a noun its article and plural, for a verb with
  irregular forms those forms. Just the form, nothing else, when there is nothing to add.
- phrase: when the word means what it does here only together with other words of the sentence
  (a verb whose parts are apart, a phrasal verb, an idiom), that phrase in its dictionary form
  in {target}; otherwise an empty string. When there is one, explain the phrase, not the word.
- part_of_speech: in {language}, one or two words.
- meaning: in {language}, short like a dictionary entry: the meaning it has here first, then at
  most two other common ones, separated by commas.
- in_context: one short sentence in {language} on what it means in this sentence.

Write part_of_speech, meaning, and in_context in {language}. {only_quoted}

Reply with a single JSON object matching this schema, and nothing else:
{schema}"""


def _explain(word: str, sentence: str, language: str) -> Explained:
    target = current_language()
    reply = complete(
        PROMPT.format(
            target=target.name,
            language=language,
            only_quoted=target.only_quoted(language),
            schema=Explained.model_json_schema(),
        ),
        f"Sentence: {sentence}\nWord: {word}",
        max_tokens=1000,
        response_format={"type": "json_object"},
        reasoning_effort="low",
    )
    found = parse_json_reply(reply, Explained)
    found.meaning = in_own_language(found.meaning, language)
    found.in_context = in_own_language(found.in_context, language)
    return found


@router.post("/lookup", response_model=WordLookup)
def look_up(body: LookupRequest) -> WordLookup:
    """What a word means in a sentence, in the learner's language; kept once explained."""
    key = (current_language().code, feedback_language(), body.word, body.sentence)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT explained FROM word_lookups WHERE target = ? AND language = ? AND word = ? AND sentence = ?",
            key,
        ).fetchone()
    if row:
        return WordLookup(word=body.word, **Explained.model_validate_json(row["explained"]).model_dump())
    try:
        found = _explain(body.word, body.sentence, key[1])
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Could not look up the word: {e}") from e
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO word_lookups (target, language, word, sentence, explained) VALUES (?, ?, ?, ?, ?)",
            (*key, found.model_dump_json()),
        )
    return WordLookup(word=body.word, **found.model_dump())
