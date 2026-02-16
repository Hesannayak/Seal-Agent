"""Research Skill — Prospect and company intelligence gathering."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.prospect_repo import ProspectRepository
from seal_agent.db.repositories.interaction_repo import InteractionRepository
from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()


class ResearchSkill(BaseSkill):
    """Gathers intelligence on prospects and companies for sales preparation."""

    def __init__(self, reasoning_engine: Any = None) -> None:
        self._reasoning = reasoning_engine

    @property
    def name(self) -> str:
        return "research"

    @property
    def description(self) -> str:
        return "Prospect and company intelligence gathering for sales preparation"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "research_prospect": self._research_prospect,
            "research_company": self._research_company,
            "build_briefing": self._build_briefing,
            "find_talking_points": self._find_talking_points,
            "competitive_analysis": self._competitive_analysis,
        }
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return [
            "research_prospect", "research_company", "build_briefing",
            "find_talking_points", "competitive_analysis",
        ]

    async def _research_prospect(self, params: dict[str, Any]) -> dict[str, Any]:
        """Deep research on a prospect using all available data sources."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}

        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                prospect = await repo.get_by_id(prospect_id)
                if not prospect:
                    return {"error": "Prospect not found"}

                interaction_repo = InteractionRepository(session)
                interactions = await interaction_repo.list_by_prospect(prospect_id, limit=20)

                # Compile profile from stored data
                profile = {
                    "name": f"{prospect.first_name} {prospect.last_name}",
                    "title": prospect.title,
                    "company": prospect.company,
                    "email": prospect.email,
                    "linkedin_url": prospect.linkedin_url,
                    "status": prospect.status,
                    "lead_score": prospect.lead_score,
                    "sentiment": prospect.sentiment,
                    "tags": prospect.tags or [],
                }

                # Engagement analysis
                engagement = {
                    "total_interactions": len(interactions),
                    "outbound": sum(1 for i in interactions if i.direction == "outbound"),
                    "inbound": sum(1 for i in interactions if i.direction == "inbound"),
                    "reply_rate": (
                        sum(1 for i in interactions if i.replied) / len(interactions)
                        if interactions else 0.0
                    ),
                    "channels_used": list(set(i.channel for i in interactions)),
                    "last_contact": (
                        interactions[0].created_at.isoformat()
                        if interactions and interactions[0].created_at else None
                    ),
                }

                # AI-powered insights
                insights = []
                if self._reasoning:
                    try:
                        prompt = (
                            f"Analyze this sales prospect and provide 3-5 actionable insights:\n"
                            f"Name: {profile['name']}\n"
                            f"Title: {profile['title']}\n"
                            f"Company: {profile['company']}\n"
                            f"Interactions: {engagement['total_interactions']}\n"
                            f"Reply rate: {engagement['reply_rate']:.0%}\n"
                            f"Sentiment: {profile['sentiment']}\n"
                            "Format each insight as a single sentence."
                        )
                        response = await self._reasoning.generate_response(
                            message=prompt,
                            context={"task": "prospect_research"},
                        )
                        insights = [line.strip("- ").strip() for line in response.split("\n") if line.strip()]
                    except Exception:
                        log.warning("AI insights failed")

                if not insights:
                    if engagement["reply_rate"] > 0.5:
                        insights.append("High engagement — prospect is responsive")
                    elif engagement["total_interactions"] > 5 and engagement["reply_rate"] == 0:
                        insights.append("Multiple touchpoints with no reply — consider changing approach")
                    if not prospect.title:
                        insights.append("Missing title — verify role before outreach")
                    if not prospect.linkedin_url:
                        insights.append("No LinkedIn profile — consider finding and adding it")

                return {
                    "profile": profile,
                    "engagement": engagement,
                    "insights": insights,
                }
        except Exception:
            log.exception("Error researching prospect")
            return {"error": "Research failed"}

    async def _research_company(self, params: dict[str, Any]) -> dict[str, Any]:
        """Research a company for sales context."""
        company_name = params.get("company")
        domain = params.get("domain")

        if not company_name and not domain:
            return {"error": "company or domain is required"}

        company_data: dict[str, Any] = {
            "name": company_name,
            "domain": domain,
        }

        # Enrich from CRM data — find all prospects at this company
        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                prospects, total = await repo.list_all(
                    company=company_name,
                    limit=50,
                )

                contacts = []
                titles = []
                for p in prospects:
                    contacts.append({
                        "id": p.id,
                        "name": f"{p.first_name} {p.last_name}",
                        "title": p.title,
                        "status": p.status,
                        "lead_score": p.lead_score,
                    })
                    if p.title:
                        titles.append(p.title)

                company_data["known_contacts"] = contacts
                company_data["total_contacts"] = total
                company_data["titles_present"] = list(set(titles))

                # Analyze organizational coverage
                has_exec = any(
                    kw in (t.lower() for t in titles)
                    for kw in ["ceo", "cto", "cfo", "vp", "vice president"]
                )
                company_data["exec_coverage"] = has_exec
                company_data["coverage_assessment"] = (
                    "Good executive coverage" if has_exec
                    else "Need to identify executive sponsors"
                )
        except Exception:
            log.warning("Could not enrich from CRM")

        # AI-powered company analysis
        if self._reasoning and company_name:
            try:
                prompt = (
                    f"Provide a brief sales-relevant analysis of {company_name}.\n"
                    "Include: likely pain points, buying triggers, recommended approach.\n"
                    "Keep it under 100 words."
                )
                response = await self._reasoning.generate_response(
                    message=prompt,
                    context={"task": "company_research"},
                )
                company_data["ai_analysis"] = response
            except Exception:
                log.warning("AI company analysis failed")

        return company_data

    async def _build_briefing(self, params: dict[str, Any]) -> dict[str, Any]:
        """Build a pre-meeting briefing document for a prospect."""
        prospect_id = params.get("prospect_id")
        deal_id = params.get("deal_id")

        if not prospect_id:
            return {"error": "prospect_id is required"}

        prospect_data = await self._research_prospect({"prospect_id": prospect_id})
        if "error" in prospect_data:
            return prospect_data

        profile = prospect_data.get("profile", {})
        engagement = prospect_data.get("engagement", {})

        company_data = {}
        if profile.get("company"):
            company_data = await self._research_company({"company": profile["company"]})

        # Build deal context if available
        deal_context = {}
        if deal_id:
            try:
                from seal_agent.db.repositories.deal_repo import DealRepository

                async with get_session() as session:
                    repo = DealRepository(session)
                    deal = await repo.get_by_id(deal_id)
                    if deal:
                        deal_context = {
                            "title": deal.title,
                            "stage": deal.stage,
                            "value": deal.value,
                            "probability": deal.probability,
                            "competitors": deal.competitors or [],
                        }
            except Exception:
                log.warning("Could not fetch deal for briefing")

        briefing = {
            "prospect": profile,
            "company": company_data,
            "engagement_summary": engagement,
            "deal": deal_context,
            "talking_points": prospect_data.get("insights", []),
            "prepared_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        }

        return briefing

    async def _find_talking_points(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate relevant talking points for a prospect conversation."""
        prospect_id = params.get("prospect_id")
        context = params.get("context", "general")

        if not prospect_id:
            return {"error": "prospect_id is required"}

        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                prospect = await repo.get_by_id(prospect_id)
                if not prospect:
                    return {"error": "Prospect not found"}

                name = f"{prospect.first_name} {prospect.last_name}"
                title = prospect.title or "professional"
                company = prospect.company or "their company"

                if self._reasoning:
                    try:
                        prompt = (
                            f"Generate 5 talking points for a {context} conversation with "
                            f"{name}, {title} at {company}.\n"
                            "Make them specific, actionable, and focused on value creation.\n"
                            "Format as a numbered list."
                        )
                        response = await self._reasoning.generate_response(
                            message=prompt,
                            context={"task": "talking_points", "meeting_type": context},
                        )
                        points = [
                            line.strip().lstrip("0123456789.-) ").strip()
                            for line in response.split("\n")
                            if line.strip() and line.strip()[0].isdigit()
                        ]
                        if points:
                            return {"prospect_id": prospect_id, "talking_points": points}
                    except Exception:
                        log.warning("AI talking points failed")

                # Fallback generic talking points
                points = [
                    f"Ask about current challenges at {company}",
                    f"Understand {name}'s priorities as {title}",
                    f"Share relevant case study for {company}'s industry",
                    "Identify decision-making process and timeline",
                    "Discuss potential ROI and success metrics",
                ]

                return {"prospect_id": prospect_id, "talking_points": points}
        except Exception:
            log.exception("Error finding talking points")
            return {"error": "Failed to generate talking points"}

    async def _competitive_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze competitive landscape for a deal."""
        deal_id = params.get("deal_id")
        competitors = params.get("competitors", [])

        if deal_id:
            try:
                from seal_agent.db.repositories.deal_repo import DealRepository

                async with get_session() as session:
                    repo = DealRepository(session)
                    deal = await repo.get_by_id(deal_id)
                    if deal and deal.competitors:
                        competitors = deal.competitors
            except Exception:
                pass

        if not competitors:
            return {
                "competitors": [],
                "analysis": "No competitors identified. Ask the prospect about alternatives they're evaluating.",
            }

        analysis = []
        for comp in competitors:
            analysis.append({
                "name": comp,
                "recommended_positioning": f"Focus on differentiators vs {comp}",
                "talk_track": f"Unlike {comp}, we offer deep integration and dedicated support.",
            })

        return {
            "competitors": competitors,
            "count": len(competitors),
            "analysis": analysis,
            "strategy": (
                "Multi-competitor deal — focus on unique value proposition and risk of choosing wrong vendor"
                if len(competitors) > 1
                else f"Single competitor ({competitors[0]}) — direct comparison on key differentiators"
            ),
        }
