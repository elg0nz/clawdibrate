"""Score logging and history display."""

import json
from datetime import datetime

from .helpers import SCORES_PATH


def log_scores(iteration: int, scores: dict, avg: float, failures: int):
    """Log to stdout and scores.jsonl."""
    section_scores = {s: round(sc, 2) for s, sc in scores.items()}
    print(f"Iter {iteration} | avg={avg:.2f} | failures={failures} | sections={section_scores}")

    entry = {
        "iteration": iteration,
        "avg_score": round(avg, 2),
        "failures": failures,
        "section_scores": section_scores,
        "timestamp": datetime.now().isoformat(),
    }
    SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCORES_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def show_history():
    """Show score history from scores.jsonl."""
    if not SCORES_PATH.exists():
        print("No score history found. Run the loop first.")
        return
    print("Score History:")
    print("-" * 60)
    for line in SCORES_PATH.read_text().strip().split("\n"):
        entry = json.loads(line)
        print(f"Iter {entry['iteration']:2d} | avg={entry['avg_score']:.2f} | failures={entry['failures']}")
    print("-" * 60)
