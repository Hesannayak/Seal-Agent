"""Tests for sales skills."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from seal_agent.skills.prospecting import ProspectingSkill, ICP_FACTORS, MEDDIC_WEIGHTS
from seal_agent.skills.outreach import OutreachSkill
from seal_agent.skills.deal_management import DealManagementSkill


# ---------- ProspectingSkill ----------


class TestProspectingSkill:
    def setup_method(self) -> None:
        self.skill = ProspectingSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "prospecting"
        assert "MEDDIC" in self.skill.description

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "find_leads" in actions
        assert "score_lead" in actions
        assert "qualify_lead" in actions
        assert "research_prospect" in actions

    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self) -> None:
        result = await self.skill.execute("nonexistent_action", {})
        assert "error" in result

    def test_compute_lead_score_full_profile(self) -> None:
        """VP-level prospect with all contact info should score high."""
        prospect = MagicMock()
        prospect.email = "jane@example.com"
        prospect.phone = "+1234567890"
        prospect.title = "VP of Sales"
        prospect.company = "Acme Corp"
        prospect.linkedin_url = "https://linkedin.com/in/jane"

        result = ProspectingSkill._compute_lead_score(prospect)

        assert result["score"] > 50
        assert len(result["factors"]) >= 5
        factor_names = [f["factor"] for f in result["factors"]]
        assert "has_email" in factor_names
        assert "title_vp_or_above" in factor_names

    def test_compute_lead_score_minimal_profile(self) -> None:
        """Prospect with minimal info should score low."""
        prospect = MagicMock()
        prospect.email = None
        prospect.phone = None
        prospect.title = None
        prospect.company = None
        prospect.linkedin_url = None

        result = ProspectingSkill._compute_lead_score(prospect)

        assert result["score"] == 0
        assert len(result["factors"]) == 0

    def test_compute_lead_score_director_title(self) -> None:
        prospect = MagicMock()
        prospect.email = "bob@example.com"
        prospect.phone = None
        prospect.title = "Director of Engineering"
        prospect.company = "TechCo"
        prospect.linkedin_url = None

        result = ProspectingSkill._compute_lead_score(prospect)

        factor_names = [f["factor"] for f in result["factors"]]
        assert "title_director" in factor_names
        assert "title_vp_or_above" not in factor_names

    @pytest.mark.asyncio
    async def test_qualify_lead_requires_prospect_id(self) -> None:
        result = await self.skill.execute("qualify_lead", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_qualify_lead_meddic_scoring(self) -> None:
        """Test MEDDIC qualification with fully qualified lead."""
        with patch("seal_agent.skills.prospecting.get_session"):
            result = await self.skill._qualify_lead({
                "prospect_id": "test-123",
                "meddic": {
                    "metrics": True,
                    "economic_buyer": True,
                    "decision_criteria": True,
                    "decision_process": True,
                    "identify_pain": True,
                    "champion": True,
                },
            })

        assert result["qualified"] is True
        assert result["score"] == 1.0
        assert result["confidence"] == "high"
        assert len(result["missing"]) == 0

    @pytest.mark.asyncio
    async def test_qualify_lead_unqualified(self) -> None:
        """Test MEDDIC with missing criteria results in not qualified."""
        result = await self.skill._qualify_lead({
            "prospect_id": "test-123",
            "meddic": {},  # No criteria met
        })

        assert result["qualified"] is False
        assert result["score"] == 0.0
        assert result["confidence"] == "low"
        assert len(result["missing"]) == len(MEDDIC_WEIGHTS)

    @pytest.mark.asyncio
    async def test_score_lead_requires_prospect_id(self) -> None:
        result = await self.skill.execute("score_lead", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_research_requires_prospect_id(self) -> None:
        result = await self.skill.execute("research_prospect", {})
        assert "error" in result


# ---------- OutreachSkill ----------


class TestOutreachSkill:
    def setup_method(self) -> None:
        self.skill = OutreachSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "outreach"
        assert "email" in self.skill.description.lower()

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "compose_email" in actions
        assert "compose_linkedin_message" in actions
        assert "create_sequence" in actions
        assert "execute_sequence_step" in actions

    @pytest.mark.asyncio
    async def test_compose_email_cold_outreach_template(self) -> None:
        """Without AI reasoning, should fall back to template."""
        with patch.object(
            OutreachSkill, "_get_prospect_context", return_value={
                "name": "Jane Smith",
                "title": "VP of Sales",
                "company": "Acme Corp",
                "interaction_count": 0,
            }
        ):
            result = await self.skill._compose_email({
                "prospect_id": "test-123",
                "type": "cold_outreach",
            })

        assert result["type"] == "cold_outreach"
        assert "Acme Corp" in result["subject"]
        assert "Jane" in result["body"]
        assert result["subject"] != ""
        assert result["body"] != ""

    @pytest.mark.asyncio
    async def test_compose_email_follow_up_template(self) -> None:
        with patch.object(
            OutreachSkill, "_get_prospect_context", return_value={
                "name": "Bob Jones",
                "title": "CTO",
                "company": "TechCo",
                "interaction_count": 1,
            }
        ):
            result = await self.skill._compose_email({
                "type": "follow_up",
            })

        assert result["type"] == "follow_up"
        assert "follow up" in result["body"].lower()

    @pytest.mark.asyncio
    async def test_compose_linkedin_connection_request(self) -> None:
        with patch.object(
            OutreachSkill, "_get_prospect_context", return_value={
                "name": "Alice Chen",
                "title": "Director of Engineering",
                "company": "DataCo",
                "interaction_count": 0,
            }
        ):
            result = await self.skill._compose_linkedin_message({
                "type": "connection_request",
            })

        assert result["type"] == "connection_request"
        assert "Alice" in result["message"]
        assert result["char_count"] > 0

    @pytest.mark.asyncio
    async def test_create_sequence_requires_prospect_id(self) -> None:
        result = await self.skill.execute("create_sequence", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_sequence_step_requires_sequence_id(self) -> None:
        result = await self.skill.execute("execute_sequence_step", {})
        assert "error" in result


# ---------- DealManagementSkill ----------


class TestDealManagementSkill:
    def setup_method(self) -> None:
        self.skill = DealManagementSkill()

    def test_name_and_description(self) -> None:
        assert self.skill.name == "deal_management"
        assert "pipeline" in self.skill.description.lower()

    @pytest.mark.asyncio
    async def test_available_actions(self) -> None:
        actions = await self.skill.get_available_actions()
        assert "create_deal" in actions
        assert "update_stage" in actions
        assert "get_pipeline" in actions
        assert "forecast" in actions
        assert "identify_at_risk" in actions

    @pytest.mark.asyncio
    async def test_create_deal_requires_title(self) -> None:
        result = await self.skill.execute("create_deal", {"prospect_id": "test-123"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_deal_requires_prospect_id(self) -> None:
        result = await self.skill.execute("create_deal", {"title": "Test Deal"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_stage_requires_fields(self) -> None:
        result = await self.skill.execute("update_stage", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_stage_validates_stage(self) -> None:
        result = await self.skill._update_stage({
            "deal_id": "test-123",
            "stage": "invalid_stage",
        })
        assert "error" in result
        assert "Invalid stage" in result["error"]
