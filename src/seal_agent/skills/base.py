"""Base interface for all sales skills."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """Abstract base class for all Seal-Agent sales skills.

    Every skill module (prospecting, outreach, negotiation, etc.)
    must implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of this skill."""

    @property
    @abstractmethod
    def description(self) -> str:
        """A short description of what this skill does."""

    @abstractmethod
    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a skill action.

        Args:
            action: The specific action to perform within this skill.
            params: Parameters for the action.

        Returns:
            The result of the action.
        """

    async def get_available_actions(self) -> list[str]:
        """Return a list of actions this skill can perform."""
        return []
