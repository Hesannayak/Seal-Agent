"""Integration management API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Registry of available integrations (populated at startup)
_integrations: dict[str, Any] = {}


class ConnectRequest(BaseModel):
    credentials: dict[str, str]


class ExecuteRequest(BaseModel):
    action: str
    params: dict[str, Any] = {}


def register_integrations(integrations: dict[str, Any]) -> None:
    """Register integration instances for API access."""
    global _integrations
    _integrations = integrations


@router.get("/")
async def list_integrations() -> dict[str, Any]:
    """List all available integrations and their status."""
    result = []
    for name, integration in _integrations.items():
        healthy = False
        try:
            healthy = await integration.health_check()
        except Exception:
            pass
        result.append({
            "name": integration.name,
            "category": integration.category,
            "connected": healthy,
        })
    return {"integrations": result, "count": len(result)}


@router.post("/{name}/connect")
async def connect_integration(name: str, request: ConnectRequest) -> dict[str, Any]:
    """Connect an integration with credentials."""
    integration = _integrations.get(name)
    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration '{name}' not found")

    success = await integration.connect(request.credentials)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to connect integration")

    return {"name": name, "status": "connected"}


@router.post("/{name}/disconnect")
async def disconnect_integration(name: str) -> dict[str, Any]:
    """Disconnect an integration."""
    integration = _integrations.get(name)
    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration '{name}' not found")

    await integration.disconnect()
    return {"name": name, "status": "disconnected"}


@router.get("/{name}/health")
async def integration_health(name: str) -> dict[str, Any]:
    """Check health of a specific integration."""
    integration = _integrations.get(name)
    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration '{name}' not found")

    healthy = await integration.health_check()
    return {"name": name, "healthy": healthy}


@router.post("/{name}/execute")
async def execute_integration_action(name: str, request: ExecuteRequest) -> dict[str, Any]:
    """Execute an action on an integration."""
    integration = _integrations.get(name)
    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration '{name}' not found")

    try:
        result = await integration.execute(request.action, request.params)
        return result
    except NotImplementedError as e:
        raise HTTPException(status_code=400, detail=str(e))
