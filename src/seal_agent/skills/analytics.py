"""Analytics Skill — Sales analytics and forecasting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.deal_repo import DealRepository
from seal_agent.db.repositories.prospect_repo import ProspectRepository
from seal_agent.db.repositories.interaction_repo import InteractionRepository
from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()


class AnalyticsSkill(BaseSkill):
    """Provides sales analytics, performance metrics, and forecasting."""

    @property
    def name(self) -> str:
        return "analytics"

    @property
    def description(self) -> str:
        return "Sales analytics, performance metrics, pipeline health, and forecasting"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "pipeline_summary": self._pipeline_summary,
            "activity_metrics": self._activity_metrics,
            "conversion_funnel": self._conversion_funnel,
            "performance_report": self._performance_report,
            "forecast": self._forecast,
        }
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return [
            "pipeline_summary", "activity_metrics", "conversion_funnel",
            "performance_report", "forecast",
        ]

    async def _pipeline_summary(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get a comprehensive pipeline summary."""
        try:
            async with get_session() as session:
                repo = DealRepository(session)
                pipeline = await repo.get_pipeline()

                # Enhance with additional analysis
                stages = pipeline.get("stages", {})
                total_value = pipeline.get("total_value", 0)
                deal_count = pipeline.get("deal_count", 0)

                # Calculate stage distribution
                stage_analysis = {}
                for stage_name, stage_data in stages.items():
                    count = stage_data.get("count", 0)
                    value = stage_data.get("value", 0)
                    stage_analysis[stage_name] = {
                        "count": count,
                        "value": value,
                        "pct_of_pipeline": round((value / total_value * 100) if total_value else 0, 1),
                        "avg_deal_size": round(value / count, 2) if count else 0,
                    }

                return {
                    "total_pipeline_value": total_value,
                    "total_deals": deal_count,
                    "average_deal_size": round(total_value / deal_count, 2) if deal_count else 0,
                    "stages": stage_analysis,
                    "health": (
                        "healthy" if deal_count >= 10
                        else "building" if deal_count >= 5
                        else "needs_attention"
                    ),
                }
        except Exception:
            log.exception("Error generating pipeline summary")
            return {"error": "Pipeline summary failed"}

    async def _activity_metrics(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get activity metrics for a time period."""
        days = params.get("days", 30)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            async with get_session() as session:
                interaction_repo = InteractionRepository(session)

                # Get all recent interactions
                from sqlalchemy import select, func
                from seal_agent.db.models import InteractionRow

                # Total interactions
                result = await session.execute(
                    select(func.count(InteractionRow.id)).where(
                        InteractionRow.created_at >= cutoff
                    )
                )
                total_interactions = result.scalar() or 0

                # By channel
                result = await session.execute(
                    select(InteractionRow.channel, func.count(InteractionRow.id))
                    .where(InteractionRow.created_at >= cutoff)
                    .group_by(InteractionRow.channel)
                )
                by_channel = {row[0]: row[1] for row in result.all()}

                # By direction
                result = await session.execute(
                    select(InteractionRow.direction, func.count(InteractionRow.id))
                    .where(InteractionRow.created_at >= cutoff)
                    .group_by(InteractionRow.direction)
                )
                by_direction = {row[0]: row[1] for row in result.all()}

                # Reply rate
                result = await session.execute(
                    select(func.count(InteractionRow.id)).where(
                        InteractionRow.created_at >= cutoff,
                        InteractionRow.replied.is_(True),
                    )
                )
                replies = result.scalar() or 0

                # Open rate
                result = await session.execute(
                    select(func.count(InteractionRow.id)).where(
                        InteractionRow.created_at >= cutoff,
                        InteractionRow.opened.is_(True),
                    )
                )
                opens = result.scalar() or 0

                outbound = by_direction.get("outbound", 0)

                return {
                    "period_days": days,
                    "total_interactions": total_interactions,
                    "by_channel": by_channel,
                    "by_direction": by_direction,
                    "outbound_count": outbound,
                    "reply_count": replies,
                    "open_count": opens,
                    "reply_rate": round(replies / outbound * 100, 1) if outbound else 0,
                    "open_rate": round(opens / outbound * 100, 1) if outbound else 0,
                    "daily_average": round(total_interactions / days, 1) if days else 0,
                }
        except Exception:
            log.exception("Error calculating activity metrics")
            return {"error": "Activity metrics failed"}

    async def _conversion_funnel(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze the conversion funnel from prospect to closed deal."""
        try:
            async with get_session() as session:
                prospect_repo = ProspectRepository(session)
                deal_repo = DealRepository(session)

                # Count prospects by status
                from sqlalchemy import select, func
                from seal_agent.db.models import ProspectRow, DealRow

                result = await session.execute(
                    select(ProspectRow.status, func.count(ProspectRow.id))
                    .group_by(ProspectRow.status)
                )
                prospect_counts = {row[0]: row[1] for row in result.all()}

                # Count deals by stage
                result = await session.execute(
                    select(DealRow.stage, func.count(DealRow.id))
                    .group_by(DealRow.stage)
                )
                deal_counts = {row[0]: row[1] for row in result.all()}

                total_prospects = sum(prospect_counts.values())
                total_deals = sum(deal_counts.values())
                won = deal_counts.get("closed_won", 0)
                lost = deal_counts.get("closed_lost", 0)

                funnel = [
                    {"stage": "new_leads", "count": prospect_counts.get("new", 0)},
                    {"stage": "qualified", "count": prospect_counts.get("qualified", 0)},
                    {"stage": "contacted", "count": prospect_counts.get("contacted", 0)},
                    {"stage": "engaged", "count": prospect_counts.get("engaged", 0)},
                    {"stage": "opportunity", "count": prospect_counts.get("opportunity", 0) + total_deals},
                    {"stage": "closed_won", "count": won},
                    {"stage": "closed_lost", "count": lost},
                ]

                return {
                    "funnel": funnel,
                    "total_prospects": total_prospects,
                    "total_deals": total_deals,
                    "win_rate": round(won / (won + lost) * 100, 1) if (won + lost) else 0,
                    "prospect_to_deal_rate": round(total_deals / total_prospects * 100, 1) if total_prospects else 0,
                }
        except Exception:
            log.exception("Error analyzing funnel")
            return {"error": "Funnel analysis failed"}

    async def _performance_report(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a comprehensive performance report."""
        days = params.get("days", 30)

        pipeline = await self._pipeline_summary({})
        activity = await self._activity_metrics({"days": days})
        funnel = await self._conversion_funnel({})

        # Compile scores
        scores = {}
        if not pipeline.get("error"):
            deal_count = pipeline.get("total_deals", 0)
            scores["pipeline_health"] = min(100, deal_count * 10)

        if not activity.get("error"):
            reply_rate = activity.get("reply_rate", 0)
            daily_avg = activity.get("daily_average", 0)
            scores["engagement"] = min(100, reply_rate * 2)
            scores["activity_level"] = min(100, daily_avg * 10)

        if not funnel.get("error"):
            win_rate = funnel.get("win_rate", 0)
            scores["win_rate"] = min(100, win_rate * 2)

        overall = round(sum(scores.values()) / len(scores), 1) if scores else 0

        return {
            "period_days": days,
            "pipeline": pipeline,
            "activity": activity,
            "funnel": funnel,
            "scores": scores,
            "overall_score": overall,
            "grade": (
                "A" if overall >= 80
                else "B" if overall >= 60
                else "C" if overall >= 40
                else "D"
            ),
        }

    async def _forecast(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a weighted sales forecast."""
        try:
            async with get_session() as session:
                repo = DealRepository(session)
                forecast_data = await repo.forecast()

                deal_count = forecast_data.get("deal_count", 0)
                weighted = forecast_data.get("weighted_total", 0)
                unweighted = forecast_data.get("unweighted_total", 0)

                # Confidence based on pipeline maturity
                if deal_count >= 20:
                    confidence = "high"
                    confidence_pct = 80
                elif deal_count >= 10:
                    confidence = "medium"
                    confidence_pct = 60
                else:
                    confidence = "low"
                    confidence_pct = 30

                return {
                    "forecast": {
                        "weighted_total": weighted,
                        "unweighted_total": unweighted,
                        "deal_count": deal_count,
                        "best_case": unweighted,
                        "expected": weighted,
                        "worst_case": round(weighted * 0.6, 2),
                    },
                    "confidence": confidence,
                    "confidence_percentage": confidence_pct,
                    "summary": (
                        f"Forecast: ${weighted:,.0f} weighted pipeline across {deal_count} deals. "
                        f"Confidence: {confidence}."
                    ),
                }
        except Exception:
            log.exception("Error generating forecast")
            return {"error": "Forecast failed"}
