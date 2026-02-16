"""Celery tasks for outreach — sequence execution, email sending."""

import asyncio
from datetime import datetime, timezone

import structlog

from seal_agent.tasks.celery_app import celery_app

log = structlog.get_logger()


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="seal_agent.tasks.outreach_tasks.execute_due_sequences")
def execute_due_sequences(self):
    """Execute all outreach sequence steps that are due."""
    return _run_async(_execute_due_sequences())


async def _execute_due_sequences():
    from sqlalchemy import select

    from seal_agent.db.database import get_session
    from seal_agent.db.models import OutreachSequence
    from seal_agent.skills.outreach import OutreachSkill

    executed = 0

    try:
        async with get_session() as session:
            now = datetime.now(timezone.utc)
            result = await session.execute(
                select(OutreachSequence)
                .where(
                    OutreachSequence.status == "active",
                    OutreachSequence.next_action_at <= now,
                )
                .limit(20)
            )
            due_sequences = result.scalars().all()

            if not due_sequences:
                return {"executed": 0, "message": "No sequences due"}

            skill = OutreachSkill()

            for seq in due_sequences:
                try:
                    result = await skill.execute(
                        "execute_sequence_step",
                        {"sequence_id": seq.id},
                    )
                    if result.get("executed"):
                        executed += 1
                        log.info(
                            "Sequence step executed",
                            sequence_id=seq.id,
                            step=result.get("step"),
                            channel=result.get("channel"),
                        )
                except Exception:
                    log.exception("Error executing sequence step", sequence_id=seq.id)
    except Exception:
        log.exception("Error processing due sequences")

    return {"executed": executed}


@celery_app.task(bind=True, name="seal_agent.tasks.outreach_tasks.send_email")
def send_email(self, prospect_id: str, email_type: str = "cold_outreach"):
    """Compose and send an email to a prospect (triggered on demand)."""
    return _run_async(_send_email(prospect_id, email_type))


async def _send_email(prospect_id: str, email_type: str):
    from seal_agent.skills.outreach import OutreachSkill
    from seal_agent.integrations.communication.email import EmailIntegration

    skill = OutreachSkill()
    composed = await skill.execute("compose_email", {
        "prospect_id": prospect_id,
        "type": email_type,
    })

    # Try to actually send via SMTP
    email_integration = EmailIntegration()
    connected = await email_integration.connect({})

    if connected:
        # Look up prospect email
        from seal_agent.db.database import get_session
        from seal_agent.db.repositories.prospect_repo import ProspectRepository

        async with get_session() as session:
            repo = ProspectRepository(session)
            prospect = await repo.get_by_id(prospect_id)

            if prospect and prospect.email:
                send_result = await email_integration.execute("send_email", {
                    "to": prospect.email,
                    "subject": composed.get("subject", ""),
                    "body": composed.get("body", ""),
                })
                await email_integration.disconnect()
                return {"composed": composed, "sent": send_result.get("sent", False)}

        await email_integration.disconnect()

    return {"composed": composed, "sent": False, "reason": "Email not configured or prospect has no email"}


@celery_app.task(
    bind=True,
    name="seal_agent.tasks.outreach_tasks.create_and_start_sequence",
)
def create_and_start_sequence(self, prospect_id: str, sequence_name: str = "Default Sequence"):
    """Create an outreach sequence and execute the first step."""
    return _run_async(_create_and_start_sequence(prospect_id, sequence_name))


async def _create_and_start_sequence(prospect_id: str, sequence_name: str):
    from seal_agent.skills.outreach import OutreachSkill

    skill = OutreachSkill()

    # Create the sequence
    seq_result = await skill.execute("create_sequence", {
        "prospect_id": prospect_id,
        "name": sequence_name,
    })

    if "error" in seq_result:
        return seq_result

    # Execute the first step immediately
    step_result = await skill.execute("execute_sequence_step", {
        "sequence_id": seq_result["sequence_id"],
    })

    return {
        "sequence": seq_result,
        "first_step": step_result,
    }
