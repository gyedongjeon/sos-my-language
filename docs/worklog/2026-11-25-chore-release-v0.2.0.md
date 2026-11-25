---
title: "chore: release v0.2.0"
date: 2026-11-25
branch: chore/release-v0.2.0
request-source: Claude Code session, 2026-11-25
---

## Request

Release what was merged since v0.1.1, so the installed app gets it: the pages in every language a learner can choose, and the changes to the page of a video.

## Changes

- The version is raised from `0.1.1` to `0.2.0` in `backend/pyproject.toml`, `frontend/package.json`, and `desktop/package.json`, with their lock files. It is a MINOR release, because the commits since v0.1.1 include `feat`:
    - The pages are shown in every language of "Your language": 17 more besides English and Korean, translated by AI and not checked by a native speaker (#5).
    - A video can be played on without stopping at the end of a sentence (#6).
    - The subtitles YouTube draws over a video are kept off (#6).
    - The sentence being heard keeps its place when the translation is turned on or off (#6).
- No package or data changes.

## Verification

- `.github/scripts/check-version.sh v0.2.0`: all packages are at 0.2.0.
- `cd backend && uv run pytest`: 311 passed, 16 live tests deselected.
- `cd frontend && npm test`: 235 passed; `npm run build` succeeded.
- `cd desktop && npm test`: 48 passed; `npx tsc --noEmit` succeeded.
- Not verified: the installed apps of this version, which are built by the release workflow after the tag is pushed, and the update from an installed v0.1.1 to it.
