"""Base interface for all integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseIntegration(ABC):
    """Abstract base class for all external tool integrations.

    Every integration (CRM, email, LinkedIn, etc.) must implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of this integration."""

    @property
    @abstractmethod
    def category(self) -> str:
        """The category (crm, communication, sales_tools, calendar, documents)."""

    @abstractmethod
    async def connect(self, credentials: dict[str, str]) -> bool:
        """Establish a connection to the external service.

        Args:
            credentials: Authentication credentials.

        Returns:
            True if connection was successful.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the external service."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the integration is healthy and connected.

        Returns:
            True if the integration is operational.
        """

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an integration-specific action.

        Args:
            action: The action to perform.
            params: Action parameters.

        Returns:
            The result of the action.
        """
        raise NotImplementedError(f"Action '{action}' not implemented for {self.name}")
