"""SQLAlchemy ORM models for Seal-Agent."""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ProspectRow(Base):
    __tablename__ = "prospects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(200), index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    sentiment: Mapped[str] = mapped_column(String(20), default="unknown")
    lead_score: Mapped[float] = mapped_column(Float, default=0.0)
    preferred_channel: Mapped[str | None] = mapped_column(String(20))
    timezone: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[list | None] = mapped_column(ARRAY(String), default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    deals: Mapped[list[DealRow]] = relationship("DealRow", back_populates="prospect")
    interactions: Mapped[list[InteractionRow]] = relationship(
        "InteractionRow", back_populates="prospect"
    )


class DealRow(Base):
    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(300))
    prospect_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("prospects.id"), index=True
    )
    company: Mapped[str | None] = mapped_column(String(200))
    stage: Mapped[str] = mapped_column(String(20), default="prospecting", index=True)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    probability: Mapped[float] = mapped_column(Float, default=0.0)
    expected_close_date: Mapped[datetime | None] = mapped_column(DateTime)
    champion_id: Mapped[str | None] = mapped_column(String(36))
    decision_maker_id: Mapped[str | None] = mapped_column(String(36))
    competitors: Mapped[list | None] = mapped_column(ARRAY(String), default=list)
    loss_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    prospect: Mapped[ProspectRow] = relationship("ProspectRow", back_populates="deals")
    interactions: Mapped[list[InteractionRow]] = relationship(
        "InteractionRow", back_populates="deal"
    )


class InteractionRow(Base):
    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    prospect_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("prospects.id"), index=True
    )
    deal_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("deals.id"), index=True
    )
    channel: Mapped[str] = mapped_column(String(20))
    direction: Mapped[str] = mapped_column(String(10))
    subject: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(Text)
    sentiment: Mapped[str | None] = mapped_column(String(20))
    opened: Mapped[bool] = mapped_column(Boolean, default=False)
    clicked: Mapped[bool] = mapped_column(Boolean, default=False)
    replied: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    prospect: Mapped[ProspectRow] = relationship("ProspectRow", back_populates="interactions")
    deal: Mapped[DealRow | None] = relationship("DealRow", back_populates="interactions")


class MemoryEmbedding(Base):
    """Vector embeddings for semantic memory search."""

    __tablename__ = "memory_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(Vector(1024))
    memory_type: Mapped[str] = mapped_column(String(30), index=True)
    source_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_type: Mapped[str | None] = mapped_column(String(30))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EvolutionLog(Base):
    """Tracks interactions and outcomes for the evolution/learning engine."""

    __tablename__ = "evolution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_type: Mapped[str] = mapped_column(String(30), index=True)
    strategy_name: Mapped[str | None] = mapped_column(String(100), index=True)
    experiment_id: Mapped[str | None] = mapped_column(String(36), index=True)
    variant: Mapped[str | None] = mapped_column(String(50))
    outcome: Mapped[str | None] = mapped_column(String(30))
    score: Mapped[float | None] = mapped_column(Float)
    context: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OutreachSequence(Base):
    """Multi-step outreach sequences for prospects."""

    __tablename__ = "outreach_sequences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    prospect_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("prospects.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[dict | None] = mapped_column(JSONB, default=list)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class StrategyScore(Base):
    """Tracks effectiveness scores for sales strategies."""

    __tablename__ = "strategy_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    strategy_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    effectiveness: Mapped[float] = mapped_column(Float, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
