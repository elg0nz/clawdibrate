"""Argument parser for the clawdibrate CLI."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build and return the clawdibrate argument parser."""
    parser = argparse.ArgumentParser(
        description="Clawdibrate transcript-based AGENTS.md calibration"
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["calibrate"],
        help="Optional alias for the default calibration command",
    )
    parser.add_argument(
        "--agent",
        default=None,
        help="CLI agent to use (default: claude; repo .clawdibrate/env or CLAWDIBRATE_AGENT or --agent)",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=None,
        help="Path to a specific .jsonl transcript file",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Target repository root containing AGENTS.md or CLAUDE.md",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without mutating AGENTS.md",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Configure the target repo to use clawdibrate and create a pointer file when needed",
    )
    parser.add_argument(
        "--synthesize-git-history",
        action="store_true",
        help="Create a bootstrap transcript from recent git history instead of calibrating",
    )
    parser.add_argument(
        "--git-limit",
        type=int,
        default=20,
        help="Number of recent relevant commits to include when synthesizing from git",
    )
    parser.add_argument(
        "--git-files",
        nargs="+",
        default=None,
        help="Tracked instruction files to mine from git history",
    )
    parser.add_argument(
        "--holdout-ratio",
        type=float,
        default=0.2,
        help="Fraction of transcripts to hold out for overfitting detection (default: 0.2)",
    )
    parser.add_argument(
        "--staleness-halflife-days",
        type=float,
        default=30.0,
        help="Half-life in days for transcript recency decay (default: 30)",
    )
    parser.add_argument(
        "--max-transcripts",
        type=int,
        default=None,
        help="Maximum number of transcripts to process per calibration run (default: all)",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        help="Optional hard cap on total file tokens; default none (no rejections; compression if file grows past pre-run size)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4, 1 = sequential)",
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        help="Model for parallel workers (default: sonnet)",
    )
    parser.add_argument(
        "--dump-session",
        action="store_true",
        help="Convert the most recent Claude Code session into a clawdibrate transcript",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Specific Claude Code session UUID to dump (default: most recent)",
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Run compression advisor on the instruction file and print suggestions",
    )
    parser.add_argument(
        "--no-auto-section-skills",
        action="store_true",
        help="Do not create src/skills/*, replace sections with pointers, or run npx skills add",
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "progressive", "max"],
        default="progressive",
        help=(
            "Calibration mode (default: progressive). "
            "fast: single pass over a small transcript batch — use for quick spot-checks or CI gates. "
            "progressive: cancel-safe mini-iterations — the everyday default, safe to Ctrl-C at any point. "
            "max: iterate until target score or plateau — use for deep optimization sessions."
        ),
    )
    parser.add_argument(
        "--target-score",
        type=float,
        default=0.9,
        help="Optimization target score for progressive/max mode estimates (default: 0.9)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum iterations for progressive/max mode",
    )
    parser.add_argument(
        "--progressive-batch-size",
        type=int,
        default=1,
        help="How many transcripts to process per progressive iteration (default: 1)",
    )
    parser.add_argument(
        "--scores",
        action="store_true",
        help="Print score history with ASCII sparkline and exit",
    )
    parser.add_argument(
        "--check-idempotent",
        action="store_true",
        help="Run calibrate twice on the same transcript and verify the second pass makes no changes (requires --transcript)",
    )
    return parser
