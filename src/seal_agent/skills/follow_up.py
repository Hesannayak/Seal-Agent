"""Follow-Up Skill — Intelligent follow-up sequence management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.prospect_repo import ProspectRepository
from seal_agent.db.repositories.interaction_repo import InteractionRepository
from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()

# Follow-up timing rules (days after last contact)
FOLLOW_UP_CADENCE = {
    "hot": [1, 3, 5, 7],
    "warm": [2, 5, 10, 15],
    "cold": [3, 7, 14, 30],
}

# Maximum follow-ups before pausing
MAX_FOLLOW_UPS = 5


class FollowUpSkill(BaseSkill):
    """Manages intelligent follow-up sequences based on engagement signals."""

    def __init__(self, reasoning_engine: Any = None) -> None:
        self._reasoning = reasoning_engine

    @property
    def name(self) -> str:
        return "follow_up"

    @property
    def description(self) -> str:
        return "Intelligent follow-up timing and messaging based on prospect engagement"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "check_due": self._check_due_follow_ups,
            "create_follow_up": self._create_follow_up,
            "get_history": self._get_follow_up_history,
            "suggest_timing": self._suggest_timing,
            "pause": self._pause_follow_ups,
            "resume": self._resume_follow_ups,
        }
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return ["check_due", "create_follow_up", "get_history", "suggest_timing", "pause", "resume"]

    async def _check_due_follow_ups(self, params: dict[str, Any]) -> dict[str, Any]:
        """Find prospects that are due for a follow-up."""
        try:
            async with get_session() as session:
                prospect_repo = ProspectRepository(session)
                interaction_repo = InteractionRepository(session)

                # Get active prospects that have been contacted
                prospects, _ = await prospect_repo.list_all(
                    status=params.get("status", "contacted"),
                    limit=params.get("limit", 50),
                )

                due = []
                for p in prospects:
                    interactions = await interaction_repo.list_by_prospect(p.id, limit=5)
                    if not interactions:
                        continue

                    last = interactions[0]
                    if not last.created_at:
                        continue

                    days_since = (datetime.now(timezone.utc) - last.created_at).days
                    temperature = self._classify_temperature(interactions)
                    cadence = FOLLOW_UP_CADENCE.get(temperature, FOLLOW_UP_CADENCE["cold"])
                    outbound_count = sum(
                        1 for i in interactions if i.direction == "outbound"
                    )

                    if outbound_count >= MAX_FOLLOW_UPS:
                        continue

                    # Check if enough days have passed for next follow-up
                    step = min(outbound_count, len(cadence) - 1)
                    if days_since >= cadence[step]:
                        due.append({
                            "prospect_id": p.id,
                            "name": f"{p.first_name} {p.last_name}",
                            "company": p.company,
                            "days_since_last_contact": days_since,
                            "temperature": temperature,
                            "follow_up_number": outbound_count + 1,
                            "suggested_channel": self._suggest_channel(interactions),
                        })

                return {"due_follow_ups": due, "count": len(due)}
        except Exception:
            log.exception("Error checking due follow-ups")
            return {"due_follow_ups": [], "count": 0, "error": "Check failed"}

    async def _create_follow_up(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create and compose a follow-up message for a prospect."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}

        channel = params.get("channel", "email")

        try:
            async with get_session() as session:
                prospect_repo = ProspectRepository(session)
                interaction_repo = InteractionRepository(session)

                prospect = await prospect_repo.get_by_id(prospect_id)
                if not prospect:
                    return {"error": "Prospect not found"}

                interactions = await interaction_repo.list_by_prospect(prospect_id, limit=10)
                temperature = self._classify_temperature(interactions)
                follow_up_num = sum(1 for i in interactions if i.direction == "outbound") + 1

                name = f"{prospect.first_name} {prospect.last_name}"
                first_name = prospect.first_name or "there"
                company = prospect.company or "your company"

                # Generate follow-up content based on temperature and history
                if self._reasoning and follow_up_num > 2:
                    try:
                        history_summary = "; ".join(
                            f"{i.channel} ({i.direction}): {(i.subject or '')[:50]}"
                            for i in interactions[:5]
                        )
                        prompt = (
                            f"Compose follow-up #{follow_up_num} for {name} at {company}.\n"
                            f"Temperature: {temperature}\n"
                            f"History: {history_summary}\n"
                            f"Channel: {channel}\n"
                            "Keep it brief, add value, and include a clear CTA."
                        )
                        response = await self._reasoning.generate_response(
                            message=prompt,
                            context={"task": "follow_up", "channel": channel},
                        )
                        return {
                            "prospect_id": prospect_id,
                            "channel": channel,
                            "follow_up_number": follow_up_num,
                            "temperature": temperature,
                            "subject": f"Following up — {company}",
                            "body": response,
                            "ai_generated": True,
                        }
                    except Exception:
                        log.warning("AI follow-up failed, using template")

                # Template-based follow-ups
                templates = {
                    1: {
                        "subject": f"Quick follow-up — {company}",
                        "body": (
                            f"Hi {first_name},\n\n"
                            "I wanted to follow up on my previous message. "
                            "I'd love to share how we've helped similar companies.\n\n"
                            "Would a 15-minute call work this week?\n\nBest regards"
                        ),
                    },
                    2: {
                        "subject": f"One more thought for {company}",
                        "body": (
                            f"Hi {first_name},\n\n"
                            "I know you're busy, so I'll keep this short. "
                            "I recently helped a company in your space achieve significant results.\n\n"
                            "Happy to share the case study if you're interested.\n\nBest regards"
                        ),
                    },
                    3: {
                        "subject": f"Resource for {company}",
                        "body": (
                            f"Hi {first_name},\n\n"
                            "I came across something relevant to your work at "
                            f"{company} and thought of you.\n\n"
                            "Would it be helpful if I sent it over?\n\nBest regards"
                        ),
                    },
                }
                template = templates.get(
                    min(follow_up_num, 3), templates[3]
                )

                return {
                    "prospect_id": prospect_id,
                    "channel": channel,
                    "follow_up_number": follow_up_num,
                    "temperature": temperature,
                    **template,
                    "ai_generated": False,
                }
        except Exception:
            log.exception("Error creating follow-up")
            return {"error": "Failed to create follow-up"}

    async def _get_follow_up_history(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get follow-up history for a prospect."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}

        try:
            async with get_session() as session:
                interaction_repo = InteractionRepository(session)
                interactions = await interaction_repo.list_by_prospect(prospect_id, limit=20)

                follow_ups = []
                for i in interactions:
                    if i.direction == "outbound":
                        follow_ups.append({
                            "id": i.id,
                            "channel": i.channel,
                            "subject": i.subject,
                            "sent_at": i.created_at.isoformat() if i.created_at else None,
                            "opened": i.opened,
                            "clicked": i.clicked,
                            "replied": i.replied,
                        })

                return {
                    "prospect_id": prospect_id,
                    "follow_ups": follow_ups,
                    "total_sent": len(follow_ups),
                    "reply_rate": (
                        sum(1 for f in follow_ups if f["replied"]) / len(follow_ups)
                        if follow_ups else 0.0
                    ),
                }
        except Exception:
            log.exception("Error getting follow-up history")
            return {"follow_ups": [], "error": "Failed to retrieve history"}

    async def _suggest_timing(self, params: dict[str, Any]) -> dict[str, Any]:
        """Suggest optimal follow-up timing for a prospect."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}

        try:
            async with get_session() as session:
                interaction_repo = InteractionRepository(session)
                interactions = await interaction_repo.list_by_prospect(prospect_id, limit=10)

                temperature = self._classify_temperature(interactions)
                outbound_count = sum(1 for i in interactions if i.direction == "outbound")
                cadence = FOLLOW_UP_CADENCE.get(temperature, FOLLOW_UP_CADENCE["cold"])
                step = min(outbound_count, len(cadence) - 1)
                days_until_next = cadence[step]

                last_contact = None
                if interactions and interactions[0].created_at:
                    last_contact = interactions[0].created_at

                suggested_date = (
                    (last_contact + timedelta(days=days_until_next))
                    if last_contact
                    else datetime.now(timezone.utc) + timedelta(days=1)
                )

                return {
                    "prospect_id": prospect_id,
                    "temperature": temperature,
                    "suggested_date": suggested_date.isoformat(),
                    "days_until_next": days_until_next,
                    "follow_up_number": outbound_count + 1,
                    "max_follow_ups": MAX_FOLLOW_UPS,
                    "remaining": MAX_FOLLOW_UPS - outbound_count,
                    "suggested_channel": self._suggest_channel(interactions),
                }
        except Exception:
            log.exception("Error suggesting timing")
            return {"error": "Failed to suggest timing"}

    async def _pause_follow_ups(self, params: dict[str, Any]) -> dict[str, Any]:
        """Pause follow-ups for a prospect."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}
        reason = params.get("reason", "manual_pause")

        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                await repo.update(prospect_id, {
                    "tags": [reason, "follow_up_paused"],
                })
                return {"prospect_id": prospect_id, "status": "paused", "reason": reason}
        except Exception:
            log.exception("Error pausing follow-ups")
            return {"error": "Failed to pause"}

    async def _resume_follow_ups(self, params: dict[str, Any]) -> dict[str, Any]:
        """Resume follow-ups for a paused prospect."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}

        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                await repo.update(prospect_id, {"tags": []})
                return {"prospect_id": prospect_id, "status": "resumed"}
        except Exception:
            log.exception("Error resuming follow-ups")
            return {"error": "Failed to resume"}

    @staticmethod
    def _classify_temperature(interactions: list) -> str:
        """Classify prospect temperature based on engagement."""
        if not interactions:
            return "cold"

        replied = sum(1 for i in interactions if i.replied)
        opened = sum(1 for i in interactions if i.opened)
        total = len(interactions)

        if replied > 0:
            return "hot"
        if opened / total >= 0.5 and total >= 2:
            return "warm"
        return "cold"

    @staticmethod
    def _suggest_channel(interactions: list) -> str:
        """Suggest the best channel based on past engagement."""
        if not interactions:
            return "email"

        # Find channels where prospect has replied
        replied_channels = [i.channel for i in interactions if i.replied]
        if replied_channels:
            return replied_channels[0]

        # Find channels where prospect has opened
        opened_channels = [i.channel for i in interactions if i.opened]
        if opened_channels:
            return opened_channels[0]

        # Alternate channels
        last_channel = interactions[0].channel
        return "linkedin" if last_channel == "email" else "email"
