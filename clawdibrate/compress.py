"""Token compression advisor — find and fix bloat in instruction files."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from .tokens import count_tokens, count_section_tokens

# Common bloat patterns: (regex, replacement_hint)
PATTERNS: list[dict[str, str]] = [
    {"pattern": r"\bIn order to\b", "replacement": "To", "label": "verbose preamble"},
    {"pattern": r"\bIt is important to note that\b", "replacement": "", "label": "filler phrase"},
    {"pattern": r"\bPlease make sure to\b", "replacement": "", "label": "filler phrase"},
    {"pattern": r"\bAs a general rule of thumb\b", "replacement": "Generally", "label": "verbose preamble"},
    {"pattern": r"\bDue to the fact that\b", "replacement": "Because", "label": "verbose preamble"},
    {"pattern": r"\bIn the event that\b", "replacement": "If", "label": "verbose preamble"},
    {"pattern": r"\bAt this point in time\b", "replacement": "Now", "label": "verbose preamble"},
    {"pattern": r"\bIt should be noted that\b", "replacement": "", "label": "filler phrase"},
    {"pattern": r"\bFor the purpose of\b", "replacement": "To", "label": "verbose preamble"},
    {"pattern": r"\bIn terms of\b", "replacement": "Regarding", "label": "verbose preamble"},
    {"pattern": r"\bOn a regular basis\b", "replacement": "Regularly", "label": "verbose construction"},
    {"pattern": r"\bPrior to\b", "replacement": "Before", "label": "verbose preamble"},
    {"pattern": r"\bSubsequent to\b", "replacement": "After", "label": "verbose preamble"},
    {"pattern": r"\bWith regard to\b", "replacement": "About", "label": "verbose preamble"},
    {"pattern": r"\bA large number of\b", "replacement": "Many", "label": "verbose construction"},
]


def find_compressions(content: str) -> list[dict[str, str | int]]:
    """Scan text for bloat patterns, return suggestions with token savings."""
    suggestions: list[dict[str, str | int]] = []
    for pat in PATTERNS:
        for match in re.finditer(pat["pattern"], content, re.IGNORECASE):
            before = match.group(0)
            after = pat["replacement"]
            tokens_before = count_tokens(before)
            tokens_after = count_tokens(after) if after else 0
            savings = tokens_before - tokens_after
            if savings > 0:
                suggestions.append({
                    "label": pat["label"],
                    "before": before,
                    "after": after,
                    "tokens_saved": savings,
                    "position": match.start(),
                })
    return suggestions


def compress_section(
    content: str, agent: str = "claude", model: str = "haiku"
) -> tuple[str, int]:
    """Use agent to compress a section, return (compressed_text, tokens_saved).

    Uses clawdibrate.ralph.run_worker() for the agent call.
    """
    from .ralph import run_worker

    tokens_before = count_tokens(content)

    prompt = (
        "Compress this instruction section without losing any capability. "
        "Remove redundancy, prefer commands over prose, cut filler. "
        "Return ONLY the compressed text, no explanations.\n\n"
        f"```\n{content}\n```"
    )

    # Write a minimal system prompt to a temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, prefix="clawdibrate-compress-"
    ) as f:
        f.write(
            "You are a concise technical editor. Compress instruction text "
            "without losing actionable content. Output ONLY the compressed text."
        )
        system_prompt_path = Path(f.name)

    try:
        compressed = run_worker(
            prompt=prompt,
            system_prompt_path=system_prompt_path,
            model=model,
            agent=agent,
        )
    finally:
        system_prompt_path.unlink(missing_ok=True)

    tokens_after = count_tokens(compressed)
    tokens_saved = tokens_before - tokens_after

    # Only accept if we actually saved tokens
    if tokens_saved <= 0:
        return content, 0

    return compressed, tokens_saved


def run_compress_advisor(instruction_path: Path) -> None:
    """Print per-section compression suggestions for an instruction file."""
    content = instruction_path.read_text()
    sections = count_section_tokens(content)

    print(f"Compression advisor for: {instruction_path.name}")
    print(f"Total tokens: {count_tokens(content):,}\n")

    # Split into sections and scan each
    parts = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    total_savings = 0

    for part in parts:
        if not part.strip():
            continue
        match = re.match(r"^## (.+)", part)
        name = match.group(1).strip() if match else "_preamble"
        section_tokens = sections.get(name, 0)

        suggestions = find_compressions(part)
        if not suggestions:
            continue

        section_savings = sum(int(s["tokens_saved"]) for s in suggestions)
        total_savings += section_savings

        print(f"## {name} ({section_tokens:,} tokens, -{section_savings} potential)")
        for s in suggestions:
            before = s["before"]
            after = s["after"] if s["after"] else "(remove)"
            print(f"  - {s['label']}: \"{before}\" -> \"{after}\" (-{s['tokens_saved']} tokens)")
        print()

    if total_savings:
        print(f"Total potential savings: {total_savings} tokens")
    else:
        print("No pattern-based compressions found.")
