"""Prospect management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from seal_agent.models.prospect import Prospect

router = APIRouter()


@router.get("/")
async def list_prospects() -> dict:
    """List all prospects."""
    # TODO: Implement with database
    return {"prospects": [], "total": 0}


@router.post("/")
async def create_prospect(prospect: Prospect) -> dict:
    """Create a new prospect."""
    # TODO: Implement with database
    return {"id": "", "prospect": prospect.model_dump()}


@router.get("/{prospect_id}")
async def get_prospect(prospect_id: str) -> dict:
    """Get a specific prospect by ID."""
    # TODO: Implement with database
    return {"prospect": None}


@router.post("/{prospect_id}/research")
async def research_prospect(prospect_id: str) -> dict:
    """Trigger AI research on a prospect."""
    # TODO: Implement prospect research via skills
    return {"status": "researching", "prospect_id": prospect_id}
