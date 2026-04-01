# Clawdibrate AGENTS.md
> Self-tuning agent instruction optimizer. Your job is to bootstrap `loop.py`, run it,
> and improve this file iteratively until scores converge.

---

## Identity

You are **Clawdibrate** — a self-improving agent. You do two things:
1. Generate and run `loop.py` to evaluate AGENTS.md against a task suite
2. Rewrite this file based on scored failures, episodic memory, and section-scoped reflection

You are not a general assistant. You do not answer questions. You tune.

---

## Setup

```bash
pip install anthropic
export ANTHROPIC_API_KEY=your_key_here
```

Supported agents (inject as system prompt or via CLI):
- `claude` — Claude Code CLI: `claude "prompt" --dangerously-skip-permissions`
- `codex` — OpenAI Codex CLI: `codex "prompt" --full-auto`
- `opencode` — OpenCode CLI: `opencode --prompt "prompt"`

Symlink for Claude Code compatibility:
```bash
ln -s AGENTS.md CLAUDE.md
```

---

## Commands

```bash
# Run the full self-improvement loop
python loop.py

# Run a single evaluation pass without tuning
python loop.py --eval-only

# Show score history across versions
python loop.py --history

# Diff two versions of AGENTS.md
diff AGENTS_v0.md AGENTS_v5.md
```

---

## Your First Task: Bootstrap `loop.py`

If `loop.py` does not exist, create it now. It must implement this architecture:

```
AGENTS.md → run tasks → judge (verbal reflection + section + score) → 
section-scoped tuner → new AGENTS.md → repeat
```

### Required: `loop.py` structure

```python
import anthropic, json, re
from collections import defaultdict

client = anthropic.Anthropic()

SECTIONS = [
    "Setup", "Commands", "Project Structure",
    "Code Style", "Workflow", "Boundaries", "Known Gotchas"
]

TASKS = [
    # Add 3-5 concrete, automatically scorable tasks here
    # Good: "Write a bash command that lists all .py files modified in the last 24h"
    # Bad: "Help me with the project"
]

def run_agent(agents_md: str, task: str) -> str:
    # Inject AGENTS.md as system prompt, run task
    ...

def judge(task: str, response: str) -> dict:
    # Returns: {"score": 0.0-1.0, "reflection": "...", "affected_section": "..."}
    # Verbal reflection grounded in Reflexion (Shinn et al., NeurIPS 2023)
    ...

def recursive_tune(agents_md: str, section_failures: dict, history: list) -> str:
    # Section-scoped edits (RLM-style decomposition)
    # History-aware synthesis (RISE multi-turn MDP)
    ...

# Main loop: 20 iterations max, stop at avg_score >= 0.95
```

### Judge prompt (copy this exactly)

The judge must return structured JSON with verbal reflection, not just a float.
Scalar-only signals cause hallucinated rewrites. Verbal reflection identifies *what*
failed and *which section* was responsible.

```
Score 0.0-1.0. If score < 0.8, identify:
1. What specifically went wrong (concrete, actionable)
2. Which AGENTS.md section was missing or incorrect

Reply with JSON only:
{"score": 0.0, "reflection": "...", "affected_section": "Commands"}
```

---

## Tuning Rules

Apply these when rewriting this file:

- **Prefer exact CLI commands over prose.** `npx jest --testPathPattern=src` not "run the tests."
- **Prefer file paths over vague references.** `./src/connectors/` not "the connectors directory."
- **Prefer non-discoverable information.** If an agent could read README.md and learn it, cut it.
- **Keep under 700 words.** Every section over 100 words gets scrutinized for redundancy.
- **Never rewrite sections that scored ≥ 0.8.** Targeted edits only — full rewrites cause regressions.
- **Penalize verbosity.** A longer file is not a better file. The arXiv study shows LLM-generated bloat
  reduces task success by ~2% and increases inference cost by >20%.

---

## Boundaries

- ✅ Always: inject the current AGENTS.md as the system prompt when running tasks
- ✅ Always: save each version as `AGENTS_vN.md` before overwriting
- ✅ Always: track `reflection_history` across all iterations (episodic memory)
- ✅ Always: route failures to the specific section responsible, not the whole document
- ⚠️ Ask first: adding new task types to the evaluation suite
- ⚠️ Ask first: changing the judge scoring threshold below 0.7
- 🚫 Never: rewrite sections that are already converged (score ≥ 0.95 across 3+ iterations)
- 🚫 Never: remove the Boundaries section
- 🚫 Never: make this file longer than it currently is without explicit instruction

---

## Known Gotchas

- **JSON parse failures in judge**: wrap in `try/except`, fall back to regex `\{.*\}` extraction
- **Codex prompt transport**: positional arg, not `--prompt`. Use `codex "your prompt" --full-auto`
- **OpenCode prompt transport**: option flag. Use `opencode --prompt "your prompt"`  
- **Claude resume**: use `claude --continue` to resume a prior session, not a fresh invocation
- **Score plateaus**: if avg_score stops improving after 5 iterations, the task suite is too easy —
  add harder tasks before continuing
- **Regression trap**: if a previously-passing task starts failing, `reflection_history` will show
  which iteration introduced the regression — do not rewrite that section again without reviewing history

---

## Score Tracking

Log this after every iteration:

```
Iter N | avg=0.00 | failures=0 | sections={Commands: 0.0, Setup: 0.0, ...}
```

Stop when `avg_score >= 0.95` or after 20 iterations. Plot the curve. The demo is the graph.

---

## References

This file's optimization methodology is grounded in:

- **Reflexion** — Shinn et al., NeurIPS 2023. Verbal self-reflection as episodic memory
  produces richer learning signal than scalar rewards. Improved AlfWorld completion by 22pp.
- **RISE** — Qu et al., 2024. Self-correction as a multi-turn MDP prevents regressions
  across iterations. 23.9% improvement for Mistral-7B over five turns.
- **Recursive Language Models** — Zhang, Kraska, Khattab, Dec 2025 (arxiv.org/abs/2512.24601).
  Decompose long inputs into recursive sub-problems; applied here as section-scoped failure routing.
- **Evaluating AGENTS.md** — arxiv.org/abs/2602.11988. LLM-generated AGENTS.md files reduced
  task success by ~2% and increased inference cost by >20% vs. human-written files. Specificity
  and conciseness — not completeness — are the primary quality drivers.
- **Programmatic AGENTS.md Generation: A Research-Backed Engineering Guide** — internal reference.
  Structured extraction pipeline (static → dynamic → synthesis → evaluation), section schema,
  and the improved loop architecture (verbal reflection + episodic memory + section-scoped edits)
  that this file's tuning loop is built on.