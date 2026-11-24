"""The languages the app teaches. To add one, write a package like `english` or `german` next to
them and list its `Language` here; the tests in `tests/test_languages.py` say what is missing."""

from .base import LEVELS, Language, Pattern, Voice
from .english import ENGLISH
from .german import GERMAN

# In the order they are offered. The first is the one used until the learner has chosen.
LANGUAGES: dict[str, Language] = {language.code: language for language in (ENGLISH, GERMAN)}
DEFAULT = ENGLISH

__all__ = ["DEFAULT", "LANGUAGES", "LEVELS", "Language", "Pattern", "Voice"]
