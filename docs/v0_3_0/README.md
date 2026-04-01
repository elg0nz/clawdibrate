# v0.3.0 — Skills Architecture

Introduces a skills-based architecture. AGENTS.md gets a skill router. The tuning loop and kanban management become invocable skills. Built on `vercel-labs/skills` (SKILL.md format).

## What Shipped

- **Skills section in AGENTS.md** — routes `/loop` and `/kanban` to `skills/` directory
- **`skills/loop/SKILL.md`** — runs the self-improvement tuning loop
- **`skills/kanban/SKILL.md`** — creates/manages kanban cards in `docs/vX_Y_Z/kanban/`
- **`vercel-labs/skills` installed** — 7 community skills in `.claude/skills/`
- **Boundary rule** — no commit without version README complete
- **Kanban conventions** — ticket naming `clwdi-vMAJOR_MINOR_PATCH-NNN.md`, icebox carry-forward

## Contents

- `SPEC.md` — version spec and goals
- `skill-router-draft.md` — draft used to build the Skills section
- `vercel-skills.md` — research doc on vercel-labs/skills framework
- `kanban/` — all 7 cards (done)

## See Also

- Top-level changelog: [`docs/CHANGELOG.md`](../CHANGELOG.md)
- Current AGENTS.md: [`AGENTS.md`](../../AGENTS.md)
