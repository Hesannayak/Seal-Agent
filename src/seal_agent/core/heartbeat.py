"""Heartbeat Engine — Autonomous task scheduler for the agent."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from seal_agent.config import settings

if TYPE_CHECKING:
    from seal_agent.core.agent import SealAgent

log = structlog.get_logger()


class HeartbeatEngine:
    """Manages the agent's autonomous operational rhythm.

    The heartbeat runs periodic tasks at defined intervals:
    - Every 5 minutes: Check for new messages
    - Every 15 minutes: Process new leads
    - Every hour: Pipeline review and follow-ups
    - Daily: Morning briefing and end-of-day summary
    """

    def __init__(self) -> None:
        self._running = False
        self._tasks: list[asyncio.Task] = []  # type: ignore[type-arg]

    async def start(self, agent: SealAgent) -> None:
        """Start the heartbeat loop."""
        if not settings.heartbeat_enabled:
            log.info("Heartbeat is disabled")
            return

        self._running = True
        log.info("Starting heartbeat engine")

        # Launch periodic tasks
        self._tasks = [
            asyncio.create_task(self._check_messages(agent)),
            asyncio.create_task(self._process_leads(agent)),
            asyncio.create_task(self._pipeline_review(agent)),
        ]

        # Wait for all tasks (they run forever until stopped)
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def stop(self) -> None:
        """Stop the heartbeat loop."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        log.info("Heartbeat engine stopped")

    async def _check_messages(self, agent: SealAgent) -> None:
        """Check for new incoming messages every 5 minutes."""
        while self._running:
            try:
                log.debug("Heartbeat: Checking messages")
                # TODO: Implement message checking across integrations
            except Exception:
                log.exception("Error checking messages")
            await asyncio.sleep(300)  # 5 minutes

    async def _process_leads(self, agent: SealAgent) -> None:
        """Process and qualify new leads every 15 minutes."""
        while self._running:
            try:
                log.debug("Heartbeat: Processing new leads")
                # TODO: Implement lead processing
            except Exception:
                log.exception("Error processing leads")
            await asyncio.sleep(900)  # 15 minutes

    async def _pipeline_review(self, agent: SealAgent) -> None:
        """Review pipeline and execute follow-ups every hour."""
        while self._running:
            try:
                log.debug("Heartbeat: Pipeline review")
                # TODO: Implement pipeline review
            except Exception:
                log.exception("Error in pipeline review")
            await asyncio.sleep(3600)  # 1 hour
