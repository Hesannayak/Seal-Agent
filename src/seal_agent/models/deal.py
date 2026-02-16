"""Deal data model."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class DealStage(StrEnum):
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class Deal(BaseModel):
    """A sales deal in the pipeline."""

    id: str | None = None
    title: str
    prospect_id: str
    company: str | None = None
    stage: DealStage = DealStage.PROSPECTING
    value: float = 0.0
    currency: str = "USD"
    probability: float = 0.0
    expected_close_date: datetime | None = None
    champion_id: str | None = None
    decision_maker_id: str | None = None
    competitors: list[str] = []
    loss_reason: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None
