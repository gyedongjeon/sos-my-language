---
title: "chore: release v0.1.1"
date: 2026-11-24
branch: chore/release-v0.1.1
request-source: chat session, 2026-11-24
---

## Request

Release the fix for corrections explained in the wrong language, so the installed app gets it.

## Changes

- The version is raised from `0.1.0` to `0.1.1` in `backend/pyproject.toml`,
  `frontend/package.json`, and `desktop/package.json`, with their lock files. It is a PATCH
  release, because the only code commit since v0.1.0 is a `fix`:
    - A correction, or the verdict on a pattern sentence, that the model explained in the
      language being practised instead of the learner's own is noticed by its script and
      translated once (#2).
- Also on `main` since v0.1.0, with nothing in it for the installed app: the screenshots in the
  READMEs (#3).
- No package or data changes.

## Verification

- `.github/scripts/check-version.sh v0.1.1`: all packages are at 0.1.1.
- `cd backend && uv run pytest`: 294 passed, 16 live tests deselected.
- `cd frontend && npm test`: 140 passed; `npm run build` succeeded.
- `cd desktop && npm test`: 48 passed; `npx tsc --noEmit` succeeded.
- Not verified: the installed apps of this version, which are built by the release workflow
  after the tag is pushed, and the update from an installed v0.1.0 to it.
