---
title: "chore: release v0.5.0"
date: 2026-11-28
branch: chore/release-v0.5.0
request-source: Claude Code session, 2026-11-28
---

## Request

Release what was merged since v0.4.0, so the installed app gets it: Korean as a language to
practise.

## Changes

- The version is raised from `0.4.0` to `0.5.0` in `backend/pyproject.toml`,
  `frontend/package.json`, and `desktop/package.json`, with their lock files. It is a MINOR
  release, because the commits since v0.4.0 include `feat`:
    - Korean as a third language to practise, with opening lines for the built-in topics, 100
      sentence patterns, and the partner's speech level (#15).
    - Korean is read aloud by Supertonic 3, a new local voice engine with ten voices. Its model
      (~400 MB) is downloaded the first time Korean is practised (#15).
    - Spoken Korean is compared by its letters, whatever spaces speech recognition puts. An
      explanation written in Korean when the learner's own language uses Latin letters is
      sent back to be translated (#16).
- Saved data: no new tables. Rows for Korean carry `ko` in the existing `target` column, and
  nothing that was saved before changes.
- Packages: a new Python package, `supertonic` (with `soundfile`). The desktop app starts the
  backend with `uv run --frozen`, which installs it on the first launch after the update. That
  launch needs an internet connection.

## Verification

- `.github/scripts/check-version.sh v0.5.0`: all packages are at 0.5.0.
- `cd backend && uv run pytest`: 355 passed, 18 live tests deselected.
- `cd frontend && npm test`: 257 passed. `npm run build` succeeded.
- `cd desktop && npm test`: 48 passed. `npx tsc --noEmit` succeeded.
- Not verified:
    - The installed apps of this version, which the release workflow builds after the tag is
      pushed.
    - The update from an installed v0.4.0 to this version, including the install of the new
      package on its first launch.
