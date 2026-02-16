"""Deal management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from seal_agent.models.deal import Deal

router = APIRouter()


@router.get("/")
async def list_deals() -> dict:
    """List all deals in the pipeline."""
    # TODO: Implement with database
    return {"deals": [], "total": 0}


@router.post("/")
async def create_deal(deal: Deal) -> dict:
    """Create a new deal."""
    # TODO: Implement with database
    return {"id": "", "deal": deal.model_dump()}


@router.get("/pipeline")
async def get_pipeline() -> dict:
    """Get the full pipeline overview."""
    # TODO: Implement pipeline aggregation
    return {"stages": {}, "total_value": 0, "deal_count": 0}


@router.get("/{deal_id}")
async def get_deal(deal_id: str) -> dict:
    """Get a specific deal by ID."""
    # TODO: Implement with database
    return {"deal": None}


@router.put("/{deal_id}/stage")
async def update_deal_stage(deal_id: str, stage: str) -> dict:
    """Move a deal to a new stage."""
    # TODO: Implement stage transition
    return {"deal_id": deal_id, "new_stage": stage}
