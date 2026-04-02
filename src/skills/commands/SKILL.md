---
name: clawdbrt:commands
description: "Externalized AGENTS.md heading 'Commands' as clawdbrt:commands (clawdibrate auto-extract)."
---

# Commands

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
python -m clawdibrate --scores                     # print score history + ASCII sparkline
python -m clawdibrate --check-idempotent --transcript path/to.jsonl  # convergence assertion
python -m clawdibrate --token-budget 5000          # hard cap on file tokens
```

---
