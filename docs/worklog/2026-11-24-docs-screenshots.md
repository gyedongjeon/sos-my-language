---
title: "docs: add screenshots of the app to the READMEs"
date: 2026-11-24
branch: docs/screenshots
request-source: chat session, 2026-11-24
---

## Request

The READMEs had no pictures: the screenshots of `sos-my-english` were left out when
`sos-my-language` was started. Add screenshots of this app. The app icon stays the one taken
over from `sos-my-english`.

## Changes

- `docs/images/` has five screenshots, 1200 pixels wide:
  - `language.png`: the first start, asking which language to practise.
  - `home.png` and `conversation.png`: the pages in English, practising English.
  - `home.ko.png` and `conversation.ko.png`: the pages in Korean, practising German, with the
    corrections explained in Korean.
- `README.md` shows the conversation under the introduction, the language question under "First
  setup", and the home page at the start of "How it works". `README.ko.md` shows the two Korean
  ones, under the introduction and at the start of the instructions.
- The conversations are real ones, held for the pictures: the learner's lines were sent as text
  (with made-up clarity and pace, since nothing was spoken) and the partner's replies and the
  corrections came from the model (Gemini 3.1 Flash Lite). The page shown is a saved
  conversation in History, which looks like a conversation in progress without its buttons.
- The pictures were taken from a server running the fix of `fix/explanation-language`: without
  it, the first German correction came out explained in German, which is what led to that fix.

## Verification

- Each picture was looked at after it was taken: the texts are in the language meant, the two
  corrections of each conversation are shown, and nothing personal is on them (a new data
  folder, no key or name on any page).
- The five image links of the two READMEs point at files that exist in `docs/images/`.
- Not verified: how the READMEs are drawn on GitHub with the pictures.
