---
title: "fix: explain a correction in the learner's language when the model does not"
date: 2026-11-24
branch: fix/explanation-language
request-source: found while making screenshots, chat session, 2026-11-24
---

## Request

While screenshots of the app were made, a correction in a German conversation was explained in
German although Korean was the learner's language. Find out how often that happens and stop it.

## Changes

- **Measured first.** The same German lines were sent to the real model (Gemini 3.1 Flash Lite,
  Korean as the learner's language) through the running server: 5 of 45 corrections were
  explained in German, every one of them on the same line ("Ich möchte ein Kaffee mit Milch und
  eine Croissant bitte", an explanation of a noun's gender).
- **Rewording the prompt did not settle it.** Naming the learner's language at the start of the
  prompt and again after the conversation gave 3 of 45, and 5 of 30 on that one line; naming it
  in the reply's schema as well gave 10 of 30. Those changes were dropped: none was clearly
  better than chance.
- **Checked and written again instead** (`backend/app/own_language.py`). An explanation is known
  by its letters: when the learner's language is Korean, Japanese, Chinese, Russian, Ukrainian,
  Thai, Hindi, or Bengali and the explanation has no letter of that script, it is sent to the
  model once more to be translated, with the quoted words left in the language practised. If
  that request fails or its answer is again in the wrong script, the first explanation is kept.
  It is applied to the correction of a conversation and to the verdict of a pattern sentence,
  before either is saved, so the Corrections page has the readable one too.
- **What it costs**: one more short request for about one correction in ten; none otherwise.
- **Not covered**: a learner's language written in Latin letters (Spanish, French, ...) cannot be
  told from German or English by its letters, so those rely on the prompt as before. The review
  of a conversation and the note of a pattern round are not checked; no wrong one was seen.

## Verification

- `cd backend && uv run pytest`: 294 passed, 16 live tests deselected. `tests/test_own_language.py`
  is new: telling a text by its script, writing it again, keeping it when that fails, and both
  places it is applied, with no second request when the first explanation is right.
- Against the real model through the running server, with the check in place: 40 of 40
  corrections of the line that failed before were explained in Korean.
- `uv run --env-file .env pytest -m live` after the change: 16 passed.
- Not verified: languages other than Korean with the real model.
