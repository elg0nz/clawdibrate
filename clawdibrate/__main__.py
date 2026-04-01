"""Entry point for transcript-based AGENTS.md calibration."""

import argparse
import os
from pathlib import Path

from .git_history import DEFAULT_HISTORY_FILES, synthesize_transcript_from_git
from .orchestrator import calibrate


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
        help="CLI agent to use (default: CLAWDIBRATE_AGENT_CMD or claude)",
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
        help="Target repository root containing AGENTS.md",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without mutating AGENTS.md",
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
        default=list(DEFAULT_HISTORY_FILES),
        help="Tracked prompt files to mine from git history",
    )

    args = parser.parse_args()
    agent_name = args.agent or os.environ.get("CLAWDIBRATE_AGENT", "claude")
    if args.synthesize_git_history:
        repo_root = (args.repo or Path.cwd()).resolve()
        output = synthesize_transcript_from_git(
            repo_root=repo_root,
            files=tuple(args.git_files),
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
    )


if __name__ == "__main__":
    main()
