"""Scheduling Skill — Meeting scheduling and calendar management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.prospect_repo import ProspectRepository
from seal_agent.db.repositories.interaction_repo import InteractionRepository
from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()

# Default meeting types
MEETING_TYPES = {
    "discovery": {"duration_minutes": 30, "description": "Initial discovery call"},
    "demo": {"duration_minutes": 45, "description": "Product demonstration"},
    "technical": {"duration_minutes": 60, "description": "Technical deep-dive"},
    "proposal_review": {"duration_minutes": 30, "description": "Proposal review and Q&A"},
    "negotiation": {"duration_minutes": 45, "description": "Contract negotiation"},
    "kickoff": {"duration_minutes": 60, "description": "Implementation kickoff"},
    "check_in": {"duration_minutes": 15, "description": "Quick check-in call"},
}


class SchedulingSkill(BaseSkill):
    """Handles meeting scheduling, availability, and calendar coordination."""

    @property
    def name(self) -> str:
        return "scheduling"

    @property
    def description(self) -> str:
        return "Meeting scheduling, availability management, and calendar coordination"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "suggest_meeting": self._suggest_meeting,
            "create_meeting_request": self._create_meeting_request,
            "get_meeting_types": self._get_meeting_types,
            "suggest_times": self._suggest_times,
            "prepare_agenda": self._prepare_agenda,
        }
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return [
            "suggest_meeting", "create_meeting_request", "get_meeting_types",
            "suggest_times", "prepare_agenda",
        ]

    async def _suggest_meeting(self, params: dict[str, Any]) -> dict[str, Any]:
        """Suggest the appropriate meeting type based on deal stage."""
        deal_stage = params.get("stage", "prospecting")
        prospect_id = params.get("prospect_id")

        stage_to_meeting = {
            "prospecting": "discovery",
            "qualification": "discovery",
            "discovery": "demo",
            "proposal": "proposal_review",
            "negotiation": "negotiation",
            "closed_won": "kickoff",
        }

        meeting_type = stage_to_meeting.get(deal_stage, "check_in")
        meeting_info = MEETING_TYPES[meeting_type]

        result: dict[str, Any] = {
            "suggested_type": meeting_type,
            "duration_minutes": meeting_info["duration_minutes"],
            "description": meeting_info["description"],
            "deal_stage": deal_stage,
        }

        if prospect_id:
            try:
                async with get_session() as session:
                    repo = ProspectRepository(session)
                    prospect = await repo.get_by_id(prospect_id)
                    if prospect:
                        result["prospect_name"] = f"{prospect.first_name} {prospect.last_name}"
                        result["prospect_timezone"] = prospect.timezone
            except Exception:
                pass

        return result

    async def _create_meeting_request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a meeting request message for a prospect."""
        prospect_id = params.get("prospect_id")
        meeting_type = params.get("type", "discovery")
        proposed_times = params.get("proposed_times", [])

        if not prospect_id:
            return {"error": "prospect_id is required"}

        meeting_info = MEETING_TYPES.get(meeting_type)
        if not meeting_info:
            return {"error": f"Unknown meeting type: {meeting_type}"}

        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                prospect = await repo.get_by_id(prospect_id)
                if not prospect:
                    return {"error": "Prospect not found"}

                first_name = prospect.first_name or "there"
                duration = meeting_info["duration_minutes"]

                if not proposed_times:
                    proposed_times = self._generate_time_slots(3)

                time_options = "\n".join(
                    f"  - {t}" for t in proposed_times
                )

                message = (
                    f"Hi {first_name},\n\n"
                    f"I'd love to schedule a {duration}-minute {meeting_info['description'].lower()} "
                    "with you. Here are a few time options:\n\n"
                    f"{time_options}\n\n"
                    "Do any of these work for you? If not, feel free to suggest "
                    "a time that's more convenient.\n\n"
                    "Best regards"
                )

                # Log as interaction
                interaction_repo = InteractionRepository(session)
                await interaction_repo.create({
                    "prospect_id": prospect_id,
                    "channel": "email",
                    "direction": "outbound",
                    "subject": f"Meeting Request: {meeting_info['description']}",
                    "content": message,
                })

                return {
                    "prospect_id": prospect_id,
                    "meeting_type": meeting_type,
                    "duration_minutes": duration,
                    "proposed_times": proposed_times,
                    "message": message,
                    "status": "sent",
                }
        except Exception:
            log.exception("Error creating meeting request")
            return {"error": "Failed to create meeting request"}

    async def _get_meeting_types(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return available meeting types."""
        return {
            "meeting_types": {
                name: {
                    "duration_minutes": info["duration_minutes"],
                    "description": info["description"],
                }
                for name, info in MEETING_TYPES.items()
            }
        }

    async def _suggest_times(self, params: dict[str, Any]) -> dict[str, Any]:
        """Suggest available time slots for a meeting."""
        num_slots = params.get("num_slots", 3)
        preferred_days = params.get("preferred_days", ["Tuesday", "Wednesday", "Thursday"])
        preferred_hours = params.get("preferred_hours", [10, 14, 15])
        prospect_timezone = params.get("timezone")

        slots = self._generate_time_slots(
            num_slots,
            preferred_days=preferred_days,
            preferred_hours=preferred_hours,
        )

        return {
            "suggested_times": slots,
            "timezone_note": (
                f"Times shown in {prospect_timezone}" if prospect_timezone
                else "Times shown in UTC — adjust for prospect's timezone"
            ),
        }

    async def _prepare_agenda(self, params: dict[str, Any]) -> dict[str, Any]:
        """Prepare a meeting agenda."""
        meeting_type = params.get("type", "discovery")
        prospect_id = params.get("prospect_id")
        deal_id = params.get("deal_id")

        meeting_info = MEETING_TYPES.get(meeting_type, MEETING_TYPES["discovery"])
        duration = meeting_info["duration_minutes"]

        agendas = {
            "discovery": [
                {"item": "Introductions and context", "minutes": 5},
                {"item": "Understand current challenges", "minutes": 10},
                {"item": "Explore goals and priorities", "minutes": 10},
                {"item": "Discuss potential fit and next steps", "minutes": 5},
            ],
            "demo": [
                {"item": "Recap pain points from discovery", "minutes": 5},
                {"item": "Product walkthrough", "minutes": 25},
                {"item": "Q&A", "minutes": 10},
                {"item": "Next steps", "minutes": 5},
            ],
            "technical": [
                {"item": "Technical requirements review", "minutes": 15},
                {"item": "Architecture and integration discussion", "minutes": 20},
                {"item": "Security and compliance", "minutes": 15},
                {"item": "Implementation timeline", "minutes": 10},
            ],
            "proposal_review": [
                {"item": "Proposal walkthrough", "minutes": 15},
                {"item": "Pricing discussion", "minutes": 10},
                {"item": "Decision timeline and next steps", "minutes": 5},
            ],
            "negotiation": [
                {"item": "Review open items", "minutes": 10},
                {"item": "Terms discussion", "minutes": 20},
                {"item": "Alignment and commitment", "minutes": 15},
            ],
            "kickoff": [
                {"item": "Team introductions", "minutes": 10},
                {"item": "Implementation plan review", "minutes": 20},
                {"item": "Success criteria and milestones", "minutes": 15},
                {"item": "Communication cadence", "minutes": 10},
                {"item": "Immediate next steps", "minutes": 5},
            ],
            "check_in": [
                {"item": "Status update", "minutes": 5},
                {"item": "Open items review", "minutes": 5},
                {"item": "Next steps", "minutes": 5},
            ],
        }

        agenda_items = agendas.get(meeting_type, agendas["discovery"])

        return {
            "meeting_type": meeting_type,
            "duration_minutes": duration,
            "agenda": agenda_items,
            "total_minutes": sum(item["minutes"] for item in agenda_items),
        }

    @staticmethod
    def _generate_time_slots(
        count: int = 3,
        preferred_days: list[str] | None = None,
        preferred_hours: list[int] | None = None,
    ) -> list[str]:
        """Generate time slot suggestions."""
        if preferred_days is None:
            preferred_days = ["Tuesday", "Wednesday", "Thursday"]
        if preferred_hours is None:
            preferred_hours = [10, 14, 15]

        slots = []
        now = datetime.now(timezone.utc)
        day = now + timedelta(days=1)

        while len(slots) < count:
            day_name = day.strftime("%A")
            if day_name in preferred_days:
                for hour in preferred_hours:
                    if len(slots) >= count:
                        break
                    slot_time = day.replace(hour=hour, minute=0, second=0, microsecond=0)
                    slots.append(slot_time.strftime("%A, %B %d at %I:%M %p UTC"))
            day += timedelta(days=1)

            # Safety limit
            if (day - now).days > 30:
                break

        return slots
