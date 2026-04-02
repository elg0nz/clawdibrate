# Quickstart

```bash
npx skills add ./src/skills --all -y
# After this completes, restart your terminal (or reload your IDE) so the new skills are available

# Record a real session first
/clawdbrt:record-start
# ...do normal work...
/clawdbrt:record-stop

# Install once, then run against any repo with an AGENTS.md
python -m pip install -e .

# Configure a target repo to use clawdibrate
python -m clawdibrate --repo ~/Code/other-repo --setup

# Calibrate from all recorded transcripts in the current repo (default agent: Claude Code CLI)
python -m clawdibrate

# Persist agent choice for IDE tasks / non-login shells (loaded before each run)
mkdir -p .clawdibrate && cp clawdibrate.env.example .clawdibrate/env

# Or one-off in the shell: export CLAWDIBRATE_AGENT=cursor

# Or target a different repo and transcript explicitly
python -m clawdibrate --repo ~/Code/other-repo --agent codex
python -m clawdibrate --repo ~/Code/other-repo --transcript .clawdibrate/transcripts/example.jsonl
python -m clawdibrate --repo ~/Code/other-repo calibrate --dry-run

# Bootstrap a synthetic transcript from the active instruction file's git history
python -m clawdibrate --repo ~/Code/other-repo --synthesize-git-history
```
