"""Agent control API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class MessageRequest(BaseModel):
    message: str
    context: dict | None = None


class MessageResponse(BaseModel):
    response: str
    metadata: dict | None = None


@router.post("/chat", response_model=MessageResponse)
async def chat(request: Request, body: MessageRequest) -> MessageResponse:
    """Send a message to the agent and get a response."""
    agent = request.app.state.agent
    response = await agent.process_message(body.message, body.context)
    return MessageResponse(response=response)


@router.get("/status")
async def agent_status(request: Request) -> dict:
    """Get the agent's current status."""
    agent = request.app.state.agent
    return {
        "running": agent._running,
        "soul_loaded": bool(agent.soul.identity),
    }


@router.get("/soul")
async def get_soul(request: Request) -> dict:
    """Get a summary of the agent's soul configuration."""
    agent = request.app.state.agent
    return agent.soul.get_soul_summary()
