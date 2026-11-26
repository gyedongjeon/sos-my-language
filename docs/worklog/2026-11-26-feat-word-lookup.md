---
title: "feat: tap a word to see what it means"
date: 2026-11-26
branch: feat/word-lookup
request-source: Claude Code session, 2026-11-26
---

## Request

Make it easy to find what each word means, in the learner's own language. Today a word like
"cortex" in a correction card has to be looked up in a dictionary by hand. After discussing
selecting words (drag or double-click) against tapping them, tapping a word was chosen. The
first version only looks words up; saving them to a word list comes later.

## Changes

- **Backend**: `POST /api/lookup` (`backend/app/word_lookup.py`) takes a word and the sentence
  it is in, and the model explains it in the feedback language. It returns:
  - the dictionary form, with an article and plural or irregular forms where the language
    has them;
  - the phrase the word belongs to in that sentence, such as a German verb in two parts or an
    English phrasal verb;
  - the part of speech, a short dictionary-style meaning (the one it has here first), and one
    line on what it means in this sentence.

  The sentence is sent so that the meaning is the one the word has there. The prompt names no
  language; what differs comes from `Language` (`only_quoted`). A meaning or note in the wrong
  language is written again through `in_own_language`. A word that is not in its sentence is
  refused with 422, and a model failure returns 502 and is not kept.
- **Cache**: a new `word_lookups` table, keyed by `target`, feedback language, word, and
  sentence. A word is asked for once per sentence, and asked again after the feedback language
  changes. It is added to the test of tables that carry `target`.
- **Frontend**:
  - `splitWords` (`src/words.ts`) cuts a sentence into words and the text between them. It
    keeps short forms and hyphenated words whole, works with any alphabet, and leaves numbers
    out.
  - `LookupText.vue` shows a sentence with each word as a button.
  - A `lookup` store keeps the word tapped last. An answer to an earlier tap, or one that
    arrives after the popover was closed, is not shown.
  - `WordPopover.vue`, in `App.vue`, shows the explanation next to the word, with a button to
    hear it. It stays inside the window and opens above the word when there is no room below.
    Tapping elsewhere, Escape, scrolling, or changing page closes it.
- **Where words can be tapped**: the sentence of each correction card on the Corrections page,
  the partner's lines in Practice and in past conversations, and the better sentence of the
  correction card in a conversation.
- **Page texts**: three new keys (`lookup.word`, `lookup.looking`, `lookup.dialog`) in every
  page language.
- **Rejected or left for later**:
  - Selecting text, rejected: tapping is quicker, and the model finds phrases from the sentence.
  - An offline dictionary, rejected: few learner languages have one, and it cannot tell which
    meaning a word has in the sentence.
  - Video subtitle lines, left for later: each line is already a button that plays it, so
    tappable words need their own change.
  - A word list, left for later.

## Verification

- `cd backend && uv run pytest`: 321 passed. New `tests/test_word_lookup.py` covers:
  - the explanation is in the feedback language, and the sentence is sent;
  - an explanation is kept and not asked for again;
  - a word is asked for again in another feedback language, and in another language being
    learned;
  - a phrase is returned;
  - a failure returns 502 and is not kept;
  - a word that is not in its sentence is refused.
- `uv run --env-file .env pytest -m live -k "tapped_word or two_parts"`: 2 passed. "cortex" is
  explained in Korean with an English dictionary form, and German "fängt" in "Der Film fängt
  um acht Uhr an." is given the phrase "anfangen".
- `cd frontend && npm test`: 250 passed (new `src/words.test.ts`, `src/stores/lookup.test.ts`).
  `npm run build` passed.
- Running app, on a copy of the data: `POST /api/lookup` for "cortex" and "lobes" in a saved
  shadowing sentence answered in Korean in about 2 s. The same word again answered from the
  cache in about 10 ms. The popover itself was not checked in a browser in this session.
