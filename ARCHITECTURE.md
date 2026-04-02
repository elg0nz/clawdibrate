# Clawdibrate Architecture

Clawdibrate is a transcript-based instruction file calibration system. It reads real agent conversation transcripts, computes deterministic waste metrics, identifies failures in the active instruction file (`AGENTS.md`), and rewrites only the implicated sections to improve system prompt quality.

---

## Directory Structure

```
clawdibrate/
├── clawdibrate/                  # Main Python package
│   ├── __main__.py               # CLI entry point & argument parsing
│   ├── orchestrator.py           # Core calibration orchestrator
│   ├── instruction_files.py      # Detect/setup instruction files, skill installation
│   ├── session_dump.py           # Parse agent session logs to structured transcripts
│   ├── git_history.py            # Bootstrap synthetic transcripts from git history
│   ├── compress.py               # Token compression advisor
│   ├── env_bootstrap.py          # Load .clawdibrate/env or .env for agent config
│   ├── tokens.py                 # Token counting (tiktoken cl100k_base)
│   ├── ralph.py                  # Parallel worker pool (fan_out for multi-agent runs)
│   └── prompts/
│       ├── bug-identifier.md     # Failure taxonomy analyzer prompt
│       ├── judge.md              # Scores fixes & produces JSON edits
│       └── implementer.md        # Applies edits to instruction file
├── src/skills/                   # Canonical source for all skills
│   ├── loop/                     # Main calibration loop skill
│   ├── kanban/                   # Kanban board management
│   ├── add-new-features/         # MINOR version feature addition
│   ├── implement/                # Card implementation
│   ├── record-start/             # Transcript recording start
│   ├── record-stop/              # Transcript recording stop
│   ├── record-from-git/          # Git history → synthetic transcript
│   ├── scores/                   # Calibration scoreboard
│   ├── identity/                 # Identity guidance (externalized section)
│   ├── boundaries/               # Boundary rules (externalized section)
│   └── known-gotchas/            # Known issues (externalized section)
├── skills/                       # Installed skills output (committed, never edit directly)
├── .agents/skills/               # Per-agent skill installs (committed, never edit directly)
├── docs/
│   ├── CHANGELOG.md
│   └── vX_Y_Z/
│       ├── README.md             # Version-specific implementation guide
│       ├── kanban/               # Kanban cards for this version
│       └── specs/                # Spec documents
├── .clawdibrate/                 # Working directory (gitignored)
│   ├── env                       # Agent config (preferred over .env)
│   ├── transcripts/              # Recorded session JSONLs
│   ├── history/
│   │   ├── scores.jsonl          # Per-run calibration scores
│   │   ├── baselines.jsonl       # Baseline metrics for drift detection
│   │   ├── reflections.jsonl     # Episodic memory of past failures
│   │   └── instrumentation.jsonl # Stage timings, mode, token deltas
│   └── iterations/               # AGENTS.md snapshots (AGENTS_vN.md)
├── AGENTS.md                     # Active instruction file
├── skills-lock.json              # NPX skills registry lock (committed)
└── pyproject.toml                # Package config (Python 3.10+)
```

---

## Calibration Pipeline

The core loop is a four-stage pipeline:

```
transcript.jsonl
    ↓
[1. DETERMINISTIC METRICS]  (no LLM, pure transcript analysis)
    ├─ token_efficiency:     ideal_calls / actual_calls
    ├─ search_waste_ratio:   wasted_searches / total_searches
    ├─ correction_rate:      user_corrections / user_messages
    ├─ repetition_score:     repeated_tool_calls (Rouge-L > 0.8)
    └─ success_rate:         1.0 if task completed, else 0.0
    ↓
[2. BUG IDENTIFIER]  (LLM agent, prompts/bug-identifier.md)
    ├─ Input:  AGENTS.md + transcript + metrics
    ├─ Failure taxonomy:
    │   ├─ unnecessary_search       (searched for info already in AGENTS.md)
    │   ├─ wrong_tool               (wrong CLI flag or tool)
    │   ├─ boundary_violation       (violated an explicit rule)
    │   ├─ unnecessary_clarification(asked user for something AGENTS.md answers)
    │   ├─ circuitous_path          (N steps when M < N was possible)
    │   └─ repetition_loop          (repeated same action without progress)
    └─ Output: JSON array of failure objects with responsible section
    ↓
[3. JUDGE]  (LLM agent, prompts/judge.md)
    ├─ Input:  failures + suggested fixes
    ├─ Scores each fix (0.0–1.0)
    ├─ Produces JSON section edits
    └─ Output: approved edits + justification
    ↓
[4. IMPLEMENTER]  (LLM agent, prompts/implementer.md)
    ├─ Input:  approved edits + current AGENTS.md
    ├─ Applies edits surgically to responsible sections only
    └─ Output: updated AGENTS.md
    ↓
[SNAPSHOT & COMMIT]
    ├─ Save prior AGENTS.md → .clawdibrate/iterations/AGENTS_vN.md
    ├─ Auto-bump PATCH version
    ├─ Log scores → .clawdibrate/history/scores.jsonl
    ├─ git commit
    └─ Auto-create section skills if section score < 0.7 or churn ≥ 3
```

---

## Key Modules

| Module | Role |
|--------|------|
| `orchestrator.py` | Core loop: `calibrate()`, `compute_metrics()`, `split_transcripts()` |
| `__main__.py` | CLI argument parsing, mode routing |
| `instruction_files.py` | `detect_instruction_file()`, `ensure_clawdibrate_setup()`, `_install_bundled_skills()` |
| `session_dump.py` | Parse `~/.claude/projects/<mangled-path>/*.jsonl` → structured transcripts |
| `git_history.py` | Bootstrap synthetic transcripts from git history |
| `ralph.py` | `fan_out()` thread pool for parallel multi-agent runs |
| `tokens.py` | `count_tokens()` using tiktoken cl100k_base |
| `env_bootstrap.py` | Load `.clawdibrate/env` then `.env` (CLAWDIBRATE_* keys only) |

---

## Skills System

Skills are slash commands that route to `SKILL.md` files. All use the `clawdbrt:` namespace.

**Canonical source:** `src/skills/{name}/SKILL.md` with YAML frontmatter:
```yaml
---
name: clawdbrt:<skill-name>
description: Short description
---
# Agent instructions
```

**Distribution:**
```bash
npx skills add ./src/skills --agent claude-code cursor codex --skill '*' -y
```
This writes `skills/` and `.agents/skills/` (both committed). Never edit those outputs directly.

**Section skills:** When a section scores < 0.7 across 3+ runs or has churn ≥ 3 in git, its content is externalized to `src/skills/<section-name>/SKILL.md` and referenced from AGENTS.md: `See /clawdbrt:<skill-name> for detailed guidance.`

---

## Agent Configuration

Priority order for agent selection:

1. `--agent` CLI flag
2. `CLAWDIBRATE_AGENT` environment variable
3. `.clawdibrate/env` (preferred — gitignored, `KEY=value`)
4. `.env` (fallback — only `CLAWDIBRATE_*` keys merged)
5. Default: `claude`

**Built-in agents:**

| Name | Command |
|------|---------|
| `claude` | `claude -p "{prompt}" --dangerously-skip-permissions` |
| `cursor` | `cursor agent --print --force` |
| `codex` | `codex exec --full-auto "{prompt}"` |
| `opencode` | `opencode --prompt "{prompt}"` |
| `llm` | `llm "{prompt}"` |

**Custom agent:** Set `CLAWDIBRATE_AGENT_CMD` with `{system_prompt}` and `{prompt}` placeholders.

---

## Transcript Format

Sessions are JSONL in `.clawdibrate/transcripts/`. Each line:
```json
{"role": "user|assistant", "tool": "Glob|Grep|Read|Edit|Bash|...", "content": "...", "args": {...}}
```

Claude Code sessions are parsed from `~/.claude/projects/<mangled-cwd>/*.jsonl` (path `/` → `-`).

---

## Run Modes

| Mode | Behavior |
|------|---------|
| `fast` | Single pass, quick low-hanging-fruit fixes |
| `progressive` | Many small cancel-safe iterations |
| `max` | Iterate until `--target-score` reached or plateau |

---

## Versioning

| Bump | Trigger | Who |
|------|---------|-----|
| PATCH `X.Y.Z+1` | Wording/tuning fixes | `/clawdbrt:loop` (auto) |
| MINOR `X.Y+1.0` | New sections, commands, skills | `/clawdbrt:add-new-features` |
| MAJOR `X+1.0.0` | Breaking loop contract or CLI | Human only |

Version workflow: `SPEC.md → kanban cards → copy icebox → implement cards → README.md → CHANGELOG.md → bump → commit`

---

## Data Files

| File | Purpose |
|------|---------|
| `.clawdibrate/history/scores.jsonl` | Per-run scores + section breakdowns |
| `.clawdibrate/history/baselines.jsonl` | Baseline metrics for drift detection |
| `.clawdibrate/history/reflections.jsonl` | Episodic memory of past failures |
| `.clawdibrate/history/instrumentation.jsonl` | Stage timings, token deltas |
| `.clawdibrate/iterations/AGENTS_vN.md` | Snapshots before each overwrite |
| `skills-lock.json` | NPX skills registry (committed) |
| `clawdibrate.env.example` | Template for `.clawdibrate/env` |
