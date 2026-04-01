"""Custom agent via CLAWDIBRATE_AGENT_CMD env var."""

import os

from .base import BaseAgent


class CustomAgent(BaseAgent):
    name = "custom"
    binary = ""

    @property
    def template(self) -> str:
        return os.environ.get("CLAWDIBRATE_AGENT_CMD", "")

    @property
    def env_prefixes(self) -> tuple[str, ...]:
        return ()

    def detect_from_env(self) -> bool:
        return bool(os.environ.get("CLAWDIBRATE_AGENT_CMD"))
