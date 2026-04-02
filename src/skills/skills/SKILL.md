---
name: clawdbrt:skills
description: "Externalized AGENTS.md heading 'Skills' as clawdbrt:skills (clawdibrate auto-extract)."
---

# Skills

Slash commands route to `SKILL.md` files in `src/skills/`. All skills use the `clawdbrt:` namespace prefix.

**Registration:** One directory per skill in `src/skills/`, each containing a `SKILL.md` with YAML frontmatter (`name: clawdbrt:<skill-name>`). Run `npx skills add ./src/skills --agent <detected-agents> --skill '*' -y` to distribute to `skills/` and `.agents/`.

**After `npx skills add`, commit `skills-lock.json` and any updated files in `skills/` and `.agents/` alongside the source skill.**

**Interface:** Every skill must have `name` (with `clawdbrt:` prefix) and `description` in frontmatter. The body is agent instructions.

**Canonical source:** `src/skills/` is source of truth. `skills/` and `.agents/skills/` are install outputs — never edit them directly, but always commit them. **Always use `src/skills/` in all references — never `skills/`, `.agents/skills/`, or other variants.**

**All new capabilities must be implemented as skills.** The loop, kanban, feature generation, and implementation are all skills — not standalone scripts.

**Skills:**
- `/clawdbrt:loop` — runs the tuning loop, produces PATCH versions (`src/skills/loop/SKILL.md`)
- `/clawdbrt:kanban` — manages cards in `docs/vX_Y_Z/kanban/` (`src/skills/kanban/SKILL.md`)
- `/clawdbrt:add-new-features` — proposes and builds new features as MINOR versions (`src/skills/add-new-features/SKILL.md`)
- `/clawdbrt:implement` — reads kanban board, implements cards by priority with parallel agents (`src/skills/implement/SKILL.md`)
- `/clawdbrt:scores` — show calibration scoreboard for a repo or all tracked repos (`src/skills/scores/SKILL.md`)

**Section skills:** When a section scores below 0.7 across 3+ runs, or has churn ≥ 3 in git history, create a dedicated skill for it. Name it after the section: `src/skills/<kebab-section-name>/SKILL.md`. The skill body is the expanded, step-by-step version of the rule — more context than fits in the instruction file. Reference it from the section: `See /clawdbrt:<skill-name> for detailed guidance.` This externalizes complexity without bloating the instruction file.
