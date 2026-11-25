---
title: "feat: show the pages in every language a learner can choose"
date: 2026-11-25
branch: feat/page-languages
request-source: Claude Code session, 2026-11-25
---

## Request

When "Your language" is changed, the texts of the pages (menus, buttons, notes) should change to that language for every language offered, as they already do for Korean. A translation that reads a little oddly is acceptable; a check by native speakers is out of reach for now, so the translation should simply be as good as it can be made.

## Changes

- **Texts of the pages in 17 more languages**: Japanese, Simplified Chinese, Traditional Chinese, Spanish, French, German, Italian, Portuguese, Polish, Russian, Ukrainian, Turkish, Vietnamese, Thai, Indonesian, Hindi, and Bengali each got a `frontend/src/i18n/<code>.ts` (every key of `en.ts`) and a `content.<code>.json` (the built-in topics, categories, pattern notes, and voice words). With English and Korean, every language of `LANGUAGES` in the settings store now has its pages.
- **How they were translated**: by AI, one language at a time, from `en.ts` with `ko.ts` as the model of how free a translation may be. They have not been checked by a native speaker. Rules given for every language:
    - `{language}` is filled with the uninflected name from `lang.*`, so each sentence is worded to take that one form (a colon or brackets in Polish, Russian, and Ukrainian; no suffix on it in Turkish).
    - `one | many` has two forms only, so languages with more plural forms use one wording that fits any number ("Sentences: {n}").
    - The two sentences split around a link are worded so the page's name fits in the middle unchanged.
- **`index.ts`** lists every language file; a language without one would still fall back to English.
- **The note under "Your language"** no longer says the pages are in English and Korean only. It now says that most languages were translated by AI and not checked by a native speaker.
- **Tests**: the check that Korean has every text with the same names to fill in became `files.test.ts`, which runs for every language file it finds and also checks the number of forms, the leading ` · ` of appended texts, and that each `content.<code>.json` has the same texts. `index.test.ts` checks that every language of `LANGUAGES` has its pages.
- **Docs**: `README.md`, `README.ko.md`, and `AGENTS.md` say that the pages are in every language offered and which of them are AI translations; "Adding a language for the pages" describes the rules above.

Considered and left out:

- Loading a language's texts only when it is chosen. All of them are bundled instead, which takes the script from about 243 kB to about 971 kB; the app is served from the same computer, and `t()` stays a plain function.
- German: `lang.unknown` ("der Lernsprache") does not fit after "auf", which the sentences use for "auf Englisch / auf Deutsch". It is only said before a language to practise is chosen.

## Verification

- `cd frontend && npm test`: 230 tests pass, among them the checks of each of the 18 language files and 18 content files.
- `cd frontend && npm run build`: the type check passes (a file lacking a key of `en.ts` is refused).
- `cd backend && uv run pytest`: 311 pass; `test_page_texts.py` finds every built-in text of the backend in each `content.<code>.json`.
- Not done: looking at the pages in each language in the running app, and a reading by native speakers.
