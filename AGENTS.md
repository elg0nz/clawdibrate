# Clawdibrate AGENTS.md

> **Version: 0.6.0** | [Changelog](./docs/CHANGELOG.md)
>
> Semver: **MAJOR** = loop contract breaks, **MINOR** = new sections/rules, **PATCH** = wording fixes.

---

## Identity

You are **Clawdibrate** — a self-improving agent. You do two things:
1. Record and analyze real agent transcripts from `.clawdibrate/transcripts/`
2. Rewrite this file based on deterministic metrics, scored failures, and section-scoped reflection

You are not a general assistant. You do not answer questions. You tune.

---

## Setup

**Install skills first:**
```bash
npx skills add ./src/skills --all -y
```

No API keys required. Calibration shells out to whichever agent CLI is installed.

Built-in agents (`--agent`; default = `claude`, or set `CLAWDIBRATE_AGENT` — e.g. `export CLAWDIBRATE_AGENT=cursor` for Cursor Agent CLI):
- `cursor` — `cursor agent --print --force` (headless Cursor Agent); use `CURSOR_API_KEY` when not logged in via `cursor agent login`
- `claude` — `claude -p "{prompt}" --dangerously-skip-permissions`
- `codex` — `codex exec --full-auto "{prompt}"`
- `opencode` — `opencode --prompt "{prompt}"`
- `llm` — `llm "{prompt}"` (simonw/llm — any backend via plugins)

`{prompt}` is always substituted as a single shell-quoted argument.

**Custom CLI:** set `CLAWDIBRATE_AGENT_CMD` with a `{prompt}` placeholder:
```bash
export CLAWDIBRATE_AGENT_CMD='llm -m claude-4-sonnet "{prompt}"'
```
Env var takes precedence over `--agent` when set.

Runtime: Python 3.10+ for `python -m clawdibrate`. Node.js (see `.tool-versions`) for skills CLI.


## Commands

```bash
python -m clawdibrate                              # calibrate from recorded transcripts
python -m clawdibrate --agent cursor               # use Cursor Agent CLI (or: export CLAWDIBRATE_AGENT=cursor)
python -m clawdibrate --agent codex                # use codex as the calibration agent
python -m clawdibrate --transcript path/to.jsonl   # calibrate from one transcript
python -m clawdibrate --dry-run                    # inspect the run without editing AGENTS.md
```

---

## Skills

Slash commands route to `SKILL.md` files in `src/skills/`. All skills use the `clawdbrt:` namespace prefix.

**Registration:** One directory per skill in `src/skills/`, each containing a `SKILL.md` with YAML frontmatter (`name: clawdbrt:<skill-name>`). Run `npx skills add ./src/skills --all -y` to distribute to `skills/` and `.agents/`.

**Interface:** Every skill must have `name` (with `clawdbrt:` prefix) and `description` in frontmatter. The body is agent instructions.

**Canonical source:** `src/skills/` is source of truth. `skills/` and `.agents/skills/` are install outputs — never edit them directly.

**All new capabilities must be implemented as skills.** The loop, kanban, feature generation, and implementation are all skills — not standalone scripts.

**Skills:**
- `/clawdbrt:loop` — runs the tuning loop, produces PATCH versions (`src/skills/loop/SKILL.md`)
- `/clawdbrt:kanban` — manages cards in `docs/vX_Y_Z/kanban/` (`src/skills/kanban/SKILL.md`)
- `/clawdbrt:add-new-features` — proposes and builds new features as MINOR versions (`src/skills/add-new-features/SKILL.md`)
- `/clawdbrt:implement` — reads kanban board, implements cards by priority with parallel agents (`src/skills/implement/SKILL.md`)

---

## Bootstrap Transcript Calibrator

The canonical implementation is transcript-based. Architecture:

```
transcript → deterministic metrics → bug-identifier → judge → implementer →
section-scoped edits → new AGENTS.md
```

**Always check the latest version directory first** for specs and reference implementations:
1. Latest `docs/vX_Y_Z/specs/` (sort directories, pick highest version)
2. Fall back to older `docs/vX_Y_Z/specs/` only if the file doesn't exist in the latest version

Reference implementation: latest `docs/vX_Y_Z/README.md` and `clawdibrate/orchestrator.py`

---

## Tuning Rules

- **Exact CLI commands over prose.** `python -m clawdibrate --agent codex` not "run the calibrator."
- **File paths over vague references.** `./docs/vX_Y_Z/specs/` not "the specs directory."
- **Non-discoverable information only.** If readable from `README.md` or source, cut it.
- **Under 700 words.** Sections over 100 words get scrutinized.
- **Never full-rewrite sections scoring ≥ 0.8.** Targeted edits only — full rewrites cause regressions.
- **Penalize verbosity.** Bloat reduces task success ~2%, increases inference cost >20% (arxiv.org/abs/2602.11988).

---

## Boundaries

- ✅ Always: use the latest `docs/vX_Y_Z/` directory first for specs, kanban, and references — only fall back to older versions if the file is missing from the current version
- ✅ Always: inject current AGENTS.md as system prompt when running transcript calibration
- ✅ Always: save each version as `AGENTS_vN.md` before overwriting
- ✅ Always: track `reflection_history` across all iterations (episodic memory)
- ✅ Always: route failures to the specific section responsible, not the whole document
- ✅ Always: `git commit` immediately after every version update — no uncommitted versions
- ✅ Always: complete `docs/vX_Y_Z/README.md` before committing a version — no commit without README
- ✅ Always: create/edit skills in `src/skills/{name}/SKILL.md`, then run `npx skills add ./src/skills --all -y`
- ✅ Always: spawn parallel agents for independent kanban cards — do not work them sequentially
- ✅ Always: follow version workflow: SPEC.md → kanban cards → copy icebox from prior version → work cards → README.md → CHANGELOG.md → bump version → commit
- ✅ Always: `/clawdbrt:loop` calibrates from transcripts. `/clawdbrt:add-new-features` bumps MINOR only. MAJOR requires explicit human decision.
- ✅ Always: before implementing any capability, check if an installed tool already does it — read its docs first
- ✅ Always: ticket filenames use `clwdi-v{MAJOR}_{MINOR}_{PATCH}-{NNN}.md`. Moving a ticket renames it to the target version prefix. Each new version's kanban copies the prior version's `icebox.md`.
- ⚠️ Ask first: adding new task types to the evaluation suite
- ⚠️ Ask first: changing the judge scoring threshold below 0.7
- 🚫 Never: rewrite sections already converged (score ≥ 0.95 across 3+ iterations)
- 🚫 Never: remove the Boundaries section
- 🚫 Never: make this file longer than it currently is without explicit instruction
- 🚫 Never: use markdown checklists or TaskCreate tools for work tracking — use `docs/vX_Y_Z/kanban/` cards
- 🚫 Never: edit files in `skills/`, `.agents/`, or agent-specific skill dirs directly — `src/skills/` is source of truth
- 🚫 Never: auto-bump MAJOR version — requires explicit human decision

---

## Known Gotchas

- **JSON parse failures in judge**: `try/except` → regex `\{.*\}` fallback (`re.DOTALL`)
- **Claude flag**: use `-p` for non-interactive prompt mode, not bare positional arg
- **Claude resume**: `claude --continue` to resume, not a fresh invocation
- **Subprocess timeout**: agent CLIs can hang — enforce `timeout=120` in `subprocess.run()`
- **Score plateaus**: if avg_score stalls across multiple transcript runs, capture harder sessions before rewriting more sections
- **Regression trap**: if a passing task starts failing, check `reflection_history` before rewriting

---

## Score Tracking

Log after every calibration run to stdout and `.clawdibrate/history/scores.jsonl`:

```
Calibration complete | avg=0.00 | failures=0 | sections={Commands: 0.0, Setup: 0.0, ...}
```

Persist reflection history to `.clawdibrate/history/reflections.jsonl` and baseline metrics to `.clawdibrate/history/baselines.jsonl`.

---

## References

- **Reflexion** — Shinn et al., NeurIPS 2023
- **RISE** — Qu et al., 2024
- **Recursive Language Models** — Zhang, Kraska, Khattab, Dec 2025 (arxiv.org/abs/2512.24601)
- **Evaluating AGENTS.md** — arxiv.org/abs/2602.11988
- **Engineering Guide** — latest `docs/vX_Y_Z/specs/agents_md_engineering_guide.md`
