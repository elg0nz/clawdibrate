---
name: loop
description: Run the Clawdibrate self-improvement tuning loop
---

# /loop

Run the AGENTS.md self-improvement loop. Evaluates the current AGENTS.md against a task suite, scores failures, and rewrites sections based on verbal reflection and episodic memory.

---

## Usage

### Full tuning loop (default)

```
/loop
```

Equivalent to `python loop.py`. Runs up to 20 iterations or until `avg_score >= 0.95`. Each iteration:

1. Runs all tasks with the current AGENTS.md injected as system prompt
2. Judges each response (score + verbal reflection + affected section)
3. Routes failures to the responsible section
4. Applies section-scoped edits via the tuner
5. Saves `AGENTS_vN.md` before overwriting
6. Logs scores to `scores.jsonl`
7. Commits the new version

### Eval-only mode

```
/loop --eval-only
```

Single evaluation pass. Runs tasks and scores them but does **not** tune AGENTS.md. Use this to benchmark the current file without side effects.

### History mode

```
/loop --history
```

Displays score history across all saved versions. Use this to check for regressions or confirm convergence.

### Agent selection

```
/loop --agent codex
/loop --agent opencode
```

Default agent is `claude`. Supported agents: `claude`, `codex`, `opencode`.

---

## Architecture

```
AGENTS.md --> run tasks --> judge (verbal reflection + section + score) -->
section-scoped tuner --> new AGENTS.md --> repeat
```

Key design decisions:
- **Verbal reflection over scalar scores.** Scalar-only signals cause hallucinated rewrites. The judge returns structured JSON with `score`, `reflection`, and `affected_section`.
- **Section-scoped edits.** Failures route to specific AGENTS.md sections, not the whole document. Based on RLM-style recursive decomposition.
- **Episodic memory.** `reflection_history` persists across iterations to prevent regressions (RISE multi-turn MDP).
- **CLI-first.** No API keys. Shells out to agent CLIs via `subprocess.run()` with `timeout=120`.

---

## Skill interface

Conforms to the skill router contract defined in `docs/v0_3_0/skill-router-draft.md`:

```python
NAME: str = "loop"
DESCRIPTION: str = "Run the AGENTS.md self-improvement tuning loop"

def run(args: list[str], ctx: dict) -> int:
    # args: parsed from slash command (e.g. ["--eval-only"])
    # ctx keys: agents_md, version, workdir
    # returns 0 on success
```

Sub-agents spawned via `subprocess.run()` with `timeout=120`. Context serialized to tempfiles -- never shared across processes.

---

## Reference

Full reference implementation (loop.py structure, judge prompt, seed tasks, sections list): `docs/v0_0_0/specs/agents-proto.md`
