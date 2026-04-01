"""Base agent interface."""

import os
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Each agent defines its CLI template, binary name, and env detection markers."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def template(self) -> str:
        """CLI template with {prompt} placeholder."""
        ...

    @property
    @abstractmethod
    def binary(self) -> str:
        """Binary name for shutil.which() detection."""
        ...

    @property
    def env_prefixes(self) -> tuple[str, ...]:
        """Environment variable prefixes that indicate this agent is active."""
        return ()

    def detect_from_env(self) -> bool:
        if not self.env_prefixes:
            return False
        return any(key.startswith(self.env_prefixes) for key in os.environ)
