# Pull Request Convention

To ensure high-quality reviews and a clear project history, all Pull Requests (PRs) should follow this convention.

## PR Title Format
Follow the same convention as our commit messages:
`<type>[optional scope]: <description>`

Examples:
- `feat(auth): add password reset flow`
- `docs: update PR convention document`
- `fix(api): handle empty response from server`

See [commit-convention.md](commit-convention.md) for the full list of types.

## Worklog is the Source of Truth
In this repository, the **branch worklog file is the source of truth for the PR** (see the Worklog rules in [AGENTS.md](../../AGENTS.md)):

- **PR title** = the worklog `title` field.
- **PR description** = the worklog body (from `## Request` down).

Generate the PR from the worklog file, never the other way around. If scope changes during review, update the worklog first, then sync the PR description to match.

## PR Description Template
GitHub automatically applies the template at [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md) when you open a PR. Use it as a fallback checklist; for changes driven by a worklog, the worklog body takes precedence over the template sections.

## PR Process
1. **Atomic PRs**: Keep PRs focused on a single task or feature.
2. **Draft PRs**: Use Draft PRs for work-in-progress if you need early feedback.
3. **Reviewers**: Tag relevant team members for review.
4. **Approval**: At least one approval is required before merging into `main` (for team projects).
