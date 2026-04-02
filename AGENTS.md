# Clawdibrate AGENTS.md

> **Version: 0.12.1** | [Changelog](./docs/CHANGELOG.md)
>
> Semver: **PATCH** = backward-compatible fixes (wording, tuning). **MINOR** = new backward-compatible functionality (new sections, commands, skills). **MAJOR** = incompatible changes to the calibration loop contract or CLI interface.
>
> Repo note: Do **not** add the "This repo uses clawdibrate... Install... Run..." onboarding snippet here. That snippet is for target repos being calibrated, not for clawdibrate's own `AGENTS.md`.

---

## Identity

`/clawdbrt:identity`


## Setup

```bash
npx skills add ./src/skills --agent claude-code cursor codex --skill '*' -y --global
```

**Agent env:**
1. `repo/.clawdibrate/env` — copy `clawdibrate.env.example`, set `CLAWDIBRATE_AGENT=cursor`
2. Fallback: `repo/.env` (`CLAWDIBRATE_*` keys only)

**Built-in agents** (`--agent`/`CLAWDIBRATE_AGENT`, default `claude`):
- `cursor` — `cursor agent --print --force`
- `claude` — `claude -p "{prompt}" --dangerously-skip-permissions`
- `codex` — `codex exec --full-auto "{prompt}"`
- `opencode` — `opencode --prompt "{prompt}"`
- `llm` — `llm "{prompt}"`

**Custom:** `CLAWDIBRATE_AGENT_CMD='llm -s "$(cat {system_prompt})" {prompt}'`

**Runtime:** Python 3.10+, Node.js


## Commands

See `/clawdbrt:commands` for detailed guidance.


## Skills

Skills: `src/skills/<name>/SKILL.md`, prefix `clawdbrt:`. Frontmatter: `name: clawdbrt:<skill-name>`, `description`. Register: `npx skills add ./src/skills --agent <agents> --skill '*' -y --global`. Commit `skills-lock.json`, `skills/`, `.agents/`. Edit only `src/skills/`—never `skills/`/`.agents/skills/`. All capabilities must be skills.

Core skills: `loop` (tuning), `kanban` (cards), `add-new-features` (proposals), `implement` (parallel), `scores` (scoreboard).

Extract section to `src/skills/<kebab>/SKILL.md` when score <0.7 (3+ runs) or churn ≥3. Reference inline as `See /clawdbrt:<skill>`.


## Bootstrap Transcript Calibrator

Transcript pipeline: `transcript → metrics → bug-identifier → judge → implementer → section-scoped edits → new AGENTS.md`

**Specs:** Use latest `docs/vX_Y_Z/specs/`; fallback to older. Ref: latest `docs/vX_Y_Z/README.md` + `clawdibrate/orchestrator.py`

**Pre-analysis:** Verify transcript completeness + AGENTS.md ends properly. STOP if truncated.

**AGENTS.md boundary:** Injected as system prompt — Read in full only, never with offset/limit.

**Rules:**
- Flag high-churn sections (≥3 edits) before editing
- File reads: Read tool only (offset/limit ok except AGENTS.md); no `cat`/`head`/`sed -n` via Bash
- File discovery: Glob only; content search: Grep only — no `find`/`grep` via Bash
- >3 files: single batched agent OR parallel tool calls
- Delegate exploration OR read directly — never both for same files
- Always Read before Edit; on success never re-edit without re-reading
- Shell commands: Shell tool only — never markdown code blocks
- Output: complete valid JSON with all required fields


## Tuning Rules

`/clawdbrt:tuning-rules`


## Boundaries

- Use latest `docs/vX_Y_Z/`; fallback to older
- Inject AGENTS.md as system prompt; save `.clawdibrate/iterations/AGENTS_vN.md` before overwrite; track `reflection_history`; route failures to specific section
- Flow: SPEC.md → kanban → icebox → cards → README.md → CHANGELOG.md → bump → commit
- Version bump atomic: `pyproject.toml` + `AGENTS.md` header + `CHANGELOG.md`; use `/clawdbrt:bump-version` if exists; `git commit` after
- Skills: `src/skills/{name}/SKILL.md` → `npx skills add ./src/skills --agent <agents> --skill '*' -y --global`
- Tickets: `clwdi-v{MAJOR}_{MINOR}_{PATCH}-{NNN}.md`; rename on move; copy `icebox.md`
- Spawn parallel agents for independent kanban cards; don't read files if agent spawned to read them
- `/clawdbrt:loop`=PATCH calibration; `/clawdbrt:add-new-features`=MINOR only; MAJOR needs approval
- Ask first: new eval types, judge <0.7
- Never: rewrite converged (≥0.95, 3+ iter), remove Boundaries, add lines without instruction, use checklists/TaskCreate, edit `skills/`/`.agents/` directly, auto-bump MAJOR
- Check tools before implementing


## Known Gotchas

- JSON parse fail: `try/except` → regex `re.search(r'\{.*\}', s, re.DOTALL)`
- Claude prompt flag: `-p`, not bare args
- Claude resume: `--continue`, not fresh invocation
- Subprocess: `timeout=120` in `subprocess.run()`
- Score plateau: capture harder sessions before rewriting sections
- Regression: check `reflection_history` before rewriting failing tasks
- CC logs: JSONL at `~/.claude/projects/<mangled-cwd>/` (`/`→`-`); parse message types/content blocks directly


## Score Tracking

After every calibration run, log to stdout and append to these files:

`.clawdibrate/history/scores.jsonl` — `Calibration complete | avg=0.00 | failures=0 | sections={Commands: 0.0, Setup: 0.0, ...}`
`.clawdibrate/history/reflections.jsonl` — reflection history
`.clawdibrate/history/baselines.jsonl` — baseline metrics
`.clawdibrate/history/instrumentation.jsonl` — stage timings, mode, estimate, token deltas


## References

- **Reflexion** — Shinn et al., NeurIPS 2023
- **RISE** — Qu et al., 2024
- **Recursive Language Models** — Zhang, Kraska, Khattab, Dec 2025 (arxiv.org/abs/2512.24601)
- **Evaluating AGENTS.md** — arxiv.org/abs/2602.11988
- **Engineering Guide** — latest `docs/vX_Y_Z/specs/agents_md_engineering_guide.md`

<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

`Run /clawdbrt:issue-tracking-with-bd-beads for guidance.`


## Landing the Plane (Session Completion)

`/clawdbrt:landing-the-plane-session-completion` handles all commits. Never run `git add/commit/push` manually.

