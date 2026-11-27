"""A word the learner taps in a sentence of the language being learned, explained in their own
language by the model. The sentence is sent with it, so the meaning given is the one the word
has there, and a word that is part of a phrase (a verb in two parts, an idiom) is explained as
that phrase. Each explanation is kept, so a word is looked up once in each sentence. A word can
be saved to the learner's list of words, with its sentence and what it means there."""

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
    # Its plural or irregular forms, written short ("pl. cortices"), or "".
    forms: str = ""
    # How the headword is said, in the International Phonetic Alphabet, without marks around it.
    pronunciation: str = ""
    phrase: str
    part_of_speech: str
    meaning: str = Field(min_length=1)
    # The whole sentence in the learner's language ("" when that is the language being learned),
    # and the words of it that stand for the tapped word, as they are written there.
    translation: str = ""
    in_translation: str = ""


class WordLookup(Explained):
    word: str
    # The id this word in this sentence is saved as in the learner's list, or None.
    saved: int | None = None


PROMPT = """\
A learner of {target} reads a sentence in {target} and taps a word they do not know. Explain the
word to them in {language}, their own language, as a good learner's dictionary would, for the
meaning it has in that sentence.

- lemma: the word's dictionary form in {target}, alone, as a dictionary's headword, and never
  the form it has in the sentence when that is another. When the nouns of {target} have a
  gender that an article shows, a noun is given with its article, here and nowhere else. No
  plural, other forms, or notes here; they go in forms.
- forms: what a learner needs to use the phrase (when there is one) or else the dictionary form
  that {target} has, written short in {target} as its dictionaries write it: for a noun its
  plural, for a verb with irregular forms those forms. Just the forms, separated by commas,
  without labels such as "plural" and without the article. An empty string when there is
  nothing to add.
- pronunciation: how the phrase (when there is one) or else lemma is said, exactly as written
  there (not the form in the sentence) and without its article, in the International Phonetic
  Alphabet as a learner's dictionary of {target} gives it, with its stress marks; just the
  symbols, without slashes or brackets around them.
- phrase: when the word means what it does here only together with other words of the sentence
  (a verb whose parts are apart, a phrasal verb, an idiom), that phrase in its dictionary form
  in {target}; otherwise an empty string. When there is one, explain the phrase, not the word.
- part_of_speech: in {language}, one or two words.
- meaning: in {language}, short like a dictionary entry: the meaning it has here first, then at
  most two other common ones, separated by commas.
- translation: the whole sentence translated into natural {language}, keeping its meaning and
  tone; an empty string when {language} is {target}.
- in_translation: the words of your translation that stand for the word (or its phrase), copied
  exactly as they are written in it; an empty string when there are none or no translation.
  Leave out any particle or postposition attached to them that only marks their role in the
  sentence (a case or topic marker); a verb or adjective keeps its endings.

Write part_of_speech, meaning, and translation in {language}. {only_quoted}

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
    found.pronunciation = found.pronunciation.strip().strip("/[]").strip()
    found.meaning = in_own_language(found.meaning, language)
    if found.translation:
        found.translation = in_own_language(found.translation, language)
    # Only words that are there can be shown in it.
    found.in_translation = found.in_translation.strip()
    if found.in_translation not in found.translation:
        found.in_translation = ""
    return found


def explanation(word: str, sentence: str) -> Explained:
    """What a word means in a sentence, in the learner's language; kept once explained, so a
    word is asked for once in each sentence. Raises HTTPException 502 when the model fails."""
    key = (current_language().code, feedback_language(), word, sentence)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT explained FROM word_lookups WHERE target = ? AND language = ? AND word = ? AND sentence = ?",
            key,
        ).fetchone()
    kept = Explained.model_validate_json(row["explained"]) if row else None
    # One kept before the sentence was translated, or before it had a pronunciation or its forms
    # apart from its dictionary form, is asked for again.
    if kept and {"translation", "pronunciation", "forms"} <= kept.model_fields_set:
        return kept
    try:
        found = _explain(word, sentence, key[1])
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Could not look up the word: {e}") from e
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO word_lookups (target, language, word, sentence, explained) VALUES (?, ?, ?, ?, ?)",
            (*key, found.model_dump_json()),
        )
    return found


@router.post("/lookup", response_model=WordLookup)
def look_up(body: LookupRequest) -> WordLookup:
    """What a word means in a sentence, in the learner's language, and whether it is saved."""
    found = explanation(body.word, body.sentence)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM saved_words WHERE target = ? AND word = ? AND sentence = ?",
            (current_language().code, body.word, body.sentence),
        ).fetchone()
    return WordLookup(word=body.word, saved=row["id"] if row else None, **found.model_dump())


class SavedWord(Explained):
    id: int
    headword: str
    word: str
    sentence: str
    saved_at: str


SAVED = (
    "id, headword, word, sentence, lemma, forms, pronunciation, phrase, part_of_speech, meaning,"
    " translation, in_translation, saved_at"
)


@router.get("/words", response_model=list[SavedWord])
def list_words() -> list[SavedWord]:
    """The words the learner saved in the language being learned, the newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT {SAVED} FROM saved_words WHERE target = ? ORDER BY saved_at DESC, id DESC",
            (current_language().code,),
        ).fetchall()
    return [SavedWord(**row) for row in rows]


@router.post("/words", response_model=SavedWord, status_code=201)
def save_word(body: LookupRequest) -> SavedWord:
    """Saves a word with its sentence and what it means there; saved again from the same
    sentence, it is kept once."""
    found = explanation(body.word, body.sentence)
    headword = found.phrase or found.lemma
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO saved_words
                   (target, headword, word, sentence, lemma, forms, pronunciation, phrase, part_of_speech, meaning, translation,
                    in_translation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (target, word, sentence) DO UPDATE SET
                   headword = excluded.headword, lemma = excluded.lemma, forms = excluded.forms,
                   pronunciation = excluded.pronunciation,
                   phrase = excluded.phrase, part_of_speech = excluded.part_of_speech,
                   meaning = excluded.meaning, translation = excluded.translation,
                   in_translation = excluded.in_translation""",
            (
                current_language().code,
                headword,
                body.word,
                body.sentence,
                found.lemma,
                found.forms,
                found.pronunciation,
                found.phrase,
                found.part_of_speech,
                found.meaning,
                found.translation,
                found.in_translation,
            ),
        )
        row = conn.execute(
            f"SELECT {SAVED} FROM saved_words WHERE target = ? AND word = ? AND sentence = ?",
            (current_language().code, body.word, body.sentence),
        ).fetchone()
    return SavedWord(**row)


@router.delete("/words/{word_id}", status_code=204)
def remove_word(word_id: int) -> None:
    """Takes a word off the learner's list."""
    with get_connection() as conn:
        removed = conn.execute(
            "DELETE FROM saved_words WHERE id = ? AND target = ?", (word_id, current_language().code)
        ).rowcount
    if not removed:
        raise HTTPException(status_code=404, detail="No such saved word.")
