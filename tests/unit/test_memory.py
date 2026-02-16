"""Tests for the Memory Engine."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from seal_agent.core.memory import MemoryEngine


class TestMemoryEngine:
    def setup_method(self) -> None:
        self.engine = MemoryEngine()

    def test_initial_state(self) -> None:
        assert self.engine._initialized is False
        assert self.engine._voyage_client is None

    def test_fallback_embedding_produces_correct_dimensions(self) -> None:
        """Fallback embedding should produce 1024-dimensional vector."""
        embedding = MemoryEngine._fallback_embedding("test text")

        assert len(embedding) == 1024
        assert all(isinstance(v, float) for v in embedding)
        assert all(-1.0 <= v <= 1.0 for v in embedding)

    def test_fallback_embedding_is_deterministic(self) -> None:
        """Same input should produce same embedding."""
        emb1 = MemoryEngine._fallback_embedding("hello world")
        emb2 = MemoryEngine._fallback_embedding("hello world")
        assert emb1 == emb2

    def test_fallback_embedding_differs_for_different_text(self) -> None:
        """Different inputs should produce different embeddings."""
        emb1 = MemoryEngine._fallback_embedding("hello")
        emb2 = MemoryEngine._fallback_embedding("world")
        assert emb1 != emb2

    def test_fallback_embedding_case_insensitive(self) -> None:
        """Embedding should be case-insensitive."""
        emb1 = MemoryEngine._fallback_embedding("Hello World")
        emb2 = MemoryEngine._fallback_embedding("hello world")
        assert emb1 == emb2

    @pytest.mark.asyncio
    async def test_close_resets_state(self) -> None:
        self.engine._initialized = True
        with patch("seal_agent.core.memory.close_db", new_callable=AsyncMock):
            await self.engine.close()
        assert self.engine._initialized is False

    @pytest.mark.asyncio
    async def test_recall_returns_empty_on_error(self) -> None:
        """Recall should return empty list on database errors."""
        with patch("seal_agent.core.memory.get_session", side_effect=Exception("DB down")):
            result = await self.engine.recall("test query")
        assert result == []

    @pytest.mark.asyncio
    async def test_store_interaction_handles_errors(self) -> None:
        """Store interaction should not raise on errors."""
        with patch("seal_agent.core.memory.get_session", side_effect=Exception("DB down")):
            # Should not raise
            await self.engine.store_interaction(
                message="test", response="test", context={}
            )

    @pytest.mark.asyncio
    async def test_store_prospect_returns_none_on_error(self) -> None:
        with patch("seal_agent.core.memory.get_session", side_effect=Exception("DB down")):
            result = await self.engine.store_prospect({"first_name": "Test"})
        assert result is None

    @pytest.mark.asyncio
    async def test_get_prospect_history_returns_empty_on_error(self) -> None:
        with patch("seal_agent.core.memory.get_session", side_effect=Exception("DB down")):
            result = await self.engine.get_prospect_history("test-123")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_patterns_returns_empty_on_error(self) -> None:
        with patch("seal_agent.core.memory.get_session", side_effect=Exception("DB down")):
            result = await self.engine.search_patterns("test_pattern")
        assert result == []
