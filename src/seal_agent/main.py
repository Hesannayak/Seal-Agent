"""Seal-Agent application entry point."""

import asyncio
import structlog

from seal_agent.config import settings
from seal_agent.core.agent import SealAgent

log = structlog.get_logger()


async def main() -> None:
    """Initialize and start the Seal-Agent."""
    log.info("Starting Seal-Agent", version=settings.app_version)

    agent = SealAgent()
    await agent.initialize()

    log.info("Seal-Agent initialized successfully")

    # Keep the agent running
    try:
        await agent.run()
    except KeyboardInterrupt:
        log.info("Shutting down Seal-Agent")
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
