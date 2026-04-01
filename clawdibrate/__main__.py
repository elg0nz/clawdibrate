"""Entry point: python -m clawdibrate"""

import argparse
import os
from pathlib import Path

from .agents import AGENTS, resolve_agent
from .log import BOLD, DIM, RESET, log_step
from .loop import DEFAULT_ITERATIONS, run_loop
from .runner import validate_agent
from .scores import show_history


def main():
    parser = argparse.ArgumentParser(description="Clawdibrate self-improvement tuning loop")
    subparsers = parser.add_subparsers(dest="command")

    # Legacy loop command (default when no subcommand given)
    parser.add_argument("--agent", default=None, choices=["auto", *AGENTS.keys()],
                        help="Agent CLI to use (default: auto-detect current agent)")
    parser.add_argument("--eval-only", action="store_true",
                        help="Single evaluation pass, no tuning")
    parser.add_argument("--iterations", "-n", type=int, default=DEFAULT_ITERATIONS,
                        help=f"Number of iterations (default: {DEFAULT_ITERATIONS})")
    parser.add_argument("--history", action="store_true",
                        help="Show score history across versions")

    # New transcript-based calibration command
    cal_parser = subparsers.add_parser("calibrate", help="Transcript-based AGENTS.md calibration")
    cal_parser.add_argument("--agent", default=None)
    cal_parser.add_argument("--transcript", type=Path, default=None,
                            help="Path to a specific .jsonl transcript file")
    cal_parser.add_argument("--dry-run", action="store_true",
                            help="Show plan without making changes")

    args = parser.parse_args()

    if args.command == "calibrate":
        from .orchestrator import calibrate
        agent_name = args.agent or os.environ.get("CLAWDIBRATE_AGENT_CMD", "claude")
        calibrate(agent=agent_name, transcript_path=args.transcript, dry_run=args.dry_run)
        return

    print(f"\n{BOLD}clawdibrate{RESET}")
    print(f"{DIM}{'\u2500' * 40}{RESET}")

    if os.environ.get("CLAWDIBRATE_AGENT_CMD"):
        log_step(f"CLAWDIBRATE_AGENT_CMD: {os.environ['CLAWDIBRATE_AGENT_CMD']}")

    agent, source = resolve_agent(args.agent)
    log_step(f"Agent: {BOLD}{agent}{RESET} ({source})")

    if args.history:
        show_history()
        return

    validate_agent(agent)
    run_loop(agent=agent, eval_only=args.eval_only, iterations=args.iterations)


if __name__ == "__main__":
    main()
