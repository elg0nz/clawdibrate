"""OpenAI Codex agent."""

from .base import BaseAgent


class CodexAgent(BaseAgent):
    name = "codex"
    template = "codex exec --full-auto {prompt}"
    binary = "codex"
    env_prefixes = ("CODEX_",)
