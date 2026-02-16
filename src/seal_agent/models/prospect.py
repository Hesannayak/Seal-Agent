"""Prospect data model."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr


class ProspectStatus(StrEnum):
    NEW = "new"
    RESEARCHING = "researching"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    ENGAGED = "engaged"
    OPPORTUNITY = "opportunity"
    CUSTOMER = "customer"
    CHURNED = "churned"
    DISQUALIFIED = "disqualified"


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


class Prospect(BaseModel):
    """A sales prospect."""

    id: str | None = None
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    company: str | None = None
    linkedin_url: str | None = None
    status: ProspectStatus = ProspectStatus.NEW
    sentiment: Sentiment = Sentiment.UNKNOWN
    lead_score: float = 0.0
    preferred_channel: str | None = None
    timezone: str | None = None
    tags: list[str] = []
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
