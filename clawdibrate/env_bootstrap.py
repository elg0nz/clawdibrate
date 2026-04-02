"""Load local KEY=value pairs into os.environ before CLI logic runs.

``.clawdibrate/`` is often gitignored; a file ``.clawdibrate/env`` lets
``CLAWDIBRATE_AGENT=cursor`` (and related vars) apply in IDE tasks and other
non-login shells that do not source shell profiles.
"""

from __future__ import annotations

import os
from pathlib import Path


def _parse_env_lines(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out


def _apply_parsed_env(parsed: dict[str, str], *, prefix_filter: str | None) -> None:
    for key, value in parsed.items():
        if prefix_filter is not None and not key.startswith(prefix_filter):
            continue
        if key not in os.environ:
            os.environ[key] = value


def load_clawdibrate_env(repo_root: Path) -> None:
    """Merge env files into ``os.environ`` without overriding existing keys.

    1. If ``repo_root/.clawdibrate/env`` exists, load all ``KEY=value`` pairs.
    2. Else if ``repo_root/.env`` exists, load only keys starting with
       ``CLAWDIBRATE_`` (avoids pulling unrelated app secrets into the process).

    For a dedicated file, prefer ``.clawdibrate/env`` (see ``clawdibrate.env.example``).
    """
    claw_env = repo_root / ".clawdibrate" / "env"
    if claw_env.is_file():
        try:
            text = claw_env.read_text(encoding="utf-8")
        except OSError:
            return
        _apply_parsed_env(_parse_env_lines(text), prefix_filter=None)
        return

    dot_env = repo_root / ".env"
    if dot_env.is_file():
        try:
            text = dot_env.read_text(encoding="utf-8")
        except OSError:
            return
        _apply_parsed_env(_parse_env_lines(text), prefix_filter="CLAWDIBRATE_")
