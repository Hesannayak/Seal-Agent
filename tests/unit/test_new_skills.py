"""Tests for new skills: follow_up, negotiation, research, proposal, scheduling, analytics, objection."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from seal_agent.skills.follow_up import FollowUpSkill
from seal_agent.skills.negotiation import NegotiationSkill
from seal_agent.skills.research import ResearchSkill
from seal_agent.skills.proposal import ProposalSkill
from seal_agent.skills.scheduling import SchedulingSkill
from seal_agent.skills.analytics import AnalyticsSkill
from seal_agent.skills.objection import ObjectionSkill


# ── FollowUpSkill ──────────────────────────────────────────────

class TestFollowUpSkill:
    def setup_method(self) -> None:
        self.skill = FollowUpSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "follow_up"
        assert "follow-up" in self.skill.description.lower()

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "check_due" in actions
        assert "create_follow_up" in actions
        assert "suggest_timing" in actions

    @pytest.mark.asyncio
    async def test_create_follow_up_requires_prospect_id(self) -> None:
        result = await self.skill.execute("create_follow_up", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self) -> None:
        result = await self.skill.execute("nonexistent", {})
        assert "error" in result

    def test_classify_temperature_no_interactions(self) -> None:
        assert FollowUpSkill._classify_temperature([]) == "cold"

    def test_classify_temperature_with_replies(self) -> None:
        interactions = [MagicMock(replied=True, opened=True)]
        assert FollowUpSkill._classify_temperature(interactions) == "hot"

    def test_suggest_channel_default_email(self) -> None:
        assert FollowUpSkill._suggest_channel([]) == "email"

    def test_suggest_channel_alternates(self) -> None:
        interaction = MagicMock(channel="email", replied=False, opened=False)
        assert FollowUpSkill._suggest_channel([interaction]) == "linkedin"


# ── NegotiationSkill ───────────────────────────────────────────

class TestNegotiationSkill:
    def setup_method(self) -> None:
        self.skill = NegotiationSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "negotiation"
        assert "negotiation" in self.skill.description.lower()

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "suggest_tactics" in actions
        assert "handle_objection" in actions
        assert "prepare_counter_offer" in actions

    @pytest.mark.asyncio
    async def test_suggest_tactics_for_negotiation_stage(self) -> None:
        result = await self.skill.execute("suggest_tactics", {"stage": "negotiation"})
        assert "recommended_tactics" in result
        assert len(result["recommended_tactics"]) > 0

    @pytest.mark.asyncio
    async def test_handle_price_objection(self) -> None:
        result = await self.skill.execute("handle_objection", {"type": "price"})
        assert "response" in result
        assert result["objection_type"] == "price"

    @pytest.mark.asyncio
    async def test_handle_timing_objection(self) -> None:
        result = await self.skill.execute("handle_objection", {"type": "timing"})
        assert result["objection_type"] == "timing"
        assert "response" in result

    @pytest.mark.asyncio
    async def test_handle_unknown_objection(self) -> None:
        result = await self.skill.execute("handle_objection", {"type": "xyz_unknown"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_counter_offer_accept(self) -> None:
        result = await self.skill.execute("prepare_counter_offer", {
            "their_offer": 15000,
            "our_target": 10000,
        })
        assert result["recommendation"] == "accept"

    @pytest.mark.asyncio
    async def test_counter_offer_reject(self) -> None:
        result = await self.skill.execute("prepare_counter_offer", {
            "their_offer": 3000,
            "our_target": 15000,
            "floor": 10000,
        })
        assert result["recommendation"] == "reject_or_reframe"

    @pytest.mark.asyncio
    async def test_counter_offer_counter(self) -> None:
        result = await self.skill.execute("prepare_counter_offer", {
            "their_offer": 8000,
            "our_target": 12000,
        })
        assert result["recommendation"] == "counter"
        assert result["counter_offer"] > 8000

    @pytest.mark.asyncio
    async def test_recommend_close_hot_resolved(self) -> None:
        result = await self.skill.execute("recommend_close", {
            "temperature": "hot",
            "objections_resolved": True,
        })
        assert result["recommended_technique"] == "assumptive"

    @pytest.mark.asyncio
    async def test_recommend_close_cold(self) -> None:
        result = await self.skill.execute("recommend_close", {
            "temperature": "cold",
            "objections_resolved": False,
        })
        assert result["recommended_technique"] == "trial"

    def test_classify_objection_price(self) -> None:
        result = NegotiationSkill._classify_objection("This is too expensive for our budget")
        assert result == "price"

    def test_classify_objection_timing(self) -> None:
        result = NegotiationSkill._classify_objection("We're too busy right now, maybe later")
        assert result == "timing"


# ── ResearchSkill ──────────────────────────────────────────────

class TestResearchSkill:
    def setup_method(self) -> None:
        self.skill = ResearchSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "research"
        assert "intelligence" in self.skill.description.lower()

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "research_prospect" in actions
        assert "research_company" in actions
        assert "build_briefing" in actions

    @pytest.mark.asyncio
    async def test_research_prospect_requires_id(self) -> None:
        result = await self.skill.execute("research_prospect", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_research_company_requires_input(self) -> None:
        result = await self.skill.execute("research_company", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_competitive_analysis_no_competitors(self) -> None:
        result = await self.skill.execute("competitive_analysis", {})
        assert result["competitors"] == []
        assert "analysis" in result

    @pytest.mark.asyncio
    async def test_competitive_analysis_with_competitors(self) -> None:
        result = await self.skill.execute("competitive_analysis", {
            "competitors": ["Acme Corp", "BigCo"],
        })
        assert result["count"] == 2
        assert len(result["analysis"]) == 2


# ── ProposalSkill ──────────────────────────────────────────────

class TestProposalSkill:
    def setup_method(self) -> None:
        self.skill = ProposalSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "proposal"

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "generate_proposal" in actions
        assert "create_quote" in actions
        assert "calculate_roi" in actions

    @pytest.mark.asyncio
    async def test_generate_proposal_requires_deal_id(self) -> None:
        result = await self.skill.execute("generate_proposal", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_quote_starter(self) -> None:
        result = await self.skill.execute("create_quote", {"tier": "starter", "users": 5})
        assert "pricing" in result
        assert result["tier"] == "Starter"
        assert result["pricing"]["monthly"] > 0

    @pytest.mark.asyncio
    async def test_create_quote_with_discount(self) -> None:
        result = await self.skill.execute("create_quote", {
            "tier": "professional",
            "users": 10,
            "discount": 10,
        })
        assert result["pricing"]["discount_percent"] == 10
        assert result["pricing"]["discount_amount"] > 0

    @pytest.mark.asyncio
    async def test_create_quote_invalid_tier(self) -> None:
        result = await self.skill.execute("create_quote", {"tier": "nonexistent"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_calculate_roi(self) -> None:
        result = await self.skill.execute("calculate_roi", {
            "investment": 10000,
            "annual_revenue_impact": 25000,
            "annual_cost_savings": 5000,
            "years": 3,
        })
        assert result["roi_percentage"] > 0
        assert result["net_benefit"] > 0
        assert result["payback_months"] > 0

    @pytest.mark.asyncio
    async def test_calculate_roi_requires_investment(self) -> None:
        result = await self.skill.execute("calculate_roi", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_build_business_case(self) -> None:
        result = await self.skill.execute("build_business_case", {
            "investment": 20000,
            "current_cost": 100000,
            "expected_improvement_pct": 20,
        })
        assert "business_case" in result
        assert result["business_case"]["annual_savings"] > 0


# ── SchedulingSkill ────────────────────────────────────────────

class TestSchedulingSkill:
    def setup_method(self) -> None:
        self.skill = SchedulingSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "scheduling"

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "suggest_meeting" in actions
        assert "get_meeting_types" in actions
        assert "prepare_agenda" in actions

    @pytest.mark.asyncio
    async def test_suggest_meeting_discovery_stage(self) -> None:
        result = await self.skill.execute("suggest_meeting", {"stage": "prospecting"})
        assert result["suggested_type"] == "discovery"

    @pytest.mark.asyncio
    async def test_suggest_meeting_demo_stage(self) -> None:
        result = await self.skill.execute("suggest_meeting", {"stage": "discovery"})
        assert result["suggested_type"] == "demo"

    @pytest.mark.asyncio
    async def test_get_meeting_types(self) -> None:
        result = await self.skill.execute("get_meeting_types", {})
        assert "meeting_types" in result
        assert "discovery" in result["meeting_types"]
        assert "demo" in result["meeting_types"]

    @pytest.mark.asyncio
    async def test_prepare_agenda_discovery(self) -> None:
        result = await self.skill.execute("prepare_agenda", {"type": "discovery"})
        assert "agenda" in result
        assert len(result["agenda"]) > 0
        assert result["total_minutes"] > 0

    @pytest.mark.asyncio
    async def test_suggest_times(self) -> None:
        result = await self.skill.execute("suggest_times", {"num_slots": 3})
        assert "suggested_times" in result
        assert len(result["suggested_times"]) <= 3

    @pytest.mark.asyncio
    async def test_create_meeting_request_requires_prospect_id(self) -> None:
        result = await self.skill.execute("create_meeting_request", {})
        assert "error" in result


# ── AnalyticsSkill ─────────────────────────────────────────────

class TestAnalyticsSkill:
    def setup_method(self) -> None:
        self.skill = AnalyticsSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "analytics"
        assert "analytics" in self.skill.description.lower()

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "pipeline_summary" in actions
        assert "activity_metrics" in actions
        assert "conversion_funnel" in actions
        assert "forecast" in actions

    @pytest.mark.asyncio
    async def test_unknown_action(self) -> None:
        result = await self.skill.execute("nonexistent", {})
        assert "error" in result


# ── ObjectionSkill ─────────────────────────────────────────────

class TestObjectionSkill:
    def setup_method(self) -> None:
        self.skill = ObjectionSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "objection"
        assert "objection" in self.skill.description.lower()

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "handle" in actions
        assert "classify" in actions
        assert "get_playbook" in actions

    @pytest.mark.asyncio
    async def test_handle_price_objection(self) -> None:
        result = await self.skill.execute("handle", {"type": "price"})
        assert "response" in result
        assert result["objection_type"] == "price"
        assert "follow_up" in result

    @pytest.mark.asyncio
    async def test_handle_timing_objection(self) -> None:
        result = await self.skill.execute("handle", {"type": "timing"})
        assert result["objection_type"] == "timing"
        assert "response" in result

    @pytest.mark.asyncio
    async def test_handle_competition_objection(self) -> None:
        result = await self.skill.execute("handle", {"type": "competition"})
        assert result["objection_type"] == "competition"

    @pytest.mark.asyncio
    async def test_handle_authority_objection(self) -> None:
        result = await self.skill.execute("handle", {"type": "authority"})
        assert result["objection_type"] == "authority"

    @pytest.mark.asyncio
    async def test_handle_trust_objection(self) -> None:
        result = await self.skill.execute("handle", {"type": "trust"})
        assert result["objection_type"] == "trust"

    @pytest.mark.asyncio
    async def test_handle_requires_input(self) -> None:
        result = await self.skill.execute("handle", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_classify_objection_price(self) -> None:
        result = await self.skill.execute("classify", {"text": "This is way too expensive for us"})
        assert result["type"] == "price"

    @pytest.mark.asyncio
    async def test_classify_objection_timing(self) -> None:
        result = await self.skill.execute("classify", {"text": "We're not ready, timing is bad"})
        assert result["type"] == "timing"

    @pytest.mark.asyncio
    async def test_classify_requires_text(self) -> None:
        result = await self.skill.execute("classify", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_playbook_all(self) -> None:
        result = await self.skill.execute("get_playbook", {})
        assert "categories" in result
        assert "price" in result["categories"]
        assert "timing" in result["categories"]

    @pytest.mark.asyncio
    async def test_get_playbook_specific(self) -> None:
        result = await self.skill.execute("get_playbook", {"type": "price"})
        assert result["type"] == "price"
        assert "scenarios" in result
        assert "techniques" in result

    @pytest.mark.asyncio
    async def test_suggest_response(self) -> None:
        result = await self.skill.execute("suggest_response", {"type": "price"})
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_list_techniques(self) -> None:
        result = await self.skill.execute("list_techniques", {})
        assert "techniques" in result
        assert result["count"] > 0
