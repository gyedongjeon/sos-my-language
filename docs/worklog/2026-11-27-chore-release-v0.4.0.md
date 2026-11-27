---
title: "chore: release v0.4.0"
date: 2026-11-27
branch: chore/release-v0.4.0
request-source: Claude Code session, 2026-11-27
---

## Request

Release what was merged since v0.3.0, so the installed app gets it: tapping a word to see what
it means, and the list of saved words.

## Changes

- The version is raised from `0.3.0` to `0.4.0` in `backend/pyproject.toml`,
  `frontend/package.json`, and `desktop/package.json`, with their lock files. It is a MINOR
  release, because the commits since v0.3.0 include `feat`:
    - Tap a word in a correction or in the partner's lines to see what it means in that
      sentence, in the learner's language (#11).
    - Save a tapped word to the new Words page, with its sentence (#12). The explanation now
      gives a translation of the sentence, the word in the accent color in the sentence and in
      the translation, its IPA, and its dictionary form with its plural or irregular forms
      apart.
    - Tap the words of the sentences on the Words page and of a video's sentences. A tap while
      the video plays pauses it (#13).
- Saved data: two new tables, `word_lookups` (#11) and `saved_words` (#12). They are created
  when the app starts, and nothing that was saved before changes. No package changes.

## Verification

- `.github/scripts/check-version.sh v0.4.0`: all packages are at 0.4.0.
- `cd backend && uv run pytest`: 335 passed, 18 live tests deselected.
- `cd frontend && npm test`: 257 passed. `npm run build` succeeded.
- `cd desktop && npm test`: 48 passed. `npx tsc --noEmit` succeeded.
- Not verified:
    - The installed apps of this version, which the release workflow builds after the tag is
      pushed.
    - The update from an installed v0.3.0 to this version.
