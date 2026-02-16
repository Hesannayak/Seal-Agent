"""Celery tasks for prospecting — lead scoring, qualification, research."""

import asyncio

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


@celery_app.task(bind=True, name="seal_agent.tasks.prospecting_tasks.score_new_leads")
def score_new_leads(self):
    """Find and score all unscored new leads."""
    return _run_async(_score_new_leads())


async def _score_new_leads():
    from seal_agent.db.database import get_session
    from seal_agent.db.repositories.prospect_repo import ProspectRepository
    from seal_agent.skills.prospecting import ProspectingSkill

    skill = ProspectingSkill()
    scored = 0

    try:
        async with get_session() as session:
            repo = ProspectRepository(session)
            prospects, _ = await repo.list_all(status="new", limit=50)

            for prospect in prospects:
                if prospect.lead_score == 0:
                    result = await skill.execute(
                        "score_lead", {"prospect_id": prospect.id}
                    )
                    scored += 1
                    log.info(
                        "Scored lead",
                        prospect_id=prospect.id,
                        score=result.get("score"),
                    )
    except Exception:
        log.exception("Error scoring leads")

    return {"scored": scored}


@celery_app.task(bind=True, name="seal_agent.tasks.prospecting_tasks.research_prospect")
def research_prospect(self, prospect_id: str):
    """Run AI research on a specific prospect (triggered on demand)."""
    return _run_async(_research_prospect(prospect_id))


async def _research_prospect(prospect_id: str):
    from seal_agent.skills.prospecting import ProspectingSkill

    skill = ProspectingSkill()
    result = await skill.execute("research_prospect", {"prospect_id": prospect_id})
    log.info("Prospect research complete", prospect_id=prospect_id)
    return result


@celery_app.task(bind=True, name="seal_agent.tasks.prospecting_tasks.qualify_lead")
def qualify_lead(self, prospect_id: str, meddic: dict | None = None):
    """Qualify a lead using MEDDIC framework (triggered on demand)."""
    return _run_async(_qualify_lead(prospect_id, meddic or {}))


async def _qualify_lead(prospect_id: str, meddic: dict):
    from seal_agent.skills.prospecting import ProspectingSkill

    skill = ProspectingSkill()
    result = await skill.execute("qualify_lead", {
        "prospect_id": prospect_id,
        "meddic": meddic,
    })
    log.info("Lead qualified", prospect_id=prospect_id, qualified=result.get("qualified"))
    return result
