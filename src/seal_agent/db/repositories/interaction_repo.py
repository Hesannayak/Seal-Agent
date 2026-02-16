"""Interaction data repository."""

from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from seal_agent.db.models import InteractionRow


class InteractionRepository:
    """Data access layer for interactions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: dict) -> InteractionRow:
        interaction = InteractionRow(**data)
        self.session.add(interaction)
        await self.session.flush()
        return interaction

    async def get_by_id(self, interaction_id: str) -> InteractionRow | None:
        result = await self.session.execute(
            select(InteractionRow).where(InteractionRow.id == interaction_id)
        )
        return result.scalar_one_or_none()

    async def list_by_prospect(
        self, prospect_id: str, limit: int = 50
    ) -> list[InteractionRow]:
        result = await self.session.execute(
            select(InteractionRow)
            .where(InteractionRow.prospect_id == prospect_id)
            .order_by(InteractionRow.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_deal(self, deal_id: str, limit: int = 50) -> list[InteractionRow]:
        result = await self.session.execute(
            select(InteractionRow)
            .where(InteractionRow.deal_id == deal_id)
            .order_by(InteractionRow.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_recent_inbound(self, limit: int = 10) -> list[InteractionRow]:
        """Get recent inbound interactions that have no response yet."""
        result = await self.session.execute(
            select(InteractionRow)
            .where(
                InteractionRow.direction == "inbound",
                InteractionRow.response.is_(None),
            )
            .order_by(InteractionRow.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats(self, prospect_id: str | None = None) -> dict:
        """Get interaction statistics."""
        query = select(
            InteractionRow.channel,
            func.count(InteractionRow.id).label("total"),
            func.sum(InteractionRow.opened.cast(int)).label("opened"),
            func.sum(InteractionRow.replied.cast(int)).label("replied"),
        )
        if prospect_id:
            query = query.where(InteractionRow.prospect_id == prospect_id)
        query = query.group_by(InteractionRow.channel)

        result = await self.session.execute(query)
        rows = result.all()
        stats = {}
        for row in rows:
            stats[row.channel] = {
                "total": row.total,
                "opened": int(row.opened or 0),
                "replied": int(row.replied or 0),
                "open_rate": (int(row.opened or 0) / row.total * 100) if row.total > 0 else 0,
                "reply_rate": (int(row.replied or 0) / row.total * 100) if row.total > 0 else 0,
            }
        return stats
