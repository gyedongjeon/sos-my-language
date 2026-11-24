"""English, as the app teaches it."""

from ..base import Language, kokoro
from .openers import OPENERS
from .patterns import PATTERNS

# Short forms that are spelled differently from their words, and the ones that follow no rule.
IRREGULAR = {"won't": "will not", "can't": "can not", "cannot": "can not", "shan't": "shall not", "let's": "let us"}
ENDINGS = {"n't": " not", "'m": " am", "'re": " are", "'ve": " have", "'ll": " will"}
# After these words "'s" is "is" and "'d" is "would" far more often than anything else; after any
# other word "'s" is left alone, because it usually marks an owner ("my friend's car").
PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "that", "there", "here", "what", "who", "where", "how"}

NUMBERS = dict(
    zip(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
        "sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety".split(),
        [*map(str, range(21)), "30", "40", "50", "60", "70", "80", "90"],
        strict=True,
    )
)


def spell_out(word: str) -> str:
    """Short forms spelled out, so "I'm" equals "I am"."""
    stem, apostrophe, ending = word.rpartition("'")
    if word in IRREGULAR:
        return IRREGULAR[word]
    if apostrophe and stem in PRONOUNS and ending in ("s", "d"):
        return f"{stem} {'is' if ending == 's' else 'would'}"
    for short, full in ENDINGS.items():
        if word.endswith(short) and len(word) > len(short):
            return word.removesuffix(short) + full
    return word


ENGLISH = Language(
    code="en",
    name="English",
    native="English",
    locale="en-US",
    # The English-only model hears English better than the multilingual one of the same size.
    whisper_model="small.en",
    subtitles=("en", "en-US", "en-GB", "en-CA", "en-AU", "en-IN"),
    abbreviations=frozenset({"mr.", "mrs.", "ms.", "dr.", "st.", "vs.", "e.g.", "i.e.", "etc."}),
    spell_out=spell_out,
    numbers=NUMBERS,
    # Kokoro's English voices that sound natural, best first within each accent. Another Kokoro
    # voice can still be set with TTS_VOICE; its prefix gives the accent: "a" American, "b" British.
    voices=(
        kokoro("af_heart", "Heart · American · female"),
        kokoro("af_bella", "Bella · American · female"),
        kokoro("af_nicole", "Nicole · American · female · soft"),
        kokoro("af_sarah", "Sarah · American · female"),
        kokoro("am_michael", "Michael · American · male"),
        kokoro("am_fenrir", "Fenrir · American · male"),
        kokoro("am_puck", "Puck · American · male"),
        kokoro("bf_emma", "Emma · British · female"),
        kokoro("bf_isabella", "Isabella · British · female"),
        kokoro("bm_george", "George · British · male"),
        kokoro("bm_fable", "Fable · British · male"),
    ),
    sample="Hi! It's nice to see you. How has your week been so far?",
    openers=OPENERS,
    patterns=PATTERNS,
    pattern_slots='"+ verb", "+ -ing", "+ past participle", "+ noun", or "…"',
    pattern_example=(
        'from "I should have left earlier" with "should have left" marked: "should have + past participle"'
    ),
    instruction_example="Say that you regret not leaving earlier.",
)
