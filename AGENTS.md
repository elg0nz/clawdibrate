# Clawdibrate AGENTS.md

> **Version: 0.9.6** | [Changelog](./docs/CHANGELOG.md)
>
> Semver: **PATCH** = backward-compatible fixes (wording, tuning). **MINOR** = new backward-compatible functionality (new sections, commands, skills). **MAJOR** = incompatible changes to the calibration loop contract or CLI interface.

---

## Identity

See `/clawdbrt:identity` for detailed guidance.


## Setup

```bash
npx skills add ./src/skills --agent claude-code cursor codex --skill '*' -y
```

**Agent env:**
1. `repo/.clawdibrate/env` — copy `clawdibrate.env.example`, set `CLAWDIBRATE_AGENT=cursor`
2. Fallback: `repo/.env` (only `CLAWDIBRATE_*` keys)

**Built-in agents** (`--agent`/`CLAWDIBRATE_AGENT`, default `claude`):
- `cursor` — `cursor agent --print --force`
- `claude` — `claude -p "{prompt}" --dangerously-skip-permissions`
- `codex` — `codex exec --full-auto "{prompt}"`
- `opencode` — `opencode --prompt "{prompt}"`
- `llm` — `llm "{prompt}"`

**Custom:** `CLAWDIBRATE_AGENT_CMD='llm -s "$(cat {system_prompt})" {prompt}'`

**Runtime:** Python 3.10+, Node.js


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

Skills route to `src/skills/<name>/SKILL.md` with `clawdbrt:` prefix. YAML frontmatter: `name: clawdbrt:<skill-name>`, `description`. Register: `npx skills add ./src/skills --agent <agents> --skill '*' -y`. Commit `skills-lock.json`, `skills/`, `.agents/`. Source: `src/skills/` only—never edit `skills/`/`.agents/skills/`. All capabilities must be skills.

Core: `/clawdbrt:loop` (tuning), `/clawdbrt:kanban` (cards), `/clawdbrt:add-new-features` (proposals), `/clawdbrt:implement` (parallel), `/clawdbrt:scores` (scoreboard).

Section skills: score <0.7 (3+ runs) or churn ≥3 → `src/skills/<kebab>/SKILL.md`. Reference: `See /clawdbrt:<skill>`.


## Bootstrap Transcript Calibrator

Transcript-based architecture: `transcript → metrics → bug-identifier → judge → implementer → section-scoped edits → new AGENTS.md`

**Version specs:** Latest `docs/vX_Y_Z/specs/` first, fallback to older only if missing. Reference: latest `docs/vX_Y_Z/README.md` and `clawdibrate/orchestrator.py`

**Before analysis:** Verify transcript completeness. Request complete data if truncated.

**Boundary:** AGENTS.md injected as system prompt — NEVER use Read with offset/limit on AGENTS.md.

**Rules:**
- Auto-detect high-churn sections (≥3 edits), flag before changes
- Read large files once fully (no offset/limit) — chunking wastes 4x calls/tokens  
- Multiple files (>3): single agent with batch instructions OR parallel tool calls
- Either delegate exploration OR read directly — never both for same files
- Verify current content before editing AGENTS.md sections
- Output complete, valid JSON with all required fields


## Tuning Rules

- **Exact CLI commands over prose.** `python -m clawdibrate --agent codex` not "run the calibrator."
- **File paths over vague references.** `./docs/vX_Y_Z/specs/` not "the specs directory."
- **Non-discoverable information only.** If readable from `README.md` or source, cut it.
- **Under 700 words.** Sections over 100 words get scrutinized.
- **Never full-rewrite sections scoring ≥ 0.8.** Check `.clawdibrate/history/scores.jsonl` before editing — block rewrites of converged sections.
- **If externalizing sections to skills, do not re-add equivalent content to AGENTS.md in the same run.**
- **If calibration changes same sections across runs, implement exponential backoff until new transcript data.**
- **Penalize verbosity.** Bloat reduces task success ~2%, increases inference cost >20% (arxiv.org/abs/2602.11988).


## Boundaries

- Use latest `docs/vX_Y_Z/` first, fallback to older
- Inject AGENTS.md as system prompt for calibration
- Save `.clawdibrate/iterations/AGENTS_vN.md` before overwrite
- Track `reflection_history` across iterations
- Route failures to specific section
- `git commit` after version update
- Complete `docs/vX_Y_Z/README.md` before commit
- Skills: `src/skills/{name}/SKILL.md` → `npx skills add ./src/skills --agent <agents> --skill '*' -y`
- Spawn parallel agents for independent kanban cards
- Don't read files if agent spawned to read them
- Flow: SPEC.md → kanban → icebox → cards → README.md → CHANGELOG.md → bump → commit
- `/clawdbrt:loop` calibrates, `/clawdbrt:add-new-features` MINOR only, MAJOR needs approval
- Check tools before implementing
- Tickets: `clwdi-v{MAJOR}_{MINOR}_{PATCH}-{NNN}.md`, rename on move, copy `icebox.md`
- Ask first: new eval types, judge <0.7
- Never: rewrite converged (≥0.95, 3+ iter), remove Boundaries, add lines without instruction, use checklists/TaskCreate, edit `skills/`/`.agents/` directly, auto-bump MAJOR


## Known Gotchas

- **JSON parse failures in judge**: `try/except` → regex `\{.*\}` fallback (`re.DOTALL`)
- **Claude flag**: use `-p` for non-interactive prompt mode, not bare positional arg
- **Claude resume**: `claude --continue` to resume, not a fresh invocation
- **Subprocess timeout**: agent CLIs can hang — enforce `timeout=120` in `subprocess.run()`
- **Score plateaus**: if avg_score stalls across multiple transcript runs, capture harder sessions before rewriting more sections
- **Regression trap**: if a passing task starts failing, check `reflection_history` before rewriting
- **Claude Code session format**: JSONL at `~/.claude/projects/<mangled-cwd>/` (path `/` → `-`). Structure: `{"type":"user"|"assistant","message":{"content":[{"type":"text","text":"..."}|{"type":"tool_use","id":"...","name":"...","input":{...}}|{"type":"tool_result","tool_use_id":"...","content":"..."}]}}`. Parse message types and content blocks directly; avoid exploratory reverse-engineering.


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
