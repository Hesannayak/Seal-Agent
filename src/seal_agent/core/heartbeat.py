"""Heartbeat Engine — Autonomous task scheduler for the agent."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

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
            asyncio.create_task(self._execute_sequences(agent)),
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

                # Check for unread email replies by looking at interactions
                # that have been received but not processed
                from seal_agent.db.database import get_session
                from seal_agent.db.repositories.interaction_repo import InteractionRepository

                async with get_session() as session:
                    repo = InteractionRepository(session)
                    # Find recent inbound interactions that need processing
                    recent = await repo.list_recent_inbound(limit=10)

                    for interaction in recent:
                        if not interaction.response:
                            log.info(
                                "Processing unresponded message",
                                prospect_id=interaction.prospect_id,
                                channel=interaction.channel,
                            )
                            # Auto-generate a response via the agent
                            try:
                                response = await agent.process_message(
                                    message=interaction.content,
                                    context={
                                        "prospect_id": interaction.prospect_id,
                                        "channel": interaction.channel,
                                        "deal_id": interaction.deal_id,
                                    },
                                )
                                interaction.response = response
                                await session.flush()
                            except Exception:
                                log.exception("Error auto-responding to message")
            except Exception:
                log.exception("Error checking messages")
            await asyncio.sleep(300)  # 5 minutes

    async def _process_leads(self, agent: SealAgent) -> None:
        """Process and qualify new leads every 15 minutes."""
        while self._running:
            try:
                log.debug("Heartbeat: Processing new leads")

                from seal_agent.skills.prospecting import ProspectingSkill

                skill = ProspectingSkill()

                # Find new unscored leads
                result = await skill.execute("find_leads", {"status": "new", "limit": 10})
                leads = result.get("leads", [])

                for lead in leads:
                    if lead.get("score", 0) == 0:
                        # Score the lead
                        score_result = await skill.execute(
                            "score_lead", {"prospect_id": lead["id"]}
                        )
                        log.info(
                            "Scored lead",
                            prospect_id=lead["id"],
                            score=score_result.get("score"),
                        )
            except Exception:
                log.exception("Error processing leads")
            await asyncio.sleep(900)  # 15 minutes

    async def _pipeline_review(self, agent: SealAgent) -> None:
        """Review pipeline and execute follow-ups every hour."""
        while self._running:
            try:
                log.debug("Heartbeat: Pipeline review")

                from seal_agent.skills.deal_management import DealManagementSkill

                skill = DealManagementSkill()

                # Check for at-risk deals
                at_risk = await skill.execute("identify_at_risk", {"stale_days": 14})
                risk_count = at_risk.get("count", 0)

                if risk_count > 0:
                    log.warning(
                        "At-risk deals detected",
                        count=risk_count,
                        total_value=at_risk.get("total_risk_value", 0),
                    )

                # Get pipeline overview for logging
                pipeline = await skill.execute("get_pipeline", {})
                log.info(
                    "Pipeline review complete",
                    total_value=pipeline.get("total_value", 0),
                    deal_count=pipeline.get("deal_count", 0),
                    at_risk=risk_count,
                )
            except Exception:
                log.exception("Error in pipeline review")
            await asyncio.sleep(3600)  # 1 hour

    async def _execute_sequences(self, agent: SealAgent) -> None:
        """Execute due outreach sequence steps every 10 minutes."""
        while self._running:
            try:
                log.debug("Heartbeat: Checking outreach sequences")

                from seal_agent.db.database import get_session
                from seal_agent.db.models import OutreachSequence
                from seal_agent.skills.outreach import OutreachSkill

                async with get_session() as session:
                    now = datetime.now(timezone.utc)
                    result = await session.execute(
                        select(OutreachSequence)
                        .where(
                            OutreachSequence.status == "active",
                            OutreachSequence.next_action_at <= now,
                        )
                        .limit(10)
                    )
                    due_sequences = result.scalars().all()

                    if due_sequences:
                        skill = OutreachSkill(reasoning_engine=agent.reasoning)
                        for seq in due_sequences:
                            log.info(
                                "Executing sequence step",
                                sequence_id=seq.id,
                                step=seq.current_step,
                            )
                            await skill.execute(
                                "execute_sequence_step",
                                {"sequence_id": seq.id},
                            )
            except Exception:
                log.exception("Error executing sequences")
            await asyncio.sleep(600)  # 10 minutes
