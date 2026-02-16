"""Soul Engine — Loads and manages the agent's identity from soul/*.md files."""

from __future__ import annotations

from pathlib import Path

import markdown
import structlog

from seal_agent.config import settings

log = structlog.get_logger()


class SoulEngine:
    """Loads and provides access to the agent's soul system.

    The soul system is a collection of markdown files that define the agent's
    identity, communication style, operational rhythm, memory architecture,
    sales playbook, and self-learning rules.
    """

    def __init__(self) -> None:
        self.soul_dir = settings.soul_dir
        self.identity: str = ""
        self.heartbeat_config: str = ""
        self.style_guide: str = ""
        self.memory_architecture: str = ""
        self.playbook: str = ""
        self.evolution_rules: str = ""

    async def load(self) -> None:
        """Load all soul files from the soul directory."""
        log.info("Loading soul system", path=str(self.soul_dir))

        soul_files = {
            "soul.md": "identity",
            "heartbeat.md": "heartbeat_config",
            "style.md": "style_guide",
            "memory.md": "memory_architecture",
            "playbook.md": "playbook",
            "evolution.md": "evolution_rules",
        }

        for filename, attr in soul_files.items():
            filepath = self.soul_dir / filename
            if filepath.exists():
                content = filepath.read_text(encoding="utf-8")
                setattr(self, attr, content)
                log.info("Loaded soul file", file=filename)
            else:
                log.warning("Soul file not found", file=filename)

    def get_system_prompt(self) -> str:
        """Build the agent's system prompt from soul files.

        Returns:
            A comprehensive system prompt incorporating the agent's identity,
            style, and playbook.
        """
        return f"""You are Seal-Agent, a world-class AI sales agent.

## Your Identity
{self.identity}

## Your Communication Style
{self.style_guide}

## Your Sales Playbook
{self.playbook}

## Your Evolution Rules
{self.evolution_rules}

Follow your identity, style, and playbook in every interaction.
Always be learning and improving.
"""

    def get_soul_summary(self) -> dict[str, str]:
        """Return a summary of all loaded soul components."""
        return {
            "identity": self.identity[:200] + "..." if len(self.identity) > 200 else self.identity,
            "style": self.style_guide[:200] + "..."
            if len(self.style_guide) > 200
            else self.style_guide,
            "playbook": self.playbook[:200] + "..."
            if len(self.playbook) > 200
            else self.playbook,
        }
