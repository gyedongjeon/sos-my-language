---
title: "feat: hear Korean whatever its spaces, and catch explanations written in Korean"
date: 2026-11-28
branch: feat/korean-practice
request-source: Claude Code session, 2026-11-28
---

## Request

Two follow-ups to adding Korean (#15), both left for later there:

1. Ignore spacing when what the learner said is compared, for Korean.
2. Catch a correction's explanation that the LLM wrote in Korean when the learner's own language
   is written in Latin letters, so that it is sent back to be translated.

## Changes

- **Tidy first**: corrections and shadowing each took the words of a sentence out of what was
  said, one at a time. That step is now one class, `Heard` in `corrections.py`, used by both.
  This is a `refactor:` commit of its own, with no change in behaviour.
- **Spaces in Korean**:
  - `Language` has a new field, `spaces_heard`, which is true by default and false for Korean.
    Whisper often leaves out the spaces of Korean or adds some ("할수 있어요" for
    "할 수 있어요"). Those spaces come from speech recognition, not from the learner.
  - Where `spaces_heard` is false, what was said is compared by its letters:
    - Saying a correction again: the sentence must appear among the letters said, wherever
      the spaces fall.
    - Words not heard: `Heard` looks for each word among the letters said. A word taken from
      the middle leaves the letters on either side apart, so they cannot run together into a
      word that was not said.
    - Shadowing a video sentence: the same, through `Heard`.
    - A pattern answer that matches the model answer apart from its spaces is right without
      asking the LLM.
    - A correction from the partner that changes only spaces is dropped, like one that changes
      only punctuation or capitals. The new `alike` in `conversation.py` makes this check for
      corrections and for pattern answers.
  - English and German keep comparing word by word.
- **Explanations written in Korean**:
  - Until now, `looks_written_in` only checked that a text had letters of the learner's own
    language. With English as the learner's language it could not tell anything.
  - When the language practised has letters of its own (Korean), a text written mostly in
    those letters is now taken as not in the learner's language, unless the learner's language
    is the same one or shares those letters. Quoting Korean in an English or Japanese
    explanation is still fine.
- **README**: the shadowing section says that Korean is compared by its letters. The "Your
  language" section says which explanations in Korean are now caught.

## Verification

- `cd backend && uv run pytest`: 355 passed. New tests:
  - `tests/test_languages.py`:
    - `test_korean_is_said_right_whatever_spaces_speech_recognition_puts`. It also checks the
      words not heard, and that letters left on either side of a heard word do not make
      another.
    - `test_english_words_still_need_their_spaces`
    - `test_a_correction_of_spaces_alone_is_dropped_in_korean`
    - `test_a_pattern_answer_said_with_other_spaces_is_right_without_asking_the_model`
    - `test_a_korean_video_sentence_is_shadowed_whatever_the_spaces`
  - `tests/test_own_language.py`:
    - `test_a_text_in_the_letters_of_the_language_practised_is_known_when_it_has_its_own`.
      Korean prose fails for English, Spanish, and Japanese. Korean quoted in English or
      Japanese passes. Korean for a Korean learner passes.
    - `test_an_explanation_in_korean_is_written_again_in_english`
- Each new test was run before its change and failed for the expected reason. Spoken answers
  counted words as missing, the spacing-only correction was kept, the pattern check went to the
  LLM (502 in the test), shadowing scored 33, and the Korean explanation was left as it was.
- No frontend change; the frontend tests were not run again.
