"""Logging helpers with immediate flush for real-time visibility."""

import sys
from datetime import datetime

DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"

# Force line-buffered stdout so output appears immediately
sys.stdout.reconfigure(line_buffering=True)


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log_phase(phase: str):
    print(f"\n{BOLD}{CYAN}[{_ts()}] ▶ {phase}{RESET}")


def log_step(msg: str):
    print(f"  {DIM}[{_ts()}]{RESET} {msg}")


def log_result(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")


def log_warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def log_error(msg: str):
    print(f"  {RED}✗{RESET} {msg}")
