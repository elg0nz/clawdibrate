# v0.10.0 Smoke Test

End-to-end validation of clawdibrate on a synthetic repo. Tests the full pipeline, all modes, new features, and returns a scoreboard.

## Prerequisites

```bash
cd ~/Code/clawdibrate
pip install ruff mypy bandit vulture radon   # if not already installed
python -m pytest tests/test_calibrate.py -v  # unit tests — expect 40/40 pass
./scripts/presubmit.sh                       # quality gate — expect all green
```

---

## Step 1: Create a synthetic test repo

```bash
# Create a throwaway repo with a deliberately flawed AGENTS.md
mkdir -p /tmp/clawdibrate-smoke && cd /tmp/clawdibrate-smoke
git init

cat > AGENTS.md << 'EOF'
# Smoke Test AGENTS.md

> **Version: 0.1.0**

## Identity
You are a helpful coding assistant.

## Known Gotchas
- Sometimes the agent reads files with offset/limit instead of reading them fully.
- The agent occasionally uses inline imports inside hot loops.
- Watch out for bare except clauses.

## Boundaries
- Stay within the repo directory.
- Never modify files outside the project root.
- Ask before deleting anything.

## Commands
- `git status` — check repo state
- `npm test` — run tests
EOF

git add AGENTS.md && git commit -m "init: seed AGENTS.md"
```

## Step 2: Create synthetic transcripts

```bash
mkdir -p .clawdibrate/transcripts

# Transcript 1: Agent wastes searches, user corrects
cat > .clawdibrate/transcripts/session_001.jsonl << 'EOF'
{"role": "user", "content": "Fix the bug in parser.py"}
{"role": "assistant", "tool": "Grep", "args": "parser"}
{"role": "assistant", "tool": "Grep", "args": "parser.py"}
{"role": "assistant", "tool": "Read", "args": "parser.py", "content": ""}
{"role": "assistant", "tool": "Read", "args": "parser.py:1-50", "content": ""}
{"role": "user", "content": "No, not that — read the whole file, don't use offset"}
{"role": "assistant", "tool": "Read", "args": "parser.py", "content": "full file"}
{"role": "assistant", "tool": "Edit", "args": "parser.py", "content": "fixed"}
{"role": "assistant", "content": "Done, task complete."}
EOF

# Transcript 2: Agent uses inline imports, gets corrected
cat > .clawdibrate/transcripts/session_002.jsonl << 'EOF'
{"role": "user", "content": "Add logging to the auth module"}
{"role": "assistant", "tool": "Read", "args": "auth.py"}
{"role": "assistant", "tool": "Edit", "args": "auth.py", "content": "import logging inside function"}
{"role": "user", "content": "Don't use inline imports, move it to the top"}
{"role": "assistant", "tool": "Edit", "args": "auth.py", "content": "moved import to top"}
{"role": "assistant", "content": "Done, all complete."}
EOF

# Transcript 3: Clean session, no issues
cat > .clawdibrate/transcripts/session_003.jsonl << 'EOF'
{"role": "user", "content": "Refactor the config loader"}
{"role": "assistant", "tool": "Read", "args": "config.py"}
{"role": "assistant", "tool": "Edit", "args": "config.py"}
{"role": "assistant", "content": "Refactoring complete, task finished."}
EOF

# Transcript 4: Lots of wasted searches
cat > .clawdibrate/transcripts/session_004.jsonl << 'EOF'
{"role": "user", "content": "Find where the API key is used"}
{"role": "assistant", "tool": "Grep", "args": "API_KEY"}
{"role": "assistant", "tool": "Grep", "args": "api_key"}
{"role": "assistant", "tool": "Grep", "args": "apiKey"}
{"role": "assistant", "tool": "Glob", "args": "**/*.env"}
{"role": "assistant", "tool": "Read", "args": ".env"}
{"role": "assistant", "tool": "Read", "args": "config.py"}
{"role": "assistant", "content": "Found it in config.py"}
EOF

# Transcript 5: Repetitive tool calls
cat > .clawdibrate/transcripts/session_005.jsonl << 'EOF'
{"role": "user", "content": "Update the test suite"}
{"role": "assistant", "tool": "Read", "args": "tests/test_main.py"}
{"role": "assistant", "tool": "Read", "args": "tests/test_main.py"}
{"role": "assistant", "tool": "Read", "args": "tests/test_main.py"}
{"role": "assistant", "tool": "Edit", "args": "tests/test_main.py"}
{"role": "assistant", "content": "Tests updated, done."}
EOF

# Transcript 6: User correction + failure to complete
cat > .clawdibrate/transcripts/session_006.jsonl << 'EOF'
{"role": "user", "content": "Deploy the service"}
{"role": "assistant", "tool": "Bash", "args": "docker build ."}
{"role": "user", "content": "Stop, wrong approach, use the Makefile instead"}
{"role": "assistant", "tool": "Bash", "args": "make deploy"}
{"role": "assistant", "content": "Deployment started"}
EOF
```

## Step 3: Run dry-run to verify setup

```bash
cd /tmp/clawdibrate-smoke
python -m clawdibrate --repo . --dry-run 2>&1
```

**Expected:** Metrics printed for each transcript, no agent calls, `reason=dry_run`.

## Step 4: Test each mode

### 4a. Standard mode (single pass)

```bash
python -m clawdibrate --repo . --mode standard --no-auto-section-skills 2>&1 | tee /tmp/smoke-standard.log
```

**Expected:** 3-stage pipeline runs (bug-id → judge → implementer). AGENTS.md updated, version bumped to 0.1.1.

### 4b. Fast mode

```bash
python -m clawdibrate --repo . --mode fast --no-auto-section-skills 2>&1 | tee /tmp/smoke-fast.log
```

**Expected:** Quick pass with `--max-transcripts 3 --workers 1 --holdout-ratio 0`.

### 4c. Progressive mode

```bash
python -m clawdibrate --repo . --mode progressive --max-iterations 3 --progressive-batch-size 2 --no-auto-section-skills 2>&1 | tee /tmp/smoke-progressive.log
```

**Expected:** Up to 3 iterations, 2 transcripts per batch. Each iteration commits separately. Cancel-safe.

### 4d. Max mode

```bash
python -m clawdibrate --repo . --mode max --target-score 0.9 --max-iterations 5 --no-auto-section-skills 2>&1 | tee /tmp/smoke-max.log
```

**Expected:** Iterates until avg >= 0.9 or plateau or 5 iterations. Reports optimization estimate.

## Step 5: Test new v0.10.0 features

### 5a. Score history

```bash
python -m clawdibrate --repo . --scores
```

**Expected:** Table of scores from the runs above + ASCII sparkline.

### 5b. Idempotency check

```bash
python -m clawdibrate --repo . --check-idempotent --transcript .clawdibrate/transcripts/session_003.jsonl --no-auto-section-skills
echo "Exit code: $?"
```

**Expected:** PASS if second run produces no changes. Exit code 0.

### 5c. Token budget enforcement

```bash
python -m clawdibrate --repo . --token-budget 50 --no-auto-section-skills --transcript .clawdibrate/transcripts/session_001.jsonl 2>&1 | grep -i "rejected\|budget\|cap"
```

**Expected:** Edits rejected when they would exceed the 50-token cap.

## Step 6: Collect the scoreboard

```bash
echo ""
echo "========================================="
echo "  CLAWDIBRATE v0.10.0 SMOKE TEST RESULTS"
echo "========================================="
echo ""

echo "--- Unit Tests ---"
cd ~/Code/clawdibrate
python -m pytest tests/test_calibrate.py --tb=no -q 2>&1 | tail -1

echo ""
echo "--- Presubmit Gate ---"
./scripts/presubmit.sh 2>&1 | grep -E "^=== |All checks|Success:|All tooling"

echo ""
echo "--- Radon Complexity (calibrate) ---"
radon cc clawdibrate/orchestrator.py -nb -s 2>&1 | grep "calibrate"

echo ""
echo "--- Score History ---"
cd /tmp/clawdibrate-smoke
python -m clawdibrate --repo . --scores 2>&1

echo ""
echo "--- Git Log (version progression) ---"
git log --oneline | head -10

echo ""
echo "--- Final AGENTS.md version ---"
head -5 AGENTS.md
```

## Expected Scoreboard Output

```
=========================================
  CLAWDIBRATE v0.10.0 SMOKE TEST RESULTS
=========================================

--- Unit Tests ---
40 passed in 0.XXs

--- Presubmit Gate ---
=== Ruff (lint + style) ===     All checks passed!
=== Mypy (types) ===            Success: no issues found in 12 source files
=== Bandit (security) ===       (clean)
=== Vulture (dead code) ===     (clean)
=== All tooling clean. Proceed to copilot prompt. ===

--- Radon Complexity (calibrate) ---
    F XXXX:0 calibrate - D (was F)

--- Score History ---
Score | Date       | Avg   | Token Delta
------|------------|-------|------------
    1 | 2026-04-02 | 0.XXX | +XX
  ... | ...        | ...   | ...
Trend: ▁▃▅▇█  0.XXX

--- Git Log (version progression) ---
XXXXXXX clawdibrate: calibrate AGENTS.md -> 0.1.X
...

--- Final AGENTS.md version ---
> **Version: 0.1.X**
```

## Cleanup

```bash
rm -rf /tmp/clawdibrate-smoke
```
