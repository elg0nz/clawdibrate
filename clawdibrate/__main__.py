"""Entry point for transcript-based AGENTS.md calibration."""

import argparse
import os
from pathlib import Path

from .git_history import synthesize_transcript_from_git
from .instruction_files import (
    ensure_clawdibrate_setup,
)
from .compress import run_compress_advisor
from .orchestrator import calibrate, resolve_default_calibration_agent
from .session_dump import dump_session


def main():
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
        help="CLI agent to use (default: claude; override with CLAWDIBRATE_AGENT or --agent)",
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
        help="Max token count for instruction file (default: None = current file size)",
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

    args = parser.parse_args()
    agent_name = args.agent or resolve_default_calibration_agent()
    if args.setup:
        repo_root = (args.repo or Path.cwd()).resolve()
        result = ensure_clawdibrate_setup(repo_root)
        print(f"Active instruction file: {result['active_path']}")
        if result["created_pointer"]:
            print(f"Created pointer file: {result['created_pointer']}")
        if result.get("skills_installed"):
            print("Skills installed: record-start, record-stop, record-from-git, loop")
        if result.get("permissions_configured"):
            print("Permissions configured: .claude/settings.json")
        return

    if args.dump_session:
        repo_root = (args.repo or Path.cwd()).resolve()
        output = dump_session(
            repo_root=repo_root,
            session_id=args.session_id,
            output_path=args.transcript,
            agent=agent_name,
        )
        print(output)
        return

    if args.compress:
        from .instruction_files import detect_instruction_file
        repo_root = (args.repo or Path.cwd()).resolve()
        instruction_path = detect_instruction_file(repo_root)
        run_compress_advisor(instruction_path)
        return

    if args.synthesize_git_history:
        repo_root = (args.repo or Path.cwd()).resolve()
        output = synthesize_transcript_from_git(
            repo_root=repo_root,
            files=tuple(args.git_files) if args.git_files else None,
            limit=args.git_limit,
            output_path=args.transcript,
        )
        print(output)
        return

    calibrate(
        agent=agent_name,
        transcript_path=args.transcript,
        repo_root=args.repo,
        dry_run=args.dry_run,
        holdout_ratio=args.holdout_ratio,
        staleness_halflife_days=args.staleness_halflife_days,
        max_transcripts=args.max_transcripts,
        token_budget=args.token_budget,
        workers=args.workers,
        model=args.model,
    )


if __name__ == "__main__":
    main()
