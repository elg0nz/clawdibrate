"""Ensure pyproject.toml and AGENTS.md versions stay in sync."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _pyproject_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "version not found in pyproject.toml"
    return m.group(1)


def _agents_version() -> str:
    text = (REPO_ROOT / "AGENTS.md").read_text()
    m = re.search(r"\*\*Version:\s*([^\*]+)\*\*", text)
    assert m, "Version not found in AGENTS.md (expected '**Version: X.Y.Z**')"
    return m.group(1).strip()


def test_versions_in_sync():
    pyproject = _pyproject_version()
    agents = _agents_version()
    assert pyproject == agents, (
        f"Version mismatch: pyproject.toml={pyproject!r}, AGENTS.md={agents!r}\n"
        "Run: bump both files together when releasing."
    )
