"""Tests for clawdibrate.history — persistence and convergence tracking."""

from __future__ import annotations

import json
from pathlib import Path

from clawdibrate.history import (
    estimate_iterations_to_target,
    is_converged,
    load_baselines,
    load_reflections,
    save_baseline,
    save_reflection,
    save_score,
)


class TestReflections:
    def test_load_empty(self, tmp_path: Path) -> None:
        assert load_reflections(tmp_path) == []

    def test_save_and_load(self, tmp_path: Path) -> None:
        save_reflection(tmp_path, {"section": "Identity", "score": 0.8})
        result = load_reflections(tmp_path)
        assert len(result) == 1
        assert result[0]["section"] == "Identity"


class TestScores:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        save_score(tmp_path, {"avg": 0.75, "timestamp": "2026-04-01"})
        path = tmp_path / "scores.jsonl"
        assert path.exists()
        entry = json.loads(path.read_text().strip())
        assert entry["avg"] == 0.75


class TestBaselines:
    def test_load_empty(self, tmp_path: Path) -> None:
        assert load_baselines(tmp_path) == {}

    def test_save_and_load(self, tmp_path: Path) -> None:
        save_baseline(tmp_path, {"transcript": "a.jsonl", "token_efficiency": 0.8})
        result = load_baselines(tmp_path)
        assert "a.jsonl" in result
        assert result["a.jsonl"]["token_efficiency"] == 0.8


class TestEstimateIterations:
    def test_no_history(self, tmp_path: Path) -> None:
        result = estimate_iterations_to_target(tmp_path)
        assert result["iterations_remaining"] is None
        assert result["confidence"] == "low"

    def test_improving_trend(self, tmp_path: Path) -> None:
        tmp_path.mkdir(exist_ok=True)
        scores = [{"avg": 0.5 + i * 0.05} for i in range(6)]
        (tmp_path / "scores.jsonl").write_text(
            "\n".join(json.dumps(s) for s in scores)
        )
        result = estimate_iterations_to_target(tmp_path, target_score=0.9)
        assert result["iterations_remaining"] is not None
        assert result["iterations_remaining"] > 0
        assert result["slope_per_run"] > 0


class TestIsConverged:
    def test_not_enough_runs(self) -> None:
        reflections = [{"section_scores": {"Identity": 0.96}}]
        assert is_converged("Identity", reflections) is False

    def test_converged(self) -> None:
        reflections = [
            {"section_scores": {"Identity": 0.96}},
            {"section_scores": {"Identity": 0.97}},
            {"section_scores": {"Identity": 0.95}},
        ]
        assert is_converged("Identity", reflections) is True

    def test_not_converged(self) -> None:
        reflections = [
            {"section_scores": {"Identity": 0.96}},
            {"section_scores": {"Identity": 0.70}},
            {"section_scores": {"Identity": 0.95}},
        ]
        assert is_converged("Identity", reflections) is False
