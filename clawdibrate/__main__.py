"""Entry point for transcript-based AGENTS.md calibration."""

import argparse
import os
from pathlib import Path

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
        "--dry-run",
        action="store_true",
        help="Show what would run without mutating AGENTS.md",
    )

    args = parser.parse_args()
    agent_name = args.agent or os.environ.get("CLAWDIBRATE_AGENT", "claude")
    calibrate(agent=agent_name, transcript_path=args.transcript, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
