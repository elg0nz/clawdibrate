"""Tests for clawdibrate.repo — instruction file operations."""

from __future__ import annotations

from clawdibrate.repo import (
    bump_patch_version,
    extract_section,
    parse_instruction_version,
    replace_section,
    strip_prompt_artifacts,
    validate_no_prompt_leaks,
)

SAMPLE_MD = """\
# AGENTS.md

> **Version: 1.2.3**

## Identity

You are a coding assistant.

## Known Gotchas

- Don't use inline imports.

## Boundaries

Stay within the repo.
"""


class TestParseVersion:
    def test_valid(self) -> None:
        assert parse_instruction_version(SAMPLE_MD) == (1, 2, 3)

    def test_missing(self) -> None:
        assert parse_instruction_version("# No version here") is None


class TestBumpPatchVersion:
    def test_bumps(self) -> None:
        content, version = bump_patch_version(SAMPLE_MD)
        assert version == (1, 2, 4)
        assert "1.2.4" in content

    def test_no_version(self) -> None:
        content, version = bump_patch_version("# No version")
        assert version is None
        assert content == "# No version"


class TestExtractSection:
    def test_extracts(self) -> None:
        result = extract_section(SAMPLE_MD, "Known Gotchas")
        assert "inline imports" in result

    def test_missing_section(self) -> None:
        assert extract_section(SAMPLE_MD, "Nonexistent") == ""


class TestReplaceSection:
    def test_replaces(self) -> None:
        result = replace_section(SAMPLE_MD, "Known Gotchas", "- New gotcha.\n")
        assert "New gotcha" in result
        assert "inline imports" not in result

    def test_preserves_other_sections(self) -> None:
        result = replace_section(SAMPLE_MD, "Known Gotchas", "- Changed.\n")
        assert "You are a coding assistant." in result
        assert "Stay within the repo." in result


class TestStripPromptArtifacts:
    def test_strips_preamble(self) -> None:
        result = strip_prompt_artifacts("Here is the updated section:\n- actual content")
        assert result == "- actual content"

    def test_strips_trailing_summary(self) -> None:
        result = strip_prompt_artifacts("- content\n\n**Summary:** blah blah")
        assert "Summary" not in result

    def test_clean_passthrough(self) -> None:
        assert strip_prompt_artifacts("- clean content") == "- clean content"


class TestValidateNoPromptLeaks:
    def test_clean(self) -> None:
        assert validate_no_prompt_leaks("- normal content") == []

    def test_detects_leak(self) -> None:
        leaks = validate_no_prompt_leaks("Here is the updated section\n- content")
        assert len(leaks) > 0
