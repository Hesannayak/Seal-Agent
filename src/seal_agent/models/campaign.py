"""Campaign data model."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignType(StrEnum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    MULTI_CHANNEL = "multi_channel"
    EVENT = "event"
    REFERRAL = "referral"


class Campaign(BaseModel):
    """A sales outreach campaign targeting a group of prospects."""

    id: str | None = None
    name: str
    description: str | None = None
    campaign_type: CampaignType = CampaignType.EMAIL
    status: CampaignStatus = CampaignStatus.DRAFT

    # Targeting
    target_criteria: dict | None = None
    prospect_ids: list[str] = []

    # Metrics
    total_prospects: int = 0
    contacted: int = 0
    opened: int = 0
    replied: int = 0
    converted: int = 0

    # Sequence
    sequence_steps: list[dict] = []
    current_step: int = 0

    # Dates
    start_date: datetime | None = None
    end_date: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def open_rate(self) -> float:
        return (self.opened / self.contacted * 100) if self.contacted else 0.0

    @property
    def reply_rate(self) -> float:
        return (self.replied / self.contacted * 100) if self.contacted else 0.0

    @property
    def conversion_rate(self) -> float:
        return (self.converted / self.total_prospects * 100) if self.total_prospects else 0.0
