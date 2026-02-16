"""Tests for new data models: campaign and learning."""

from __future__ import annotations

import pytest

from seal_agent.models.campaign import Campaign, CampaignStatus, CampaignType
from seal_agent.models.learning import LearningRecord, LearningType, Outcome, ABTestRecord


class TestCampaignModel:
    def test_campaign_creation(self) -> None:
        campaign = Campaign(name="Q1 Outreach")
        assert campaign.name == "Q1 Outreach"
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.campaign_type == CampaignType.EMAIL

    def test_campaign_with_all_fields(self) -> None:
        campaign = Campaign(
            name="Multi-Channel Launch",
            description="Launch campaign",
            campaign_type=CampaignType.MULTI_CHANNEL,
            status=CampaignStatus.ACTIVE,
            total_prospects=100,
            contacted=50,
            opened=25,
            replied=10,
            converted=5,
        )
        assert campaign.open_rate == 50.0
        assert campaign.reply_rate == 20.0
        assert campaign.conversion_rate == 5.0

    def test_campaign_zero_rates(self) -> None:
        campaign = Campaign(name="Empty Campaign")
        assert campaign.open_rate == 0.0
        assert campaign.reply_rate == 0.0
        assert campaign.conversion_rate == 0.0

    def test_campaign_status_values(self) -> None:
        for status in CampaignStatus:
            campaign = Campaign(name="Test", status=status)
            assert campaign.status == status

    def test_campaign_type_values(self) -> None:
        for ctype in CampaignType:
            campaign = Campaign(name="Test", campaign_type=ctype)
            assert campaign.campaign_type == ctype


class TestLearningModel:
    def test_learning_record_creation(self) -> None:
        record = LearningRecord(
            learning_type=LearningType.WIN_ANALYSIS,
            observation="Value-based messaging led to faster close",
        )
        assert record.learning_type == LearningType.WIN_ANALYSIS
        assert record.outcome == Outcome.NEUTRAL
        assert record.confidence == 0.5

    def test_learning_record_with_all_fields(self) -> None:
        record = LearningRecord(
            learning_type=LearningType.LOSS_ANALYSIS,
            outcome=Outcome.NEGATIVE,
            deal_id="deal_123",
            prospect_id="prospect_456",
            strategy_used="aggressive_pricing",
            observation="Lost to competitor on features",
            insight="Need to focus on differentiation for enterprise deals",
            action_taken="Updated playbook",
            confidence=0.8,
            impact_score=7.5,
            tags=["enterprise", "competitive"],
        )
        assert record.outcome == Outcome.NEGATIVE
        assert record.confidence == 0.8
        assert "enterprise" in record.tags

    def test_ab_test_record_creation(self) -> None:
        test = ABTestRecord(
            test_name="Subject Line A/B",
            variant_a="Short subject",
            variant_b="Long subject with details",
        )
        assert test.test_name == "Subject Line A/B"
        assert test.is_complete is False
        assert test.winner is None

    def test_ab_test_rates(self) -> None:
        test = ABTestRecord(
            test_name="CTA Test",
            variant_a="Book a call",
            variant_b="Learn more",
            variant_a_count=100,
            variant_a_successes=15,
            variant_b_count=100,
            variant_b_successes=10,
        )
        assert test.variant_a_rate == 15.0
        assert test.variant_b_rate == 10.0

    def test_ab_test_zero_rates(self) -> None:
        test = ABTestRecord(
            test_name="Empty",
            variant_a="A",
            variant_b="B",
        )
        assert test.variant_a_rate == 0.0
        assert test.variant_b_rate == 0.0

    def test_learning_types(self) -> None:
        for lt in LearningType:
            record = LearningRecord(learning_type=lt, observation="test")
            assert record.learning_type == lt

    def test_outcome_values(self) -> None:
        for outcome in Outcome:
            record = LearningRecord(
                learning_type=LearningType.FEEDBACK,
                outcome=outcome,
                observation="test",
            )
            assert record.outcome == outcome
