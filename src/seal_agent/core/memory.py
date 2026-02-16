"""Memory Engine — Long-term memory management for the agent."""

from __future__ import annotations

import httpx
import structlog

from seal_agent.config import settings
from seal_agent.db.database import get_session, init_db, close_db
from seal_agent.db.repositories.memory_repo import MemoryRepository
from seal_agent.db.repositories.interaction_repo import InteractionRepository
from seal_agent.db.repositories.prospect_repo import ProspectRepository

log = structlog.get_logger()


class MemoryEngine:
    """Manages the agent's long-term memory using PostgreSQL + pgvector.

    Memory types:
    - Prospect memory: Everything known about a specific person
    - Deal memory: Full context of active and closed deals
    - Pattern memory: Aggregate insights from interactions
    - Company memory: Organization-level knowledge
    - Relationship memory: Network and connections
    """

    def __init__(self) -> None:
        self._initialized = False
        self._voyage_client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        """Initialize the memory subsystem and database connections."""
        log.info("Initializing memory engine")
        await init_db()

        voyage_key = settings.voyage_api_key or settings.anthropic_api_key
        if voyage_key:
            self._voyage_client = httpx.AsyncClient(
                base_url="https://api.voyageai.com/v1",
                headers={
                    "Authorization": f"Bearer {voyage_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            log.info("Voyage embedding client initialized", model=settings.voyage_model)
        else:
            log.warning("No Voyage/Anthropic API key — using fallback embeddings")

        self._initialized = True
        log.info("Memory engine initialized")

    async def close(self) -> None:
        """Close database connections and HTTP clients."""
        log.info("Closing memory engine")
        if self._voyage_client:
            await self._voyage_client.aclose()
            self._voyage_client = None
        await close_db()
        self._initialized = False

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector using the Voyage API.

        Falls back to a deterministic hash-based embedding if the API is
        unavailable or unconfigured.
        """
        if not self._voyage_client:
            return self._fallback_embedding(text)

        try:
            response = await self._voyage_client.post(
                "/embeddings",
                json={
                    "model": settings.voyage_model,
                    "input": [text[:8000]],  # Voyage supports up to 16k tokens
                    "input_type": "document",
                    "output_dimension": settings.voyage_dimensions,
                },
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]
            return embedding
        except Exception:
            log.warning("Voyage API unavailable, using fallback embedding")
            return self._fallback_embedding(text)

    @staticmethod
    def _fallback_embedding(text: str) -> list[float]:
        """Generate a deterministic hash-based embedding as a fallback.

        This is a simple fallback — replace with a real embedding model in production.
        """
        import hashlib

        # Create a 1024-dimensional pseudo-embedding from text hash
        text_bytes = text.lower().encode("utf-8")
        embedding = []
        for i in range(1024):
            chunk = text_bytes + i.to_bytes(4, "big")
            h = hashlib.sha256(chunk).digest()
            val = (int.from_bytes(h[:4], "big") / (2**32)) * 2 - 1  # Normalize to [-1, 1]
            embedding.append(val)
        return embedding

    async def recall(self, query: str, context: dict | None = None) -> list[dict]:
        """Retrieve relevant memories for a given query.

        Combines vector semantic search with structured data lookups.
        """
        log.debug("Recalling memories", query=query[:50])
        memories: list[dict] = []

        try:
            query_embedding = await self._get_embedding(query)

            async with get_session() as session:
                mem_repo = MemoryRepository(session)

                # Semantic search across all memory types
                memory_type = None
                if context and "prospect_id" in context:
                    memory_type = "interaction"

                similar = await mem_repo.search_similar(
                    embedding=query_embedding,
                    memory_type=memory_type,
                    limit=10,
                    min_similarity=0.3,
                )
                memories.extend(similar)

                # If we have a prospect context, also fetch their interaction history
                if context and "prospect_id" in context:
                    interaction_repo = InteractionRepository(session)
                    interactions = await interaction_repo.list_by_prospect(
                        context["prospect_id"], limit=10
                    )
                    for interaction in interactions:
                        memories.append({
                            "content": f"[{interaction.channel}] {interaction.content}",
                            "memory_type": "interaction_history",
                            "source_id": interaction.prospect_id,
                            "created_at": (
                                interaction.created_at.isoformat()
                                if interaction.created_at
                                else None
                            ),
                        })
        except Exception:
            log.exception("Error recalling memories")

        return memories

    async def store_interaction(
        self,
        message: str,
        response: str,
        context: dict | None = None,
    ) -> None:
        """Store a new interaction in memory with embeddings."""
        log.debug("Storing interaction in memory")

        try:
            combined_text = f"Message: {message}\nResponse: {response}"
            embedding = await self._get_embedding(combined_text)

            async with get_session() as session:
                # Store the interaction record
                interaction_repo = InteractionRepository(session)
                interaction_data = {
                    "prospect_id": context.get("prospect_id", "unknown") if context else "unknown",
                    "deal_id": context.get("deal_id") if context else None,
                    "channel": context.get("channel", "chat") if context else "chat",
                    "direction": "inbound",
                    "content": message,
                    "response": response,
                    "sentiment": context.get("sentiment") if context else None,
                }
                await interaction_repo.create(interaction_data)

                # Store the embedding for semantic search
                mem_repo = MemoryRepository(session)
                await mem_repo.store(
                    content=combined_text,
                    embedding=embedding,
                    memory_type="interaction",
                    source_id=context.get("prospect_id") if context else None,
                    source_type="interaction",
                    metadata={
                        "channel": context.get("channel") if context else "chat",
                        "deal_id": context.get("deal_id") if context else None,
                    },
                )
        except Exception:
            log.exception("Error storing interaction")

    async def store_prospect(self, prospect_data: dict) -> str | None:
        """Store or update prospect information. Returns the prospect ID."""
        log.debug("Storing prospect data")
        try:
            async with get_session() as session:
                repo = ProspectRepository(session)

                # Check if prospect exists by email
                if prospect_data.get("email"):
                    existing = await repo.get_by_email(prospect_data["email"])
                    if existing:
                        await repo.update(existing.id, prospect_data)
                        return existing.id

                prospect = await repo.create(prospect_data)

                # Also store an embedding for the prospect
                mem_repo = MemoryRepository(session)
                summary = (
                    f"{prospect_data.get('first_name', '')} "
                    f"{prospect_data.get('last_name', '')} at "
                    f"{prospect_data.get('company', 'Unknown')} - "
                    f"{prospect_data.get('title', 'Unknown role')}"
                )
                embedding = await self._get_embedding(summary)
                await mem_repo.store(
                    content=summary,
                    embedding=embedding,
                    memory_type="prospect",
                    source_id=prospect.id,
                    source_type="prospect",
                )

                return prospect.id
        except Exception:
            log.exception("Error storing prospect")
            return None

    async def store_deal(self, deal_data: dict) -> str | None:
        """Store or update deal information. Returns the deal ID."""
        log.debug("Storing deal data")
        try:
            from seal_agent.db.repositories.deal_repo import DealRepository

            async with get_session() as session:
                repo = DealRepository(session)
                deal = await repo.create(deal_data)
                return deal.id
        except Exception:
            log.exception("Error storing deal")
            return None

    async def get_prospect_history(self, prospect_id: str) -> list[dict]:
        """Retrieve full interaction history for a prospect."""
        try:
            async with get_session() as session:
                repo = InteractionRepository(session)
                interactions = await repo.list_by_prospect(prospect_id)
                return [
                    {
                        "id": i.id,
                        "channel": i.channel,
                        "direction": i.direction,
                        "content": i.content,
                        "response": i.response,
                        "sentiment": i.sentiment,
                        "opened": i.opened,
                        "replied": i.replied,
                        "created_at": i.created_at.isoformat() if i.created_at else None,
                    }
                    for i in interactions
                ]
        except Exception:
            log.exception("Error getting prospect history")
            return []

    async def search_patterns(
        self, pattern_type: str, filters: dict | None = None
    ) -> list[dict]:
        """Search pattern memory for aggregate insights."""
        try:
            query_text = f"pattern:{pattern_type}"
            if filters:
                query_text += " " + " ".join(f"{k}:{v}" for k, v in filters.items())

            embedding = await self._get_embedding(query_text)

            async with get_session() as session:
                mem_repo = MemoryRepository(session)
                return await mem_repo.search_similar(
                    embedding=embedding,
                    memory_type="pattern",
                    limit=20,
                    min_similarity=0.2,
                )
        except Exception:
            log.exception("Error searching patterns")
            return []
