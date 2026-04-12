"""Tests for clawdibrate.modes — mode defaults and transcript listing."""

from __future__ import annotations

import argparse
from pathlib import Path

from clawdibrate.modes import resolve_mode_defaults, list_transcripts


def _make_args(**overrides) -> argparse.Namespace:
    defaults = {
        "mode": "progressive",
        "max_transcripts": None,
        "workers": 4,
        "no_auto_section_skills": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestResolveModeDefaults:
    def test_fast_caps_transcripts(self) -> None:
        args = _make_args(mode="fast")
        resolve_mode_defaults(args)
        assert args.max_transcripts == 8

    def test_fast_disables_auto_skills(self) -> None:
        args = _make_args(mode="fast")
        resolve_mode_defaults(args)
        assert args.no_auto_section_skills is True

    def test_progressive_sets_workers_to_1(self) -> None:
        args = _make_args(mode="progressive")
        resolve_mode_defaults(args)
        assert args.workers == 1

    def test_max_keeps_workers_at_least_2(self) -> None:
        args = _make_args(mode="max")
        resolve_mode_defaults(args)
        assert args.workers >= 2

    def test_explicit_workers_not_overridden(self) -> None:
        args = _make_args(mode="fast", workers=8)
        resolve_mode_defaults(args)
        assert args.workers == 8

    def test_explicit_max_transcripts_not_overridden(self) -> None:
        args = _make_args(mode="fast", max_transcripts=3)
        resolve_mode_defaults(args)
        assert args.max_transcripts == 3


class TestListTranscripts:
    def test_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        assert list_transcripts(tmp_path) == []

    def test_returns_jsonl_files_newest_first(self, tmp_path: Path) -> None:
        t_dir = tmp_path / ".clawdibrate" / "transcripts"
        t_dir.mkdir(parents=True)
        # create two files with different mtimes
        (t_dir / "old.jsonl").write_text("{}")
        (t_dir / "new.jsonl").write_text("{}")
        import os, time
        old_time = time.time() - 100
        os.utime(t_dir / "old.jsonl", (old_time, old_time))

        result = list_transcripts(tmp_path)
        assert len(result) == 2
        assert result[0].name == "new.jsonl"

    def test_ignores_non_jsonl(self, tmp_path: Path) -> None:
        t_dir = tmp_path / ".clawdibrate" / "transcripts"
        t_dir.mkdir(parents=True)
        (t_dir / "notes.txt").write_text("not a transcript")
        (t_dir / "real.jsonl").write_text("{}")
        result = list_transcripts(tmp_path)
        assert len(result) == 1
        assert result[0].name == "real.jsonl"
