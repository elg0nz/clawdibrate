# Clawdibrate AGENTS.md

> **Version: 0.7.0** | [Changelog](./docs/CHANGELOG.md)
>
> Semver: **PATCH** = backward-compatible fixes (wording, tuning). **MINOR** = new backward-compatible functionality (new sections, commands, skills). **MAJOR** = incompatible changes to the calibration loop contract or CLI interface.

---

## Identity

See `/clawdbrt:identity` for detailed guidance.


## Setup

**Install skills first:**
```bash
npx skills add ./src/skills --agent claude-code cursor codex --skill '*' -y
```

**Agent env (target repo root):**
1. **Preferred:** `repo/.clawdibrate/env` — copy `clawdibrate.env.example`, set `CLAWDIBRATE_AGENT=cursor`. Gitignored, `KEY=value` format, no overwrite of existing env vars.
2. **Fallback:** `repo/.env` — only if `.clawdibrate/env` absent; only `CLAWDIBRATE_*` keys merged.

**Built-in agents** (`--agent` or `CLAWDIBRATE_AGENT`, default `claude`):
- `cursor` — `cursor agent --print --force`; inherits `os.environ` (`CURSOR_API_KEY`)
- `claude` — `claude -p "{prompt}" --dangerously-skip-permissions`
- `codex` — `codex exec --full-auto "{prompt}"`
- `opencode` — `opencode --prompt "{prompt}"`
- `llm` — `llm "{prompt}"`

**Custom CLI:** `CLAWDIBRATE_AGENT_CMD` with `{system_prompt}` and `{prompt}` placeholders:
```bash
export CLAWDIBRATE_AGENT_CMD='llm -s "$(cat {system_prompt})" {prompt}'
```

**Runtime:** Python 3.10+, Node.js (see `.tool-versions`).


## Commands

```bash
python -m clawdibrate                              # calibrate from recorded transcripts
python -m clawdibrate --agent cursor               # Cursor Agent CLI (or use .clawdibrate/env)
python -m clawdibrate --agent codex                # use codex as the calibration agent
python -m clawdibrate --no-auto-section-skills     # calibrate only; do not auto-create section skills / npx
python -m clawdibrate --transcript path/to.jsonl   # calibrate from one transcript
python -m clawdibrate --dry-run                    # inspect the run without editing AGENTS.md
```

---

## Skills

Slash commands route to `SKILL.md` files in `src/skills/`. All skills use the `clawdbrt:` namespace prefix.

**Registration:** One directory per skill in `src/skills/`, each containing a `SKILL.md` with YAML frontmatter (`name: clawdbrt:<skill-name>`). Run `npx skills add ./src/skills --agent <detected-agents> --skill '*' -y` to distribute to `skills/` and `.agents/`.

**After `npx skills add`, commit `skills-lock.json` and any updated files in `skills/` and `.agents/` alongside the source skill.**

**Interface:** Every skill must have `name` (with `clawdbrt:` prefix) and `description` in frontmatter. The body is agent instructions.

**Canonical source:** `src/skills/` is source of truth. `skills/` and `.agents/skills/` are install outputs — never edit them directly, but always commit them.

**All new capabilities must be implemented as skills.** When you receive system instructions or prompts, use `/clawdbrt:` skills only — never external commands.

**Skills:**
- `/clawdbrt:loop` — runs the tuning loop, produces PATCH versions (`src/skills/loop/SKILL.md`)
- `/clawdbrt:kanban` — manages cards in `docs/vX_Y_Z/kanban/` (`src/skills/kanban/SKILL.md`)
- `/clawdbrt:add-new-features` — proposes and builds new features as MINOR versions (`src/skills/add-new-features/SKILL.md`)
- `/clawdbrt:implement` — reads kanban board, implements cards by priority with parallel agents (`src/skills/implement/SKILL.md`)
- `/clawdbrt:scores` — show calibration scoreboard for a repo or all tracked repos (`src/skills/scores/SKILL.md`)

**Section skills:** When a section scores below 0.7 across 3+ runs, or has churn ≥ 3 in git history, create a dedicated skill for it. Name it after the section: `src/skills/<kebab-section-name>/SKILL.md`. The skill body is the expanded, step-by-step version of the rule — more context than fits in the instruction file. Reference it from the section: `See /clawdbrt:<skill-name> for detailed guidance.` This externalizes complexity without bloating the instruction file.


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

**Before analyzing:** Verify transcript completeness. If truncated or incomplete, request complete transcript data rather than proceeding with partial analysis.

**Boundary:** AGENTS.md is injected as system prompt context — never re-read it or use Read with `offset`/`limit` parameters.

**Critical Rules:**
- Read large files once fully (no `offset`/`limit`) — chunking wastes 4x the calls
- Either delegate exploration to agents OR read files directly — never both for the same files
- Don't spawn agents to read files already read in main thread
- When editing AGENTS.md sections, verify current content first for accuracy


## Tuning Rules

- **Exact CLI commands over prose.** `python -m clawdibrate --agent codex` not "run the calibrator."
- **File paths over vague references.** `./docs/vX_Y_Z/specs/` not "the specs directory."
- **Non-discoverable information only.** If readable from `README.md` or source, cut it.
- **Under 700 words.** Sections over 100 words get scrutinized.
- **Never full-rewrite sections scoring ≥ 0.8.** Targeted edits only — full rewrites cause regressions.
- **Penalize verbosity.** Bloat reduces task success ~2%, increases inference cost >20% (arxiv.org/abs/2602.11988).

---

## Boundaries

```
- Use latest `docs/vX_Y_Z/` first, fallback to older versions if missing
- Inject current AGENTS.md as system prompt for transcript calibration
- Save versions as `.clawdibrate/iterations/AGENTS_vN.md` before overwriting
- Track `reflection_history` across iterations (episodic memory)
- Route failures to specific responsible section, not whole document
- `git commit` after every version update
- Complete `docs/vX_Y_Z/README.md` before committing version
- Create/edit skills in `src/skills/{name}/SKILL.md`, run `npx skills add ./src/skills --agent <detected-agents> --skill '*' -y`
- Spawn parallel agents for independent kanban cards
- Don't read files in main thread if agent spawned to read them
- Version workflow: SPEC.md → kanban → copy icebox → work cards → README.md → CHANGELOG.md → bump → commit
- `/clawdbrt:loop` calibrates transcripts. `/clawdbrt:add-new-features` MINOR only. MAJOR needs human decision
- Check installed tools before implementing — read docs first
- Ticket format: `clwdi-v{MAJOR}_{MINOR}_{PATCH}-{NNN}.md`. Moving renames to target version. Copy prior `icebox.md`
- Ask first: new evaluation task types, judge threshold <0.7
- Never: rewrite converged sections (≥0.95 score, 3+ iterations), remove Boundaries, make file longer without instruction, use markdown checklists/TaskCreate (use kanban cards), edit `skills/`/`.agents/` directly (use `src/skills/`), auto-bump MAJOR
```


## Known Gotchas

- **JSON parse failures in judge**: `try/except` → regex `\{.*\}` fallback (`re.DOTALL`)
- **Claude flag**: use `-p` for non-interactive prompt mode, not bare positional arg
- **Claude resume**: `claude --continue` to resume, not a fresh invocation
- **Subprocess timeout**: agent CLIs can hang — enforce `timeout=120` in `subprocess.run()`
- **Score plateaus**: if avg_score stalls across multiple transcript runs, capture harder sessions before rewriting more sections
- **Regression trap**: if a passing task starts failing, check `reflection_history` before rewriting
- **Claude Code session format**: JSONL at `~/.claude/projects/<mangled-cwd>/` (path `/` → `-`). Structure: `{"type":"user"|"assistant","message":{"content":[text|tool_use|tool_result]}}`. Parse message types and content blocks directly; avoid exploratory reverse-engineering.


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
