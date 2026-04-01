# v0.4.2 — Fix skills tracking and conversation logging

Codex `/loop` run failed because `git status` showed phantom deletes and path references were inconsistent. Fixed all three issues.

## What Shipped

- **Untracked `skills/` from git index** — files were tracked before `.gitignore` rule, `npx skills add` clobbered them
- **Fixed `skills/` → `src/skills/` everywhere** — AGENTS.md, CHANGELOG, v0.4.0 README all corrected
- **Gitignored `.conversations/`** — session logs are runtime data, not source
- **Backfilled conversation logs** — v0.2.0→v0.4.0 and v0.4.1 sessions now in `.conversations/`

## See Also

- Top-level changelog: [`docs/CHANGELOG.md`](../CHANGELOG.md)
- Current AGENTS.md: [`AGENTS.md`](../../AGENTS.md)
