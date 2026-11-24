# Versioning: Semantic Versioning

This project follows [Semantic Versioning 2.0.0](https://semver.org/). A version is written
`MAJOR.MINOR.PATCH`, for example `0.1.0`.

## What Each Number Means

The app has no public API, so "compatible" is judged from the user's side: their saved data and
the way they install and run the app.

| Part | Raise it when | Examples |
| :--- | :--- | :--- |
| **MAJOR** | A release breaks something the user relies on | Saved data (`app.db`) cannot be read without manual steps; a feature is removed; a new requirement to run the app |
| **MINOR** | A release adds something and existing use keeps working | A new page, a new provider, a new setting |
| **PATCH** | A release only fixes or polishes | Bug fixes, wording, styling, dependency updates with no visible change |

Raising a number resets the ones to its right to zero (`0.3.2` → `0.4.0`).

## From Commits to a Version

The commit types in [commit-convention.md](commit-convention.md) decide the next version. Take
the highest bump among the commits since the last release:

| Commits since the last release | Bump |
| :--- | :--- |
| Any breaking change: `!` after the type (`feat!: ...`) or a `BREAKING CHANGE:` footer | MAJOR |
| At least one `feat` | MINOR |
| Only `fix`, `perf`, `refactor`, `style`, `build`, or `chore` | PATCH |
| Only `docs`, `test`, or `ci` | No release needed |

## Before 1.0.0

While the version is `0.y.z`, the app is still taking shape and anything may change:

- A breaking change raises **MINOR** instead of MAJOR (`0.3.2` → `0.4.0`).
- New features still raise MINOR and fixes still raise PATCH.
- `1.0.0` is released by decision, once the app is stable enough that breaking saved data
  should be rare and announced.

## One Version for the Whole Project

The backend, frontend, and desktop app are released together and always carry the same version.
It is written in three files, which must match:

- `backend/pyproject.toml` (`version`)
- `frontend/package.json` (`version`)
- `desktop/package.json` (`version`) — this one names the built app and its `.dmg`

## Releasing

Versions are raised at release time, not in every PR.

1. On a branch, set the new version in the three files above and refresh the lock files:
   ```bash
   (cd frontend && npm version <version> --no-git-tag-version)
   (cd desktop && npm version <version> --no-git-tag-version)
   # edit `version` in backend/pyproject.toml, then:
   (cd backend && uv lock)
   ```
2. Commit as `chore: release v<version>` and merge through a PR as usual.
3. Tag the merge commit on `main` with a `v` prefix and push the tag:
   ```bash
   git tag -a v<version> -m "v<version>"
   git push origin v<version>
   ```

4. Pushing the tag starts `.github/workflows/release.yml`. It checks that the tag matches the
   version in the three files, runs the tests, builds the macOS installer (`.dmg`) and the
   archive the app updates itself from (`.zip`), and publishes a GitHub Release with both
   attached and generated release notes. Installed apps offer the new version to their users
   once the release is marked as the latest. If the
   check or a test fails, nothing is published; fix it on `main` and release a new version.

Tags are never moved or reused. A mistake in a release is fixed by a new version.
