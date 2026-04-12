"""Persistence and convergence tracking for calibration history."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def load_reflections(history_dir: Path) -> list[dict[str, Any]]:
    path = history_dir / "reflections.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def save_reflection(history_dir: Path, entry: dict[str, Any]) -> None:
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "reflections.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def central_scoreboard_path(repo_root: Path) -> Path:
    """~/.clawdibrate/scoreboards/<repo-slug>.jsonl for cross-repo score tracking."""
    slug = str(repo_root.resolve()).replace("/", "-").lstrip("-")
    board_dir = Path.home() / ".clawdibrate" / "scoreboards"
    board_dir.mkdir(parents=True, exist_ok=True)
    return board_dir / f"{slug}.jsonl"


def save_score(
    history_dir: Path,
    entry: dict[str, Any],
    repo_root: Path | None = None,
) -> None:
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "scores.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    if repo_root is not None:
        board_path = central_scoreboard_path(repo_root)
        with open(board_path, "a") as f:
            f.write(json.dumps({"repo": str(repo_root.resolve()), **entry}) + "\n")


def save_instrumentation(history_dir: Path, entry: dict[str, Any]) -> None:
    """Append developer-facing run instrumentation metrics."""
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "instrumentation.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def estimate_iterations_to_target(
    history_dir: Path,
    target_score: float = 0.9,
    lookback: int = 8,
) -> dict[str, Any]:
    """Estimate remaining calibration iterations from recent score trend."""
    path = history_dir / "scores.jsonl"
    if not path.exists():
        return {
            "target_score": target_score,
            "current_avg": 0.0,
            "iterations_remaining": None,
            "slope_per_run": 0.0,
            "confidence": "low",
            "reason": "no history",
        }

    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    avgs = [float(r.get("avg", 0.0)) for r in rows if isinstance(r.get("avg"), (int, float))]
    if not avgs:
        return {
            "target_score": target_score,
            "current_avg": 0.0,
            "iterations_remaining": None,
            "slope_per_run": 0.0,
            "confidence": "low",
            "reason": "no average scores",
        }

    window = avgs[-lookback:]
    current = window[-1]
    if len(window) < 2:
        return {
            "target_score": target_score,
            "current_avg": round(current, 3),
            "iterations_remaining": None,
            "slope_per_run": 0.0,
            "confidence": "low",
            "reason": "insufficient history",
        }

    slope = (window[-1] - window[0]) / (len(window) - 1)
    if current >= target_score:
        remaining: int | None = 0
        reason = "target reached"
    elif slope <= 0:
        remaining = None
        reason = "non-improving trend"
    else:
        remaining = int(math.ceil((target_score - current) / slope))
        remaining = max(1, min(remaining, 200))
        reason = "trend projection"

    confidence = "low"
    if len(window) >= 6 and slope > 0:
        confidence = "high"
    elif len(window) >= 4 and slope > 0:
        confidence = "medium"

    return {
        "target_score": target_score,
        "current_avg": round(current, 3),
        "iterations_remaining": remaining,
        "slope_per_run": round(slope, 4),
        "confidence": confidence,
        "reason": reason,
    }


def load_baselines(history_dir: Path) -> dict[str, Any]:
    path = history_dir / "baselines.jsonl"
    if not path.exists():
        return {}
    baselines: dict[str, Any] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            entry = json.loads(line)
            baselines[entry.get("transcript")] = entry
    return baselines


def save_baseline(history_dir: Path, entry: dict[str, Any]) -> None:
    history_dir.mkdir(parents=True, exist_ok=True)
    with open(history_dir / "baselines.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def is_converged(
    section_name: str,
    reflections: list[dict[str, Any]],
    threshold: float = 0.95,
    min_runs: int = 3,
) -> bool:
    """Return True if section scored >= threshold across the last min_runs calibration runs."""
    recent_scores = [
        r["section_scores"].get(section_name)
        for r in reflections[-min_runs:]
        if "section_scores" in r and section_name in r["section_scores"]
    ]
    if len(recent_scores) < min_runs:
        return False
    return all(s >= threshold for s in recent_scores)
