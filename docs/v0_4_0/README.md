# v0.4.0 — Self-Serve Skills

Type `/loop` in any agent CLI to auto-improve. Type `/add-new-features` to extend Clawdibrate. All skill distribution handled by `npx skills add`.

## What Shipped

- **`/add-new-features` skill** — meta-skill that proposes features, creates kanban cards, spawns agents to implement
- **`npx skills add ./skills --all -y` in Setup** — first thing any agent does on bootstrap
- **`/loop` produces PATCH versions only** — MINOR/MAJOR require human decision
- **Skills installed to all 45 agents** — Claude Code, Codex, Cursor, Cline, OpenCode, and 40 more via vercel-labs/skills
- **`skills/` is source of truth** — `.agents/skills/` and agent dirs symlink back

## Contents

- `SPEC.md` — version spec and goals
- `kanban/` — all 3 cards (done)

## See Also

- Top-level changelog: [`docs/CHANGELOG.md`](../CHANGELOG.md)
- Current AGENTS.md: [`AGENTS.md`](../../AGENTS.md)
