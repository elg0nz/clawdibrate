"""Token counting utilities using tiktoken (cl100k_base)."""

from __future__ import annotations

import re
from pathlib import Path

import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in a string using cl100k_base encoding."""
    return len(_enc.encode(text))


def count_section_tokens(content: str) -> dict[str, int]:
    """Parse ## sections and count tokens in each.

    Returns a dict mapping section name to token count.
    A leading block before the first ## heading is keyed as "_preamble".
    """
    parts = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    result: dict[str, int] = {}
    for part in parts:
        if not part.strip():
            continue
        match = re.match(r"^## (.+)", part)
        if match:
            name = match.group(1).strip()
        else:
            name = "_preamble"
        result[name] = count_tokens(part)
    return result


def count_file_tokens(path: Path) -> dict:
    """Count tokens for a file: total + per-section breakdown.

    Returns {"total": int, "sections": dict[str, int]}.
    """
    content = path.read_text()
    return {
        "total": count_tokens(content),
        "sections": count_section_tokens(content),
    }
