"""Initial schema — all tables for Seal-Agent.

Revision ID: 001_initial
Revises: None
Create Date: 2026-02-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- prospects ---
    op.create_table(
        "prospects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), index=True),
        sa.Column("phone", sa.String(50)),
        sa.Column("title", sa.String(200)),
        sa.Column("company", sa.String(200), index=True),
        sa.Column("linkedin_url", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False, server_default="new", index=True),
        sa.Column("sentiment", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("lead_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("preferred_channel", sa.String(20)),
        sa.Column("timezone", sa.String(50)),
        sa.Column("tags", ARRAY(sa.String)),
        sa.Column("notes", sa.Text),
        sa.Column("custom_fields", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # --- deals ---
    op.create_table(
        "deals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column(
            "prospect_id",
            sa.String(36),
            sa.ForeignKey("prospects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("company", sa.String(200)),
        sa.Column("stage", sa.String(20), nullable=False, server_default="prospecting", index=True),
        sa.Column("value", sa.Float, nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("probability", sa.Float, nullable=False, server_default="0"),
        sa.Column("expected_close_date", sa.DateTime),
        sa.Column("champion_id", sa.String(36)),
        sa.Column("decision_maker_id", sa.String(36)),
        sa.Column("competitors", ARRAY(sa.String)),
        sa.Column("loss_reason", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("custom_fields", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("closed_at", sa.DateTime),
    )

    # --- interactions ---
    op.create_table(
        "interactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "prospect_id",
            sa.String(36),
            sa.ForeignKey("prospects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "deal_id",
            sa.String(36),
            sa.ForeignKey("deals.id", ondelete="SET NULL"),
            index=True,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("subject", sa.String(500)),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("response", sa.Text),
        sa.Column("sentiment", sa.String(20)),
        sa.Column("opened", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("clicked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("replied", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- memory_embeddings ---
    op.create_table(
        "memory_embeddings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("memory_type", sa.String(30), nullable=False, index=True),
        sa.Column("source_id", sa.String(36), index=True),
        sa.Column("source_type", sa.String(30)),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- evolution_logs ---
    op.create_table(
        "evolution_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(30), nullable=False, index=True),
        sa.Column("strategy_name", sa.String(100), index=True),
        sa.Column("experiment_id", sa.String(36), index=True),
        sa.Column("variant", sa.String(50)),
        sa.Column("outcome", sa.String(30)),
        sa.Column("score", sa.Float),
        sa.Column("context", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # --- outreach_sequences ---
    op.create_table(
        "outreach_sequences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "prospect_id",
            sa.String(36),
            sa.ForeignKey("prospects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", index=True),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_steps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("steps", JSONB, server_default="[]"),
        sa.Column("next_action_at", sa.DateTime, index=True),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # --- strategy_scores ---
    op.create_table(
        "strategy_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("strategy_name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("effectiveness", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("sample_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # --- HNSW index for fast vector similarity search ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memory_embeddings_vector "
        "ON memory_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_memory_embeddings_vector")
    op.drop_table("strategy_scores")
    op.drop_table("outreach_sequences")
    op.drop_table("evolution_logs")
    op.drop_table("memory_embeddings")
    op.drop_table("interactions")
    op.drop_table("deals")
    op.drop_table("prospects")
