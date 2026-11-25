---
title: "chore: release v0.3.0"
date: 2026-11-25
branch: chore/release-v0.3.0
request-source: Claude Code session, 2026-11-25
---

## Request

Release what was merged since v0.2.0, so the installed app gets it: the theme choice and the tabs of the Corrections page.

## Changes

- The version is raised from `0.2.0` to `0.3.0` in `backend/pyproject.toml`, `frontend/package.json`, and `desktop/package.json`, with their lock files. It is a MINOR release, because the commits since v0.2.0 include `feat`:
    - Settings has an "Appearance" card: follow the system's light or dark mode, or keep the pages light or dark (#8).
    - The Corrections page has two tabs: "Expressions", the better sentences from conversations and pattern practice, and "Shadowing", the sentences of videos not said in full after them (#9).
- No package or data changes.

## Verification

- `.github/scripts/check-version.sh v0.3.0`: all packages are at 0.3.0.
- `cd backend && uv run pytest`: 314 passed, 16 live tests deselected.
- `cd frontend && npm test`: 241 passed; `npm run build` succeeded.
- `cd desktop && npm test`: 48 passed; `npx tsc --noEmit` succeeded.
- Not verified: the installed apps of this version, which are built by the release workflow after the tag is pushed, and the update from an installed v0.2.0 to it.
