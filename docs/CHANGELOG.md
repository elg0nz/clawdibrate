# Changelog

All notable changes to AGENTS.md will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for tracking AGENTS.md versions.

## [0.4.1] - 2026-04-01

### Fixed
- **Untracked `skills/` from git index** — files were added before `.gitignore` rule, causing `npx skills add` to dirty the working tree with phantom deletes

## [0.4.0] - 2026-04-01

### Added
- **`/add-new-features` skill** — meta-skill for proposing and building new features as MINOR versions
- **`npx skills add ./skills --all -y`** as first step in AGENTS.md Setup — bootstraps skills to all 45 agents
- **Version semantics enforced** — `/loop` produces PATCH only, `/add-new-features` produces MINOR, MAJOR is human-only

### Changed
- Skills section updated: lists `/loop`, `/kanban`, `/add-new-features` with version semantics
- `skills/` is now canonical source of truth — `.agents/skills/` symlinks from it via `npx skills add`
- `/loop` SKILL.md explicitly states each iteration is a PATCH version

## [0.3.0] - 2026-04-01

### Added
- **Skills section in AGENTS.md** — skill router for `/loop` and `/kanban`
- `skills/loop/SKILL.md` — tuning loop as a skill
- `skills/kanban/SKILL.md` — kanban card management as a skill
- Installed `vercel-labs/skills` framework (7 community skills in `.claude/skills/`)
- Research doc: `docs/v0_3_0/vercel-skills.md`
- Boundary rule: no commit without version README complete
- Kanban ticket naming convention: `clwdi-vMAJOR_MINOR_PATCH-NNN.md`
- Kanban board files: `inbox.md`, `in-progress.md`, `done.md`, `icebox.md`
- Icebox carry-forward between versions

### Changed
- Seed tasks and SECTIONS list moved from AGENTS.md to proto spec (word budget)
- SECTIONS list updated to include "Skills"

## [0.2.0] - 2026-04-01

### Added
- Boundary rule: `git commit` immediately after every version update

## [0.1.0] - 2026-04-01

### Changed
- **CLI-first architecture**: `loop.py` shells out to agent CLIs via `subprocess` — no `anthropic` SDK or API keys required
- `run_agent()` and `judge()` use `AGENT_COMMANDS` dispatch table (`claude -p`, `codex`, `opencode`)
- Added `--agent` flag to `loop.py` for selecting which CLI to use (default: `claude`)
- Inline reference implementation moved back to `docs/v0_0_0/specs/agents-proto.md` — AGENTS.md keeps architecture + pointer only (trimmed under 700 words)
- Trimmed version header to 2 lines
- Compressed Tuning Rules with inline arXiv citation
- Known Gotchas consolidated (Codex/OpenCode transport merged into Setup)
- References reduced to citations only (descriptions in engineering guide)

### Added
- Seed tasks: 5 concrete, automatically scorable tasks in the `TASKS` list
- `SECTIONS` list updated to match actual AGENTS.md headings
- Subprocess timeout gotcha (`timeout=120`)
- Claude `-p` flag gotcha for non-interactive prompt mode
- `re.DOTALL` flag for JSON regex fallback
- `scores.jsonl` output path for Score Tracking
- Runtime note (Node.js from `.tool-versions`, Python 3.10+)
- Link to engineering guide in References
- `docs/CHANGELOG.md` — top-level changelog across all versions
- `.conversations/` directory for session metrics and tuning history

### Removed
- `pip install anthropic` / `ANTHROPIC_API_KEY` from Setup (no longer needed)
- `import anthropic` / `client = anthropic.Anthropic()` from reference implementation
- `ln -s AGENTS.md CLAUDE.md` (already done, discoverable)
- Structure section (not actionable)
- Paper description prose in References
- Per-version `CHANGELOG.md` files (consolidated to `docs/CHANGELOG.md`)

## [0.0.0] - 2026-04-01

### Added
- Initial AGENTS.md with project identity, setup, commands, tuning rules, and boundaries
- Spec for self-tuning agent instruction optimizer (`agents-proto.md`)
- Engineering guide (`agents_md_engineering_guide.md`)
- Semantic versioning scheme for AGENTS.md tracking
- Kanban folder for project tracking
- Logo and brand identity spec
