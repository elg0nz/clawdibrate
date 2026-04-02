---
name: clawdbrt:tokens
description: Show per-section token breakdown and budget status for the instruction file
---

# /clawdbrt:tokens — Token Dashboard

Show token usage per section with trend data from the last calibration run.

## Usage

```
/clawdbrt:tokens                          # token dashboard for current repo
/clawdbrt:tokens --file PATH              # specify instruction file explicitly
```

## Steps

1. **Determine instruction file.** Use `--file` if provided, otherwise detect `AGENTS.md` in the repo root.

2. **Count tokens.** Use `clawdibrate.tokens.count_file_tokens()` to get the per-section breakdown:

   ```bash
   python3 -c "
   import json
   from pathlib import Path
   from clawdibrate.tokens import count_file_tokens

   result = count_file_tokens(Path('AGENTS.md'))
   print(json.dumps(result))
   "
   ```

3. **Load trend data.** Read the last entry from `.clawdibrate/history/scores.jsonl` and extract the `token_counts` field (if present) for comparison:

   ```bash
   python3 -c "
   import json
   from pathlib import Path

   scores_path = Path('.clawdibrate/history/scores.jsonl')
   prev = {}
   if scores_path.exists():
       lines = [l for l in scores_path.read_text().splitlines() if l.strip()]
       if lines:
           prev = json.loads(lines[-1]).get('token_counts', {}).get('sections', {})
   print(json.dumps(prev))
   "
   ```

4. **Print formatted table.** Combine the current counts with the previous counts to produce a dashboard. Sort sections by token count (heaviest first). For each section compute:
   - **Tokens** — current token count
   - **%** — percentage of total
   - **Trend** — compare to previous: `↑ +N` if increased, `↓ -N` if decreased, `→ 0` if unchanged or no prior data

5. **Show budget status.** If the repo was configured with `--token-budget` (check `.clawdibrate/config.toml` or `.clawdibrate/config.json` for a `token_budget` field), print a budget header line:

   ```
   AGENTS.md token budget: 1,198 / 1,300 (92%)
   ```

   If no budget is set, just print the total:

   ```
   AGENTS.md tokens: 1,198
   ```

## Output format

```
AGENTS.md token budget: 1,198 / 1,300 (92%)

Section                  Tokens    %    Trend
─────────────────────────────────────────────
Boundaries                 312   26%    ↓ -15
Known Gotchas              198   17%    → 0
Setup                      156   13%    ↓ -8
Skills                     142   12%    → 0
Bootstrap Transcript Cal   128   11%    ↑ +12
Tuning Rules                98    8%    ↓ -22
Commands                    64    5%    → 0
Score Tracking              52    4%    → 0
Identity                    28    2%    → 0
References                  20    2%    → 0
```

## Implementation

Run the full dashboard in a single script:

```bash
python3 -c "
import json, sys
from pathlib import Path
from clawdibrate.tokens import count_file_tokens

# Determine instruction file
file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('AGENTS.md')
if not file_path.exists():
    print(f'{file_path} not found.')
    sys.exit(1)

# Count current tokens
result = count_file_tokens(file_path)
total = result['total']
sections = result['sections']

# Load previous token counts from last calibration
prev = {}
scores_path = Path('.clawdibrate/history/scores.jsonl')
if scores_path.exists():
    lines = [l for l in scores_path.read_text().splitlines() if l.strip()]
    if lines:
        prev = json.loads(lines[-1]).get('token_counts', {}).get('sections', {})

# Load budget if configured
budget = None
for cfg in [Path('.clawdibrate/config.toml'), Path('.clawdibrate/config.json')]:
    if cfg.exists():
        text = cfg.read_text()
        if cfg.suffix == '.json':
            budget = json.loads(text).get('token_budget')
        else:
            for line in text.splitlines():
                if line.startswith('token_budget'):
                    budget = int(line.split('=')[1].strip())
        break

# Print header
name = file_path.name
if budget:
    pct = round(total / budget * 100)
    print(f'{name} token budget: {total:,} / {budget:,} ({pct}%)')
else:
    print(f'{name} tokens: {total:,}')

print()
print(f\"{'Section':<25} {'Tokens':>6} {'%':>5}    Trend\")
print('─' * 50)

# Sort by token count descending
for sec, count in sorted(sections.items(), key=lambda x: -x[1]):
    pct = round(count / total * 100) if total else 0
    diff = count - prev.get(sec, count)
    if diff > 0:
        arrow = f'↑ +{diff}'
    elif diff < 0:
        arrow = f'↓ {diff}'
    else:
        arrow = '→ 0'
    label = sec[:25]
    print(f'{label:<25} {count:>6}  {pct:>3}%    {arrow}')
"
```
