"""Deterministic transcript metrics — Tier 1 scoring with no LLM calls."""

from __future__ import annotations

import difflib
import math
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def rouge_l_similarity(a: str, b: str) -> float:
    """Approximate Rouge-L similarity for short strings."""
    if not a or not b:
        return 0.0
    tokens_a, tokens_b = a.split(), b.split()
    if not tokens_a or not tokens_b:
        return 0.0
    la, lb = len(tokens_a), len(tokens_b)
    dp = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            if tokens_a[i - 1] == tokens_b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[la][lb]
    precision = lcs / la
    recall = lcs / lb
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compute_metrics(transcript: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute deterministic token-waste metrics from a structured transcript.

    Returns the five Tier-1 metrics:
      - token_efficiency: tokens_used / tokens_in_ideal_path (capped 0-1)
      - search_waste_ratio: fraction of searches with no following action
      - correction_rate: user_corrections / user_messages
      - repetition_score: repeated_tool_patterns / total_tool_calls
      - success_rate: 1.0 if task completed, else 0.0
    """
    search_tools = {"Glob", "Grep", "Read", "glob", "grep", "read"}
    action_tools = {"Edit", "Write", "Bash", "edit", "write", "bash"}
    correction_patterns = re.compile(
        r"\b(no,?\s+not\s+that|don'?t|stop\s+doing|use\s+\w+\s+instead|wrong)\b",
        re.IGNORECASE,
    )
    success_patterns = re.compile(
        r"\b(done|complete[d]?|finished|task\s+complete|all\s+done)\b",
        re.IGNORECASE,
    )

    search_calls = 0
    action_calls = 0
    total_calls = 0
    user_messages = 0
    user_corrections = 0
    tool_args_window: list[str] = []
    repeated_patterns = 0
    searches_since_last_action = 0
    task_succeeded = False

    for event in transcript:
        role = event.get("role", "")
        tool = event.get("tool", "")
        content = event.get("content", "")

        if tool:
            total_calls += 1
            if tool in search_tools:
                search_calls += 1
                searches_since_last_action += 1
            elif tool in action_tools:
                action_calls += 1
                searches_since_last_action = 0

            args_str = str(event.get("args", ""))
            tool_args_window.append(f"{tool}:{args_str}")
            if len(tool_args_window) > 5:
                tool_args_window.pop(0)
            if len(tool_args_window) == 5:
                last = tool_args_window[-1]
                for prior in tool_args_window[:-1]:
                    if rouge_l_similarity(last, prior) > 0.8:
                        repeated_patterns += 1
                        break

        if role == "user" and content:
            user_messages += 1
            user_corrections += bool(correction_patterns.search(str(content)))

        if role == "assistant" and content:
            if success_patterns.search(str(content)):
                task_succeeded = True

    wasted_search_calls = searches_since_last_action

    ideal_calls = max(action_calls * 2, 1)
    token_efficiency = min(ideal_calls / max(total_calls, 1), 1.0)

    search_waste_ratio = wasted_search_calls / max(search_calls, 1)
    search_waste_ratio = min(max(search_waste_ratio, 0.0), 1.0)

    correction_rate = user_corrections / max(user_messages, 1)
    correction_rate = min(max(correction_rate, 0.0), 1.0)

    repetition_score = repeated_patterns / max(total_calls, 1)

    success_rate = 1.0 if task_succeeded else 0.0

    return {
        "token_efficiency": round(token_efficiency, 3),
        "search_waste_ratio": round(search_waste_ratio, 3),
        "correction_rate": round(correction_rate, 3),
        "repetition_score": round(repetition_score, 3),
        "success_rate": success_rate,
        "total_tool_calls": total_calls,
        "search_calls": search_calls,
        "action_calls": action_calls,
        "user_messages": user_messages,
        "user_correction_count": user_corrections,
        "wasted_search_calls": wasted_search_calls,
    }


def split_transcripts(
    transcripts: list[Path],
    holdout_ratio: float = 0.2,
    seed: int = 42,
) -> tuple[list[Path], list[Path]]:
    """Split transcripts into train/test sets.

    For < 5 transcripts, uses leave-one-out (last transcript as test).
    Otherwise, shuffles deterministically and splits at holdout_ratio.
    """
    if len(transcripts) < 2:
        return transcripts, []
    if len(transcripts) < 5:
        return transcripts[:-1], transcripts[-1:]
    rng = random.Random(seed)
    shuffled = list(transcripts)
    rng.shuffle(shuffled)
    split_idx = max(1, len(shuffled) - int(len(shuffled) * holdout_ratio))
    return shuffled[:split_idx], shuffled[split_idx:]


def compute_edit_distance(old: str, new: str) -> int:
    """Compute line-level edit distance between old and new content."""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, n=0))
    return sum(
        1 for line in diff
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    )


def compute_recency_weight(
    transcript_path: Path,
    halflife_days: float = 30.0,
    floor: float = 0.3,
) -> float:
    """Exponential decay weight based on transcript file modification time."""
    try:
        mtime = transcript_path.stat().st_mtime
        age_days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400.0
    except OSError:
        age_days = 0.0
    if age_days <= 0 or halflife_days <= 0:
        return 1.0
    decay = math.exp(-math.log(2) * age_days / halflife_days)
    return max(floor, decay)


def compute_diversity(failures: list[dict[str, Any]]) -> dict[str, Any]:
    """Count distinct failure categories and transcripts."""
    categories = set()
    transcript_sources = set()
    for f in failures:
        cat = f.get("category") or f.get("failure_type") or f.get("failure", "unknown")
        categories.add(cat)
        src = f.get("transcript") or f.get("source_transcript") or "unknown"
        transcript_sources.add(src)
    overfit = len(categories) <= 1 and len(transcript_sources) <= 1
    return {
        "category_count": len(categories),
        "transcript_count": len(transcript_sources),
        "overfit_warning": overfit,
    }
