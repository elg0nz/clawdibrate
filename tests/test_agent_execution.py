"""Tests for clawdibrate.agent_execution — agent CLI invocation and JSON extraction."""

from __future__ import annotations

from clawdibrate.agent_execution import (
    apply_builtin_model_flag,
    extract_json,
    resolve_default_calibration_agent,
)


class TestResolveDefaultAgent:
    def test_returns_claude(self) -> None:
        assert resolve_default_calibration_agent() == "claude"


class TestApplyBuiltinModelFlag:
    def test_claude_injects_model(self) -> None:
        template = 'claude --system-prompt "x" -p "y" --dangerously-skip-permissions'
        result = apply_builtin_model_flag(template, "claude", "opus")
        assert "--model opus" in result

    def test_none_model_no_change(self) -> None:
        template = 'claude -p "y"'
        result = apply_builtin_model_flag(template, "claude", None)
        assert result == template


class TestExtractJson:
    def test_plain_json(self) -> None:
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_json_in_text(self) -> None:
        result = extract_json('Here is the result: {"a": 1} done')
        assert result == {"a": 1}

    def test_json_array(self) -> None:
        result = extract_json('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_no_json(self) -> None:
        assert extract_json("no json here") is None

    def test_empty(self) -> None:
        assert extract_json("") is None
