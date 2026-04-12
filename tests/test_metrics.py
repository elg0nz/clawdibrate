"""Tests for clawdibrate.metrics — deterministic transcript metrics."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from clawdibrate.metrics import (
    compute_diversity,
    compute_edit_distance,
    compute_metrics,
    compute_recency_weight,
    rouge_l_similarity,
    split_transcripts,
)


def _event(role: str = "assistant", tool: str = "", content: str = "", args: str = "") -> dict[str, Any]:
    d: dict[str, Any] = {"role": role}
    if tool:
        d["tool"] = tool
    if content:
        d["content"] = content
    if args:
        d["args"] = args
    return d


class TestComputeMetrics:
    def test_empty_transcript(self) -> None:
        result = compute_metrics([])
        assert result["token_efficiency"] == 1.0
        assert result["correction_rate"] == 0.0

    def test_search_then_action(self) -> None:
        transcript = [
            _event(tool="Grep", args="foo"),
            _event(tool="Edit", args="foo.py"),
        ]
        result = compute_metrics(transcript)
        assert result["search_waste_ratio"] == 0.0
        assert result["total_tool_calls"] == 2

    def test_user_correction_detected(self) -> None:
        transcript = [
            _event(role="user", content="Fix the bug"),
            _event(role="user", content="no, not that file"),
        ]
        result = compute_metrics(transcript)
        assert result["user_correction_count"] == 1
        assert result["correction_rate"] > 0

    def test_success_detected(self) -> None:
        transcript = [
            _event(tool="Edit", args="foo.py"),
            _event(role="assistant", content="Done, task complete."),
        ]
        result = compute_metrics(transcript)
        assert result["success_rate"] == 1.0

    def test_wasted_searches(self) -> None:
        transcript = [
            _event(tool="Grep", args="a"),
            _event(tool="Grep", args="b"),
            _event(tool="Grep", args="c"),
        ]
        result = compute_metrics(transcript)
        assert result["wasted_search_calls"] == 3


class TestRougeLSimilarity:
    def test_identical(self) -> None:
        assert rouge_l_similarity("hello world", "hello world") == 1.0

    def test_empty(self) -> None:
        assert rouge_l_similarity("", "hello") == 0.0

    def test_partial_overlap(self) -> None:
        score = rouge_l_similarity("a b c d", "a x c y")
        assert 0.0 < score < 1.0


class TestSplitTranscripts:
    def test_single_transcript(self, tmp_path: Path) -> None:
        t = tmp_path / "a.jsonl"
        t.touch()
        train, test = split_transcripts([t])
        assert train == [t]
        assert test == []

    def test_few_transcripts_leave_one_out(self, tmp_path: Path) -> None:
        paths = [tmp_path / f"{i}.jsonl" for i in range(3)]
        for p in paths:
            p.touch()
        train, test = split_transcripts(paths)
        assert len(test) == 1
        assert test[0] == paths[-1]

    def test_many_transcripts_split(self, tmp_path: Path) -> None:
        paths = [tmp_path / f"{i}.jsonl" for i in range(10)]
        for p in paths:
            p.touch()
        train, test = split_transcripts(paths, holdout_ratio=0.2)
        assert len(train) + len(test) == 10
        assert len(test) >= 1


class TestComputeEditDistance:
    def test_identical(self) -> None:
        assert compute_edit_distance("a\nb\n", "a\nb\n") == 0

    def test_one_line_change(self) -> None:
        assert compute_edit_distance("a\nb\n", "a\nc\n") == 2  # -b, +c


class TestComputeRecencyWeight:
    def test_fresh_file(self, tmp_path: Path) -> None:
        p = tmp_path / "t.jsonl"
        p.touch()
        w = compute_recency_weight(p)
        assert w >= 0.99

    def test_missing_file(self, tmp_path: Path) -> None:
        p = tmp_path / "missing.jsonl"
        w = compute_recency_weight(p)
        assert w == 1.0


class TestComputeDiversity:
    def test_single_failure(self) -> None:
        result = compute_diversity([{"category": "wrong_tool", "transcript": "a.jsonl"}])
        assert result["category_count"] == 1
        assert result["overfit_warning"] is True

    def test_diverse_failures(self) -> None:
        failures = [
            {"category": "wrong_tool", "transcript": "a.jsonl"},
            {"category": "boundary_violation", "transcript": "b.jsonl"},
        ]
        result = compute_diversity(failures)
        assert result["category_count"] == 2
        assert result["overfit_warning"] is False
