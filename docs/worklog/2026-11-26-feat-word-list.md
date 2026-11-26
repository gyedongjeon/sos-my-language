---
title: "feat: save tapped words to a list of words"
date: 2026-11-26
branch: feat/word-list
request-source: Claude Code session, 2026-11-26
---

## Request

Build the word list that word lookup (#11) left for later: a word the learner taps can be saved,
and the saved words can be found again. After seeing the Words page, two more changes were
asked for:

- Drop the line on what the word means in its sentence ("여기서는 …", "이 문장에서는 …") and
  show a translation of the sentence instead.
- Show the word in another color, both in the sentence and in the translation, so it stands out.
- Color the same kind of words in the translation each time. One was colored with its particle
  ("피질의") and another without ("엽").
- Show the IPA of a word for English, and for German too, since German dictionaries give it.

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
- **A translation in place of the note** (this changes the lookup of #11 too):
  - The model no longer writes `in_context`, the line on what the word means in the sentence.
    It translates the whole sentence into the learner's language (`translation`) and names the
    words of that translation that stand for the tapped word (`in_translation`), copied as they
    are written there. This stays one request per word.
  - `in_translation` leaves out a particle or postposition that only marks the word's role in
    the sentence, while a verb or adjective keeps its endings. The prompt had no such rule, so
    the model took the particle with the word in one sentence and not in another. The rule is
    written for any language, as the code must not name one.
  - `in_translation` is trimmed, and left empty when it is not in the translation.
  - An explanation kept before this change has no translation, so it is asked for again.
  - When the learner's language is the language being learned, the translation is empty.
- **IPA**: the model gives how the phrase, or else the dictionary form, is said
  (`pronunciation`), in IPA as a learner's dictionary of the language gives it. It is asked for
  every language, since English and German dictionaries both give it. Slashes or brackets
  around it are taken off, and the page shows it between slashes. An explanation kept without a
  pronunciation is asked for again.
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
  - The word popover and the Words page show the IPA under or next to the headword.
  - The word popover shows the translation, with the words that stand for the tapped word in
    the accent color, in place of the note.
  - The word popover has a "Save" button. Once the word is saved it shows "✓ Saved", and
    pressing it again takes the word off the list. The save and remove logic is
    `toggleSaved` in the `lookup` store.
  - A new **Words** page (`/words`, in the navigation bar after Corrections) lists each saved
    word with its headword, part of speech, meaning, sentence, and the translation, with "Hear
    it" and "Delete" buttons. The tapped word in the sentence and its words in the translation
    are in the accent color. "Hear it" reads the phrase or the word as tapped, not the
    dictionary form with its added forms.
  - `markPart` (`src/words.ts`) finds what to color. The tapped word is matched as a whole word
    in any case, so "a" is not found inside "and". The words of a translation are matched as
    they are written. `MarkedText.vue` shows the text with that part colored.
- **Page texts**: six new keys (`nav.words`, `lookup.save`, `lookup.saved`, `words.intro`,
  `words.none`, `words.remove`) in every page language.
- **READMEs**: a feature line on tapping and saving words in `README.md` and `README.ko.md`;
  the lookup itself had not been mentioned yet.
- **Left for later**:
  - Practising the saved words (cards, spaced repetition).
  - Tapping the words of a sentence on the Words page.
  - Words in the video subtitle lines.

## Verification

- `cd backend && uv run pytest`: 332 passed. In `tests/test_word_lookup.py`, new tests cover:
  - an explanation kept without a translation is asked for again;
  - words said to be in the translation that are not there are left out;
  - those words are given without the spaces around them;
  - an explanation kept without a pronunciation is asked for again;
  - a pronunciation is given without the slashes or brackets around it.
- `uv run --env-file .env pytest -m live -k "tapped_word or two_parts"`: 2 passed. The Korean
  translation is checked, and so is that its words for "cortex" are found in it. On real
  requests, "lobes" was marked as "엽", German "fängt" in "Der Film fängt um acht Uhr an." as
  "시작합니다", and "give" in "I had to give up smoking last year." as "끊어야만". The particle
  of "피질의" was left in.
- With the rule on particles, nine words were tried in Korean and Japanese:
  - Nouns came without their particles: "피질", "엽", "책", "개", "大脳皮質", "犬".
  - Verbs were marked as "끊어야" and "시작합니다" in one run, and only as their stems ("끊",
    "시작") in another. Both are inside the translation, so both are colored.
- Real IPA: "cortex" ˈkɔːrteks, "give up" ɡɪv ʌp, German "anfangen" ˈanˌfaŋən, "Hund" hʊnt,
  "Mädchen" ˈmɛːtçən. The live test now checks that a pronunciation is given.
- New `tests/test_word_list.py` covers:
  - a saved word is listed with its meaning and sentence;
  - a word saved again from its sentence is kept once;
  - a word from another sentence is saved apart, with the meaning it has there;
  - a word in a phrase is saved as the phrase;
  - the words of another language being learned are not listed;
  - a saved word can be removed, and removing it again is a 404;
  - a lookup says whether its word is saved from that sentence;
  - a word that cannot be explained is not saved.
- `cd frontend && npm test`: 256 passed. New tests in `src/stores/lookup.test.ts` cover saving
  the word shown, taking it off, and showing why a save failed. New tests in `src/words.test.ts`
  cover `markPart`. `npm run build` passed.
- Running app, on a copy of the data: a lookup of "cortex" returned `saved: null`. Saving it
  returned id 1, saving it again returned the same id, and the lookup then returned `saved: 1`.
  The list held one word, and deleting it returned 204 and emptied the list.
- The Words page was checked in a browser on a copy of the data, and its layout led to the
  translation change above. The browser automation of this session could not reach the local
  server, so the colored words were not seen by it.
