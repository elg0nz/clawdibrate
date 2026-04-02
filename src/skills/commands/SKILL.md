---
name: clawdbrt:commands
description: "Externalized AGENTS.md heading 'Commands' as clawdbrt:commands (clawdibrate auto-extract)."
---

# Commands

```bash
# Loop modes (progressive is the default — cancel-safe, right for 90% of runs)
python -m clawdibrate                              # progressive: cancel-safe mini-iterations (default)
python -m clawdibrate --mode fast                  # fast: single pass, quick spot-check or CI gate
python -m clawdibrate --mode max --target-score 0.9 # max: iterate until optimized / plateau

# Agent selection
python -m clawdibrate --agent cursor               # Cursor Agent CLI (or use .clawdibrate/env)
python -m clawdibrate --agent codex                # use codex as the calibration agent
python -m clawdibrate --no-auto-section-skills     # calibrate only; do not auto-create section skills / npx
python -m clawdibrate --transcript path/to.jsonl   # calibrate from one transcript
python -m clawdibrate --dry-run                    # inspect the run without editing AGENTS.md
python -m clawdibrate --scores                     # print score history + ASCII sparkline
python -m clawdibrate --check-idempotent --transcript path/to.jsonl  # convergence assertion
python -m clawdibrate --token-budget 5000          # hard cap on file tokens
```

---
