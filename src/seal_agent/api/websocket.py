"""WebSocket support for real-time agent communication."""

from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
log = structlog.get_logger()


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        log.info("WebSocket client connected", total=len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.remove(websocket)
        log.info("WebSocket client disconnected", total=len(self._connections))

    async def send_message(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        await websocket.send_json(data)

    async def broadcast(self, data: dict[str, Any]) -> None:
        disconnected = []
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self._connections.remove(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


@router.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time agent interaction.

    Messages from client:
        {"type": "chat", "message": "..."}
        {"type": "skill", "skill": "...", "action": "...", "params": {...}}
        {"type": "ping"}

    Messages to client:
        {"type": "response", "message": "..."}
        {"type": "skill_result", "data": {...}}
        {"type": "notification", "message": "..."}
        {"type": "pong"}
        {"type": "error", "message": "..."}
    """
    await manager.connect(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_message(websocket, {
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            msg_type = data.get("type", "")

            if msg_type == "ping":
                await manager.send_message(websocket, {"type": "pong"})

            elif msg_type == "chat":
                message = data.get("message", "")
                if not message:
                    await manager.send_message(websocket, {
                        "type": "error",
                        "message": "Empty message",
                    })
                    continue

                # Get agent from app state
                agent = websocket.app.state.agent  # type: ignore[attr-defined]
                try:
                    response = await agent.process_message(
                        message=message,
                        context=data.get("context"),
                    )
                    await manager.send_message(websocket, {
                        "type": "response",
                        "message": response,
                    })
                except Exception as e:
                    log.exception("WebSocket chat error")
                    await manager.send_message(websocket, {
                        "type": "error",
                        "message": f"Agent error: {str(e)}",
                    })

            elif msg_type == "skill":
                skill_name = data.get("skill", "")
                action = data.get("action", "")
                params = data.get("params", {})

                if not skill_name or not action:
                    await manager.send_message(websocket, {
                        "type": "error",
                        "message": "skill and action are required",
                    })
                    continue

                agent = websocket.app.state.agent  # type: ignore[attr-defined]
                try:
                    result = await agent.execute_skill(skill_name, action, params)
                    await manager.send_message(websocket, {
                        "type": "skill_result",
                        "skill": skill_name,
                        "action": action,
                        "data": result,
                    })
                except Exception as e:
                    log.exception("WebSocket skill error")
                    await manager.send_message(websocket, {
                        "type": "error",
                        "message": f"Skill error: {str(e)}",
                    })

            else:
                await manager.send_message(websocket, {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
