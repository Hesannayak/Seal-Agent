"""Tests for the Evolution Engine."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from seal_agent.core.evolution import EvolutionEngine


class TestEvolutionEngine:
    def setup_method(self) -> None:
        self.engine = EvolutionEngine()

    def test_initial_state(self) -> None:
        assert self.engine._initialized is False
        assert self.engine._strategy_cache == {}

    @pytest.mark.asyncio
    async def test_initialize_sets_initialized(self) -> None:
        with patch("seal_agent.core.evolution.get_session"):
            await self.engine.initialize()
        assert self.engine._initialized is True

    @pytest.mark.asyncio
    async def test_close_resets_initialized(self) -> None:
        self.engine._initialized = True
        await self.engine.close()
        assert self.engine._initialized is False

    @pytest.mark.asyncio
    async def test_get_strategy_scores_returns_cache(self) -> None:
        self.engine._strategy_cache = {"direct_outreach": 0.75, "warm_intro": 0.85}

        scores = await self.engine.get_strategy_scores()

        assert scores["direct_outreach"] == 0.75
        assert scores["warm_intro"] == 0.85

    @pytest.mark.asyncio
    async def test_get_strategy_scores_empty_cache_queries_db(self) -> None:
        mock_score = MagicMock()
        mock_score.strategy_name = "test_strategy"
        mock_score.effectiveness = 0.6

        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.get_all_strategy_scores = AsyncMock(return_value=[mock_score])

        with patch("seal_agent.core.evolution.get_session") as mock_gs:
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("seal_agent.core.evolution.EvolutionRepository", return_value=mock_repo):
                scores = await self.engine.get_strategy_scores()

        assert scores["test_strategy"] == 0.6

    @pytest.mark.asyncio
    async def test_log_interaction_does_not_raise(self) -> None:
        """Evolution engine should silently handle logging failures."""
        with patch("seal_agent.core.evolution.get_session", side_effect=Exception("DB down")):
            # Should not raise
            await self.engine.log_interaction(
                message="test", response="test", context={}
            )

    @pytest.mark.asyncio
    async def test_record_outcome_logs_event(self) -> None:
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.log_event = AsyncMock()

        with patch("seal_agent.core.evolution.get_session") as mock_gs:
            mock_gs.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("seal_agent.core.evolution.EvolutionRepository", return_value=mock_repo):
                await self.engine.record_outcome(
                    deal_id="deal-123",
                    outcome="won",
                )

        mock_repo.log_event.assert_called_once()
