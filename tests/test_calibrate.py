"""Tests for orchestrator.calibrate — the main calibration loop.

Strategy: mock all agent calls (run_agent, fan_out) and filesystem persistence
so we can test orchestration logic in isolation. Each test targets a specific
phase or decision branch of calibrate().
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_AGENTS_MD = """\
<!-- version: 0.1.0 -->
# AGENTS.md

## Identity
You are a coding assistant.

## Known Gotchas
- Don't use inline imports.
- Always check for None before indexing.

## Boundaries
Stay within the repo.
"""


def _make_transcript_event(
    role: str = "assistant",
    tool: str = "",
    content: str = "",
    args: str = "",
) -> dict[str, Any]:
    d: dict[str, Any] = {"role": role}
    if tool:
        d["tool"] = tool
    if content:
        d["content"] = content
    if args:
        d["args"] = args
    return d


def _make_transcript_lines() -> list[str]:
    """A minimal transcript with search, action, and user messages."""
    events = [
        _make_transcript_event(role="user", content="Fix the bug in foo.py"),
        _make_transcript_event(tool="Grep", args="foo.py"),
        _make_transcript_event(tool="Read", args="foo.py"),
        _make_transcript_event(tool="Edit", args="foo.py"),
        _make_transcript_event(role="assistant", content="Done, task complete."),
    ]
    return [json.dumps(e) for e in events]


@pytest.fixture()
def calibrate_env(tmp_path: Path) -> dict[str, Any]:
    """Set up a minimal repo structure for calibrate()."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Instruction file
    clawdibrate_dir = repo / ".clawdibrate"
    clawdibrate_dir.mkdir()
    instruction_file = repo / "AGENTS.md"
    instruction_file.write_text(SAMPLE_AGENTS_MD)

    # Transcripts
    transcripts_dir = clawdibrate_dir / "transcripts"
    transcripts_dir.mkdir()
    t1 = transcripts_dir / "session_001.jsonl"
    t1.write_text("\n".join(_make_transcript_lines()))
    t2 = transcripts_dir / "session_002.jsonl"
    t2.write_text("\n".join(_make_transcript_lines()))

    # History dir
    history_dir = clawdibrate_dir / "history"
    history_dir.mkdir()

    return {
        "repo": repo,
        "instruction_file": instruction_file,
        "transcripts_dir": transcripts_dir,
        "history_dir": history_dir,
        "clawdibrate_dir": clawdibrate_dir,
    }


def _patch_resolve_repo_root(env: dict[str, Any]):
    """Patch resolve_repo_root to return our tmp repo."""
    return patch(
        "clawdibrate.orchestrator.resolve_repo_root",
        return_value=env["repo"],
    )


def _patch_repo_paths(env: dict[str, Any]):
    """Patch repo_paths to return our tmp paths."""
    return patch(
        "clawdibrate.orchestrator.repo_paths",
        return_value={
            "instruction_file": env["instruction_file"],
            "transcripts_dir": env["transcripts_dir"],
            "history_dir": env["history_dir"],
        },
    )


def _patch_git_commands():
    """Patch subprocess.run to no-op git commands."""
    return patch("clawdibrate.orchestrator.subprocess.run")


def _bug_identifier_response(section: str = "Known Gotchas") -> str:
    """Fake bug-identifier agent JSON output."""
    return json.dumps([
        {
            "failure": "Agent used inline import in hot path",
            "responsible_section": section,
            "severity": "medium",
        }
    ])


def _judge_response(weight: float = 0.7) -> str:
    """Fake judge agent JSON output."""
    return json.dumps({
        "actionable": True,
        "weight": weight,
        "category": "style",
        "reasoning": "Inline imports violate the documented convention.",
    })


def _implementer_response(section: str = "Known Gotchas") -> str:
    """Fake implementer output — a rewritten section."""
    return (
        "- Don't use inline imports — move all imports to module top.\n"
        "- Always check for None before indexing.\n"
        "- Prefer explicit error messages over bare exceptions."
    )


# ---------------------------------------------------------------------------
# Tests: early exits
# ---------------------------------------------------------------------------


class TestCalibrateEarlyExits:
    """Tests for branches that exit before any agent calls."""

    def test_no_transcripts_returns_no_transcripts_reason(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """When transcript dir is empty, returns reason='no_transcripts'."""
        env = calibrate_env
        # Remove transcripts
        for f in env["transcripts_dir"].iterdir():
            f.unlink()

        from clawdibrate.orchestrator import calibrate

        with _patch_resolve_repo_root(env), _patch_repo_paths(env):
            result = calibrate(repo_root=env["repo"])

        assert result["reason"] == "no_transcripts"
        assert result["changed"] is False
        assert result["failures"] == 0

    def test_dry_run_never_calls_agents(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """dry_run=True computes metrics but never invokes run_agent."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            result = calibrate(repo_root=env["repo"], dry_run=True)

        mock_agent.assert_not_called()
        mock_fan_out.assert_not_called()
        assert result["reason"] == "dry_run"
        assert result["changed"] is False

    def test_single_transcript_path(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """When transcript_path is given, only that transcript is used."""
        env = calibrate_env
        t1 = env["transcripts_dir"] / "session_001.jsonl"

        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            mock_agent.return_value = _bug_identifier_response()
            result = calibrate(
                repo_root=env["repo"],
                transcript_path=t1,
                dry_run=True,
            )

        assert result["reason"] == "dry_run"


# ---------------------------------------------------------------------------
# Tests: stage 1 — bug identification
# ---------------------------------------------------------------------------


class TestStage1BugIdentification:
    """Tests for the bug identification stage."""

    def test_sequential_bug_identification(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """With workers=1, run_agent is called sequentially for each transcript."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            # Stage 1 returns failures, stage 2 returns verdict, stage 3 returns new content
            mock_agent.side_effect = [
                # Bug ID for each transcript (2 train transcripts after split)
                _bug_identifier_response(),
                _bug_identifier_response(),
                # Judge for each failure
                _judge_response(),
                _judge_response(),
                # Implementer for each section
                _implementer_response(),
            ]
            result = calibrate(repo_root=env["repo"], workers=1)

        assert mock_agent.call_count >= 1
        assert result["failures"] >= 1

    def test_parallel_bug_identification(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """With workers>1 and multiple transcripts, fan_out is used."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            # fan_out returns list of {id, result, error}
            mock_fan_out.side_effect = [
                # Stage 1: bug ID
                [
                    {"id": 0, "result": _bug_identifier_response(), "error": None},
                    {"id": 1, "result": _bug_identifier_response(), "error": None},
                ],
                # Stage 2: judge
                [
                    {"id": 0, "result": _judge_response(), "error": None},
                    {"id": 1, "result": _judge_response(), "error": None},
                ],
                # Stage 3: implementer
                [
                    {"id": 0, "result": _implementer_response(), "error": None},
                ],
            ]
            result = calibrate(repo_root=env["repo"], workers=4)

        assert mock_fan_out.call_count == 3
        assert result["failures"] >= 1

    def test_bug_identifier_error_is_skipped(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """If bug-identifier returns an error, that transcript is skipped."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            mock_agent.side_effect = [
                RuntimeError("agent timeout"),
                _bug_identifier_response(),
                _judge_response(),
                _implementer_response(),
            ]
            # workers=1 triggers sequential path
            # First call raises, second succeeds
            result = calibrate(repo_root=env["repo"], workers=1)

        # Should still have some failures from the second transcript
        assert isinstance(result, dict)

    def test_bug_identifier_non_list_is_skipped(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """If bug-identifier returns non-list JSON, that result is skipped."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            mock_agent.side_effect = [
                '{"not": "a list"}',  # Invalid format
                _bug_identifier_response(),
                _judge_response(),
                _implementer_response(),
            ]
            result = calibrate(repo_root=env["repo"], workers=1)

        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Tests: stage 2 — judge
# ---------------------------------------------------------------------------


class TestStage2Judge:
    """Tests for the judge stage."""

    def test_low_weight_skips_implementer(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Failures with avg weight < 0.3 are not sent to implementer."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            mock_fan_out.side_effect = [
                [
                    {"id": 0, "result": _bug_identifier_response(), "error": None},
                    {"id": 1, "result": _bug_identifier_response(), "error": None},
                ],
                [
                    {"id": 0, "result": _judge_response(weight=0.1), "error": None},
                    {"id": 1, "result": _judge_response(weight=0.1), "error": None},
                ],
                # Stage 3 should NOT be called (empty impl_tasks)
            ]
            result = calibrate(repo_root=env["repo"], workers=4)

        # fan_out called only twice (bug-id + judge), not three times
        assert mock_fan_out.call_count == 2
        assert result["changed"] is False

    def test_judge_error_skips_failure(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """If judge returns an error, that failure is dropped."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            mock_fan_out.side_effect = [
                [
                    {"id": 0, "result": _bug_identifier_response(), "error": None},
                    {"id": 1, "result": _bug_identifier_response(), "error": None},
                ],
                [
                    {"id": 0, "result": None, "error": "judge timed out"},
                    {"id": 1, "result": None, "error": "judge timed out"},
                ],
            ]
            result = calibrate(repo_root=env["repo"], workers=4)

        assert result["reason"] == "no_actionable_failures"
        assert result["failures"] == 0


# ---------------------------------------------------------------------------
# Tests: stage 3 — implementer
# ---------------------------------------------------------------------------


class TestStage3Implementer:
    """Tests for the implementer stage and content validation."""

    def test_empty_implementer_output_rejected(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Empty implementer output is rejected, section not updated."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            mock_fan_out.side_effect = [
                [{"id": 0, "result": _bug_identifier_response(), "error": None}],
                [{"id": 0, "result": _judge_response(weight=0.8), "error": None}],
                [{"id": 0, "result": "", "error": None}],  # Empty!
            ]
            result = calibrate(repo_root=env["repo"], workers=4)

        assert result["changed"] is False

    def test_prompt_leak_rejected(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Implementer output with prompt artifacts is rejected."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        leak_content = (
            "Here is the updated section:\n"
            "```markdown\n"
            "- Don't use inline imports.\n"
            "```\n"
            "I've updated the section as requested."
        )

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
            patch("clawdibrate.orchestrator.validate_no_prompt_leaks", return_value=["found leak pattern"]),
        ):
            mock_fan_out.side_effect = [
                [{"id": 0, "result": _bug_identifier_response(), "error": None}],
                [{"id": 0, "result": _judge_response(weight=0.8), "error": None}],
                [{"id": 0, "result": leak_content, "error": None}],
            ]
            result = calibrate(repo_root=env["repo"], workers=4)

        assert result["changed"] is False

    def test_successful_section_update(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Full happy path: bug-id → judge → implementer → section updated."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            mock_fan_out.side_effect = [
                [{"id": 0, "result": _bug_identifier_response(), "error": None}],
                [{"id": 0, "result": _judge_response(weight=0.8), "error": None}],
                [{"id": 0, "result": _implementer_response(), "error": None}],
            ]
            result = calibrate(repo_root=env["repo"], workers=4)

        assert result["changed"] is True
        assert result["failures"] >= 1
        # Verify the file was actually written
        updated = env["instruction_file"].read_text()
        assert "move all imports to module top" in updated

    def test_token_budget_rejects_large_edit(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """If edit would exceed --token-budget, it's rejected."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        # Giant implementer output
        huge_content = "- " + "word " * 500 + "\n"

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            mock_fan_out.side_effect = [
                [{"id": 0, "result": _bug_identifier_response(), "error": None}],
                [{"id": 0, "result": _judge_response(weight=0.8), "error": None}],
                [{"id": 0, "result": huge_content, "error": None}],
            ]
            result = calibrate(
                repo_root=env["repo"],
                workers=4,
                token_budget=50,  # Very low budget
            )

        # Should reject the edit due to token budget
        assert result["changed"] is False


# ---------------------------------------------------------------------------
# Tests: persistence and reporting
# ---------------------------------------------------------------------------


class TestPersistence:
    """Tests for reflection/score/instrumentation persistence."""

    def test_reflection_saved_after_calibration(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """A reflection entry is written to history after calibration."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            mock_fan_out.side_effect = [
                [{"id": 0, "result": _bug_identifier_response(), "error": None}],
                [{"id": 0, "result": _judge_response(weight=0.8), "error": None}],
                [{"id": 0, "result": _implementer_response(), "error": None}],
            ]
            calibrate(repo_root=env["repo"], workers=4)

        reflections_file = env["history_dir"] / "reflections.jsonl"
        assert reflections_file.exists()
        lines = reflections_file.read_text().strip().splitlines()
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert "failures" in entry
        assert "avg_score" in entry
        assert "tokens_before" in entry

    def test_instrumentation_saved(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Instrumentation entry is always saved, even on early exit."""
        env = calibrate_env
        # Remove transcripts to trigger early exit
        for f in env["transcripts_dir"].iterdir():
            f.unlink()

        from clawdibrate.orchestrator import calibrate

        with _patch_resolve_repo_root(env), _patch_repo_paths(env):
            calibrate(repo_root=env["repo"])

        instrumentation_file = env["history_dir"] / "instrumentation.jsonl"
        assert instrumentation_file.exists()
        entry = json.loads(instrumentation_file.read_text().strip().splitlines()[-1])
        assert entry["mode"] == "standard"
        assert "result" in entry

    def test_summary_contains_expected_keys(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """The returned summary dict has all expected keys."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            mock_fan_out.side_effect = [
                [{"id": 0, "result": _bug_identifier_response(), "error": None}],
                [{"id": 0, "result": _judge_response(weight=0.8), "error": None}],
                [{"id": 0, "result": _implementer_response(), "error": None}],
            ]
            result = calibrate(repo_root=env["repo"], workers=4)

        expected_keys = {
            "timestamp", "mode", "iteration", "reason", "changed",
            "failures", "avg_score", "section_scores", "optimized",
            "target_score", "estimate", "stage_times_ms", "elapsed_ms",
        }
        assert expected_keys.issubset(result.keys())


# ---------------------------------------------------------------------------
# Tests: convergence and overfit detection
# ---------------------------------------------------------------------------


class TestConvergenceAndOverfit:
    """Tests for convergence skipping and overfit revert."""

    def test_converged_section_skipped(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Sections that have converged are not sent to implementer."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        # Write fake reflections showing convergence
        reflections = [
            {"section": "Known Gotchas", "edit_distances": {"Known Gotchas": 0}, "timestamp": "2026-01-01T00:00:00Z"},
            {"section": "Known Gotchas", "edit_distances": {"Known Gotchas": 0}, "timestamp": "2026-01-02T00:00:00Z"},
            {"section": "Known Gotchas", "edit_distances": {"Known Gotchas": 0}, "timestamp": "2026-01-03T00:00:00Z"},
        ]
        reflections_file = env["history_dir"] / "reflections.jsonl"
        reflections_file.write_text("\n".join(json.dumps(r) for r in reflections))

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
            patch("clawdibrate.orchestrator.is_converged", return_value=True),
        ):
            mock_fan_out.side_effect = [
                [{"id": 0, "result": _bug_identifier_response(), "error": None}],
                [{"id": 0, "result": _judge_response(weight=0.8), "error": None}],
                # No stage 3 — section is converged
            ]
            result = calibrate(repo_root=env["repo"], workers=4)

        assert mock_fan_out.call_count == 2  # Only bug-id + judge


# ---------------------------------------------------------------------------
# Tests: compute_metrics (deterministic, no mocks needed)
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    """Tests for the deterministic metrics computation."""

    def test_empty_transcript(self) -> None:
        from clawdibrate.orchestrator import compute_metrics

        result = compute_metrics([])
        assert result["total_tool_calls"] == 0
        assert result["token_efficiency"] == 0.0
        assert result["success_rate"] == 0.0

    def test_successful_transcript(self) -> None:
        from clawdibrate.orchestrator import compute_metrics

        events = [
            {"role": "user", "content": "Fix the bug"},
            {"role": "assistant", "tool": "Grep", "content": ""},
            {"role": "assistant", "tool": "Edit", "content": ""},
            {"role": "assistant", "content": "Done, task complete."},
        ]
        result = compute_metrics(events)
        assert result["success_rate"] == 1.0
        assert result["total_tool_calls"] == 2
        assert result["search_calls"] == 1
        assert result["action_calls"] == 1
        assert result["correction_rate"] == 0.0

    def test_correction_detected(self) -> None:
        from clawdibrate.orchestrator import compute_metrics

        events = [
            {"role": "user", "content": "Fix the bug"},
            {"role": "user", "content": "No, not that, use the other file"},
        ]
        result = compute_metrics(events)
        assert result["user_correction_count"] == 1
        assert result["correction_rate"] == 0.5

    def test_wasted_searches(self) -> None:
        from clawdibrate.orchestrator import compute_metrics

        events = [
            {"role": "assistant", "tool": "Grep", "content": ""},
            {"role": "assistant", "tool": "Read", "content": ""},
            {"role": "assistant", "tool": "Glob", "content": ""},
            # No action follows — all searches are wasted
        ]
        result = compute_metrics(events)
        assert result["wasted_search_calls"] == 3
        assert result["search_waste_ratio"] == 1.0

    def test_metrics_deterministic(self) -> None:
        """Same input always produces same output."""
        from clawdibrate.orchestrator import compute_metrics

        events = [
            {"role": "user", "content": "Do something"},
            {"role": "assistant", "tool": "Read"},
            {"role": "assistant", "tool": "Edit"},
            {"role": "assistant", "content": "All done"},
        ]
        r1 = compute_metrics(events)
        r2 = compute_metrics(events)
        assert r1 == r2


# ---------------------------------------------------------------------------
# Tests: split_transcripts
# ---------------------------------------------------------------------------


class TestSplitTranscripts:
    """Tests for the hold-out split logic."""

    def test_single_transcript_no_split(self, tmp_path: Path) -> None:
        from clawdibrate.orchestrator import split_transcripts

        t = [tmp_path / "a.jsonl"]
        train, test = split_transcripts(t)
        assert len(train) == 1
        assert len(test) == 0

    def test_small_set_leave_one_out(self, tmp_path: Path) -> None:
        from clawdibrate.orchestrator import split_transcripts

        ts = [tmp_path / f"{i}.jsonl" for i in range(3)]
        train, test = split_transcripts(ts)
        assert len(test) == 1
        assert len(train) == 2

    def test_large_set_ratio_split(self, tmp_path: Path) -> None:
        from clawdibrate.orchestrator import split_transcripts

        ts = [tmp_path / f"{i}.jsonl" for i in range(10)]
        train, test = split_transcripts(ts, holdout_ratio=0.2)
        assert len(test) == 2
        assert len(train) == 8

    def test_split_is_deterministic(self, tmp_path: Path) -> None:
        from clawdibrate.orchestrator import split_transcripts

        ts = [tmp_path / f"{i}.jsonl" for i in range(10)]
        train1, test1 = split_transcripts(ts)
        train2, test2 = split_transcripts(ts)
        assert train1 == train2
        assert test1 == test2


# ---------------------------------------------------------------------------
# Tests: extract_section / replace_section
# ---------------------------------------------------------------------------


class TestSectionOps:
    """Tests for section extraction and replacement."""

    def test_extract_existing_section(self) -> None:
        from clawdibrate.orchestrator import extract_section

        content = extract_section(SAMPLE_AGENTS_MD, "Known Gotchas")
        assert "inline imports" in content
        assert "None before indexing" in content

    def test_extract_missing_section(self) -> None:
        from clawdibrate.orchestrator import extract_section

        content = extract_section(SAMPLE_AGENTS_MD, "Nonexistent Section")
        assert content == ""

    def test_replace_section(self) -> None:
        from clawdibrate.orchestrator import replace_section

        new = replace_section(SAMPLE_AGENTS_MD, "Known Gotchas", "- New bullet.\n")
        assert "- New bullet." in new
        assert "inline imports" not in new
        # Other sections untouched
        assert "Stay within the repo." in new

    def test_replace_preserves_other_sections(self) -> None:
        from clawdibrate.orchestrator import replace_section

        new = replace_section(SAMPLE_AGENTS_MD, "Identity", "Updated identity.\n")
        assert "Updated identity." in new
        assert "Known Gotchas" in new
        assert "Boundaries" in new
