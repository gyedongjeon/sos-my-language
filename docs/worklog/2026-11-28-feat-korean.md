---
title: "feat: add Korean as a language to practise"
date: 2026-11-28
branch: feat/korean
request-source: Claude Code session, 2026-11-28
---

## Request

Add Korean as a new language that can be practised, next to English and German.

## Changes

- **Korean package** (`backend/app/languages/korean/`), listed in `languages/__init__.py`:
  - Code `ko`, locale `ko-KR`, the multilingual Whisper `small` model, subtitles `ko`/`ko-KR`.
  - An opening line for each of the 40 built-in topics.
  - 100 sentence patterns (20/20/20/20/12/8 from A1 to C2, the same split as English and
    German). They are placed by the TOPIK levels 1 to 6 and the International Standard
    Curriculum of Korean, read as A1 to C2. They are written in Korean grammar notation
    ("V-(으)ㄹ 수 있어요").
  - How the partner speaks to the learner: 해요체 by default, 반말 only between close friends,
    family, or classmates, and 합쇼체 where staff or officials would use it.
  - Native Korean numbers said on their own ("셋") are heard as figures. The forms before a
    counter ("세") and the Sino-Korean ones are left out, since each is also a common word
    ("이" is "this", "일" is "work", "네" is "yes").
- **A third voice engine, Supertonic 3**:
  - Kokoro and Piper have no Korean voice. The options were to add a local engine or to leave
    Korean to the browser's voice, whose quality depends on the OS (Windows needs a Korean
    language pack). The local engine was chosen in the session.
  - The `supertonic` package (MIT) loads the model from the app's own `tts/supertonic-3/`
    folder with `auto_download=False`. The app downloads the files itself, like the Piper
    voices, so the download shows its progress and leaves no partial files.
  - The files come from the `supertone-oss-archive/supertonic-3` repository on Hugging Face,
    pinned to commit `aafc6e32`. Supertonic's makers archived the project in September 2026
    and point to that archive. Its model is under OpenRAIL-M. Like Piper's voices, it is not
    part of the repository or the installer.
  - The ten voices, F1 to F5 and M1 to M5, share six model files (~398 MB). Each voice adds a
    style file of ~290 KB. F1 is the default.
  - `Language`'s `voices` now accept `supertonic(...)`, and `speech.model_files` can return
    more than two files, kept in subfolders.
- **Page texts**: 34 of the patterns' "use" notes were new. They were added to all 18
  `content.<language>.json` files. Korean was written by hand; the other 17 languages were
  translated by AI, like the rest of those files. The other 66 notes reuse ones that English or
  German already had.
- **README** and **README.ko.md**: Korean among the languages, its download size, its voices,
  the Supertonic licence, and the known limits below.
- **Left for later**:
  - Spoken answers are compared word by word. In Korean, a space that speech recognition leaves
    out or adds ("할수 있어요") counts as a word not heard.
  - An explanation written in Korean, when the learner's own language uses Latin letters,
    cannot be caught by its letters and sent back to be translated.

## Verification

- `cd backend && uv run pytest`: 343 passed. New tests in `tests/test_languages.py`:
  - `test_the_korean_partner_is_told_which_speech_level_to_use`
  - `test_the_built_in_topics_open_in_korean`
  - `test_korean_numbers_are_heard_as_figures`
  - `test_korean_lines_are_read_by_a_supertonic_voice` (a fake Supertonic, 44.1 kHz WAV)
  - `test_supertonic_voices_share_one_model_and_each_has_its_own_style`
  - `test_a_supertonic_voice_is_downloaded_from_the_archive_of_the_model`
  - The checks that apply to every language now also cover Korean: openers for every topic,
    patterns at every level, voices, and page texts in every content file.
- `cd frontend && npm test`: 257 passed. `npm run build` passed.
- The file sizes in `base.py` and `korean/__init__.py` match the archive's file listing at the
  pinned commit.
- With the real model, downloaded from the pinned archive URLs into a scratch data folder,
  `speech.synthesize` read a Korean line with F1 and produced a 44.1 kHz WAV (~3 s on this
  machine). Nobody has listened to it yet, so the quality of the voice is unchecked.
