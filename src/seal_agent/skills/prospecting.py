"""Prospecting Skill — Lead generation and qualification."""

from __future__ import annotations

from typing import Any

import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.prospect_repo import ProspectRepository
from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()

# MEDDIC framework criteria weights
MEDDIC_WEIGHTS = {
    "metrics": 0.15,
    "economic_buyer": 0.20,
    "decision_criteria": 0.15,
    "decision_process": 0.15,
    "identify_pain": 0.20,
    "champion": 0.15,
}

# Default ICP (Ideal Customer Profile) scoring factors
ICP_FACTORS = {
    "has_email": 5,
    "has_phone": 3,
    "has_title": 5,
    "has_company": 10,
    "has_linkedin": 5,
    "title_vp_or_above": 15,
    "title_director": 10,
    "title_manager": 5,
}


class ProspectingSkill(BaseSkill):
    """Handles lead generation, scoring, and qualification."""

    @property
    def name(self) -> str:
        return "prospecting"

    @property
    def description(self) -> str:
        return "Lead generation, scoring, and qualification using MEDDIC/BANT frameworks"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "find_leads": self._find_leads,
            "score_lead": self._score_lead,
            "qualify_lead": self._qualify_lead,
            "research_prospect": self._research_prospect,
        }

        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}

        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return ["find_leads", "score_lead", "qualify_lead", "research_prospect"]

    async def _find_leads(self, params: dict[str, Any]) -> dict[str, Any]:
        """Find leads based on ideal customer profile criteria."""
        log.info("Finding leads", criteria=params)

        status_filter = params.get("status", "new")
        company_filter = params.get("company")
        limit = params.get("limit", 20)

        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                prospects, total = await repo.list_all(
                    status=status_filter,
                    company=company_filter,
                    limit=limit,
                )

                leads = []
                for p in prospects:
                    score_result = self._compute_lead_score(p)
                    leads.append({
                        "id": p.id,
                        "name": f"{p.first_name} {p.last_name}",
                        "email": p.email,
                        "company": p.company,
                        "title": p.title,
                        "score": score_result["score"],
                        "status": p.status,
                    })

                # Sort by score descending
                leads.sort(key=lambda x: x["score"], reverse=True)

                return {"leads": leads, "count": len(leads), "total_available": total}
        except Exception:
            log.exception("Error finding leads")
            return {"leads": [], "count": 0, "error": "Failed to query leads"}

    async def _score_lead(self, params: dict[str, Any]) -> dict[str, Any]:
        """Score a lead based on fit and intent signals."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}

        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                prospect = await repo.get_by_id(prospect_id)
                if not prospect:
                    return {"error": "Prospect not found", "score": 0, "factors": []}

                result = self._compute_lead_score(prospect)

                # Persist the score
                await repo.update(prospect_id, {"lead_score": result["score"]})

                return result
        except Exception:
            log.exception("Error scoring lead")
            return {"score": 0, "factors": [], "error": "Scoring failed"}

    @staticmethod
    def _compute_lead_score(prospect: Any) -> dict[str, Any]:
        """Compute a lead score from prospect attributes."""
        score = 0.0
        factors: list[dict[str, Any]] = []

        if prospect.email:
            score += ICP_FACTORS["has_email"]
            factors.append({"factor": "has_email", "points": ICP_FACTORS["has_email"]})

        if prospect.phone:
            score += ICP_FACTORS["has_phone"]
            factors.append({"factor": "has_phone", "points": ICP_FACTORS["has_phone"]})

        if prospect.title:
            score += ICP_FACTORS["has_title"]
            factors.append({"factor": "has_title", "points": ICP_FACTORS["has_title"]})

            title_lower = prospect.title.lower()
            title_words = set(title_lower.replace(",", " ").replace("-", " ").split())
            vp_keywords = {"vp", "ceo", "cto", "cfo", "coo", "cro"}
            if title_words & vp_keywords or "vice president" in title_lower:
                score += ICP_FACTORS["title_vp_or_above"]
                factors.append({"factor": "title_vp_or_above", "points": ICP_FACTORS["title_vp_or_above"]})
            elif "director" in title_lower:
                score += ICP_FACTORS["title_director"]
                factors.append({"factor": "title_director", "points": ICP_FACTORS["title_director"]})
            elif "manager" in title_lower:
                score += ICP_FACTORS["title_manager"]
                factors.append({"factor": "title_manager", "points": ICP_FACTORS["title_manager"]})

        if prospect.company:
            score += ICP_FACTORS["has_company"]
            factors.append({"factor": "has_company", "points": ICP_FACTORS["has_company"]})

        if prospect.linkedin_url:
            score += ICP_FACTORS["has_linkedin"]
            factors.append({"factor": "has_linkedin", "points": ICP_FACTORS["has_linkedin"]})

        # Normalize to 0-100
        max_possible = sum(ICP_FACTORS.values())
        normalized = min(100.0, (score / max_possible) * 100)

        return {"score": round(normalized, 1), "factors": factors, "raw_score": score}

    async def _qualify_lead(self, params: dict[str, Any]) -> dict[str, Any]:
        """Qualify a lead using MEDDIC framework."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}

        meddic_input = params.get("meddic", {})

        # Score each MEDDIC criterion (0-1 scale)
        meddic_scores: dict[str, float] = {}
        for criterion in MEDDIC_WEIGHTS:
            value = meddic_input.get(criterion)
            if value is True or value == "yes":
                meddic_scores[criterion] = 1.0
            elif value is False or value == "no":
                meddic_scores[criterion] = 0.0
            elif isinstance(value, (int, float)):
                meddic_scores[criterion] = min(1.0, max(0.0, float(value)))
            else:
                meddic_scores[criterion] = 0.0  # Not assessed

        # Calculate weighted qualification score
        total_score = sum(
            meddic_scores.get(c, 0.0) * w for c, w in MEDDIC_WEIGHTS.items()
        )

        qualified = total_score >= 0.6  # 60% threshold
        confidence = "high" if total_score >= 0.8 else "medium" if total_score >= 0.5 else "low"

        # Update prospect status if qualified
        if qualified:
            try:
                async with get_session() as session:
                    repo = ProspectRepository(session)
                    await repo.update(prospect_id, {"status": "qualified"})
            except Exception:
                log.exception("Error updating prospect status")

        return {
            "qualified": qualified,
            "score": round(total_score, 2),
            "confidence": confidence,
            "meddic": meddic_scores,
            "missing": [c for c in MEDDIC_WEIGHTS if meddic_scores.get(c, 0.0) == 0.0],
        }

    async def _research_prospect(self, params: dict[str, Any]) -> dict[str, Any]:
        """Research a prospect — gathers all available data from memory."""
        prospect_id = params.get("prospect_id")
        if not prospect_id:
            return {"error": "prospect_id is required"}

        try:
            async with get_session() as session:
                repo = ProspectRepository(session)
                prospect = await repo.get_by_id(prospect_id)
                if not prospect:
                    return {"error": "Prospect not found"}

                from seal_agent.db.repositories.interaction_repo import InteractionRepository

                interaction_repo = InteractionRepository(session)
                interactions = await interaction_repo.list_by_prospect(prospect_id, limit=20)

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

                insights = []
                if interactions:
                    total = len(interactions)
                    replied_count = sum(1 for i in interactions if i.replied)
                    insights.append(f"Total interactions: {total}")
                    insights.append(f"Reply rate: {replied_count/total*100:.0f}%")
                    insights.append(f"Last contact: {interactions[0].created_at.isoformat() if interactions[0].created_at else 'unknown'}")

                    channels = set(i.channel for i in interactions)
                    insights.append(f"Channels used: {', '.join(channels)}")
                else:
                    insights.append("No prior interactions — cold prospect")

                return {
                    "profile": profile,
                    "insights": insights,
                    "interaction_count": len(interactions),
                }
        except Exception:
            log.exception("Error researching prospect")
            return {"profile": {}, "insights": ["Research failed"], "error": "Research error"}
