# Branching Strategy: GitHub Flow

Our project follows the **GitHub Flow** strategy to ensure simplicity and speed. Releases are cut from `main` by tagging, as described in [versioning.md](versioning.md).

## Core Principles

1.  **The `main` branch is always releasable.**
    *   Avoid committing directly to `main`.
    *   All code in `main` must be tested and stable.

2.  **To work on something new, create a descriptive branch from `main`.**
    *   Use clear and concise names for branches.
    *   Examples: `feat/setup-project`, `fix/login-bug`, `docs/add-readme`.

3.  **Commit and push to your branch regularly.**
    *   Pushing your work to the remote repository backs up your work and shares your progress with the team.

4.  **Open a Pull Request (PR) when you need feedback or are ready to merge.**
    *   PRs are for discussion, code review, and final checks.
    *   Provide a clear description of your changes in the PR.

5.  **Merge into `main` after review and approval.**
    *   Merge only after all checks pass and at least one team member has approved the PR.
    *   **Always create a merge commit when merging into `main` (use `--no-ff` / No Fast-Forward).** Do not perform fast-forward merges to preserve the branching history.

6.  **Delete the feature branch once it has been merged.**

7.  **Release by tagging `main`, not by merging.**
    *   Merged work collects on `main` until it is worth releasing; a merge does not release anything by itself.
    *   A release is a `v`-prefixed version tag on a merge commit of `main`. Pushing the tag builds and publishes the installer. See [versioning.md](versioning.md).
    *   There are no `develop`, `release`, or `hotfix` branches. An urgent fix is a `fix/` branch merged into `main` and released as the next patch version.

## Branch Naming Convention

*   `feat/`: New features or enhancements.
*   `fix/`: Bug fixes.
*   `docs/`: Documentation changes (README, architecture docs, etc.).
*   `refactor/`: Code changes that neither fix a bug nor add a feature.
*   `test/`: Adding or correcting tests.
*   `chore/`: Updates to build tasks, package manager configs, etc.

## Merge Strategy

To ensure a clear, traceable commit history:
*   **Command Line Merge**: When merging branches locally, always use the `--no-ff` flag to force a merge commit:
    ```bash
    git merge --no-ff <branch-name>
    ```
*   **GitHub Pull Requests**: Select "Create a merge commit" (not Squash or Rebase) when merging Pull Requests, ensuring all branch history is kept.
