"""Prospect data repository."""

from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from seal_agent.db.models import ProspectRow


class ProspectRepository:
    """Data access layer for prospects."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: dict) -> ProspectRow:
        prospect = ProspectRow(**data)
        self.session.add(prospect)
        await self.session.flush()
        return prospect

    async def get_by_id(self, prospect_id: str) -> ProspectRow | None:
        result = await self.session.execute(
            select(ProspectRow).where(ProspectRow.id == prospect_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> ProspectRow | None:
        result = await self.session.execute(
            select(ProspectRow).where(ProspectRow.email == email)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        status: str | None = None,
        company: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProspectRow], int]:
        query = select(ProspectRow)
        count_query = select(func.count()).select_from(ProspectRow)

        if status:
            query = query.where(ProspectRow.status == status)
            count_query = count_query.where(ProspectRow.status == status)
        if company:
            query = query.where(ProspectRow.company.ilike(f"%{company}%"))
            count_query = count_query.where(ProspectRow.company.ilike(f"%{company}%"))

        query = query.order_by(ProspectRow.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)

        return list(result.scalars().all()), count_result.scalar_one()

    async def update(self, prospect_id: str, data: dict) -> ProspectRow | None:
        prospect = await self.get_by_id(prospect_id)
        if prospect is None:
            return None
        for key, value in data.items():
            if hasattr(prospect, key):
                setattr(prospect, key, value)
        await self.session.flush()
        return prospect

    async def delete(self, prospect_id: str) -> bool:
        prospect = await self.get_by_id(prospect_id)
        if prospect is None:
            return False
        await self.session.delete(prospect)
        await self.session.flush()
        return True

    async def search(self, query: str, limit: int = 20) -> list[ProspectRow]:
        pattern = f"%{query}%"
        result = await self.session.execute(
            select(ProspectRow)
            .where(
                (ProspectRow.first_name.ilike(pattern))
                | (ProspectRow.last_name.ilike(pattern))
                | (ProspectRow.company.ilike(pattern))
                | (ProspectRow.email.ilike(pattern))
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[ProspectRow]:
        result = await self.session.execute(
            select(ProspectRow)
            .where(ProspectRow.status == status)
            .order_by(ProspectRow.lead_score.desc())
        )
        return list(result.scalars().all())
