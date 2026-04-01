"""Opencode agent."""

from .base import BaseAgent


class OpencodeAgent(BaseAgent):
    name = "opencode"
    template = "opencode --prompt {prompt}"
    binary = "opencode"
    env_prefixes = ("OPENCODE_",)
