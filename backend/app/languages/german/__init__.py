"""German, as the app teaches it."""

from ..base import Language, piper
from .openers import OPENERS
from .patterns import PATTERNS

# Words are compared with "ß" spelled "ss", so "dreißig" is listed as "dreissig".
NUMBERS = dict(
    zip(
        "null eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf dreizehn vierzehn fünfzehn "
        "sechzehn siebzehn achtzehn neunzehn zwanzig dreissig vierzig fünfzig sechzig siebzig achtzig neunzig".split(),
        [*map(str, range(21)), "30", "40", "50", "60", "70", "80", "90"],
        strict=True,
    )
)
# "zwo" is said for "zwei" to tell it from "drei".
NUMBERS["zwo"] = "2"


def spell_out(word: str) -> str:
    """ "'s" spelled out, so "geht's" equals "geht es", and "ß" as "ss", as Swiss German writes it."""
    word = word.replace("ß", "ss")
    if word.endswith("'s") and len(word) > 2:
        # Spoken German shortens "es" after a verb or a question word: "wie geht's?"
        return word.removesuffix("'s") + " es"
    return word


GERMAN = Language(
    code="de",
    name="German",
    native="Deutsch",
    locale="de-DE",
    whisper_model="small",
    subtitles=("de", "de-DE", "de-AT", "de-CH"),
    abbreviations=frozenset(
        {"dr.", "hr.", "fr.", "prof.", "nr.", "ca.", "bzw.", "usw.", "etc.", "evtl.", "ggf.", "vgl.", "z.b.", "d.h.", "u.a."}
    ),
    spell_out=spell_out,
    numbers=NUMBERS,
    # Kokoro has no German voice. These are Piper's German voices with one speaker each, best
    # first: Thorsten is the only one in high quality; the others are in low quality, Eva in the
    # lowest. Another Piper voice can still be set with TTS_VOICE.
    voices=(
        piper("de_DE-thorsten-high", "Thorsten · male · best quality", 113_895_201 + 4_875),
        piper("de_DE-kerstin-low", "Kerstin · female", 63_104_526 + 4_158),
        piper("de_DE-ramona-low", "Ramona · female", 63_104_526 + 4_157),
        piper("de_DE-eva_k-x_low", "Eva · female · lower quality", 20_628_813 + 4_158),
        piper("de_DE-karlsson-low", "Karlsson · male", 63_104_526 + 4_159),
        piper("de_DE-pavoque-low", "Pavoque · male", 63_104_526 + 4_158),
    ),
    sample="Hallo! Schön, dich zu sehen. Wie war deine Woche bisher?",
    openers=OPENERS,
    patterns=PATTERNS,
    pattern_slots='"+ infinitive", "+ past participle", "+ noun", "+ dative", "verb at the end", or "…"',
    pattern_example=(
        'from "Ich hätte früher gehen sollen" with "hätte … gehen sollen" marked: "hätte + infinitive + sollen"'
    ),
    instruction_example="Sag, dass du bereust, nicht früher gegangen zu sein.",
    address=(
        'Use "du" or "Sie" as the situation calls for (friends, family, and classmates say "du"; staff, '
        'officials, and strangers say "Sie"), and keep to it.'
    ),
    opener_address='Use "du" or "Sie" as the situation calls for.',
    text_address='Say "du" to the learner.',
)
