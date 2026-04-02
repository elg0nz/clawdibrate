# Ralph Loop Strategy for v0.8.0

## Overview

Use Ralph-style headless loops to implement v0.8.0 kanban cards ~10x faster via parallel `claude -p` workers using `--model haiku`. The ralph worker infrastructure lives in the `clawdibrate` Python package — not as a shell script — so it powers **both** kanban card implementation and the calibration loop itself.

## Two Uses of Ralph Workers

### 1. Calibration loop (`/clawdbrt:loop`)

The orchestrator fans out parallel workers for each stage:
- N workers for bug-identification (one per transcript)
- M workers for judging (one per failure)
- K workers for implementing (one per section)

This replaces the current sequential `run_agent()` calls.

### 2. Kanban card implementation (`/clawdbrt:implement`)

The orchestrator reads kanban cards, resolves dependency waves, and fans out parallel workers per wave:
- Wave 1: cards with no dependencies (blocking)
- Wave 2+: cards whose dependencies are satisfied (parallel)

## Mapping

| Ralph Concept | Clawdibrate Equivalent |
|---|---|
| `PROMPT.md` | Per-task prompt built by Python orchestrator |
| `AGENTS.md` | Existing operational guide (injected every iteration) |
| `IMPLEMENTATION_PLAN.md` | `docs/v0_8_0/kanban/` cards (status field = shared state) |
| `specs/*` | `docs/v0_8_0/SPEC.md` |
| Outer bash loop | `clawdibrate/ralph.py` — Python worker pool |
| Subagents | `claude -p "..." --model haiku` spawned via `subprocess` |
| Backpressure | `python -m pytest`, `python -c "import clawdibrate"` |

## Architecture: `clawdibrate/ralph.py`

```python
# Core worker primitive
def run_worker(prompt: str, model: str = "haiku", timeout: int = 120) -> str:
    """Spawn a headless claude worker and return its stdout."""
    # claude -p "{prompt}" --model {model} --dangerously-skip-permissions

# Fan-out primitive
def fan_out(tasks: list[dict], workers: int = 4, model: str = "haiku") -> list[dict]:
    """Run N tasks in parallel using a worker pool. Each task has a prompt and an id."""
    # concurrent.futures.ProcessPoolExecutor or ThreadPoolExecutor

# Calibration fan-out
def calibrate_parallel(transcripts, agents_md, ...) -> list[dict]:
    """Ralph-style parallel calibration: fan out bug-id, judge, implement."""

# Kanban fan-out
def implement_cards(cards: list[Path], spec: str, agents_md: str, ...) -> list[dict]:
    """Ralph-style parallel kanban implementation: resolve waves, fan out per wave."""
```

### Calibration flow

```
orchestrator.py
  ├── fan_out: N transcript workers (bug-identifier)
  │     └── claude -p "..." --model haiku
  ├── collect failures
  ├── fan_out: M failure workers (judge)
  │     └── claude -p "..." --model haiku
  ├── collect verdicts
  ├── fan_out: K section workers (implementer)
  │     └── claude -p "..." --model haiku
  └── collect, validate, merge, commit
```

### Kanban flow

```
ralph.py
  ├── read kanban cards, resolve dependency graph
  ├── Wave 1: fan_out(independent cards)
  │     └── claude -p "{agents_md + spec + card}" --model haiku
  ├── Wave 2: fan_out(cards whose deps are done)
  │     └── claude -p "..." --model haiku
  └── report results
```

## Execution Waves for v0.8.0

Cards 002–005 all depend on 001 (token counting core). So:

- **Wave 1** (sequential): `clwdi-v0_8_0-001` — tiktoken core in `clawdibrate/tokens.py`
- **Wave 2** (parallel, 4 workers): `clwdi-v0_8_0-002`, `003`, `004`, `005` simultaneously

2 waves instead of 5 sequential = ~2.5x from parallelism, plus haiku speed ≈ 10x total.

## CLI Integration

```bash
# Calibrate with parallel workers (default: 4 workers, haiku model)
python -m clawdibrate --workers 4 --model haiku

# Implement kanban cards via ralph workers
python -m clawdibrate --implement docs/v0_8_0/kanban --workers 4 --model haiku

# Sequential fallback
python -m clawdibrate --workers 1
```

## Key Ralph Principles Applied

1. **Context is everything** — each worker gets only its task context (~5K tokens). Fresh context per task = 100% smart zone.
2. **Main process = scheduler** — Python orchestrator dispatches, workers do all the LLM work.
3. **Backpressure** — workers must pass validation before their output is accepted.
4. **Let Ralph Ralph** — workers implement, test, commit. No human in the loop.
5. **AGENTS.md stays operational** — workers return content to orchestrator; only orchestrator writes to AGENTS.md.

## Key Constraints

- Workers must not modify AGENTS.md directly — they return content, orchestrator merges
- Worker I/O via temp files: `/tmp/clawdibrate-worker-{uuid}.json`
- Workers inherit `CLAWDIBRATE_AGENT_CMD` if set, otherwise use `claude -p`
- Timeout per worker: 120s default (configurable via `--timeout`)
- `--model` flag: `haiku` for speed, `sonnet`/`opus` for quality
