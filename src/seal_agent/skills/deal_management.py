"""Deal Management Skill — Pipeline and deal tracking."""

from __future__ import annotations

from typing import Any

import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.deal_repo import DealRepository
from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()


class DealManagementSkill(BaseSkill):
    """Handles deal pipeline management, tracking, and forecasting."""

    @property
    def name(self) -> str:
        return "deal_management"

    @property
    def description(self) -> str:
        return "Deal pipeline management, stage tracking, and forecasting"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "create_deal": self._create_deal,
            "update_stage": self._update_stage,
            "get_pipeline": self._get_pipeline,
            "forecast": self._forecast,
            "identify_at_risk": self._identify_at_risk,
        }

        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}

        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return ["create_deal", "update_stage", "get_pipeline", "forecast", "identify_at_risk"]

    async def _create_deal(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a new deal in the pipeline."""
        required = ("title", "prospect_id")
        for field in required:
            if field not in params:
                return {"error": f"Missing required field: {field}"}

        try:
            async with get_session() as session:
                repo = DealRepository(session)
                deal = await repo.create({
                    "title": params["title"],
                    "prospect_id": params["prospect_id"],
                    "company": params.get("company"),
                    "stage": params.get("stage", "prospecting"),
                    "value": params.get("value", 0.0),
                    "currency": params.get("currency", "USD"),
                    "probability": params.get("probability", 0.1),
                    "expected_close_date": params.get("expected_close_date"),
                    "notes": params.get("notes"),
                })

                return {
                    "deal_id": deal.id,
                    "stage": deal.stage,
                    "value": deal.value,
                    "status": "created",
                }
        except Exception:
            log.exception("Error creating deal")
            return {"error": "Failed to create deal"}

    async def _update_stage(self, params: dict[str, Any]) -> dict[str, Any]:
        """Move a deal to a new pipeline stage."""
        deal_id = params.get("deal_id")
        new_stage = params.get("stage")

        if not deal_id or not new_stage:
            return {"error": "deal_id and stage are required"}

        valid_stages = {
            "prospecting", "qualification", "discovery",
            "proposal", "negotiation", "closed_won", "closed_lost",
        }
        if new_stage not in valid_stages:
            return {"error": f"Invalid stage: {new_stage}"}

        try:
            async with get_session() as session:
                repo = DealRepository(session)
                deal = await repo.get_by_id(deal_id)
                if not deal:
                    return {"error": "Deal not found"}

                previous_stage = deal.stage
                updated = await repo.update_stage(deal_id, new_stage)

                return {
                    "deal_id": deal_id,
                    "previous_stage": previous_stage,
                    "new_stage": updated.stage,
                    "closed_at": (
                        updated.closed_at.isoformat() if updated.closed_at else None
                    ),
                }
        except Exception:
            log.exception("Error updating deal stage")
            return {"error": "Failed to update stage"}

    async def _get_pipeline(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get the current pipeline overview."""
        try:
            async with get_session() as session:
                repo = DealRepository(session)
                return await repo.get_pipeline()
        except Exception:
            log.exception("Error getting pipeline")
            return {"stages": {}, "total_value": 0, "deal_count": 0}

    async def _forecast(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a sales forecast based on pipeline data."""
        try:
            async with get_session() as session:
                repo = DealRepository(session)
                forecast_data = await repo.forecast()

                # Calculate confidence based on pipeline health
                deal_count = forecast_data["deal_count"]
                if deal_count >= 20:
                    confidence = 0.8
                elif deal_count >= 10:
                    confidence = 0.6
                elif deal_count >= 5:
                    confidence = 0.4
                else:
                    confidence = 0.2

                return {
                    "forecast": forecast_data,
                    "confidence": confidence,
                    "summary": (
                        f"Pipeline has {deal_count} active deals worth "
                        f"${forecast_data['unweighted_total']:,.0f} "
                        f"(weighted: ${forecast_data['weighted_total']:,.0f})"
                    ),
                }
        except Exception:
            log.exception("Error generating forecast")
            return {"forecast": {}, "confidence": 0, "error": "Forecast failed"}

    async def _identify_at_risk(self, params: dict[str, Any]) -> dict[str, Any]:
        """Identify deals at risk of slipping or being lost."""
        stale_days = params.get("stale_days", 14)

        try:
            async with get_session() as session:
                repo = DealRepository(session)
                at_risk = await repo.get_at_risk(stale_days=stale_days)

                deals = []
                total_risk_value = 0.0
                for d in at_risk:
                    risk_factors = []
                    if d.updated_at:
                        from datetime import timezone as tz

                        days_stale = (
                            __import__("datetime").datetime.now(tz.utc) - d.updated_at
                        ).days
                        risk_factors.append(f"No activity for {days_stale} days")

                    if d.probability < 0.3:
                        risk_factors.append(f"Low probability ({d.probability:.0%})")

                    deals.append({
                        "id": d.id,
                        "title": d.title,
                        "stage": d.stage,
                        "value": d.value,
                        "probability": d.probability,
                        "risk_factors": risk_factors,
                        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                    })
                    total_risk_value += d.value

                return {
                    "at_risk_deals": deals,
                    "count": len(deals),
                    "total_risk_value": total_risk_value,
                    "stale_threshold_days": stale_days,
                }
        except Exception:
            log.exception("Error identifying at-risk deals")
            return {"at_risk_deals": [], "count": 0, "error": "Analysis failed"}
