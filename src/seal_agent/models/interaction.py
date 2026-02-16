"""Interaction data model."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class Channel(StrEnum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    PHONE = "phone"
    SLACK = "slack"
    TEAMS = "teams"
    WHATSAPP = "whatsapp"
    MEETING = "meeting"
    OTHER = "other"


class InteractionDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Interaction(BaseModel):
    """A recorded interaction with a prospect."""

    id: str | None = None
    prospect_id: str
    deal_id: str | None = None
    channel: Channel
    direction: InteractionDirection
    subject: str | None = None
    content: str
    response: str | None = None
    sentiment: str | None = None
    opened: bool = False
    clicked: bool = False
    replied: bool = False
    created_at: datetime | None = None
