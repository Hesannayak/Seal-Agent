"""Analytics API routes — Sales metrics, pipeline health, and reports."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from seal_agent.skills.analytics import AnalyticsSkill

router = APIRouter()
_analytics = AnalyticsSkill()


@router.get("/pipeline")
async def pipeline_summary() -> dict[str, Any]:
    """Get pipeline summary with stage breakdown."""
    return await _analytics.execute("pipeline_summary", {})


@router.get("/activity")
async def activity_metrics(
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Get activity metrics for the given time period."""
    return await _analytics.execute("activity_metrics", {"days": days})


@router.get("/funnel")
async def conversion_funnel() -> dict[str, Any]:
    """Get conversion funnel from prospects to closed deals."""
    return await _analytics.execute("conversion_funnel", {})


@router.get("/forecast")
async def sales_forecast() -> dict[str, Any]:
    """Get weighted sales forecast."""
    return await _analytics.execute("forecast", {})


@router.get("/report")
async def performance_report(
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """Get a comprehensive performance report with scores."""
    return await _analytics.execute("performance_report", {"days": days})
