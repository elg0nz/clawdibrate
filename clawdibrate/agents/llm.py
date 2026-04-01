"""simonw/llm agent (any backend via plugins)."""

from .base import BaseAgent


class LlmAgent(BaseAgent):
    name = "llm"
    template = "llm {prompt}"
    binary = "llm"
    env_prefixes = ("LLM_",)
