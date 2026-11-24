"""The built-in topics, categories, pattern notes, and what is said of a voice are kept in English by the backend and
shown in the learner's language by the frontend, which has them by their English text. A text
added or changed here has to be added there too."""

import json
from pathlib import Path

import pytest

from app.db import CATEGORIES, SEED_TOPICS
from app.languages import LANGUAGES
from app.patterns import OWN_LEVEL

PAGE_TEXTS = Path(__file__).parent.parent.parent / "frontend" / "src" / "i18n"
CONTENT = sorted(PAGE_TEXTS.glob("content.*.json"))


def built_in() -> set[str]:
    texts = {*CATEGORIES, OWN_LEVEL}
    for title, situation, _ in SEED_TOPICS:
        texts |= {title, situation}
    for language in LANGUAGES.values():
        texts |= {pattern.use for pattern in language.patterns}
        # What is said of a voice after its name: "Emma · British · female".
        texts |= {part for voice in language.voices for part in voice.label.split(" · ")[1:]}
    return texts


def test_the_built_in_texts_are_written_in_another_language():
    assert CONTENT, f"No content.<language>.json in {PAGE_TEXTS}"


@pytest.mark.parametrize("path", CONTENT, ids=lambda path: path.name)
def test_every_built_in_text_is_there_in_each_language_of_the_pages(path):
    written = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(built_in() - set(written))
    assert not missing, f"{path.name} lacks: {missing}"
    assert all(text.strip() for text in written.values())
