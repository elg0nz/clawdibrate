"""Agent registry — auto-discovers agent modules in this package."""

import os
import shutil

from .claude import ClaudeAgent
from .codex import CodexAgent
from .opencode import OpencodeAgent
from .llm import LlmAgent
from .custom import CustomAgent

# Registry: name -> agent instance
AGENTS: dict[str, "BaseAgent"] = {}

for cls in (ClaudeAgent, CodexAgent, OpencodeAgent, LlmAgent):
    agent = cls()
    AGENTS[agent.name] = agent


def get_agent_names() -> list[str]:
    return list(AGENTS.keys())


def get_agent(name: str):
    return AGENTS.get(name)


def detect_current_agent() -> str | None:
    """Infer the current agent from the environment."""
    configured = os.environ.get("CLAWDIBRATE_AGENT")
    if configured in AGENTS:
        return configured

    for name, agent in AGENTS.items():
        if agent.detect_from_env():
            return name

    for name, agent in AGENTS.items():
        if shutil.which(agent.binary):
            return name

    return None


def resolve_agent(requested: str | None) -> tuple[str, str]:
    """Return (agent_name, reason) for the chosen agent."""
    if os.environ.get("CLAWDIBRATE_AGENT_CMD"):
        name = requested or detect_current_agent() or "custom"
        return name, "CLAWDIBRATE_AGENT_CMD"

    if requested and requested != "auto":
        return requested, "--agent"

    detected = detect_current_agent()
    if detected:
        return detected, "auto-detected"

    return "claude", "default"
