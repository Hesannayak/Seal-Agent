"""FastAPI application setup."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from seal_agent.config import settings
from seal_agent.core.agent import SealAgent
from seal_agent.api.routes import agent as agent_routes
from seal_agent.api.routes import prospects as prospect_routes
from seal_agent.api.routes import deals as deal_routes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application startup and shutdown lifecycle."""
    # Startup
    seal_agent = SealAgent()
    await seal_agent.initialize()
    app.state.agent = seal_agent

    yield

    # Shutdown
    await seal_agent.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="The Claude of Sales — AI-powered sales agent API",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Register route modules
    app.include_router(agent_routes.router, prefix="/api/agent", tags=["Agent"])
    app.include_router(prospect_routes.router, prefix="/api/prospects", tags=["Prospects"])
    app.include_router(deal_routes.router, prefix="/api/deals", tags=["Deals"])

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "agent": settings.app_name}

    return app
