"""Deal data repository."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from seal_agent.db.models import DealRow


class DealRepository:
    """Data access layer for deals."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: dict) -> DealRow:
        deal = DealRow(**data)
        self.session.add(deal)
        await self.session.flush()
        return deal

    async def get_by_id(self, deal_id: str) -> DealRow | None:
        result = await self.session.execute(
            select(DealRow).where(DealRow.id == deal_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        stage: str | None = None,
        prospect_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DealRow], int]:
        query = select(DealRow)
        count_query = select(func.count()).select_from(DealRow)

        if stage:
            query = query.where(DealRow.stage == stage)
            count_query = count_query.where(DealRow.stage == stage)
        if prospect_id:
            query = query.where(DealRow.prospect_id == prospect_id)
            count_query = count_query.where(DealRow.prospect_id == prospect_id)

        query = query.order_by(DealRow.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)

        return list(result.scalars().all()), count_result.scalar_one()

    async def update(self, deal_id: str, data: dict) -> DealRow | None:
        deal = await self.get_by_id(deal_id)
        if deal is None:
            return None
        for key, value in data.items():
            if hasattr(deal, key):
                setattr(deal, key, value)
        await self.session.flush()
        return deal

    async def update_stage(self, deal_id: str, new_stage: str) -> DealRow | None:
        deal = await self.get_by_id(deal_id)
        if deal is None:
            return None
        previous_stage = deal.stage
        deal.stage = new_stage
        if new_stage in ("closed_won", "closed_lost"):
            deal.closed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return deal

    async def get_pipeline(self) -> dict:
        """Get pipeline summary grouped by stage."""
        result = await self.session.execute(
            select(
                DealRow.stage,
                func.count(DealRow.id).label("count"),
                func.coalesce(func.sum(DealRow.value), 0).label("total_value"),
                func.coalesce(func.avg(DealRow.probability), 0).label("avg_probability"),
            )
            .where(DealRow.stage.notin_(["closed_won", "closed_lost"]))
            .group_by(DealRow.stage)
        )
        rows = result.all()
        stages = {}
        total_value = 0.0
        deal_count = 0
        for row in rows:
            stages[row.stage] = {
                "count": row.count,
                "total_value": float(row.total_value),
                "avg_probability": float(row.avg_probability),
            }
            total_value += float(row.total_value)
            deal_count += row.count
        return {"stages": stages, "total_value": total_value, "deal_count": deal_count}

    async def get_at_risk(self, stale_days: int = 14) -> list[DealRow]:
        """Find deals that haven't been updated in stale_days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
        result = await self.session.execute(
            select(DealRow)
            .where(
                DealRow.stage.notin_(["closed_won", "closed_lost"]),
                DealRow.updated_at < cutoff,
            )
            .order_by(DealRow.value.desc())
        )
        return list(result.scalars().all())

    async def forecast(self) -> dict:
        """Generate a weighted pipeline forecast."""
        result = await self.session.execute(
            select(DealRow).where(
                DealRow.stage.notin_(["closed_won", "closed_lost"])
            )
        )
        deals = list(result.scalars().all())

        total_weighted = sum(d.value * d.probability for d in deals)
        total_unweighted = sum(d.value for d in deals)
        by_stage: dict[str, float] = {}
        for d in deals:
            by_stage.setdefault(d.stage, 0.0)
            by_stage[d.stage] += d.value * d.probability

        return {
            "weighted_total": total_weighted,
            "unweighted_total": total_unweighted,
            "by_stage": by_stage,
            "deal_count": len(deals),
        }
