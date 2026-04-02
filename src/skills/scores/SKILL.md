---
name: clawdbrt:scores
description: Show calibration scoreboard for a repo or all tracked repos
---

# /clawdbrt:scores — Calibration Scoreboard

Show score history from past calibration runs.

## Usage

```
/clawdbrt:scores                  # scores for the current repo
/clawdbrt:scores --repo /path     # scores for a specific repo
/clawdbrt:scores --all            # scores for all tracked repos
```

## Steps

1. **Current repo (default):** Read `.clawdibrate/history/scores.jsonl` in the current working directory (or `--repo` path). Print a table: timestamp | avg | train_avg | test_avg | top sections.

2. **All repos (`--all`):** Read every file in `~/.clawdibrate/scoreboards/`. Group entries by `repo` field. For each repo, show the most recent entry plus a trend arrow (↑↓→) based on whether avg improved from the prior run.

## Output format

```
Repo: /path/to/repo
──────────────────────────────────────────────────────
  Date           Avg    Train  Test   Sections
  2026-04-01     0.64   0.64   0.50   Git Version Control: 0.72 | scorgix-mcp: 0.81
  2026-03-15     0.51   0.51   —      CHANGELOG Rules: 0.44
──────────────────────────────────────────────────────
Trend: ↑ +0.13
```

For `--all`, repeat the block for each tracked repo, sorted by most recently calibrated.

## Implementation

Read the JSONL files directly with `python3 -c` or a short inline script — no dependencies needed:

```bash
# Current repo
python3 -c "
import json, sys
from pathlib import Path
scores_path = Path('.clawdibrate/history/scores.jsonl')
if not scores_path.exists():
    print('No scores found. Run calibration first.')
    sys.exit(0)
rows = [json.loads(l) for l in scores_path.read_text().splitlines() if l.strip()]
for r in rows:
    secs = ' | '.join(f'{k}: {v:.2f}' for k,v in r.get('sections',{}).items())
    print(f\"  {r['timestamp'][:10]}  avg={r['avg']:.3f}  train={r.get('train_avg','—')}  test={r.get('test_avg','—')}\")
    if secs:
        print(f'    {secs}')
"
```

For `--all`, glob `~/.clawdibrate/scoreboards/*.jsonl` and process each.
