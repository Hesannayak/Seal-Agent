"""Celery tasks for pipeline management — reviews, forecasting, alerts."""

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


@celery_app.task(bind=True, name="seal_agent.tasks.pipeline_tasks.pipeline_review")
def pipeline_review(self):
    """Hourly pipeline review — logs pipeline health metrics."""
    return _run_async(_pipeline_review())


async def _pipeline_review():
    from seal_agent.skills.deal_management import DealManagementSkill

    skill = DealManagementSkill()

    pipeline = await skill.execute("get_pipeline", {})
    forecast = await skill.execute("forecast", {})

    log.info(
        "Pipeline review complete",
        total_value=pipeline.get("total_value", 0),
        deal_count=pipeline.get("deal_count", 0),
        weighted_forecast=forecast.get("forecast", {}).get("weighted_total", 0),
        confidence=forecast.get("confidence", 0),
    )

    return {
        "pipeline": pipeline,
        "forecast": forecast,
    }


@celery_app.task(bind=True, name="seal_agent.tasks.pipeline_tasks.identify_at_risk_deals")
def identify_at_risk_deals(self, stale_days: int = 14):
    """Daily check for deals at risk of slipping."""
    return _run_async(_identify_at_risk_deals(stale_days))


async def _identify_at_risk_deals(stale_days: int):
    from seal_agent.skills.deal_management import DealManagementSkill

    skill = DealManagementSkill()
    result = await skill.execute("identify_at_risk", {"stale_days": stale_days})

    count = result.get("count", 0)
    total_risk = result.get("total_risk_value", 0)

    if count > 0:
        log.warning(
            "At-risk deals detected",
            count=count,
            total_risk_value=total_risk,
        )

        # Send Slack notification if configured
        try:
            from seal_agent.integrations.communication.slack import SlackIntegration
            from seal_agent.config import settings

            if settings.slack_bot_token:
                slack = SlackIntegration()
                connected = await slack.connect({})
                if connected:
                    deals_summary = "\n".join(
                        f"• {d['title']} ({d['stage']}) — ${d['value']:,.0f}"
                        for d in result.get("at_risk_deals", [])[:5]
                    )
                    await slack.execute("send_notification", {
                        "channel": "#sales-alerts",
                        "title": f"At-Risk Deals Alert: {count} deals need attention",
                        "message": f"Total value at risk: ${total_risk:,.0f}\n\n{deals_summary}",
                        "level": "warning",
                    })
                    await slack.disconnect()
        except Exception:
            log.exception("Error sending at-risk Slack notification")
    else:
        log.info("No at-risk deals found")

    return result


@celery_app.task(bind=True, name="seal_agent.tasks.pipeline_tasks.record_deal_outcome")
def record_deal_outcome(self, deal_id: str, outcome: str, metadata: dict | None = None):
    """Record a deal outcome for evolution engine tracking."""
    return _run_async(_record_deal_outcome(deal_id, outcome, metadata))


async def _record_deal_outcome(deal_id: str, outcome: str, metadata: dict | None):
    from seal_agent.core.evolution import EvolutionEngine

    engine = EvolutionEngine()
    try:
        await engine.initialize()
        await engine.record_outcome(deal_id=deal_id, outcome=outcome, metadata=metadata)
        log.info("Deal outcome recorded", deal_id=deal_id, outcome=outcome)
        return {"recorded": True, "deal_id": deal_id, "outcome": outcome}
    except Exception:
        log.exception("Error recording deal outcome")
        return {"recorded": False, "error": "Recording failed"}
