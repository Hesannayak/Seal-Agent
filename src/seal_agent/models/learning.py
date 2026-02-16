"""Learning data model — Records for the evolution/self-learning system."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class LearningType(StrEnum):
    WIN_ANALYSIS = "win_analysis"
    LOSS_ANALYSIS = "loss_analysis"
    STRATEGY_MUTATION = "strategy_mutation"
    AB_TEST_RESULT = "ab_test_result"
    FEEDBACK = "feedback"
    PATTERN_DISCOVERY = "pattern_discovery"


class Outcome(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class LearningRecord(BaseModel):
    """A record of something the agent learned from an interaction or outcome."""

    id: str | None = None
    learning_type: LearningType
    outcome: Outcome = Outcome.NEUTRAL

    # Context
    deal_id: str | None = None
    prospect_id: str | None = None
    strategy_used: str | None = None

    # What was learned
    observation: str
    insight: str | None = None
    action_taken: str | None = None

    # Metrics
    confidence: float = 0.5
    impact_score: float = 0.0

    # Metadata
    tags: list[str] = []
    created_at: datetime | None = None


class ABTestRecord(BaseModel):
    """Tracks A/B test variants for messaging and strategies."""

    id: str | None = None
    test_name: str
    variant_a: str
    variant_b: str
    metric: str = "reply_rate"

    # Results
    variant_a_count: int = 0
    variant_a_successes: int = 0
    variant_b_count: int = 0
    variant_b_successes: int = 0

    # Status
    winner: str | None = None
    confidence_level: float = 0.0
    is_complete: bool = False

    created_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def variant_a_rate(self) -> float:
        return (self.variant_a_successes / self.variant_a_count * 100) if self.variant_a_count else 0.0

    @property
    def variant_b_rate(self) -> float:
        return (self.variant_b_successes / self.variant_b_count * 100) if self.variant_b_count else 0.0
