# Clawdibrate AGENTS.md

> **Version: 0.14.1** | [Changelog](./docs/CHANGELOG.md)
>
> Semver: **PATCH** = backward-compatible fixes (wording, tuning). **MINOR** = new backward-compatible functionality (new sections, commands, skills). **MAJOR** = incompatible changes to the calibration loop contract or CLI interface.
>
> Repo note: Do **not** add the "This repo uses clawdibrate... Install... Run..." onboarding snippet here. That snippet is for target repos being calibrated, not for clawdibrate's own `AGENTS.md`.

---

## Identity

`/clawdbrt-identity`


## Setup

```bash
npx skills add ./src/skills --agent claude-code cursor codex --skill '*' -y --global
```

**Agent env:** `repo/.clawdibrate/env` (copy `clawdibrate.env.example`, set `CLAWDIBRATE_AGENT=cursor`) or fallback `repo/.env` (`CLAWDIBRATE_*` keys only).

**Agents** (`--agent`/`CLAWDIBRATE_AGENT`, default `claude`):
- `cursor` → `cursor agent --print --force`
- `claude` → `claude -p "{prompt}" --dangerously-skip-permissions`
- `codex` → `codex exec --full-auto "{prompt}"`
- `opencode` → `opencode --prompt "{prompt}"`
- `llm` → `llm "{prompt}"`
- Custom: `CLAWDIBRATE_AGENT_CMD='llm -s "$(cat {system_prompt})" {prompt}'`

**Runtime:** Python 3.10+, Node.js. Use `uv` only — `uv add` for deps, `uv run` to execute (never `pip install`).


## Commands

See `/clawdbrt-commands` for detailed guidance.


## Skills

Skills: `src/skills/<name>/SKILL.md`, prefix `clawdbrt-`. Frontmatter: `name`+`description`. Register: `npx skills add ./src/skills --agent <agents> --skill '*' -y --global`. Commit `skills-lock.json`, `skills/`, `.agents/`. Edit only `src/skills/`—never `skills/` or `.agents/skills/`. All capabilities must be skills.

Core skills: `loop`, `kanban`, `add-new-features`, `implement`, `scores`.

Extract section→`src/skills/<kebab>/SKILL.md` when score <0.7 (3+ runs) or churn ≥3. Reference as `See /clawdbrt-<skill>`. Never re-expand externalized sections inline (boundary violation).


## Bootstrap Transcript Calibrator

`transcript → metrics → bug-identifier → judge → implementer → section-scoped edits → new AGENTS.md`

**Specs:** Latest `docs/vX_Y_Z/specs/` (fallback older). Ref: `docs/vX_Y_Z/README.md` + `clawdibrate/orchestrator.py`

**Pre-analysis:** Verify transcript + AGENTS.md completeness; STOP if truncated. Read AGENTS.md in full (no offset/limit).

**Tool rules:**
- Read=reads; Glob=discovery; Grep=search; Read offset/limit=line ranges — no Bash cat/head/sed/awk/find/grep
- Always Read before Edit; on failure Read again before retry
- Shell tool only for shell commands

**Edit rules:**
- Flag sections with ≥3 edits before editing
- Batch all churn signals into one parallel pass — never sequential per-event
- All AGENTS.md changes: single batched commit; 2 consecutive AGENTS.md-only commits within 5min = loop → STOP
- >3 files: single batched agent OR parallel tool calls; Explore OR read directly — never both for same files

**Output:** Complete valid JSON with all required fields.


## Tuning Rules

`/clawdbrt-tuning-rules`


## Boundaries

- Use latest `docs/vX_Y_Z/`; fallback older
- Inject AGENTS.md as system prompt; save `.clawdibrate/iterations/AGENTS_vN.md` before overwrite; track `reflection_history`; route failures to section
- Flow: SPEC.md→kanban→icebox→cards→README.md→CHANGELOG.md→bump→commit
- Atomic bump: `pyproject.toml`+`AGENTS.md` header+`CHANGELOG.md`; use `/clawdbrt-bump-version` if exists; commit after
- Skills: `src/skills/{name}/SKILL.md`→`npx skills add ./src/skills --agent <agents> --skill '*' -y --global`
- Tickets: `clwdi-v{MAJ}_{MIN}_{PAT}-{NNN}.md`; rename on move; copy `icebox.md`
- Parallel agents for independent cards; skip file reads if agent handles them
- `/clawdbrt-loop`=PATCH; `/clawdbrt-add-new-features`=MINOR; MAJOR needs approval
- Ask before: new eval types, judge <0.7
- Never: rewrite ≥0.95/3+iter, remove Boundaries, add unrequested lines, use checklists/TaskCreate, directly edit `skills/`/`.agents/`, auto-bump MAJOR
- Check existing tools before implementing


## Known Gotchas

- JSON parse fail: `try/except` → `re.search(r'\{.*\}', s, re.DOTALL)`
- Claude: prompt=-p, resume=--continue, subprocess timeout=120
- Score plateau: capture harder sessions before rewriting sections
- Regression: check `reflection_history` before rewriting failing tasks
- CC logs: JSONL `~/.claude/projects/<mangled-cwd>/` (`/`→`-`); lines: `{type,message:{role,content:[{type:"text",text}|{type:"tool_use",id,name,input}|{type:"tool_result",tool_use_id,content}]}}`; `json.loads()` per line, filter on `type`/`content[*].type`


## Score Tracking

After every calibration run, log to stdout and append to these files:

`.clawdibrate/history/scores.jsonl` — `Calibration complete | avg=0.00 | failures=0 | sections={Commands: 0.0, Setup: 0.0, ...}`
`.clawdibrate/history/reflections.jsonl` — reflection history
`.clawdibrate/history/baselines.jsonl` — baseline metrics
`.clawdibrate/history/instrumentation.jsonl` — stage timings, mode, estimate, token deltas


## References

**Refs:** Reflexion (Shinn et al., NeurIPS 2023) · RISE (Qu et al., 2024) · Recursive LMs (Zhang/Kraska/Khattab, arxiv.org/abs/2512.24601) · Evaluating AGENTS.md (arxiv.org/abs/2602.11988) · Engineering Guide: `docs/vX_Y_Z/specs/agents_md_engineering_guide.md`

<!-- BEGIN BEADS INTEGRATION -->


## Issue Tracking with bd (beads)

`Run /clawdbrt-issue-tracking-with-bd-beads for guidance.`


## Landing the Plane (Session Completion)

`/clawdbrt-landing-the-plane-session-completion` handles all commits. Never run `git add/commit/push` manually — not even at session end. If the skill was already invoked, do not fall back to raw git commands.

