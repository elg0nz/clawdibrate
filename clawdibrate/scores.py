"""Score history display and sparkline rendering."""

from __future__ import annotations

import json
from pathlib import Path

_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float]) -> str:
    """Return an ASCII sparkline string for a list of floats using Unicode block chars."""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = hi - lo
    result: list[str] = []
    for v in values:
        if span == 0:
            idx = len(_SPARK_CHARS) // 2
        else:
            idx = int((v - lo) / span * (len(_SPARK_CHARS) - 1))
            idx = max(0, min(idx, len(_SPARK_CHARS) - 1))
        result.append(_SPARK_CHARS[idx])
    return "".join(result)


def show_scores(repo_root: Path) -> None:
    """Read .clawdibrate/history/scores.jsonl and print a score history table + sparkline."""
    scores_path = repo_root / ".clawdibrate" / "history" / "scores.jsonl"
    if not scores_path.exists():
        print("No scores found. Run calibration first.")
        return

    entries: list[dict] = []
    for line in scores_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not entries:
        print("No scores found. Run calibration first.")
        return

    last_10 = entries[-10:]
    print(f"{'Date':<12}  {'Avg':>6}  {'Token Delta':>12}")
    print("-" * 34)
    for e in last_10:
        ts = e.get("timestamp", "")
        date_str = ts[:10] if ts else "unknown"
        avg = e.get("avg", 0.0)
        token_delta = e.get("token_delta", 0)
        sign = "+" if token_delta > 0 else ""
        print(f"{date_str:<12}  {avg:>6.3f}  {sign}{token_delta:>11}")

    avgs = [e.get("avg", 0.0) for e in entries]
    spark = sparkline(avgs)
    print()
    print(f"Trend ({len(avgs)} runs): {spark}")
