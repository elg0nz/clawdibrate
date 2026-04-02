# Changelog

All notable changes to AGENTS.md will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for tracking AGENTS.md versions.

## [0.10.0] - 2026-04-02

### Added
- **40-test pytest suite** — mocked agent calls, covers all `calibrate()` branches: early exits, 3-stage pipeline (bug-id, judge, implementer), persistence, convergence, overfit detection, compression, max_transcripts cap, version bump, section ops
- **`scripts/presubmit.sh`** — quality gate: ruff, mypy --strict, bandit, vulture, radon, inline imports
- **`/clawdbrt:presubmit` skill** — wraps the presubmit script for any agent
- **`--scores` flag** — ASCII sparkline of calibration score history from `scores.jsonl`
- **`--check-idempotent` flag** — runs calibrate twice on the same transcript, asserts convergence (exit 0 = idempotent, 1 = divergence)
- **End-to-end smoke test** — `docs/v0_10_0/SMOKE_TEST.md` with synthetic repo, 6 transcripts, all modes, scoreboard

### Changed
- **`calibrate()` complexity F → D** — extracted 6 stage functions: `_discover_transcripts`, `_compute_baselines`, `_run_stage_bug_id`, `_run_stage_judge`, `_run_stage_impl`, `_persist_and_report`

### Fixed
- **70 mypy --strict errors** across 8 source files (generic type params, return annotations, TypedDicts)
- **8 ruff issues** (unused imports, unused vars, bare f-strings)
- **4 bandit issues** (`tempfile.mkstemp` instead of hardcoded `/tmp`, `nosec` on intentional `shell=True`)

## [0.9.0] - 2026-04-02

### Added
- **Loop execution modes** — `--mode fast`, `--mode progressive`, and `--mode max --target-score <float>`
- **Developer instrumentation log** — `.clawdibrate/history/instrumentation.jsonl` with per-stage timings, token deltas, mode metadata, and optimization estimates
- **v0_9_0 release notes** — `docs/v0_9_0/README.md` documenting env setup, modes, and loop behavior

### Changed
- **AGENTS.md commands** updated with fast/progressive/max mode examples
- **AGENTS.md score tracking** now includes instrumentation persistence path

### Fixed
- **PATCH version progression restored in loop** — calibrations that update `AGENTS.md` now:
  - snapshot pre-overwrite content to `.clawdibrate/iterations/AGENTS_vN.md`
  - bump header patch version (`X.Y.Z -> X.Y.(Z+1)`)
  - commit the updated instruction file (and snapshot file when created)

## [0.5.0] - 2026-04-01

### Added
- **`/clawdbrt:implement` skill** — reads kanban board, resolves card dependencies, implements by priority with parallel agents
- **`clawdbrt:` namespace** — all skills renamed: `clawdbrt:loop`, `clawdbrt:kanban`, `clawdbrt:add-new-features`, `clawdbrt:implement`
- **8 new boundary rules** — parallel agents, no TaskCreate/checklists, ticket naming convention, `src/skills/` canonical source, version semantics, check existing tools, version workflow, all capabilities as skills
- **3 new "Never" rules** — no editing `skills/` directly, no auto-bump MAJOR, no checklists

### Changed
- All hardcoded version paths (`v0_0_0`, `v0_4_2`) replaced with "latest `docs/vX_Y_Z/`" language
- Skills section documents `src/skills/` as canonical source with `skills/` and `.agents/` as install outputs
- Skills architecture direction: all new capabilities must be implemented as skills

## [0.4.2] - 2026-04-01

### Fixed
- **Untracked `skills/` from git index** — two SKILL.md files were added before the `.gitignore` rule existed, so `npx skills add` clobbered them and created phantom deletes in `git status`. This broke a Codex `/loop` run that stalled on the dirty working tree.
- **Corrected all `skills/` → `src/skills/` references** — AGENTS.md (skill router lines), CHANGELOG, and v0.4.0 README still said `skills/` was canonical. Fixed to `src/skills/` everywhere.
- **Gitignored `.conversations/`** — session JSONL logs are local runtime data, not source. Untracked the bootstrap log and added `.conversations/` to `.gitignore`.
- **Backfilled conversation logs** — logged the v0.2.0→v0.4.0 skills architecture session and the v0.4.1 bugfix session to `.conversations/`

## [0.4.1] - 2026-04-01

### Fixed
- **Untracked `skills/` from git index** — files were added before `.gitignore` rule, causing `npx skills add` to dirty the working tree with phantom deletes

## [0.4.0] - 2026-04-01

### Added
- **`/add-new-features` skill** — meta-skill for proposing and building new features as MINOR versions
- **`npx skills add ./src/skills --all -y`** as first step in AGENTS.md Setup — bootstraps skills to all 45 agents
- **Version semantics enforced** — `/loop` produces PATCH only, `/add-new-features` produces MINOR, MAJOR is human-only

### Changed
- Skills section updated: lists `/loop`, `/kanban`, `/add-new-features` with version semantics
- `src/skills/` is now canonical source of truth — `npx skills add ./src/skills --all -y` distributes to all agents
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
