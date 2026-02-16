"""Prospect management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from seal_agent.db.database import get_session
from seal_agent.db.repositories.prospect_repo import ProspectRepository
from seal_agent.models.prospect import Prospect

router = APIRouter()


@router.get("/")
async def list_prospects(
    status: str | None = Query(None, description="Filter by status"),
    company: str | None = Query(None, description="Filter by company"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """List all prospects with optional filters."""
    async with get_session() as session:
        repo = ProspectRepository(session)
        prospects, total = await repo.list_all(
            status=status, company=company, limit=limit, offset=offset
        )
        return {
            "prospects": [
                {
                    "id": p.id,
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "email": p.email,
                    "phone": p.phone,
                    "title": p.title,
                    "company": p.company,
                    "linkedin_url": p.linkedin_url,
                    "status": p.status,
                    "sentiment": p.sentiment,
                    "lead_score": p.lead_score,
                    "tags": p.tags or [],
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in prospects
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.post("/", status_code=201)
async def create_prospect(prospect: Prospect) -> dict:
    """Create a new prospect."""
    async with get_session() as session:
        repo = ProspectRepository(session)

        if prospect.email:
            existing = await repo.get_by_email(prospect.email)
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Prospect with email {prospect.email} already exists",
                )

        data = prospect.model_dump(exclude_none=True, exclude={"id", "created_at", "updated_at"})
        row = await repo.create(data)

        return {"id": row.id, "prospect": {**data, "id": row.id}}


@router.get("/{prospect_id}")
async def get_prospect(prospect_id: str) -> dict:
    """Get a specific prospect by ID."""
    async with get_session() as session:
        repo = ProspectRepository(session)
        prospect = await repo.get_by_id(prospect_id)
        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")

        return {
            "prospect": {
                "id": prospect.id,
                "first_name": prospect.first_name,
                "last_name": prospect.last_name,
                "email": prospect.email,
                "phone": prospect.phone,
                "title": prospect.title,
                "company": prospect.company,
                "linkedin_url": prospect.linkedin_url,
                "status": prospect.status,
                "sentiment": prospect.sentiment,
                "lead_score": prospect.lead_score,
                "preferred_channel": prospect.preferred_channel,
                "timezone": prospect.timezone,
                "tags": prospect.tags or [],
                "notes": prospect.notes,
                "created_at": prospect.created_at.isoformat() if prospect.created_at else None,
                "updated_at": prospect.updated_at.isoformat() if prospect.updated_at else None,
            }
        }


@router.put("/{prospect_id}")
async def update_prospect(prospect_id: str, prospect: Prospect) -> dict:
    """Update a prospect."""
    async with get_session() as session:
        repo = ProspectRepository(session)
        data = prospect.model_dump(exclude_none=True, exclude={"id", "created_at", "updated_at"})
        updated = await repo.update(prospect_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Prospect not found")

        return {"id": updated.id, "status": "updated"}


@router.delete("/{prospect_id}", status_code=204)
async def delete_prospect(prospect_id: str) -> None:
    """Delete a prospect."""
    async with get_session() as session:
        repo = ProspectRepository(session)
        prospect = await repo.get_by_id(prospect_id)
        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")
        await repo.delete(prospect_id)


@router.post("/{prospect_id}/research")
async def research_prospect(prospect_id: str) -> dict:
    """Trigger AI research on a prospect."""
    async with get_session() as session:
        repo = ProspectRepository(session)
        prospect = await repo.get_by_id(prospect_id)
        if not prospect:
            raise HTTPException(status_code=404, detail="Prospect not found")

        await repo.update(prospect_id, {"status": "researching"})

    return {"status": "researching", "prospect_id": prospect_id}


@router.get("/{prospect_id}/interactions")
async def get_prospect_interactions(
    prospect_id: str,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Get interaction history for a prospect."""
    from seal_agent.db.repositories.interaction_repo import InteractionRepository

    async with get_session() as session:
        repo = InteractionRepository(session)
        interactions = await repo.list_by_prospect(prospect_id, limit=limit)
        return {
            "prospect_id": prospect_id,
            "interactions": [
                {
                    "id": i.id,
                    "channel": i.channel,
                    "direction": i.direction,
                    "subject": i.subject,
                    "content": i.content,
                    "sentiment": i.sentiment,
                    "opened": i.opened,
                    "replied": i.replied,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in interactions
            ],
            "total": len(interactions),
        }
