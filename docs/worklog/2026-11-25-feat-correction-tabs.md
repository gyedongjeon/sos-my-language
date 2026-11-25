---
title: "feat: keep expressions and shadowing apart on the Corrections page"
date: 2026-11-25
branch: feat/correction-tabs
request-source: Claude Code session, 2026-11-25
---

## Request

The Corrections page mixes two different things: better sentences the learner was given in
conversations (and pattern practice), and sentences of a video the learner did not say in full
after it. Keep them apart, under tabs, before adding blind practice of the corrections, since
each kind will be practised in its own way.

## Changes

- **Backend**: each item of `GET /api/corrections` has a `kind`: `expression` for a correction
  of a conversation or a sentence got wrong in pattern practice, `shadowing` for a sentence of a
  video. The page no longer has to tell them apart by the first letter of the id.
- **Frontend**:
  - The corrections store keeps the tab shown (`kind`), the corrections of that tab (`ofKind`),
    what is left to practise in it (`remaining`) and in each tab (`left`). It opens on the
    shadowing tab when there are no expressions but there are sentences of videos.
  - The Corrections page has two tabs, "Expressions" and "Shadowing", each with the number left
    to practise, and a line of its own when it is empty. The counts and "Show the ones already
    said right" are for the tab shown.
  - A sentence of a video shows the sentence, then "Heard:" and what was heard, not crossed out:
    what was heard is not a wrong sentence but what speech recognition made of the try.
  - The new texts are in every language of the pages (translated by AI, except English and
    Korean); the shadowing tab uses each language's existing name for saying after a video.
- **Docs**: `README.md` and `README.ko.md` name the two tabs.

Considered and left out:

- Moving the sentences of videos to the Videos page, to practise them with the video's own sound.
  The sentences would then be in two places, and would go with a deleted video; the link to the
  sentence in its video already gives its own sound.
- The "Not heard: …" line of a sentence of a video is still in English, as before; it is written
  by the backend, whose texts are in English for now.

## Verification

- `cd backend && uv run pytest`: 314 passed (the tests listing each kind of correction now check
  its `kind`).
- `cd frontend && npm test`: 241 passed (2 new store tests: the tabs and their counts, and the
  tab opened first); `npm run build` passes.
- In the running app (dev servers on a copy of the data, with two pattern mistakes added to the
  copy): both tabs were looked at during review and accepted.
