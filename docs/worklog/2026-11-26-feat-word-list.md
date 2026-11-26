---
title: "feat: save tapped words to a list of words"
date: 2026-11-26
branch: feat/word-list
request-source: Claude Code session, 2026-11-26
---

## Request

Build the word list that word lookup (#11) left for later: a word the learner taps can be saved,
and the saved words can be found again.

## Changes

- **Tidy first**: the cached explanation of a word was taken out of the `/lookup` route into
  `explanation()` in `backend/app/word_lookup.py`, so saving a word reuses it (a `refactor:`
  commit of its own).
- **Backend** (`backend/app/word_lookup.py`):
  - `POST /api/words` takes a word and its sentence, the same as `/lookup`. It explains the word
    through the same cache, so a word already looked up is not asked for again, and saves it.
    A model failure returns 502 and saves nothing.
  - `GET /api/words` lists the saved words of the language being learned, the newest first.
  - `DELETE /api/words/{id}` takes a word off the list (404 for an unknown one).
  - `/lookup` now says whether the word in that sentence is saved (`saved`: its id, or null).
- **Table**: a new `saved_words` table. It keeps the word, its sentence, the headword (the
  phrase, or else the dictionary form), and the explanation, in the language it was explained
  in. It carries `target` and is added to the test of tables that do.
- **One entry for each word in each sentence**: the key is the word and its sentence, the same
  as for a lookup. Keying by the headword was tried first and rejected: when the app was run,
  the model's dictionary form came back with forms added ("cortex (plural cortices)"). The same
  word could come back written another way from the next sentence, and the same word in another
  sentence may mean something else anyway. Saved again from the same sentence, a word is kept
  once.
- **Frontend**:
  - The word popover has a "Save" button. Once the word is saved it shows "✓ Saved", and
    pressing it again takes the word off the list. The save and remove logic is
    `toggleSaved` in the `lookup` store.
  - A new **Words** page (`/words`, in the navigation bar after Corrections) lists each saved
    word with its headword, part of speech, meaning, sentence, and what it means there, with
    "Hear it" and "Delete" buttons. "Hear it" reads the phrase or the word as tapped, not the
    dictionary form with its added forms.
- **Page texts**: six new keys (`nav.words`, `lookup.save`, `lookup.saved`, `words.intro`,
  `words.none`, `words.remove`) in every page language.
- **READMEs**: a feature line on tapping and saving words in `README.md` and `README.ko.md`;
  the lookup itself had not been mentioned yet.
- **Left for later**:
  - Practising the saved words (cards, spaced repetition).
  - Tapping the words of a sentence on the Words page.
  - Words in the video subtitle lines.

## Verification

- `cd backend && uv run pytest`: 329 passed. New `tests/test_word_list.py` covers:
  - a saved word is listed with its meaning and sentence;
  - a word saved again from its sentence is kept once;
  - a word from another sentence is saved apart, with the meaning it has there;
  - a word in a phrase is saved as the phrase;
  - the words of another language being learned are not listed;
  - a saved word can be removed, and removing it again is a 404;
  - a lookup says whether its word is saved from that sentence;
  - a word that cannot be explained is not saved.
- `cd frontend && npm test`: 253 passed. New tests in `src/stores/lookup.test.ts`: saving the
  word shown, taking it off, and showing why a save failed. `npm run build` passed.
- Running app, on a copy of the data: a lookup of "cortex" returned `saved: null`. Saving it
  returned id 1, saving it again returned the same id, and the lookup then returned `saved: 1`.
  The list held one word, and deleting it returned 204 and emptied the list.
- The popover button and the Words page were not checked in a browser: the browser used in
  this session could not reach the local server.
