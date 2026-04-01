"""Entry point: python -m clawdibrate"""

import argparse
import os

from .agents import AGENTS, resolve_agent
from .log import BOLD, DIM, RESET, log_step
from .loop import DEFAULT_ITERATIONS, run_loop
from .runner import validate_agent
from .scores import show_history


def main():
    parser = argparse.ArgumentParser(description="Clawdibrate self-improvement tuning loop")
    parser.add_argument("--agent", default=None, choices=["auto", *AGENTS.keys()],
                        help="Agent CLI to use (default: auto-detect current agent)")
    parser.add_argument("--eval-only", action="store_true",
                        help="Single evaluation pass, no tuning")
    parser.add_argument("--iterations", "-n", type=int, default=DEFAULT_ITERATIONS,
                        help=f"Number of iterations (default: {DEFAULT_ITERATIONS})")
    parser.add_argument("--history", action="store_true",
                        help="Show score history across versions")
    args = parser.parse_args()

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
