"""Evolution Engine — Self-learning and adaptation system."""

from __future__ import annotations

import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.evolution_repo import EvolutionRepository
from seal_agent.db.repositories.interaction_repo import InteractionRepository

log = structlog.get_logger()


class EvolutionEngine:
    """Manages the agent's self-learning and continuous improvement.

    Tracks interaction outcomes, runs A/B tests, performs win/loss analysis,
    and adjusts strategies based on data.
    """

    def __init__(self) -> None:
        self._initialized = False
        self._strategy_cache: dict[str, float] = {}

    async def initialize(self) -> None:
        """Initialize the evolution tracking system."""
        log.info("Initializing evolution engine")
        try:
            async with get_session() as session:
                repo = EvolutionRepository(session)
                scores = await repo.get_all_strategy_scores()
                self._strategy_cache = {
                    s.strategy_name: s.effectiveness for s in scores
                }
            log.info(
                "Loaded strategy scores",
                count=len(self._strategy_cache),
            )
        except Exception:
            log.warning("Could not load strategy scores, starting fresh")
        self._initialized = True

    async def close(self) -> None:
        """Shut down the evolution engine."""
        log.info("Closing evolution engine")
        self._initialized = False

    async def log_interaction(
        self,
        message: str,
        response: str,
        context: dict | None = None,
    ) -> None:
        """Log an interaction for analysis."""
        try:
            async with get_session() as session:
                repo = EvolutionRepository(session)
                strategy = context.get("strategy") if context else None
                experiment = context.get("experiment_id") if context else None
                variant = context.get("variant") if context else None

                await repo.log_event(
                    event_type="interaction",
                    strategy_name=strategy,
                    experiment_id=experiment,
                    variant=variant,
                    context={
                        "message_length": len(message),
                        "response_length": len(response),
                        "channel": context.get("channel") if context else None,
                        "prospect_id": context.get("prospect_id") if context else None,
                    },
                )
        except Exception:
            log.exception("Error logging interaction for evolution")

    async def record_outcome(
        self,
        deal_id: str,
        outcome: str,
        metadata: dict | None = None,
    ) -> None:
        """Record a deal outcome (won/lost) for win/loss analysis."""
        log.info("Recording deal outcome", deal_id=deal_id, outcome=outcome)

        try:
            async with get_session() as session:
                repo = EvolutionRepository(session)

                # Log the outcome event
                await repo.log_event(
                    event_type="deal_outcome",
                    outcome=outcome,
                    score=1.0 if outcome == "won" else 0.0,
                    context={
                        "deal_id": deal_id,
                        **(metadata or {}),
                    },
                )

                # Update strategy scores if strategies were used
                if metadata and "strategies_used" in metadata:
                    for strategy_name in metadata["strategies_used"]:
                        existing = await repo.get_strategy_score(strategy_name)
                        if existing:
                            # Incremental update: weighted average
                            new_sample = existing.sample_size + 1
                            new_score = outcome == "won"
                            new_effectiveness = (
                                existing.effectiveness * existing.sample_size + float(new_score)
                            ) / new_sample
                            await repo.upsert_strategy_score(
                                strategy_name, new_effectiveness, new_sample
                            )
                            self._strategy_cache[strategy_name] = new_effectiveness
                        else:
                            effectiveness = 1.0 if outcome == "won" else 0.0
                            await repo.upsert_strategy_score(strategy_name, effectiveness, 1)
                            self._strategy_cache[strategy_name] = effectiveness
        except Exception:
            log.exception("Error recording outcome")

    async def get_strategy_scores(self) -> dict[str, float]:
        """Get current effectiveness scores for all strategies."""
        if self._strategy_cache:
            return dict(self._strategy_cache)

        try:
            async with get_session() as session:
                repo = EvolutionRepository(session)
                scores = await repo.get_all_strategy_scores()
                result = {s.strategy_name: s.effectiveness for s in scores}
                self._strategy_cache = result
                return result
        except Exception:
            log.exception("Error getting strategy scores")
            return {}

    async def suggest_improvements(self) -> list[dict]:
        """Analyze recent performance and suggest improvements."""
        suggestions: list[dict] = []

        try:
            async with get_session() as session:
                # Check interaction stats
                interaction_repo = InteractionRepository(session)
                stats = await interaction_repo.get_stats()

                for channel, channel_stats in stats.items():
                    if channel_stats["reply_rate"] < 5.0 and channel_stats["total"] >= 20:
                        suggestions.append({
                            "type": "low_reply_rate",
                            "channel": channel,
                            "current_rate": channel_stats["reply_rate"],
                            "suggestion": (
                                f"Reply rate on {channel} is {channel_stats['reply_rate']:.1f}%. "
                                "Consider revising messaging approach or subject lines."
                            ),
                            "priority": "high",
                        })

                    if channel_stats["open_rate"] < 20.0 and channel_stats["total"] >= 20:
                        suggestions.append({
                            "type": "low_open_rate",
                            "channel": channel,
                            "current_rate": channel_stats["open_rate"],
                            "suggestion": (
                                f"Open rate on {channel} is {channel_stats['open_rate']:.1f}%. "
                                "Consider testing new subject lines."
                            ),
                            "priority": "medium",
                        })

                # Check strategy scores
                evo_repo = EvolutionRepository(session)
                strategy_scores = await evo_repo.get_all_strategy_scores()
                for score in strategy_scores:
                    if score.effectiveness < 0.2 and score.sample_size >= 50:
                        suggestions.append({
                            "type": "underperforming_strategy",
                            "strategy": score.strategy_name,
                            "effectiveness": score.effectiveness,
                            "sample_size": score.sample_size,
                            "suggestion": (
                                f"Strategy '{score.strategy_name}' has only "
                                f"{score.effectiveness:.0%} effectiveness over "
                                f"{score.sample_size} samples. Consider retiring it."
                            ),
                            "priority": "high",
                        })
        except Exception:
            log.exception("Error generating improvement suggestions")

        return suggestions

    async def run_ab_analysis(self, experiment_id: str) -> dict:
        """Analyze results of an A/B test."""
        try:
            async with get_session() as session:
                repo = EvolutionRepository(session)
                return await repo.get_experiment_results(experiment_id)
        except Exception:
            log.exception("Error running A/B analysis")
            return {"error": "Analysis failed", "experiment_id": experiment_id}
