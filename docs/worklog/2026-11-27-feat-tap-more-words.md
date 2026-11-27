---
title: "feat: tap the words of saved words' sentences and of video sentences"
date: 2026-11-27
branch: feat/tap-more-words
request-source: Claude Code session, 2026-11-27
---

## Request

Make words tappable in two more places that word lookup (#11) and the word list (#12) left for
later: the sentences on the Words page, and the sentences of a video.

## Changes

- **Tidy first**: finding a word among the pieces of a sentence was taken out of `markPart`
  into `findWord` (`frontend/src/words.ts`), so a sentence of buttons can mark a word too (a
  `refactor:` commit of its own).
- **Words page**:
  - Each saved word's sentence is shown with `LookupText`, so its words can be tapped like
    anywhere else.
  - `LookupText` takes a `mark` word, shown in the accent color. On the Words page it is the
    saved word, as before.
  - `markPart` no longer has a whole-word mode, since `LookupText` marks the word now. It only
    marks the words of a translation.
  - The `lookup` store counts the words saved or taken off (`savedChanges`). The Words page
    loads its list again when that count changes. A word saved from a sentence on the page then
    shows up at once, and one taken off goes away.
- **Video sentences**:
  - A line of the sentence list was one `<button>` that plays its sentence. Its words cannot be
    buttons inside it, as a button may not hold another.
  - The line is now a plain element that still plays its sentence when clicked. Its words are
    `LookupText` buttons, which do not pass the click on to the line.
  - The time at the start of the line is the button that plays it from the keyboard. It is
    labelled "Play sentence {n}" (a new key, `video.playSentenceN`, in every page language).
  - Tapping a word while the video plays pauses it. Otherwise the next sentence would scroll
    the list, and scrolling closes the explanation.
  - The translation under a sentence stays plain text.
- **Left for later**: practising the saved words (cards, spaced repetition).

## Verification

- `cd frontend && npm test`: 257 passed.
  - `src/words.test.ts`: `findWord` finds a word whatever its case, not inside another word,
    and not when it is missing. These cases moved over from `markPart`.
  - `src/stores/lookup.test.ts`: `savedChanges` counts a save and a removal, and not a failed
    save.
- `npm run build` passed.
- `cd backend && uv run pytest`: 335 passed (no backend change in this branch).
- On a copy of the data, the app was opened on a saved video and on the Words page for a check
  by hand. The browser automation of this session cannot reach the local server, so it did not
  check them.
