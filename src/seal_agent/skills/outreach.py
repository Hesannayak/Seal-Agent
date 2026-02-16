"""Outreach Skill — Multi-channel sales outreach."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.prospect_repo import ProspectRepository
from seal_agent.db.repositories.interaction_repo import InteractionRepository
from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()


class OutreachSkill(BaseSkill):
    """Handles multi-channel outreach including email, LinkedIn, and phone."""

    def __init__(self, reasoning_engine: Any = None) -> None:
        self._reasoning = reasoning_engine

    @property
    def name(self) -> str:
        return "outreach"

    @property
    def description(self) -> str:
        return "Multi-channel sales outreach (email, LinkedIn, phone, messaging)"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "compose_email": self._compose_email,
            "compose_linkedin_message": self._compose_linkedin_message,
            "create_sequence": self._create_sequence,
            "execute_sequence_step": self._execute_sequence_step,
        }

        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}

        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return [
            "compose_email",
            "compose_linkedin_message",
            "create_sequence",
            "execute_sequence_step",
        ]

    async def _compose_email(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compose a personalized sales email using AI reasoning."""
        prospect_id = params.get("prospect_id")
        email_type = params.get("type", "cold_outreach")

        log.info("Composing email", prospect=prospect_id, type=email_type)

        # Fetch prospect context
        prospect_context = await self._get_prospect_context(prospect_id)

        if self._reasoning:
            prompt = (
                f"Compose a {email_type} email for this prospect.\n"
                f"Prospect: {prospect_context.get('name', 'Unknown')}\n"
                f"Title: {prospect_context.get('title', 'Unknown')}\n"
                f"Company: {prospect_context.get('company', 'Unknown')}\n"
                f"Previous interactions: {prospect_context.get('interaction_count', 0)}\n\n"
                "Requirements:\n"
                "- Keep subject line under 60 characters\n"
                "- Keep body under 150 words\n"
                "- Include a clear CTA\n"
                "- Be personalized to their role and company\n\n"
                "Return the email in this exact format:\n"
                "SUBJECT: <subject line>\n"
                "BODY:\n<email body>"
            )

            try:
                response = await self._reasoning.generate_response(
                    message=prompt,
                    context={"task": "email_composition", "channel": "email"},
                )

                subject = ""
                body = response
                if "SUBJECT:" in response and "BODY:" in response:
                    parts = response.split("BODY:", 1)
                    subject = parts[0].replace("SUBJECT:", "").strip()
                    body = parts[1].strip()

                return {"subject": subject, "body": body, "type": email_type}
            except Exception:
                log.exception("AI email composition failed, using template")

        # Fallback template-based composition
        name = prospect_context.get("name", "there")
        company = prospect_context.get("company", "your company")
        title = prospect_context.get("title", "")

        templates = {
            "cold_outreach": {
                "subject": f"Quick question about {company}",
                "body": (
                    f"Hi {name.split()[0] if name != 'there' else 'there'},\n\n"
                    f"I noticed your work as {title} at {company} and thought "
                    "we might be able to help with your sales process.\n\n"
                    "Would you be open to a brief 15-minute call this week?\n\n"
                    "Best regards"
                ),
            },
            "follow_up": {
                "subject": f"Following up — {company}",
                "body": (
                    f"Hi {name.split()[0] if name != 'there' else 'there'},\n\n"
                    "I wanted to follow up on my previous message. "
                    "I understand you're busy, but I'd love to share how "
                    "we've helped similar companies.\n\n"
                    "Would a quick call work this week?\n\n"
                    "Best regards"
                ),
            },
            "value_add": {
                "subject": f"Resource for {company}",
                "body": (
                    f"Hi {name.split()[0] if name != 'there' else 'there'},\n\n"
                    "I came across a resource that I think would be valuable "
                    f"for your team at {company}.\n\n"
                    "Happy to share it — just let me know.\n\n"
                    "Best regards"
                ),
            },
        }

        template = templates.get(email_type, templates["cold_outreach"])
        return {**template, "type": email_type}

    async def _compose_linkedin_message(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compose a LinkedIn connection request or message."""
        prospect_id = params.get("prospect_id")
        msg_type = params.get("type", "connection_request")
        prospect_context = await self._get_prospect_context(prospect_id)

        name = prospect_context.get("name", "there")
        first_name = name.split()[0] if name != "there" else "there"
        company = prospect_context.get("company", "your company")
        title = prospect_context.get("title", "your role")

        if msg_type == "connection_request":
            message = (
                f"Hi {first_name}, I see you're working as {title} at {company}. "
                "I'd love to connect and exchange ideas on sales strategy."
            )
        else:
            message = (
                f"Hi {first_name}, thanks for connecting! "
                f"I've been following {company}'s growth and would love to "
                "chat about how we might collaborate. Would you be open to a quick call?"
            )

        return {"message": message, "type": msg_type, "char_count": len(message)}

    async def _create_sequence(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a multi-step outreach sequence for a prospect."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}

        sequence_name = params.get("name", "Default Sequence")

        # Define a standard outreach sequence
        steps = [
            {
                "step": 1,
                "channel": "email",
                "type": "cold_outreach",
                "delay_days": 0,
                "status": "pending",
            },
            {
                "step": 2,
                "channel": "linkedin",
                "type": "connection_request",
                "delay_days": 1,
                "status": "pending",
            },
            {
                "step": 3,
                "channel": "email",
                "type": "follow_up",
                "delay_days": 3,
                "status": "pending",
            },
            {
                "step": 4,
                "channel": "linkedin",
                "type": "direct_message",
                "delay_days": 5,
                "status": "pending",
            },
            {
                "step": 5,
                "channel": "email",
                "type": "value_add",
                "delay_days": 7,
                "status": "pending",
            },
        ]

        try:
            from seal_agent.db.models import OutreachSequence

            async with get_session() as session:
                seq = OutreachSequence(
                    prospect_id=prospect_id,
                    name=sequence_name,
                    status="active",
                    current_step=0,
                    total_steps=len(steps),
                    steps=steps,
                    next_action_at=datetime.now(timezone.utc),
                )
                session.add(seq)
                await session.flush()

                return {
                    "sequence_id": seq.id,
                    "steps": steps,
                    "total_steps": len(steps),
                    "status": "active",
                }
        except Exception:
            log.exception("Error creating sequence")
            seq_id = str(uuid.uuid4())
            return {
                "sequence_id": seq_id,
                "steps": steps,
                "total_steps": len(steps),
                "status": "active",
            }

    async def _execute_sequence_step(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the next step in an outreach sequence."""
        sequence_id = params.get("sequence_id")
        if not sequence_id:
            return {"error": "sequence_id is required"}

        try:
            from seal_agent.db.models import OutreachSequence
            from sqlalchemy import select

            async with get_session() as session:
                result = await session.execute(
                    select(OutreachSequence).where(OutreachSequence.id == sequence_id)
                )
                seq = result.scalar_one_or_none()
                if not seq:
                    return {"error": "Sequence not found", "executed": False}

                if seq.current_step >= seq.total_steps:
                    seq.status = "completed"
                    seq.completed_at = datetime.now(timezone.utc)
                    await session.flush()
                    return {
                        "executed": False,
                        "reason": "Sequence already completed",
                        "step": seq.current_step,
                    }

                steps = seq.steps or []
                current = steps[seq.current_step]
                channel = current["channel"]
                msg_type = current["type"]

                # Compose the message for this step
                if channel == "email":
                    content = await self._compose_email({
                        "prospect_id": seq.prospect_id,
                        "type": msg_type,
                    })
                else:
                    content = await self._compose_linkedin_message({
                        "prospect_id": seq.prospect_id,
                        "type": msg_type,
                    })

                # Log the interaction
                interaction_repo = InteractionRepository(session)
                await interaction_repo.create({
                    "prospect_id": seq.prospect_id,
                    "channel": channel,
                    "direction": "outbound",
                    "subject": content.get("subject"),
                    "content": content.get("body") or content.get("message", ""),
                })

                # Advance the sequence
                current["status"] = "executed"
                seq.current_step += 1
                if seq.current_step < seq.total_steps:
                    next_delay = steps[seq.current_step]["delay_days"]
                    seq.next_action_at = datetime.now(timezone.utc) + timedelta(days=next_delay)
                else:
                    seq.status = "completed"
                    seq.completed_at = datetime.now(timezone.utc)

                await session.flush()

                return {
                    "executed": True,
                    "step": seq.current_step,
                    "channel": channel,
                    "type": msg_type,
                    "content": content,
                    "remaining_steps": seq.total_steps - seq.current_step,
                }
        except Exception:
            log.exception("Error executing sequence step")
            return {"executed": False, "error": "Execution failed"}

    @staticmethod
    async def _get_prospect_context(prospect_id: str | None) -> dict[str, Any]:
        """Fetch prospect context for message personalization."""
        if not prospect_id:
            return {"name": "there", "company": "your company", "title": "", "interaction_count": 0}

        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                prospect = await repo.get_by_id(prospect_id)
                if not prospect:
                    return {"name": "there", "company": "your company", "title": "", "interaction_count": 0}

                interaction_repo = InteractionRepository(session)
                interactions = await interaction_repo.list_by_prospect(prospect_id, limit=5)

                return {
                    "name": f"{prospect.first_name} {prospect.last_name}",
                    "title": prospect.title or "",
                    "company": prospect.company or "your company",
                    "email": prospect.email,
                    "linkedin_url": prospect.linkedin_url,
                    "interaction_count": len(interactions),
                }
        except Exception:
            return {"name": "there", "company": "your company", "title": "", "interaction_count": 0}
