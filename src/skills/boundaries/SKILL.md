---
name: clawdbrt:boundaries
description: "Externalized AGENTS.md heading 'Boundaries' as clawdbrt:boundaries (clawdibrate auto-extract)."
---

# Boundaries

- ✅ Use latest `docs/vX_Y_Z/` first, fall back only if missing
- ✅ Inject AGENTS.md as system prompt for calibration
- ✅ Save versions to `.clawdibrate/iterations/AGENTS_vN.md`
- ✅ Track `reflection_history` across iterations
- ✅ Route failures to responsible sections
- ✅ `git commit` after version updates (atomic commits)
- ✅ Complete `docs/vX_Y_Z/README.md` before commit
- ✅ Edit `src/skills/{name}/SKILL.md` then `npx skills add ./src/skills --agent <detected-agents> --skill '*' -y`
- ✅ Spawn parallel agents for independent kanban cards
- ✅ Don't duplicate file reads between main thread and spawned agents
- ✅ Version workflow: SPEC.md → kanban → copy icebox → work cards → README.md → CHANGELOG.md → bump → commit
- ✅ `/clawdbrt:loop` calibrates, `/clawdbrt:add-new-features` MINOR only, MAJOR needs human approval
- ✅ Check existing tools before implementing
- ✅ Tickets: `clwdi-v{MAJOR}_{MINOR}_{PATCH}-{NNN}.md`, rename when moving versions, copy `icebox.md`
- ⚠️ Ask: new evaluation tasks, judge threshold <0.7
- 🚫 Don't rewrite converged sections (≥0.95 score)
- 🚫 Don't remove Boundaries section
- 🚫 Don't lengthen file without instruction
- 🚫 Use kanban cards, not markdown checklists/TaskCreate
- 🚫 Don't edit `skills/`/`.agents/` directly — `src/skills/` is source
- 🚫 Don't auto-bump MAJOR
