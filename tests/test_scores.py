"""Tests for clawdibrate.scores — sparkline and score display."""

from __future__ import annotations

import json
from pathlib import Path

from clawdibrate.scores import sparkline, show_scores


class TestSparkline:
    def test_empty_returns_empty(self) -> None:
        assert sparkline([]) == ""

    def test_single_value_uses_middle_char(self) -> None:
        result = sparkline([0.5])
        assert len(result) == 1

    def test_ascending_values(self) -> None:
        result = sparkline([0.0, 0.5, 1.0])
        assert len(result) == 3
        # first char should be lowest block, last should be highest
        assert result[0] == "▁"
        assert result[-1] == "█"

    def test_constant_values_all_same(self) -> None:
        result = sparkline([0.5, 0.5, 0.5])
        assert len(set(result)) == 1

    def test_two_values(self) -> None:
        result = sparkline([0.0, 1.0])
        assert result[0] == "▁"
        assert result[1] == "█"


class TestShowScores:
    def test_no_file_prints_message(self, tmp_path: Path, capsys) -> None:
        show_scores(tmp_path)
        assert "No scores found" in capsys.readouterr().out

    def test_empty_file_prints_message(self, tmp_path: Path, capsys) -> None:
        scores_dir = tmp_path / ".clawdibrate" / "history"
        scores_dir.mkdir(parents=True)
        (scores_dir / "scores.jsonl").write_text("")
        show_scores(tmp_path)
        assert "No scores found" in capsys.readouterr().out

    def test_valid_entries_prints_table(self, tmp_path: Path, capsys) -> None:
        scores_dir = tmp_path / ".clawdibrate" / "history"
        scores_dir.mkdir(parents=True)
        entries = [
            {"timestamp": "2026-04-01T00:00:00", "avg": 0.750, "token_delta": -200},
            {"timestamp": "2026-04-02T00:00:00", "avg": 0.800, "token_delta": 50},
        ]
        (scores_dir / "scores.jsonl").write_text(
            "\n".join(json.dumps(e) for e in entries)
        )
        show_scores(tmp_path)
        out = capsys.readouterr().out
        assert "0.750" in out
        assert "0.800" in out
        assert "Trend" in out

    def test_shows_at_most_10(self, tmp_path: Path, capsys) -> None:
        scores_dir = tmp_path / ".clawdibrate" / "history"
        scores_dir.mkdir(parents=True)
        entries = [
            {"timestamp": f"2026-04-{i+1:02d}T00:00:00", "avg": 0.5 + i * 0.01, "token_delta": 0}
            for i in range(15)
        ]
        (scores_dir / "scores.jsonl").write_text(
            "\n".join(json.dumps(e) for e in entries)
        )
        show_scores(tmp_path)
        out = capsys.readouterr().out
        # should show last 10, not all 15
        assert "2026-04-06" in out  # entry index 5 = 6th, first of last 10
        assert "2026-04-01" not in out  # entry index 0, should be trimmed
