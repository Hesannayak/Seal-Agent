"""Memory embedding repository for semantic search."""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from seal_agent.db.models import MemoryEmbedding


class MemoryRepository:
    """Data access layer for vector memory embeddings."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def store(
        self,
        content: str,
        embedding: list[float],
        memory_type: str,
        source_id: str | None = None,
        source_type: str | None = None,
        metadata: dict | None = None,
    ) -> MemoryEmbedding:
        record = MemoryEmbedding(
            content=content,
            embedding=embedding,
            memory_type=memory_type,
            source_id=source_id,
            source_type=source_type,
            metadata_json=metadata or {},
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def search_similar(
        self,
        embedding: list[float],
        memory_type: str | None = None,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> list[dict]:
        """Search for similar memories using cosine distance."""
        # pgvector cosine distance: <=> operator
        # Lower distance = more similar; distance = 1 - cosine_similarity
        query = (
            select(
                MemoryEmbedding.id,
                MemoryEmbedding.content,
                MemoryEmbedding.memory_type,
                MemoryEmbedding.source_id,
                MemoryEmbedding.source_type,
                MemoryEmbedding.metadata_json,
                MemoryEmbedding.created_at,
                (1 - MemoryEmbedding.embedding.cosine_distance(embedding)).label("similarity"),
            )
            .where(
                (1 - MemoryEmbedding.embedding.cosine_distance(embedding)) >= min_similarity
            )
        )

        if memory_type:
            query = query.where(MemoryEmbedding.memory_type == memory_type)

        query = query.order_by(
            MemoryEmbedding.embedding.cosine_distance(embedding)
        ).limit(limit)

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                "id": row.id,
                "content": row.content,
                "memory_type": row.memory_type,
                "source_id": row.source_id,
                "source_type": row.source_type,
                "metadata": row.metadata_json,
                "similarity": float(row.similarity),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def delete_by_source(self, source_id: str, source_type: str) -> int:
        """Delete all memory embeddings for a specific source."""
        result = await self.session.execute(
            select(MemoryEmbedding).where(
                MemoryEmbedding.source_id == source_id,
                MemoryEmbedding.source_type == source_type,
            )
        )
        records = result.scalars().all()
        for record in records:
            await self.session.delete(record)
        await self.session.flush()
        return len(records)
