"""Negotiation Skill — Deal negotiation strategy engine."""

from __future__ import annotations

from typing import Any

import structlog

from seal_agent.db.database import get_session
from seal_agent.db.repositories.deal_repo import DealRepository
from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()

# Negotiation tactics mapped to deal stages and scenarios
TACTICS = {
    "anchoring": {
        "description": "Set an ambitious initial offer to anchor the negotiation",
        "when": ["proposal", "negotiation"],
        "effectiveness": 0.7,
    },
    "value_framing": {
        "description": "Frame the deal in terms of ROI and business value, not cost",
        "when": ["discovery", "proposal", "negotiation"],
        "effectiveness": 0.85,
    },
    "social_proof": {
        "description": "Reference similar customers and their success stories",
        "when": ["qualification", "discovery", "proposal"],
        "effectiveness": 0.75,
    },
    "scarcity": {
        "description": "Create urgency with time-limited offers or capacity constraints",
        "when": ["negotiation"],
        "effectiveness": 0.6,
    },
    "concession_trade": {
        "description": "Offer a concession only in exchange for something of value",
        "when": ["negotiation"],
        "effectiveness": 0.8,
    },
    "silence": {
        "description": "After presenting an offer, wait for the prospect to respond first",
        "when": ["negotiation"],
        "effectiveness": 0.65,
    },
    "nibble": {
        "description": "Ask for small additional items after the main agreement",
        "when": ["negotiation"],
        "effectiveness": 0.5,
    },
    "walkaway": {
        "description": "Be willing to walk away if terms don't meet minimum thresholds",
        "when": ["negotiation"],
        "effectiveness": 0.7,
    },
}

# Common objection categories
OBJECTION_MAP = {
    "price": {
        "response_strategy": "value_framing",
        "talk_track": (
            "I understand budget is a concern. Let's look at the ROI — "
            "our customers typically see {roi_multiple}x return within {months} months. "
            "What would it mean for your team to achieve similar results?"
        ),
    },
    "timing": {
        "response_strategy": "scarcity",
        "talk_track": (
            "I appreciate that timing matters. The challenge is that every month without "
            "a solution costs your team in lost productivity. What if we started with a "
            "smaller scope to prove value quickly?"
        ),
    },
    "competition": {
        "response_strategy": "social_proof",
        "talk_track": (
            "Great that you're evaluating options. Our customers chose us because of "
            "{differentiator}. Would it help to hear directly from a customer in your space?"
        ),
    },
    "authority": {
        "response_strategy": "value_framing",
        "talk_track": (
            "Completely understand. To help build the case for your team, I can prepare "
            "a business case document with clear ROI projections. Would that be useful?"
        ),
    },
    "need": {
        "response_strategy": "social_proof",
        "talk_track": (
            "That's fair. Many of our best customers felt the same way initially. "
            "Once they saw how {use_case} improved, they wished they'd started sooner. "
            "Would a quick demo change the picture?"
        ),
    },
}


class NegotiationSkill(BaseSkill):
    """Handles deal negotiation strategy, objection responses, and closing tactics."""

    def __init__(self, reasoning_engine: Any = None) -> None:
        self._reasoning = reasoning_engine

    @property
    def name(self) -> str:
        return "negotiation"

    @property
    def description(self) -> str:
        return "Deal negotiation strategy, objection handling, and closing tactics"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "suggest_tactics": self._suggest_tactics,
            "handle_objection": self._handle_objection,
            "prepare_counter_offer": self._prepare_counter_offer,
            "analyze_leverage": self._analyze_leverage,
            "recommend_close": self._recommend_close,
        }
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return [
            "suggest_tactics", "handle_objection", "prepare_counter_offer",
            "analyze_leverage", "recommend_close",
        ]

    async def _suggest_tactics(self, params: dict[str, Any]) -> dict[str, Any]:
        """Suggest negotiation tactics based on deal stage and context."""
        deal_id = params.get("deal_id")
        stage = params.get("stage")

        if deal_id:
            try:
                async with get_session() as session:
                    repo = DealRepository(session)
                    deal = await repo.get_by_id(deal_id)
                    if deal:
                        stage = deal.stage
            except Exception:
                log.warning("Could not fetch deal for tactics")

        if not stage:
            stage = "negotiation"

        applicable = []
        for tactic_name, tactic in TACTICS.items():
            if stage in tactic["when"]:
                applicable.append({
                    "tactic": tactic_name,
                    "description": tactic["description"],
                    "effectiveness": tactic["effectiveness"],
                })

        applicable.sort(key=lambda t: t["effectiveness"], reverse=True)

        return {
            "stage": stage,
            "recommended_tactics": applicable,
            "primary_recommendation": applicable[0]["tactic"] if applicable else None,
        }

    async def _handle_objection(self, params: dict[str, Any]) -> dict[str, Any]:
        """Provide a response strategy for a specific objection."""
        objection_type = params.get("type", "").lower()
        objection_text = params.get("text", "")
        deal_id = params.get("deal_id")

        # Try to classify the objection if type not provided
        if not objection_type and objection_text:
            objection_type = self._classify_objection(objection_text)

        mapping = OBJECTION_MAP.get(objection_type)
        if not mapping:
            # Use AI if available for unclassified objections
            if self._reasoning and objection_text:
                try:
                    prompt = (
                        f"A sales prospect raised this objection: \"{objection_text}\"\n"
                        "Provide a concise, empathetic response that addresses the concern "
                        "and moves the conversation forward. Keep it under 100 words."
                    )
                    response = await self._reasoning.generate_response(
                        message=prompt,
                        context={"task": "objection_handling"},
                    )
                    return {
                        "objection_type": "unknown",
                        "response": response,
                        "strategy": "ai_generated",
                        "ai_generated": True,
                    }
                except Exception:
                    log.warning("AI objection handling failed")

            return {
                "objection_type": objection_type or "unknown",
                "error": "Unrecognized objection type. Supported: price, timing, competition, authority, need",
            }

        # Fill in template variables
        talk_track = mapping["talk_track"].format(
            roi_multiple=params.get("roi_multiple", "3-5"),
            months=params.get("months", "6"),
            differentiator=params.get("differentiator", "deep integration and superior support"),
            use_case=params.get("use_case", "their workflow"),
        )

        return {
            "objection_type": objection_type,
            "strategy": mapping["response_strategy"],
            "response": talk_track,
            "ai_generated": False,
        }

    async def _prepare_counter_offer(self, params: dict[str, Any]) -> dict[str, Any]:
        """Prepare a counter-offer based on deal parameters."""
        deal_id = params.get("deal_id")
        their_offer = params.get("their_offer", 0)
        our_target = params.get("our_target", 0)
        our_floor = params.get("floor", 0)

        if not their_offer or not our_target:
            return {"error": "their_offer and our_target are required"}

        gap = our_target - their_offer
        gap_pct = (gap / our_target * 100) if our_target else 0

        # Determine counter-offer strategy
        if their_offer >= our_target:
            return {
                "recommendation": "accept",
                "counter_offer": their_offer,
                "message": "Their offer meets or exceeds our target. Recommend accepting.",
            }

        if our_floor and their_offer < our_floor:
            return {
                "recommendation": "reject_or_reframe",
                "counter_offer": our_target,
                "gap_percentage": round(gap_pct, 1),
                "message": (
                    "Their offer is below our floor. Recommend reframing the "
                    "conversation around value rather than countering on price."
                ),
                "suggested_tactics": ["value_framing", "walkaway"],
            }

        # Calculate a strategic counter-offer (split the difference weighted toward target)
        counter = their_offer + (gap * 0.7)

        concessions = []
        if params.get("can_extend_terms"):
            concessions.append("Extended payment terms")
        if params.get("can_add_support"):
            concessions.append("Additional support hours")
        if params.get("can_add_training"):
            concessions.append("Complimentary training sessions")

        return {
            "recommendation": "counter",
            "their_offer": their_offer,
            "our_target": our_target,
            "counter_offer": round(counter, 2),
            "gap_percentage": round(gap_pct, 1),
            "possible_concessions": concessions,
            "message": (
                f"Counter at ${counter:,.2f} ({gap_pct:.1f}% gap from target). "
                "Consider bundling concessions to sweeten the deal."
            ),
        }

    async def _analyze_leverage(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze negotiation leverage for a deal."""
        deal_id = params.get("deal_id")
        if not deal_id:
            return {"error": "deal_id is required"}

        try:
            async with get_session() as session:
                repo = DealRepository(session)
                deal = await repo.get_by_id(deal_id)
                if not deal:
                    return {"error": "Deal not found"}

                leverage_factors = []
                score = 50  # Start neutral

                # Deal value signals
                if deal.value > 50000:
                    leverage_factors.append({"factor": "High deal value", "impact": +10})
                    score += 10

                # Competitor pressure
                if deal.competitors:
                    num_competitors = len(deal.competitors)
                    leverage_factors.append({
                        "factor": f"{num_competitors} competitor(s) in play",
                        "impact": -10 * num_competitors,
                    })
                    score -= 10 * num_competitors
                else:
                    leverage_factors.append({"factor": "No competitors identified", "impact": +15})
                    score += 15

                # Champion presence
                if deal.champion_id:
                    leverage_factors.append({"factor": "Internal champion identified", "impact": +15})
                    score += 15

                # Decision maker access
                if deal.decision_maker_id:
                    leverage_factors.append({"factor": "Decision maker engaged", "impact": +10})
                    score += 10

                # Pipeline stage
                if deal.stage in ("negotiation", "proposal"):
                    leverage_factors.append({"factor": "Advanced pipeline stage", "impact": +10})
                    score += 10

                score = max(0, min(100, score))

                if score >= 70:
                    position = "strong"
                elif score >= 40:
                    position = "neutral"
                else:
                    position = "weak"

                return {
                    "deal_id": deal_id,
                    "leverage_score": score,
                    "position": position,
                    "factors": leverage_factors,
                    "recommendation": (
                        "Hold firm on pricing" if position == "strong"
                        else "Consider creative structuring" if position == "neutral"
                        else "Focus on building value before negotiating price"
                    ),
                }
        except Exception:
            log.exception("Error analyzing leverage")
            return {"error": "Leverage analysis failed"}

    async def _recommend_close(self, params: dict[str, Any]) -> dict[str, Any]:
        """Recommend a closing technique based on deal context."""
        deal_id = params.get("deal_id")
        temperature = params.get("temperature", "warm")
        objections_resolved = params.get("objections_resolved", True)

        closing_techniques = {
            "assumptive": {
                "description": "Assume the sale and discuss next steps",
                "script": "Great, let's get the paperwork started. I'll send over the agreement today.",
                "best_when": "prospect_engaged",
            },
            "summary": {
                "description": "Summarize all agreed points and ask for commitment",
                "script": (
                    "So we've agreed on the scope, timeline, and investment. "
                    "Shall we move forward with the agreement?"
                ),
                "best_when": "all_objections_resolved",
            },
            "urgency": {
                "description": "Create urgency with a time-sensitive element",
                "script": (
                    "Our current pricing is available through end of month. "
                    "Would you like to lock it in?"
                ),
                "best_when": "deal_stalling",
            },
            "trial": {
                "description": "Offer a trial or pilot to reduce risk",
                "script": (
                    "How about we start with a 30-day pilot? That way your team can "
                    "experience the value firsthand before committing fully."
                ),
                "best_when": "prospect_hesitant",
            },
            "puppy_dog": {
                "description": "Let them try it with the expectation they won't give it back",
                "script": (
                    "Why don't we set you up with full access for two weeks? "
                    "If it doesn't deliver the value we discussed, no obligation."
                ),
                "best_when": "high_product_confidence",
            },
        }

        if temperature == "hot" and objections_resolved:
            recommended = "assumptive"
        elif objections_resolved:
            recommended = "summary"
        elif temperature == "cold":
            recommended = "trial"
        else:
            recommended = "urgency"

        technique = closing_techniques[recommended]

        return {
            "recommended_technique": recommended,
            "description": technique["description"],
            "script": technique["script"],
            "all_techniques": {
                name: t["description"] for name, t in closing_techniques.items()
            },
        }

    @staticmethod
    def _classify_objection(text: str) -> str:
        """Classify an objection from its text."""
        text_lower = text.lower()

        price_words = {"price", "cost", "expensive", "budget", "afford", "cheap", "discount"}
        timing_words = {"time", "timing", "later", "next quarter", "not now", "busy"}
        competition_words = {"competitor", "alternative", "other option", "comparing", "vendor"}
        authority_words = {"boss", "manager", "approval", "decision", "committee", "board"}
        need_words = {"need", "necessary", "why", "don't see", "not sure", "priority"}

        scores = {
            "price": sum(1 for w in price_words if w in text_lower),
            "timing": sum(1 for w in timing_words if w in text_lower),
            "competition": sum(1 for w in competition_words if w in text_lower),
            "authority": sum(1 for w in authority_words if w in text_lower),
            "need": sum(1 for w in need_words if w in text_lower),
        }

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        return best if scores[best] > 0 else "price"
