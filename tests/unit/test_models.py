"""Tests for data models."""

from seal_agent.models.prospect import Prospect, ProspectStatus, Sentiment
from seal_agent.models.deal import Deal, DealStage


def test_prospect_creation() -> None:
    """Test creating a prospect with basic fields."""
    prospect = Prospect(
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        company="Acme Corp",
        title="VP of Engineering",
    )

    assert prospect.full_name == "Jane Smith"
    assert prospect.status == ProspectStatus.NEW
    assert prospect.sentiment == Sentiment.UNKNOWN
    assert prospect.lead_score == 0.0


def test_prospect_with_all_fields() -> None:
    """Test creating a prospect with all fields."""
    prospect = Prospect(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        status=ProspectStatus.QUALIFIED,
        sentiment=Sentiment.POSITIVE,
        lead_score=85.5,
        tags=["enterprise", "high-priority"],
    )

    assert prospect.status == ProspectStatus.QUALIFIED
    assert prospect.lead_score == 85.5
    assert "enterprise" in prospect.tags


def test_deal_creation() -> None:
    """Test creating a deal."""
    deal = Deal(
        title="Acme Corp Enterprise Deal",
        prospect_id="prospect-123",
        company="Acme Corp",
        value=50000.0,
    )

    assert deal.stage == DealStage.PROSPECTING
    assert deal.value == 50000.0
    assert deal.currency == "USD"
    assert deal.probability == 0.0


def test_deal_stage_values() -> None:
    """Test all deal stages are valid."""
    stages = [s.value for s in DealStage]
    assert "prospecting" in stages
    assert "closed_won" in stages
    assert "closed_lost" in stages
