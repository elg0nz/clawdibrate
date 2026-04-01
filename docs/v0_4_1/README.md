# v0.4.1 — Fix skills install vs git tracking conflict

`npx skills add` was clobbering git-tracked files in `skills/`, causing persistent dirty state. Untracked `skills/` from git so the install command can manage it freely.

## What Shipped

- **Untracked `skills/` from git index** — `skills/` was already in `.gitignore` but two files were still tracked from before the ignore rule was added
- **`src/skills/` remains source of truth** — edit there, `npx skills add ./src/skills --all -y` distributes

## See Also

- Top-level changelog: [`docs/CHANGELOG.md`](../CHANGELOG.md)
- Current AGENTS.md: [`AGENTS.md`](../../AGENTS.md)
