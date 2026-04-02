# Clawdibrate AGENTS.md

> **Version: 0.9.2** | [Changelog](./docs/CHANGELOG.md)
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
python -m clawdibrate --mode fast                  # quick low-hanging-fruit pass
python -m clawdibrate --mode progressive           # cancel-safe mini-iterations
python -m clawdibrate --mode max --target-score 0.9 # iterate until optimized / plateau
python -m clawdibrate --no-auto-section-skills     # calibrate only; do not auto-create section skills / npx
python -m clawdibrate --transcript path/to.jsonl   # calibrate from one transcript
python -m clawdibrate --dry-run                    # inspect the run without editing AGENTS.md
```

---

## Skills

Slash commands route to `SKILL.md` files in `src/skills/`. All skills use `clawdbrt:` prefix.

**Registration:** `src/skills/<name>/SKILL.md` with YAML frontmatter (`name: clawdbrt:<skill-name>`, `description`). Run `npx skills add ./src/skills --agent <detected-agents> --skill '*' -y`. Commit `skills-lock.json` and updated `skills/`/`.agents/` files.

**Source:** `src/skills/` is canonical. Never edit `skills/`/`.agents/skills/` directly.

**Implementation:** All new capabilities must be skills. Use `/clawdbrt:` commands only.

**Core skills:**
- `/clawdbrt:loop` — tuning loop, PATCH versions
- `/clawdbrt:kanban` — card management in `docs/vX_Y_Z/kanban/`
- `/clawdbrt:add-new-features` — feature proposals, MINOR versions
- `/clawdbrt:implement` — kanban implementation with parallel agents
- `/clawdbrt:scores` — calibration scoreboard

**Section skills:** Score <0.7 across 3+ runs or git churn ≥3 → create `src/skills/<kebab-section-name>/SKILL.md`. Reference: `See /clawdbrt:<skill-name> for detailed guidance.`


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
- Auto-detect high-churn sections (≥3 edits) and flag them for review before making changes
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
- **If externalizing sections to skills, do not re-add equivalent content to AGENTS.md in the same run.**
- **If calibration changes same sections across runs, implement exponential backoff until new transcript data.**
- **Penalize verbosity.** Bloat reduces task success ~2%, increases inference cost >20% (arxiv.org/abs/2602.11988).


## Boundaries

- Use latest `docs/vX_Y_Z/` first, fallback to older versions
- Inject AGENTS.md as system prompt for transcript calibration
- Save versions as `.clawdibrate/iterations/AGENTS_vN.md` before overwriting
- Track `reflection_history` across iterations
- Route failures to specific section, not whole document
- `git commit` after every version update
- Complete `docs/vX_Y_Z/README.md` before committing
- Create/edit skills: `src/skills/{name}/SKILL.md`, run `npx skills add ./src/skills --agent <detected-agents> --skill '*' -y`
- Spawn parallel agents for independent kanban cards
- Don't read files if agent spawned to read them
- Workflow: SPEC.md → kanban → copy icebox → work cards → README.md → CHANGELOG.md → bump → commit
- `/clawdbrt:loop` calibrates transcripts, `/clawdbrt:add-new-features` MINOR only, MAJOR needs human decision
- Check installed tools before implementing
- Ticket format: `clwdi-v{MAJOR}_{MINOR}_{PATCH}-{NNN}.md`, moving renames to target version, copy prior `icebox.md`
- Ask first: new evaluation task types, judge threshold <0.7
- Never: rewrite converged sections (≥0.95 score, 3+ iterations), remove Boundaries, add net lines without instruction (externalize to skills), use markdown checklists/TaskCreate (use kanban), edit `skills/`/`.agents/` directly (use `src/skills/`), auto-bump MAJOR


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
Persist run instrumentation (stage timings, mode, estimate, token deltas) to `.clawdibrate/history/instrumentation.jsonl`.

---

## References

- **Reflexion** — Shinn et al., NeurIPS 2023
- **RISE** — Qu et al., 2024
- **Recursive Language Models** — Zhang, Kraska, Khattab, Dec 2025 (arxiv.org/abs/2512.24601)
- **Evaluating AGENTS.md** — arxiv.org/abs/2602.11988
- **Engineering Guide** — latest `docs/vX_Y_Z/specs/agents_md_engineering_guide.md`
