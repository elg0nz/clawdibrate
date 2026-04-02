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
    """Set up a minimal repo structure for calibrate().

    Creates 6 transcripts so split_transcripts (leave-one-out for <5,
    ratio-based for >=5) gives us enough train transcripts for parallel tests.
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Instruction file
    clawdibrate_dir = repo / ".clawdibrate"
    clawdibrate_dir.mkdir()
    instruction_file = repo / "AGENTS.md"
    instruction_file.write_text(SAMPLE_AGENTS_MD)

    # Transcripts — 6 files so holdout split gives ~5 train, 1 test
    transcripts_dir = clawdibrate_dir / "transcripts"
    transcripts_dir.mkdir()
    for i in range(6):
        t = transcripts_dir / f"session_{i:03d}.jsonl"
        t.write_text("\n".join(_make_transcript_lines()))

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


def _patch_resolve_repo_root(env: dict[str, Any]) -> Any:
    """Patch resolve_repo_root to return our tmp repo."""
    return patch(
        "clawdibrate.orchestrator.resolve_repo_root",
        return_value=env["repo"],
    )


def _patch_repo_paths(env: dict[str, Any]) -> Any:
    """Patch repo_paths to return our tmp paths."""
    return patch(
        "clawdibrate.orchestrator.repo_paths",
        return_value={
            "instruction_file": env["instruction_file"],
            "transcripts_dir": env["transcripts_dir"],
            "history_dir": env["history_dir"],
        },
    )


def _patch_git_commands() -> Any:
    """Patch subprocess.run to no-op git commands (persist phase).

    We patch subprocess.run so that git add/commit in the persist phase
    don't fail. run_agent also uses subprocess.run but is patched separately.
    """
    return patch("clawdibrate.orchestrator.subprocess.run")


def _patch_compression() -> Any:
    """Patch compress_section to no-op (avoid real agent calls in compression phase).

    compress_section is lazily imported inside calibrate, so we patch the source module.
    """
    return patch(
        "clawdibrate.compress.compress_section",
        side_effect=lambda content, **_kw: (content, 0),
    )


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
# Tests: transcript discovery
# ---------------------------------------------------------------------------


class TestTranscriptDiscovery:
    """Tests for transcript discovery and the max_transcripts cap."""

    def test_max_transcripts_caps_input(
        self, calibrate_env: dict[str, Any], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When max_transcripts=2 and there are 6 transcripts, only the 2 most recent are used.

        The capping slices the last N alphabetically (transcripts are sorted by glob),
        so session_004.jsonl and session_005.jsonl should be the survivors.
        With 2 transcripts, split_transcripts leave-one-out gives 1 train, 1 test.
        """
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            result = calibrate(repo_root=env["repo"], dry_run=True, max_transcripts=2)

        # dry_run means no agents were called
        mock_agent.assert_not_called()
        mock_fan_out.assert_not_called()

        # dry_run exits with reason="dry_run"
        assert result["reason"] == "dry_run"

        # The capping message must appear in stdout
        captured = capsys.readouterr()
        assert "Capped to 2 most recent transcripts" in captured.out

        # Instrumentation file should record the capped transcript counts
        instrumentation_file = env["history_dir"] / "instrumentation.jsonl"
        assert instrumentation_file.exists()
        entry = json.loads(instrumentation_file.read_text().strip().splitlines()[-1])
        # After capping to 2, total should be 2
        assert entry["transcripts_total"] == 2
        # With 2 transcripts, leave-one-out split: 1 train, 1 test
        assert entry["train_transcripts"] == 1
        assert entry["test_transcripts"] == 1


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

        t1 = env["transcripts_dir"] / "session_000.jsonl"

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            _patch_compression(),
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            mock_agent.side_effect = [
                _bug_identifier_response(),
                _judge_response(),
                _implementer_response(),
            ]
            result = calibrate(
                repo_root=env["repo"], workers=1, transcript_path=t1,
            )

        assert mock_agent.call_count == 3
        assert result["failures"] >= 1

    def test_parallel_bug_identification(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """With workers>1 and multiple transcripts, fan_out is used for stages with >1 task."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        n_train = 5

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            _patch_compression(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            mock_fan_out.side_effect = [
                # Stage 1: 5 bug-id tasks → fan_out (>1 task)
                [
                    {"id": i, "result": _bug_identifier_response(), "error": None}
                    for i in range(n_train)
                ],
                # Stage 2: 5 judge tasks → fan_out (>1 task)
                [
                    {"id": i, "result": _judge_response(), "error": None}
                    for i in range(n_train)
                ],
                # Stage 3 has only 1 task (1 unique section) → sequential via run_agent
            ]
            mock_agent.return_value = _implementer_response()
            result = calibrate(repo_root=env["repo"], workers=4)

        # fan_out for stages 1 & 2 (both >1 task), stage 3 sequential (1 section)
        assert mock_fan_out.call_count == 2
        assert mock_agent.call_count == 1
        assert result["failures"] >= 1

    def test_bug_identifier_error_is_skipped(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """If bug-identifier returns an error via fan_out, that transcript is skipped."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            _patch_compression(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            mock_fan_out.side_effect = [
                # Stage 1: mix of errors and successes
                [
                    {"id": 0, "result": None, "error": "agent timeout"},
                    {"id": 1, "result": None, "error": "agent timeout"},
                    {"id": 2, "result": _bug_identifier_response(), "error": None},
                    {"id": 3, "result": _bug_identifier_response(), "error": None},
                    {"id": 4, "result": _bug_identifier_response(), "error": None},
                ],
                # Stage 2: judge the survivors
                [
                    {"id": 0, "result": _judge_response(), "error": None},
                    {"id": 1, "result": _judge_response(), "error": None},
                    {"id": 2, "result": _judge_response(), "error": None},
                ],
                # Stage 3 has only 1 task (1 unique section) → sequential via run_agent
            ]
            # Stage 3 falls through to sequential run_agent (1 unique section)
            mock_agent.return_value = _implementer_response()
            result = calibrate(repo_root=env["repo"], workers=4)

        assert isinstance(result, dict)
        assert result["failures"] >= 1

    def test_bug_identifier_non_list_is_skipped(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """If bug-identifier returns non-list JSON, that result is skipped."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        # Use single transcript to simplify
        t1 = env["transcripts_dir"] / "session_000.jsonl"

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            mock_agent.return_value = '{"not": "a list"}'
            result = calibrate(
                repo_root=env["repo"], workers=1, transcript_path=t1,
            )

        assert isinstance(result, dict)
        assert result["reason"] == "no_actionable_failures"


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

        n_train = 5

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            mock_fan_out.side_effect = [
                [
                    {"id": i, "result": _bug_identifier_response(), "error": None}
                    for i in range(n_train)
                ],
                [
                    {"id": i, "result": _judge_response(weight=0.1), "error": None}
                    for i in range(n_train)
                ],
                # Stage 3 should NOT be called (low weight → no eligible sections)
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

        n_train = 5

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
        ):
            mock_fan_out.side_effect = [
                [
                    {"id": i, "result": _bug_identifier_response(), "error": None}
                    for i in range(n_train)
                ],
                [
                    {"id": i, "result": None, "error": "judge timed out"}
                    for i in range(n_train)
                ],
            ]
            result = calibrate(repo_root=env["repo"], workers=4)

        assert result["reason"] == "no_actionable_failures"
        assert result["failures"] == 0


# ---------------------------------------------------------------------------
# Tests: stage 3 — implementer
# ---------------------------------------------------------------------------


class TestStage3Implementer:
    """Tests for the implementer stage and content validation.

    Uses transcript_path with workers=1 for precise mock control.
    """

    def _run_3stage(
        self,
        env: dict[str, Any],
        impl_result: str,
        weight: float = 0.8,
        mock_leaks: list[str] | None = None,
        token_budget: int | None = None,
    ) -> dict[str, Any]:
        """Helper: run calibrate with a single transcript through all 3 stages.

        Args:
            mock_leaks: If set, patches validate_no_prompt_leaks to return this list.
        """
        from clawdibrate.orchestrator import calibrate

        t1 = env["transcripts_dir"] / "session_000.jsonl"
        extra_patches: list[Any] = []
        if mock_leaks is not None:
            extra_patches.append(
                patch("clawdibrate.orchestrator.validate_no_prompt_leaks", return_value=mock_leaks)
            )

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            _patch_compression(),
            patch("clawdibrate.orchestrator.run_agent", side_effect=[
                _bug_identifier_response(),
                _judge_response(weight=weight),
                impl_result,
            ]),
        ):
            for p in extra_patches:
                p.start()
            try:
                return calibrate(
                    repo_root=env["repo"], workers=1,
                    transcript_path=t1, token_budget=token_budget,
                )
            finally:
                for p in extra_patches:
                    p.stop()

    def test_empty_implementer_output_rejected(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Empty implementer output is rejected, section not updated."""
        result = self._run_3stage(calibrate_env, impl_result="")
        assert result["changed"] is False

    def test_prompt_leak_rejected(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Implementer output with prompt artifacts is rejected."""
        result = self._run_3stage(
            calibrate_env,
            impl_result="- Don't use inline imports.\n",
            mock_leaks=["found leak pattern"],
        )
        assert result["changed"] is False

    def test_successful_section_update(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Full happy path: bug-id → judge → implementer → section updated."""
        result = self._run_3stage(calibrate_env, impl_result=_implementer_response())
        assert result["changed"] is True
        assert result["failures"] >= 1
        updated = calibrate_env["instruction_file"].read_text()
        assert "move all imports to module top" in updated

    def test_token_budget_rejects_large_edit(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """If edit would exceed --token-budget, it's rejected."""
        huge_content = "- " + "word " * 500 + "\n"
        result = self._run_3stage(
            calibrate_env, impl_result=huge_content, token_budget=50,
        )
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

        t1 = env["transcripts_dir"] / "session_000.jsonl"

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            _patch_compression(),
            patch("clawdibrate.orchestrator.run_agent", side_effect=[
                _bug_identifier_response(),
                _judge_response(weight=0.8),
                _implementer_response(),
            ]),
        ):
            calibrate(repo_root=env["repo"], workers=1, transcript_path=t1)

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
        assert entry["mode"] == "progressive"
        assert "result" in entry

    def test_version_bumped_and_committed(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """After successful calibration that changes the instruction file:
        version is bumped on disk, git commit is called, and changed=True.
        """
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        # Overwrite instruction file with **Version:** format that bump_patch_version recognises
        versioned_content = """\
**Version: 0.1.0**
# AGENTS.md

## Identity
You are a coding assistant.

## Known Gotchas
- Don't use inline imports.
- Always check for None before indexing.

## Boundaries
Stay within the repo.
"""
        env["instruction_file"].write_text(versioned_content)

        t1 = env["transcripts_dir"] / "session_000.jsonl"

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_compression(),
            patch("clawdibrate.orchestrator.subprocess.run") as mock_subprocess,
            patch("clawdibrate.orchestrator.run_agent", side_effect=[
                _bug_identifier_response(),
                _judge_response(weight=0.8),
                _implementer_response(),
            ]),
        ):
            result = calibrate(repo_root=env["repo"], workers=1, transcript_path=t1)

        # 1. Instruction file on disk has version bumped from 0.1.0 to 0.1.1
        updated_content = env["instruction_file"].read_text()
        assert "**Version: 0.1.1**" in updated_content
        assert "**Version: 0.1.0**" not in updated_content

        # 2. subprocess.run was called with git commit args containing the version string
        all_calls = mock_subprocess.call_args_list
        commit_calls = [
            c for c in all_calls
            if c.args and c.args[0] and "commit" in c.args[0]
        ]
        assert len(commit_calls) >= 1, "Expected at least one git commit call"
        commit_cmd = commit_calls[0].args[0]
        commit_msg = commit_cmd[commit_cmd.index("-m") + 1]
        assert "0.1.1" in commit_msg

        # 3. Result dict has changed=True
        assert result["changed"] is True

    def test_summary_contains_expected_keys(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """The returned summary dict has all expected keys."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        t1 = env["transcripts_dir"] / "session_000.jsonl"

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            _patch_compression(),
            patch("clawdibrate.orchestrator.run_agent", side_effect=[
                _bug_identifier_response(),
                _judge_response(weight=0.8),
                _implementer_response(),
            ]),
        ):
            result = calibrate(repo_root=env["repo"], workers=1, transcript_path=t1)

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

        t1 = env["transcripts_dir"] / "session_000.jsonl"

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.run_agent", side_effect=[
                _bug_identifier_response(),
                _judge_response(weight=0.8),
                # No stage 3 call — section is converged
            ]),
            patch("clawdibrate.orchestrator.is_converged", return_value=True),
        ):
            result = calibrate(
                repo_root=env["repo"], workers=1, transcript_path=t1,
            )

        # Changed should be False since converged section was skipped
        assert result["changed"] is False

    def test_overfit_detection_reverts_changes(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """Overfit detection: when train_avg > 0.5 but test_avg < 0.2, changes are reverted.

        Setup:
        - 6 transcripts → split_transcripts gives 5 train, 1 test (deterministic seed=42)
        - 5 train transcripts each report a bug + high-weight judge verdict → train_avg ~0.8
        - Test transcript has many wasted searches, no actions, no success → test_avg < 0.2
        - Implementer produces a valid section update (so updated_agents_md != agents_md)
        - Overfit condition (train_avg > 0.5 and test_avg < 0.2) triggers revert
        - Instruction file must remain unchanged after calibrate() returns
        """
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate, split_transcripts

        # Determine which transcript will be held out as the test set (deterministic seed=42)
        all_transcripts = sorted(env["transcripts_dir"].glob("*.jsonl"))
        train_transcripts, test_transcripts = split_transcripts(all_transcripts)
        assert len(test_transcripts) == 1, "expected exactly 1 test transcript"
        assert len(train_transcripts) == 5, "expected exactly 5 train transcripts"

        # Overwrite the test transcript with events that produce very poor composite metrics:
        # - Many search calls with no following action → wasted_search_calls = 10
        # - No action calls → ideal_calls = max(0*2, 1) = 1, token_efficiency = 1/10 = 0.1
        # - No success signal in assistant messages → success_rate = 0.0
        # - test_avg = (0.1 + 0.0) / 2 = 0.05 < 0.2  ✓
        poor_events = [
            {"role": "user", "content": "Do something"},
            {"role": "assistant", "tool": "Grep", "args": "foo.py"},
            {"role": "assistant", "tool": "Grep", "args": "bar.py"},
            {"role": "assistant", "tool": "Read", "args": "foo.py"},
            {"role": "assistant", "tool": "Grep", "args": "baz.py"},
            {"role": "assistant", "tool": "Read", "args": "bar.py"},
            {"role": "assistant", "tool": "Grep", "args": "qux.py"},
            {"role": "assistant", "tool": "Read", "args": "baz.py"},
            {"role": "assistant", "tool": "Grep", "args": "quux.py"},
            {"role": "assistant", "tool": "Read", "args": "qux.py"},
            {"role": "assistant", "tool": "Grep", "args": "corge.py"},
            # No Edit/Write/Bash (no action) and no completion phrase
        ]
        test_transcripts[0].write_text("\n".join(json.dumps(e) for e in poor_events))

        n_train = len(train_transcripts)  # 5

        original_content = env["instruction_file"].read_text()

        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            _patch_compression(),
            patch("clawdibrate.orchestrator.fan_out") as mock_fan_out,
            patch("clawdibrate.orchestrator.run_agent") as mock_agent,
        ):
            mock_fan_out.side_effect = [
                # Stage 1: 5 bug-id tasks (n_train > 1 → fan_out)
                [
                    {"id": i, "result": _bug_identifier_response(), "error": None}
                    for i in range(n_train)
                ],
                # Stage 2: 5 judge tasks with high weight → train_avg ~0.8 (> 0.5)
                [
                    {"id": i, "result": _judge_response(weight=0.8), "error": None}
                    for i in range(n_train)
                ],
                # Stage 3: 1 unique section → sequential fallback via run_agent (not fan_out)
            ]
            # Stage 3 sequential: produces a valid section update so updated_agents_md != agents_md
            mock_agent.return_value = _implementer_response()

            result = calibrate(repo_root=env["repo"], workers=4)

        # Overfit detection should have reverted the changes
        assert result["changed"] is False, (
            "expected changed=False after overfit revert, got changed=True"
        )
        # Instruction file must be unchanged on disk
        assert env["instruction_file"].read_text() == original_content, (
            "instruction file was modified on disk despite overfit revert"
        )


# ---------------------------------------------------------------------------
# Tests: compute_metrics (deterministic, no mocks needed)
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    """Tests for the deterministic metrics computation."""

    def test_empty_transcript(self) -> None:
        from clawdibrate.orchestrator import compute_metrics

        result = compute_metrics([])
        assert result["total_tool_calls"] == 0
        # Empty transcript: ideal_calls = max(0*2, 1) = 1, min(1/1, 1.0) = 1.0
        assert result["token_efficiency"] == 1.0
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


# ---------------------------------------------------------------------------
# Tests: compression phase
# ---------------------------------------------------------------------------


class TestCompressionPhase:
    """Tests for the compression phase that runs after the implementer."""

    def test_compression_called_when_file_grows(
        self, calibrate_env: dict[str, Any]
    ) -> None:
        """When implementer output makes the file larger than tokens_start, compress_section is called."""
        env = calibrate_env
        from clawdibrate.orchestrator import calibrate

        t1 = env["transcripts_dir"] / "session_000.jsonl"

        # Build a moderately larger implementer output that:
        #   1. Passes ROI gating: score_improvement(0.9) / token_delta >= 0.005
        #      → token_delta must be <= 180
        #   2. Makes the total file grow past tokens_start (~53 tokens) so compression fires.
        # The "Known Gotchas" section is ~15 tokens; adding ~50 extra tokens keeps ROI > 0.005
        # and pushes the total file above the 53-token baseline.
        large_section_content = (
            "- Don't use inline imports — move all imports to the module top level.\n"
            "- Always check for None before indexing into any data structure.\n"
            "- Prefer explicit descriptive error messages over bare exceptions.\n"
            "- Avoid mutable default arguments; use None and assign inside the function.\n"
            "- Use type annotations on all public function signatures.\n"
        )

        # compress_section must return (content, saved_tokens) — return content unchanged
        # with 0 saved so the loop terminates cleanly.
        with (
            _patch_resolve_repo_root(env),
            _patch_repo_paths(env),
            _patch_git_commands(),
            patch("clawdibrate.orchestrator.run_agent", side_effect=[
                _bug_identifier_response(),
                _judge_response(weight=0.9),
                large_section_content,
            ]),
            patch(
                "clawdibrate.compress.compress_section",
                side_effect=lambda content, **_kw: (content, 0),
            ) as mock_compress,
        ):
            result = calibrate(repo_root=env["repo"], workers=1, transcript_path=t1)

        # The file must have grown for compression to trigger.
        assert result["changed"] is True, (
            "Expected the implementer to apply a change; check that large_section_content "
            "passes validation (non-empty, no prompt leaks)."
        )
        mock_compress.assert_called()
        # Verify it was called with the section content (first positional arg)
        first_call_content = mock_compress.call_args_list[0][0][0]
        assert isinstance(first_call_content, str)
        assert len(first_call_content) > 0


# ---------------------------------------------------------------------------
# Tests: --scores CLI flag
# ---------------------------------------------------------------------------


class TestScoresChart:
    """Tests for the _show_scores helper and --scores CLI flag."""

    def test_scores_no_data(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Missing scores file prints 'No scores found'."""
        from clawdibrate.__main__ import _show_scores

        repo = tmp_path / "repo"
        repo.mkdir()

        _show_scores(repo)

        captured = capsys.readouterr()
        assert "No scores found" in captured.out

    def test_scores_no_data_empty_file(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Scores file that exists but is empty also prints 'No scores found'."""
        from clawdibrate.__main__ import _show_scores

        repo = tmp_path / "repo"
        history_dir = repo / ".clawdibrate" / "history"
        history_dir.mkdir(parents=True)
        (history_dir / "scores.jsonl").write_text("")

        _show_scores(repo)

        captured = capsys.readouterr()
        assert "No scores found" in captured.out

    def test_scores_with_data(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Writes sample score entries and verifies table + sparkline chars appear."""
        from clawdibrate.__main__ import _show_scores, _SPARK_CHARS

        repo = tmp_path / "repo"
        history_dir = repo / ".clawdibrate" / "history"
        history_dir.mkdir(parents=True)

        sample_entries = [
            {
                "timestamp": f"2026-04-0{i + 1}T12:00:00",
                "avg": 0.5 + i * 0.05,
                "sections": {},
                "train_avg": 0.5 + i * 0.05,
                "test_avg": 0.5 + i * 0.04,
                "tokens_before": 1000,
                "tokens_after": 1000 + i * 10,
                "token_delta": i * 10,
            }
            for i in range(5)
        ]
        lines = "\n".join(json.dumps(e) for e in sample_entries) + "\n"
        (history_dir / "scores.jsonl").write_text(lines)

        _show_scores(repo)

        captured = capsys.readouterr()
        output = captured.out

        # Table header and date values should appear
        assert "Date" in output
        assert "Avg" in output
        assert "2026-04-01" in output

        # Sparkline line should appear and contain at least one block char
        assert "Trend" in output
        assert any(ch in output for ch in _SPARK_CHARS)


# ---------------------------------------------------------------------------
# Tests: --check-idempotent CLI flag
# ---------------------------------------------------------------------------


class TestIdempotencyCheck:
    """Tests for the _run_idempotency_check function."""

    def _make_args(self, tmp_path: Path) -> Any:
        import argparse

        transcript = tmp_path / "session.jsonl"
        transcript.write_text('{"role": "user", "content": "hi"}\n')
        return argparse.Namespace(
            transcript=transcript,
            repo=None,
            dry_run=False,
            holdout_ratio=0.2,
            staleness_halflife_days=30.0,
            max_transcripts=None,
            token_budget=None,
            workers=4,
            model="sonnet",
            no_auto_section_skills=False,
            mode="progressive",
            target_score=0.9,
            agent=None,
        )

    def test_pass_when_second_run_unchanged(self, tmp_path: Path) -> None:
        """Exit 0 when calibrate returns changed=False on second run."""
        from clawdibrate.__main__ import _run_idempotency_check

        args = self._make_args(tmp_path)

        run1_result = {"changed": True, "edit_distances": {"Known Gotchas": 3}}
        run2_result = {"changed": False, "edit_distances": {"Known Gotchas": 0}}

        with (
            patch("clawdibrate.__main__.calibrate", side_effect=[run1_result, run2_result]),
            patch("clawdibrate.__main__.load_clawdibrate_env"),
            patch("clawdibrate.__main__.resolve_default_calibration_agent", return_value="claude"),
            pytest.raises(SystemExit) as exc_info,
        ):
            _run_idempotency_check(args)

        assert exc_info.value.code == 0

    def test_fail_when_second_run_changed(self, tmp_path: Path) -> None:
        """Exit 1 when calibrate returns changed=True on second run."""
        from clawdibrate.__main__ import _run_idempotency_check

        args = self._make_args(tmp_path)

        run1_result = {"changed": True, "edit_distances": {"Known Gotchas": 3}}
        run2_result = {"changed": True, "edit_distances": {"Known Gotchas": 2}}

        with (
            patch("clawdibrate.__main__.calibrate", side_effect=[run1_result, run2_result]),
            patch("clawdibrate.__main__.load_clawdibrate_env"),
            patch("clawdibrate.__main__.resolve_default_calibration_agent", return_value="claude"),
            pytest.raises(SystemExit) as exc_info,
        ):
            _run_idempotency_check(args)

        assert exc_info.value.code == 1

    def test_error_when_no_transcript(self, tmp_path: Path) -> None:
        """Exit 1 with error message when --transcript is not provided."""
        from clawdibrate.__main__ import _run_idempotency_check

        args = self._make_args(tmp_path)
        args.transcript = None

        with pytest.raises(SystemExit) as exc_info:
            _run_idempotency_check(args)

        assert exc_info.value.code == 1
