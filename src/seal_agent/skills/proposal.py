"""Proposal Skill — Proposal and quote generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.deal_repo import DealRepository
from seal_agent.db.repositories.prospect_repo import ProspectRepository
from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()

# Default pricing tiers
PRICING_TIERS = {
    "starter": {"name": "Starter", "base_price": 499, "per_user": 29, "features": ["Core platform", "Email support", "5 users included"]},
    "professional": {"name": "Professional", "base_price": 999, "per_user": 49, "features": ["Everything in Starter", "API access", "Priority support", "25 users included"]},
    "enterprise": {"name": "Enterprise", "base_price": 2499, "per_user": 79, "features": ["Everything in Professional", "Dedicated CSM", "Custom integrations", "Unlimited users", "SLA guarantee"]},
}


class ProposalSkill(BaseSkill):
    """Generates proposals, quotes, and business cases for deals."""

    def __init__(self, reasoning_engine: Any = None) -> None:
        self._reasoning = reasoning_engine

    @property
    def name(self) -> str:
        return "proposal"

    @property
    def description(self) -> str:
        return "Proposal generation, pricing quotes, and business case creation"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "generate_proposal": self._generate_proposal,
            "create_quote": self._create_quote,
            "build_business_case": self._build_business_case,
            "calculate_roi": self._calculate_roi,
        }
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return ["generate_proposal", "create_quote", "build_business_case", "calculate_roi"]

    async def _generate_proposal(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a full proposal document for a deal."""
        deal_id = params.get("deal_id")
        if not deal_id:
            return {"error": "deal_id is required"}

        try:
            async with get_session() as session:
                deal_repo = DealRepository(session)
                deal = await deal_repo.get_by_id(deal_id)
                if not deal:
                    return {"error": "Deal not found"}

                prospect_repo = ProspectRepository(session)
                prospect = await prospect_repo.get_by_id(deal.prospect_id)
                prospect_name = (
                    f"{prospect.first_name} {prospect.last_name}" if prospect else "Valued Customer"
                )
                company = deal.company or (prospect.company if prospect else "Your Organization")

                # Determine tier based on deal value
                if deal.value >= 25000:
                    tier = "enterprise"
                elif deal.value >= 5000:
                    tier = "professional"
                else:
                    tier = "starter"

                tier_info = PRICING_TIERS[tier]
                valid_until = datetime.now(timezone.utc) + timedelta(days=30)

                proposal = {
                    "title": f"Proposal for {company}",
                    "deal_id": deal_id,
                    "prepared_for": prospect_name,
                    "company": company,
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "valid_until": valid_until.strftime("%Y-%m-%d"),
                    "sections": {
                        "executive_summary": (
                            f"We're excited to partner with {company} to transform your "
                            "sales operations. This proposal outlines our recommended solution "
                            "and the value it will deliver to your team."
                        ),
                        "recommended_solution": {
                            "tier": tier_info["name"],
                            "features": tier_info["features"],
                        },
                        "investment": {
                            "base_price": tier_info["base_price"],
                            "per_user_price": tier_info["per_user"],
                            "total_annual": deal.value,
                            "currency": deal.currency,
                        },
                        "timeline": {
                            "kickoff": "Week 1",
                            "implementation": "Weeks 2-4",
                            "training": "Week 5",
                            "go_live": "Week 6",
                        },
                        "next_steps": [
                            "Review and approve this proposal",
                            "Sign agreement and process payment",
                            "Schedule kickoff meeting",
                            "Begin implementation",
                        ],
                    },
                }

                # AI-enhanced executive summary
                if self._reasoning:
                    try:
                        prompt = (
                            f"Write a compelling executive summary for a sales proposal to "
                            f"{prospect_name} at {company}. Deal value: ${deal.value:,.0f}. "
                            f"Tier: {tier_info['name']}. Keep it under 100 words."
                        )
                        response = await self._reasoning.generate_response(
                            message=prompt,
                            context={"task": "proposal_generation"},
                        )
                        proposal["sections"]["executive_summary"] = response
                    except Exception:
                        log.warning("AI proposal enhancement failed")

                return proposal
        except Exception:
            log.exception("Error generating proposal")
            return {"error": "Proposal generation failed"}

    async def _create_quote(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a pricing quote."""
        tier = params.get("tier", "professional")
        num_users = params.get("users", 10)
        term_months = params.get("term_months", 12)
        discount_pct = params.get("discount", 0)

        tier_info = PRICING_TIERS.get(tier)
        if not tier_info:
            return {"error": f"Unknown tier: {tier}. Options: {list(PRICING_TIERS.keys())}"}

        base = tier_info["base_price"]
        user_cost = tier_info["per_user"] * max(0, num_users - (5 if tier == "starter" else 25 if tier == "professional" else 0))
        monthly = base + user_cost
        annual = monthly * 12
        term_total = monthly * term_months

        if discount_pct > 0:
            discount_amount = term_total * (discount_pct / 100)
            term_total -= discount_amount
        else:
            discount_amount = 0

        return {
            "tier": tier_info["name"],
            "features": tier_info["features"],
            "users": num_users,
            "term_months": term_months,
            "pricing": {
                "monthly": round(monthly, 2),
                "annual": round(annual, 2),
                "term_total": round(term_total, 2),
                "discount_percent": discount_pct,
                "discount_amount": round(discount_amount, 2),
            },
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d"),
        }

    async def _build_business_case(self, params: dict[str, Any]) -> dict[str, Any]:
        """Build a business case with ROI justification."""
        deal_id = params.get("deal_id")
        current_cost = params.get("current_cost", 0)
        expected_improvement = params.get("expected_improvement_pct", 25)

        investment = 0
        company = params.get("company", "the organization")

        if deal_id:
            try:
                async with get_session() as session:
                    repo = DealRepository(session)
                    deal = await repo.get_by_id(deal_id)
                    if deal:
                        investment = deal.value
                        company = deal.company or company
            except Exception:
                pass

        if not investment:
            investment = params.get("investment", 10000)

        annual_savings = current_cost * (expected_improvement / 100) if current_cost else investment * 3
        payback_months = round((investment / (annual_savings / 12)), 1) if annual_savings > 0 else 0
        three_year_value = (annual_savings * 3) - investment

        return {
            "company": company,
            "investment": investment,
            "business_case": {
                "current_annual_cost": current_cost,
                "expected_improvement": f"{expected_improvement}%",
                "annual_savings": round(annual_savings, 2),
                "payback_period_months": payback_months,
                "three_year_net_value": round(three_year_value, 2),
                "roi_percentage": round((three_year_value / investment) * 100, 1) if investment else 0,
            },
            "key_benefits": [
                f"Projected annual savings of ${annual_savings:,.0f}",
                f"Payback period of {payback_months} months",
                f"3-year net value of ${three_year_value:,.0f}",
                f"{expected_improvement}% improvement in operational efficiency",
            ],
        }

    async def _calculate_roi(self, params: dict[str, Any]) -> dict[str, Any]:
        """Calculate return on investment for a prospect."""
        investment = params.get("investment", 0)
        annual_revenue_impact = params.get("annual_revenue_impact", 0)
        annual_cost_savings = params.get("annual_cost_savings", 0)
        time_horizon_years = params.get("years", 3)

        if not investment:
            return {"error": "investment amount is required"}

        total_annual_benefit = annual_revenue_impact + annual_cost_savings
        total_benefit = total_annual_benefit * time_horizon_years
        net_benefit = total_benefit - investment
        roi_pct = (net_benefit / investment) * 100 if investment else 0
        payback_months = (
            round((investment / (total_annual_benefit / 12)), 1)
            if total_annual_benefit > 0 else 0
        )

        return {
            "investment": investment,
            "annual_benefit": round(total_annual_benefit, 2),
            "total_benefit": round(total_benefit, 2),
            "net_benefit": round(net_benefit, 2),
            "roi_percentage": round(roi_pct, 1),
            "payback_months": payback_months,
            "time_horizon_years": time_horizon_years,
            "verdict": (
                "Strong ROI" if roi_pct > 200
                else "Good ROI" if roi_pct > 100
                else "Moderate ROI" if roi_pct > 50
                else "Low ROI — consider reframing value"
            ),
        }
