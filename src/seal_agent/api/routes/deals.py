"""Deal management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from seal_agent.db.database import get_session
from seal_agent.db.repositories.deal_repo import DealRepository
from seal_agent.models.deal import Deal

router = APIRouter()


@router.get("/")
async def list_deals(
    stage: str | None = Query(None, description="Filter by stage"),
    prospect_id: str | None = Query(None, description="Filter by prospect"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """List all deals in the pipeline."""
    async with get_session() as session:
        repo = DealRepository(session)
        deals, total = await repo.list_all(
            stage=stage, prospect_id=prospect_id, limit=limit, offset=offset
        )
        return {
            "deals": [
                {
                    "id": d.id,
                    "title": d.title,
                    "prospect_id": d.prospect_id,
                    "company": d.company,
                    "stage": d.stage,
                    "value": d.value,
                    "currency": d.currency,
                    "probability": d.probability,
                    "expected_close_date": (
                        d.expected_close_date.isoformat() if d.expected_close_date else None
                    ),
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                    "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                }
                for d in deals
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.post("/", status_code=201)
async def create_deal(deal: Deal) -> dict:
    """Create a new deal."""
    async with get_session() as session:
        repo = DealRepository(session)
        data = deal.model_dump(exclude_none=True, exclude={"id", "created_at", "updated_at"})
        row = await repo.create(data)
        return {"id": row.id, "deal": {**data, "id": row.id}}


@router.get("/pipeline")
async def get_pipeline() -> dict:
    """Get the full pipeline overview."""
    async with get_session() as session:
        repo = DealRepository(session)
        return await repo.get_pipeline()


@router.get("/forecast")
async def get_forecast() -> dict:
    """Get weighted pipeline forecast."""
    async with get_session() as session:
        repo = DealRepository(session)
        return await repo.forecast()


@router.get("/at-risk")
async def get_at_risk_deals(
    stale_days: int = Query(14, ge=1, le=90, description="Days since last update"),
) -> dict:
    """Get deals at risk of slipping."""
    async with get_session() as session:
        repo = DealRepository(session)
        deals = await repo.get_at_risk(stale_days=stale_days)
        return {
            "at_risk_deals": [
                {
                    "id": d.id,
                    "title": d.title,
                    "stage": d.stage,
                    "value": d.value,
                    "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                }
                for d in deals
            ],
            "count": len(deals),
            "stale_threshold_days": stale_days,
        }


@router.get("/{deal_id}")
async def get_deal(deal_id: str) -> dict:
    """Get a specific deal by ID."""
    async with get_session() as session:
        repo = DealRepository(session)
        deal = await repo.get_by_id(deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

        return {
            "deal": {
                "id": deal.id,
                "title": deal.title,
                "prospect_id": deal.prospect_id,
                "company": deal.company,
                "stage": deal.stage,
                "value": deal.value,
                "currency": deal.currency,
                "probability": deal.probability,
                "expected_close_date": (
                    deal.expected_close_date.isoformat() if deal.expected_close_date else None
                ),
                "champion_id": deal.champion_id,
                "decision_maker_id": deal.decision_maker_id,
                "competitors": deal.competitors or [],
                "loss_reason": deal.loss_reason,
                "notes": deal.notes,
                "created_at": deal.created_at.isoformat() if deal.created_at else None,
                "updated_at": deal.updated_at.isoformat() if deal.updated_at else None,
                "closed_at": deal.closed_at.isoformat() if deal.closed_at else None,
            }
        }


@router.put("/{deal_id}")
async def update_deal(deal_id: str, deal: Deal) -> dict:
    """Update a deal."""
    async with get_session() as session:
        repo = DealRepository(session)
        data = deal.model_dump(
            exclude_none=True, exclude={"id", "created_at", "updated_at", "closed_at"}
        )
        updated = await repo.update(deal_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Deal not found")

        return {"id": updated.id, "status": "updated"}


@router.put("/{deal_id}/stage")
async def update_deal_stage(deal_id: str, stage: str) -> dict:
    """Move a deal to a new stage."""
    valid_stages = {
        "prospecting", "qualification", "discovery",
        "proposal", "negotiation", "closed_won", "closed_lost",
    }
    if stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage. Must be one of: {', '.join(sorted(valid_stages))}",
        )

    async with get_session() as session:
        repo = DealRepository(session)
        deal = await repo.update_stage(deal_id, stage)
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

        return {
            "deal_id": deal.id,
            "new_stage": deal.stage,
            "closed_at": deal.closed_at.isoformat() if deal.closed_at else None,
        }
