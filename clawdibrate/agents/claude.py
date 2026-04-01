"""Claude Code agent."""

from .base import BaseAgent


class ClaudeAgent(BaseAgent):
    name = "claude"
    template = "claude -p {prompt} --dangerously-skip-permissions"
    binary = "claude"
    env_prefixes = ("CLAUDECODE_", "CLAUDE_CODE_")
