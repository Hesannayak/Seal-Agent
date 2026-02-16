"""Main Seal-Agent orchestrator."""

from __future__ import annotations

import structlog

from seal_agent.core.soul_engine import SoulEngine
from seal_agent.core.heartbeat import HeartbeatEngine
from seal_agent.core.memory import MemoryEngine
from seal_agent.core.evolution import EvolutionEngine
from seal_agent.core.reasoning import ReasoningEngine
from seal_agent.skills.base import BaseSkill
from seal_agent.skills.prospecting import ProspectingSkill
from seal_agent.skills.outreach import OutreachSkill
from seal_agent.skills.deal_management import DealManagementSkill
from seal_agent.skills.follow_up import FollowUpSkill
from seal_agent.skills.negotiation import NegotiationSkill
from seal_agent.skills.research import ResearchSkill
from seal_agent.skills.proposal import ProposalSkill
from seal_agent.skills.scheduling import SchedulingSkill
from seal_agent.skills.analytics import AnalyticsSkill
from seal_agent.skills.objection import ObjectionSkill

log = structlog.get_logger()


class SealAgent:
    """The main Seal-Agent orchestrator that coordinates all subsystems."""

    def __init__(self) -> None:
        self.soul = SoulEngine()
        self.heartbeat = HeartbeatEngine()
        self.memory = MemoryEngine()
        self.evolution = EvolutionEngine()
        self.reasoning = ReasoningEngine()
        self._running = False

        # Skills registry
        self.skills: dict[str, BaseSkill] = {}

    async def initialize(self) -> None:
        """Initialize all agent subsystems."""
        log.info("Initializing agent subsystems")

        # Load the agent's soul (identity, style, playbook)
        await self.soul.load()

        # Initialize memory system
        await self.memory.initialize()

        # Initialize evolution tracking
        await self.evolution.initialize()

        # Initialize reasoning engine with soul context
        await self.reasoning.initialize(soul=self.soul)

        # Register skills
        self.skills = {
            "prospecting": ProspectingSkill(),
            "outreach": OutreachSkill(reasoning_engine=self.reasoning),
            "deal_management": DealManagementSkill(),
            "follow_up": FollowUpSkill(reasoning_engine=self.reasoning),
            "negotiation": NegotiationSkill(reasoning_engine=self.reasoning),
            "research": ResearchSkill(reasoning_engine=self.reasoning),
            "proposal": ProposalSkill(reasoning_engine=self.reasoning),
            "scheduling": SchedulingSkill(),
            "analytics": AnalyticsSkill(),
            "objection": ObjectionSkill(reasoning_engine=self.reasoning),
        }

        log.info("All subsystems initialized", skills=list(self.skills.keys()))

    async def run(self) -> None:
        """Start the agent's main loop."""
        self._running = True
        log.info("Seal-Agent is now running")

        # Start the heartbeat (autonomous task scheduler)
        await self.heartbeat.start(agent=self)

    async def shutdown(self) -> None:
        """Gracefully shut down all subsystems."""
        self._running = False
        log.info("Shutting down agent subsystems")

        await self.heartbeat.stop()
        await self.memory.close()
        await self.evolution.close()

        log.info("Seal-Agent shut down complete")

    async def process_message(self, message: str, context: dict | None = None) -> str:
        """Process an incoming message and generate a response.

        Args:
            message: The incoming message text.
            context: Optional context (prospect info, channel, etc.)

        Returns:
            The agent's response.
        """
        # Retrieve relevant memories
        memories = await self.memory.recall(message, context)

        # Generate response using reasoning engine
        response = await self.reasoning.generate_response(
            message=message,
            context=context,
            memories=memories,
            soul=self.soul,
        )

        # Store the interaction in memory
        await self.memory.store_interaction(
            message=message,
            response=response,
            context=context,
        )

        # Log for evolution tracking
        await self.evolution.log_interaction(
            message=message,
            response=response,
            context=context,
        )

        return response

    async def execute_skill(
        self, skill_name: str, action: str, params: dict
    ) -> dict:
        """Execute a skill action.

        Args:
            skill_name: Name of the skill to execute.
            action: Action within the skill.
            params: Parameters for the action.

        Returns:
            The skill result.
        """
        skill = self.skills.get(skill_name)
        if not skill:
            return {"error": f"Unknown skill: {skill_name}"}

        return await skill.execute(action, params)
