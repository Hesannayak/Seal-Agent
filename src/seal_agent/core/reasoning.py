"""Reasoning Engine — AI-powered sales reasoning using Claude."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anthropic
import structlog

from seal_agent.config import settings

if TYPE_CHECKING:
    from seal_agent.core.soul_engine import SoulEngine

log = structlog.get_logger()


class ReasoningEngine:
    """Handles AI reasoning for sales interactions using Anthropic Claude.

    This is the brain of Seal-Agent — it takes the soul (identity + style + playbook),
    relevant memories, and conversation context to generate intelligent sales responses.
    """

    def __init__(self) -> None:
        self._client: anthropic.AsyncAnthropic | None = None
        self._system_prompt: str = ""

    async def initialize(self, soul: SoulEngine) -> None:
        """Initialize the reasoning engine with the agent's soul.

        Args:
            soul: The loaded soul engine containing identity and style.
        """
        log.info("Initializing reasoning engine")
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._system_prompt = soul.get_system_prompt()
        log.info("Reasoning engine ready", model=settings.anthropic_model)

    async def generate_response(
        self,
        message: str,
        context: dict | None = None,
        memories: list[dict] | None = None,
        soul: SoulEngine | None = None,
    ) -> str:
        """Generate a sales-optimized response.

        Args:
            message: The incoming message to respond to.
            context: Conversation context (prospect info, channel, deal stage, etc.)
            memories: Relevant memories retrieved from the memory engine.
            soul: The soul engine for real-time access to identity/style.

        Returns:
            The generated response text.
        """
        if not self._client:
            raise RuntimeError("Reasoning engine not initialized")

        # Build the contextual prompt
        user_content = self._build_contextual_prompt(message, context, memories)

        response = await self._client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2048,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        result = response.content[0].text
        log.debug("Generated response", length=len(result))
        return result

    def _build_contextual_prompt(
        self,
        message: str,
        context: dict | None = None,
        memories: list[dict] | None = None,
    ) -> str:
        """Build a rich prompt with all available context.

        Args:
            message: The core message.
            context: Additional context.
            memories: Relevant memories.

        Returns:
            A fully constructed prompt string.
        """
        parts = []

        if context:
            parts.append("## Context")
            for key, value in context.items():
                parts.append(f"- **{key}**: {value}")
            parts.append("")

        if memories:
            parts.append("## Relevant History")
            for memory in memories:
                parts.append(f"- {memory}")
            parts.append("")

        parts.append("## Current Message")
        parts.append(message)

        return "\n".join(parts)
