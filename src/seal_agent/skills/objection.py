"""Objection Handling Skill — Context-aware objection responses."""

from __future__ import annotations

from typing import Any

import structlog

from seal_agent.skills.base import BaseSkill

log = structlog.get_logger()

# Comprehensive objection playbook
OBJECTION_PLAYBOOK = {
    "price": {
        "category": "Budget & Cost",
        "responses": [
            {
                "scenario": "too_expensive",
                "response": (
                    "I understand budget is important. Let me share the ROI our customers typically see — "
                    "most achieve {roi}x return within the first year. What would it mean for your team "
                    "to save {hours} hours per week?"
                ),
                "follow_up": "Would it help to see a detailed ROI analysis for your specific situation?",
            },
            {
                "scenario": "competitor_cheaper",
                "response": (
                    "That's fair — price matters. What I'd encourage is comparing total cost of ownership, "
                    "including implementation time, support quality, and hidden fees. "
                    "Our customers often find we're actually more cost-effective long-term."
                ),
                "follow_up": "Would a side-by-side comparison be helpful?",
            },
            {
                "scenario": "no_budget",
                "response": (
                    "I appreciate you being upfront about that. Many of our customers started by proving "
                    "value with a smaller engagement, which then justified the budget. "
                    "Could we explore a phased approach?"
                ),
                "follow_up": "When does your next budget cycle start?",
            },
        ],
        "techniques": ["value_reframe", "roi_justification", "phased_approach"],
    },
    "timing": {
        "category": "Timing & Priority",
        "responses": [
            {
                "scenario": "not_now",
                "response": (
                    "Completely understand — timing is everything. The question I'd ask is: "
                    "what's the cost of waiting? Every month without a solution means continued "
                    "inefficiency. What if we started small to prove value quickly?"
                ),
                "follow_up": "Can we schedule a follow-up for next month to revisit?",
            },
            {
                "scenario": "too_busy",
                "response": (
                    "I hear that a lot, and it makes sense. The good news is our implementation "
                    "is designed to be lightweight — most teams are up and running in under a week "
                    "with minimal disruption."
                ),
                "follow_up": "Would a 15-minute overview be possible? I'll make it worth your time.",
            },
            {
                "scenario": "next_quarter",
                "response": (
                    "That works. To make the most of that timeline, we could start the evaluation "
                    "now so you're ready to move quickly when Q{quarter} starts. Would a brief "
                    "discovery call make sense?"
                ),
                "follow_up": "I'll set a reminder to follow up — what's the best date?",
            },
        ],
        "techniques": ["cost_of_inaction", "minimize_effort", "pre_commitment"],
    },
    "competition": {
        "category": "Competitive",
        "responses": [
            {
                "scenario": "using_competitor",
                "response": (
                    "Great that you have a solution in place. Many of our customers switched from "
                    "{competitor} because of {differentiator}. Would you be open to seeing how "
                    "we compare on the areas that matter most to you?"
                ),
                "follow_up": "What are the top 3 things you'd improve about your current solution?",
            },
            {
                "scenario": "evaluating_alternatives",
                "response": (
                    "Smart to evaluate options. What criteria are most important in your decision? "
                    "I want to make sure we address exactly what matters to your team."
                ),
                "follow_up": "Would it help to speak with a customer in your industry?",
            },
        ],
        "techniques": ["competitive_displacement", "criteria_shaping", "social_proof"],
    },
    "authority": {
        "category": "Decision Process",
        "responses": [
            {
                "scenario": "need_approval",
                "response": (
                    "Of course — I'd expect that for a decision like this. To help build the case, "
                    "I can prepare a business justification document with ROI projections. "
                    "Would that be useful for your conversation with {stakeholder}?"
                ),
                "follow_up": "Would it help if I joined that meeting to answer technical questions?",
            },
            {
                "scenario": "not_decision_maker",
                "response": (
                    "I appreciate you being transparent. You're clearly the expert on this area though. "
                    "Would it make sense for us to put together a joint recommendation for the "
                    "decision-maker based on your evaluation?"
                ),
                "follow_up": "What would the decision-maker need to see to say yes?",
            },
        ],
        "techniques": ["champion_building", "business_case", "executive_alignment"],
    },
    "need": {
        "category": "Need & Fit",
        "responses": [
            {
                "scenario": "dont_need_it",
                "response": (
                    "That's fair feedback. Often what I find is that teams have adapted to "
                    "workarounds that feel normal but are actually costing significant time. "
                    "Would you be open to a brief assessment to quantify the impact?"
                ),
                "follow_up": "What's your team's biggest time sink right now?",
            },
            {
                "scenario": "happy_with_current",
                "response": (
                    "Glad to hear things are working well. Most of our best customers felt the same way "
                    "before they saw what was possible. Would a quick benchmark comparison be valuable, "
                    "even if just for your own reference?"
                ),
                "follow_up": "What would 'even better' look like for your team?",
            },
        ],
        "techniques": ["pain_discovery", "benchmark_comparison", "vision_setting"],
    },
    "trust": {
        "category": "Trust & Risk",
        "responses": [
            {
                "scenario": "too_new",
                "response": (
                    "That's a valid concern. While we're growing quickly, our customer retention "
                    "rate is {retention_rate}% and we're backed by {backing}. "
                    "Would a customer reference in your industry help build confidence?"
                ),
                "follow_up": "What would you need to feel comfortable moving forward?",
            },
            {
                "scenario": "security_concerns",
                "response": (
                    "Security is paramount for us too. We're SOC 2 Type II certified, "
                    "use end-to-end encryption, and can provide our security whitepaper. "
                    "Would your security team like to review our compliance documentation?"
                ),
                "follow_up": "Should I set up a call between our security teams?",
            },
        ],
        "techniques": ["social_proof", "risk_reversal", "compliance_documentation"],
    },
}


class ObjectionSkill(BaseSkill):
    """Handles prospect objections with context-aware, empathetic responses."""

    def __init__(self, reasoning_engine: Any = None) -> None:
        self._reasoning = reasoning_engine

    @property
    def name(self) -> str:
        return "objection"

    @property
    def description(self) -> str:
        return "Context-aware objection handling with empathetic, strategic responses"

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "handle": self._handle_objection,
            "classify": self._classify_objection,
            "get_playbook": self._get_playbook,
            "suggest_response": self._suggest_response,
            "list_techniques": self._list_techniques,
        }
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(params)

    async def get_available_actions(self) -> list[str]:
        return ["handle", "classify", "get_playbook", "suggest_response", "list_techniques"]

    async def _handle_objection(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle a specific objection with a tailored response."""
        objection_text = params.get("text", "")
        objection_type = params.get("type", "")
        scenario = params.get("scenario", "")

        if not objection_text and not objection_type:
            return {"error": "Either text or type is required"}

        # Classify if not provided
        if not objection_type:
            classification = self._do_classify(objection_text)
            objection_type = classification["type"]

        playbook = OBJECTION_PLAYBOOK.get(objection_type)
        if not playbook:
            # Try AI for unknown objections
            if self._reasoning and objection_text:
                try:
                    prompt = (
                        f"A prospect said: \"{objection_text}\"\n"
                        "Provide an empathetic, strategic sales response that:\n"
                        "1. Acknowledges their concern\n"
                        "2. Reframes the issue\n"
                        "3. Provides a path forward\n"
                        "Keep it under 80 words."
                    )
                    response = await self._reasoning.generate_response(
                        message=prompt,
                        context={"task": "objection_handling"},
                    )
                    return {
                        "objection_type": "custom",
                        "response": response,
                        "follow_up": "What would need to change for this to move forward?",
                        "ai_generated": True,
                    }
                except Exception:
                    pass

            return {"error": f"Unknown objection type: {objection_type}"}

        # Find best matching scenario
        responses = playbook["responses"]
        if scenario:
            matched = [r for r in responses if r["scenario"] == scenario]
            response_entry = matched[0] if matched else responses[0]
        else:
            response_entry = self._best_match_response(objection_text, responses)

        # Fill template variables
        response_text = response_entry["response"].format(
            roi=params.get("roi", "3-5"),
            hours=params.get("hours", "10"),
            competitor=params.get("competitor", "your current solution"),
            differentiator=params.get("differentiator", "deeper integration and better support"),
            stakeholder=params.get("stakeholder", "your team"),
            quarter=params.get("quarter", "next"),
            retention_rate=params.get("retention_rate", "95"),
            backing=params.get("backing", "leading investors"),
        )

        return {
            "objection_type": objection_type,
            "category": playbook["category"],
            "scenario": response_entry["scenario"],
            "response": response_text,
            "follow_up": response_entry["follow_up"],
            "techniques": playbook["techniques"],
            "ai_generated": False,
        }

    async def _classify_objection(self, params: dict[str, Any]) -> dict[str, Any]:
        """Classify an objection from its text."""
        text = params.get("text", "")
        if not text:
            return {"error": "text is required"}

        return self._do_classify(text)

    async def _get_playbook(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get the full objection playbook or a specific category."""
        category = params.get("type")

        if category:
            playbook = OBJECTION_PLAYBOOK.get(category)
            if not playbook:
                return {"error": f"Unknown category: {category}"}
            return {
                "type": category,
                "category": playbook["category"],
                "scenarios": [r["scenario"] for r in playbook["responses"]],
                "techniques": playbook["techniques"],
            }

        return {
            "categories": {
                key: {
                    "name": val["category"],
                    "scenarios": len(val["responses"]),
                    "techniques": val["techniques"],
                }
                for key, val in OBJECTION_PLAYBOOK.items()
            }
        }

    async def _suggest_response(self, params: dict[str, Any]) -> dict[str, Any]:
        """Suggest multiple response options for an objection."""
        objection_type = params.get("type", "price")

        playbook = OBJECTION_PLAYBOOK.get(objection_type)
        if not playbook:
            return {"error": f"Unknown type: {objection_type}"}

        suggestions = []
        for resp in playbook["responses"]:
            suggestions.append({
                "scenario": resp["scenario"],
                "response_preview": resp["response"][:100] + "...",
                "follow_up": resp["follow_up"],
            })

        return {
            "objection_type": objection_type,
            "suggestions": suggestions,
            "recommended": suggestions[0]["scenario"] if suggestions else None,
        }

    async def _list_techniques(self, params: dict[str, Any]) -> dict[str, Any]:
        """List all available objection handling techniques."""
        all_techniques = set()
        for playbook in OBJECTION_PLAYBOOK.values():
            all_techniques.update(playbook["techniques"])

        return {
            "techniques": sorted(all_techniques),
            "count": len(all_techniques),
        }

    @staticmethod
    def _do_classify(text: str) -> dict[str, Any]:
        """Classify objection text into a category."""
        text_lower = text.lower()

        keyword_map = {
            "price": ["price", "cost", "expensive", "budget", "afford", "cheap", "discount", "money"],
            "timing": ["time", "timing", "later", "quarter", "not now", "busy", "wait", "ready"],
            "competition": ["competitor", "alternative", "already using", "other", "vendor", "comparing"],
            "authority": ["boss", "manager", "approval", "decision", "committee", "board", "stakeholder"],
            "need": ["don't need", "not sure", "why", "necessary", "priority", "happy with"],
            "trust": ["new", "risk", "security", "trust", "reliable", "proven", "concern"],
        }

        scores: dict[str, int] = {}
        for category, keywords in keyword_map.items():
            scores[category] = sum(1 for kw in keywords if kw in text_lower)

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        confidence = "high" if scores[best] >= 3 else "medium" if scores[best] >= 1 else "low"

        return {
            "type": best if scores[best] > 0 else "price",
            "confidence": confidence,
            "all_scores": scores,
        }

    @staticmethod
    def _best_match_response(text: str, responses: list[dict]) -> dict:
        """Find the best matching response for an objection text."""
        if not text:
            return responses[0]

        text_lower = text.lower()
        best = responses[0]
        best_score = 0

        for resp in responses:
            scenario_words = resp["scenario"].replace("_", " ").split()
            score = sum(1 for w in scenario_words if w in text_lower)
            if score > best_score:
                best_score = score
                best = resp

        return best
