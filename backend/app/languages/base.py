"""What the app has to know about a language to teach it. Everything that differs from one
language to the next is in a `Language`; the rest of the app asks the one being learned."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Size of the two files every Kokoro voice is in, for showing download progress.
KOKORO_BYTES = 325_532_387 + 28_214_398


@dataclass(frozen=True)
class Pattern:
    id: str
    level: str
    # The pattern as a formula, what it is used for, and one sentence that shows it.
    pattern: str
    use: str
    example: str


def level(level: str, *rows: tuple[str, str, str, str]) -> list[Pattern]:
    return [Pattern(id, level, pattern, use, example) for id, pattern, use, example in rows]


@dataclass(frozen=True)
class Voice:
    id: str
    label: str
    # The program that speaks with it: "kokoro" or "piper".
    engine: str
    # Bytes downloaded the first time it is chosen.
    size: int


def kokoro(id: str, label: str) -> Voice:
    """A Kokoro voice. All of them are in the same two files, so one download brings them all."""
    return Voice(id, label, "kokoro", KOKORO_BYTES)


def piper(id: str, label: str, size: int) -> Voice:
    """A Piper voice, named <language>_<REGION>-<name>-<quality>; each has two files of its own."""
    return Voice(id, label, "piper", size)


@dataclass(frozen=True)
class Language:
    # Kept in the database with everything learned in the language, and Whisper's name for it.
    code: str
    # What the prompts and the pages call it, in English ("German"), and its own name ("Deutsch").
    name: str
    native: str
    # The browser's voice that reads a line when the app's own voice cannot.
    locale: str
    # The Whisper model that hears it; the ".en" models know English only.
    whisper_model: str
    # The subtitle tracks of a YouTube video that are in it, best first.
    subtitles: tuple[str, ...]
    # A full stop after one of these does not end a sentence. In lower case.
    abbreviations: frozenset[str]
    # A spoken word as it is heard, so that two spellings of the same sounds are equal: short
    # forms spelled out ("I'm" as "i am"). It gets a word in lower case.
    spell_out: Callable[[str], str]
    # Small numbers as words, with their figures: speech recognition writes either.
    numbers: Mapping[str, str]
    # The partner's voices, the default first.
    voices: tuple[Voice, ...]
    # A line to hear a voice with before choosing it.
    sample: str
    # The partner's first line of each built-in topic, by the topic's title.
    openers: Mapping[str, str]
    patterns: tuple[Pattern, ...]
    # How to name the slots of a pattern made from a sentence, with an example of one.
    pattern_slots: str
    pattern_example: str
    # What a drill's sentence is shown as when the learner's own language is this one: an
    # instruction, since there is nothing to translate from.
    instruction_example: str
    # How the partner addresses the learner, where the language makes a difference of it: in a
    # conversation, in the first line of the learner's own topic, and in that of a text's topic.
    address: str = ""
    opener_address: str = ""
    text_address: str = ""

    @property
    def default_voice(self) -> str:
        return self.voices[0].id

    def is_named(self, language: str) -> bool:
        """Whether a language given by its English name, as the feedback language is, is this one."""
        return language.strip().lower() == self.name.lower()

    def only_quoted(self, language: str) -> str:
        """A rule for a prompt whose text the learner reads in their own language: after a
        conversation in the language being learned the model tends to go on in it. Empty when
        the two are the same language."""
        if self.is_named(language):
            return ""
        return f"Do not use {self.name} for it, apart from {self.name} words and examples quoted in {language}."
