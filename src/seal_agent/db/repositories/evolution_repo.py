"""Evolution/learning data repository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from seal_agent.db.models import EvolutionLog, StrategyScore


class EvolutionRepository:
    """Data access layer for evolution tracking and strategy scoring."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_event(
        self,
        event_type: str,
        strategy_name: str | None = None,
        experiment_id: str | None = None,
        variant: str | None = None,
        outcome: str | None = None,
        score: float | None = None,
        context: dict | None = None,
    ) -> EvolutionLog:
        log_entry = EvolutionLog(
            event_type=event_type,
            strategy_name=strategy_name,
            experiment_id=experiment_id,
            variant=variant,
            outcome=outcome,
            score=score,
            context=context or {},
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry

    async def get_strategy_score(self, strategy_name: str) -> StrategyScore | None:
        result = await self.session.execute(
            select(StrategyScore).where(StrategyScore.strategy_name == strategy_name)
        )
        return result.scalar_one_or_none()

    async def get_all_strategy_scores(self) -> list[StrategyScore]:
        result = await self.session.execute(
            select(StrategyScore).order_by(StrategyScore.effectiveness.desc())
        )
        return list(result.scalars().all())

    async def upsert_strategy_score(
        self,
        strategy_name: str,
        effectiveness: float,
        sample_size: int,
    ) -> StrategyScore:
        existing = await self.get_strategy_score(strategy_name)
        if existing:
            existing.effectiveness = effectiveness
            existing.sample_size = sample_size
            existing.confidence = min(1.0, sample_size / 100.0)
            existing.last_used_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing

        score = StrategyScore(
            strategy_name=strategy_name,
            effectiveness=effectiveness,
            sample_size=sample_size,
            confidence=min(1.0, sample_size / 100.0),
            last_used_at=datetime.now(timezone.utc),
        )
        self.session.add(score)
        await self.session.flush()
        return score

    async def get_experiment_results(self, experiment_id: str) -> dict:
        """Analyze A/B test results for an experiment."""
        result = await self.session.execute(
            select(
                EvolutionLog.variant,
                func.count(EvolutionLog.id).label("total"),
                func.avg(EvolutionLog.score).label("avg_score"),
                func.count(EvolutionLog.id)
                .filter(EvolutionLog.outcome == "success")
                .label("successes"),
            )
            .where(EvolutionLog.experiment_id == experiment_id)
            .group_by(EvolutionLog.variant)
        )
        rows = result.all()

        variants = {}
        for row in rows:
            conversion = (row.successes / row.total * 100) if row.total > 0 else 0
            variants[row.variant] = {
                "total": row.total,
                "avg_score": float(row.avg_score) if row.avg_score else 0,
                "successes": row.successes,
                "conversion_rate": conversion,
            }

        winner = max(variants, key=lambda v: variants[v]["conversion_rate"]) if variants else None
        total_samples = sum(v["total"] for v in variants.values())

        return {
            "experiment_id": experiment_id,
            "variants": variants,
            "winner": winner,
            "total_samples": total_samples,
            "statistically_significant": total_samples >= 100,
        }
