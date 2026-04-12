"""Tests for clawdibrate.cli — argument parsing."""

from __future__ import annotations

from clawdibrate.cli import build_parser


class TestBuildParser:
    def test_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args([])
        assert args.mode == "progressive"
        assert args.workers == 4
        assert args.target_score == 0.9
        assert args.dry_run is False
        assert args.agent is None

    def test_fast_mode(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--mode", "fast"])
        assert args.mode == "fast"

    def test_max_mode_with_target(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--mode", "max", "--target-score", "0.85"])
        assert args.mode == "max"
        assert args.target_score == 0.85

    def test_dump_session_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--dump-session"])
        assert args.dump_session is True

    def test_setup_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--setup"])
        assert args.setup is True

    def test_check_idempotent_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--check-idempotent"])
        assert args.check_idempotent is True
