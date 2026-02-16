"""Microsoft Teams integration — Send messages and notifications."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


class TeamsIntegration(BaseIntegration):
    """Microsoft Teams integration for messaging and notifications via Graph API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    @property
    def name(self) -> str:
        return "teams"

    @property
    def category(self) -> str:
        return "communication"

    async def connect(self, credentials: dict[str, str]) -> bool:
        access_token = credentials.get("access_token", "")
        if not access_token:
            log.warning("Teams not configured — missing access token")
            return False

        self._client = httpx.AsyncClient(
            base_url=GRAPH_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=20.0,
        )

        try:
            resp = await self._client.get("/me")
            resp.raise_for_status()
            user = resp.json()
            self._connected = True
            log.info("Teams connected", user=user.get("displayName"))
            return True
        except Exception:
            log.exception("Failed to connect Teams")
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def health_check(self) -> bool:
        if not self._client or not self._connected:
            return False
        try:
            resp = await self._client.get("/me")
            return resp.status_code == 200
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "send_message": self._send_message,
            "send_channel_message": self._send_channel_message,
            "list_teams": self._list_teams,
            "list_channels": self._list_channels,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for Teams")
        return await handler(params)

    async def _send_message(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send a direct chat message."""
        if not self._client:
            return {"error": "Not connected"}
        chat_id = params.get("chat_id", "")
        content = params.get("content", "")
        if not chat_id or not content:
            return {"error": "chat_id and content are required"}

        try:
            resp = await self._client.post(f"/chats/{chat_id}/messages", json={
                "body": {"content": content, "contentType": "text"},
            })
            resp.raise_for_status()
            msg = resp.json()
            return {"id": msg.get("id"), "sent": True}
        except httpx.HTTPStatusError as e:
            return {"error": f"Teams API error: {e.response.status_code}"}

    async def _send_channel_message(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send a message to a Teams channel."""
        if not self._client:
            return {"error": "Not connected"}
        team_id = params.get("team_id", "")
        channel_id = params.get("channel_id", "")
        content = params.get("content", "")
        if not team_id or not channel_id or not content:
            return {"error": "team_id, channel_id, and content are required"}

        try:
            resp = await self._client.post(
                f"/teams/{team_id}/channels/{channel_id}/messages",
                json={"body": {"content": content, "contentType": "text"}},
            )
            resp.raise_for_status()
            msg = resp.json()
            return {"id": msg.get("id"), "sent": True}
        except httpx.HTTPStatusError as e:
            return {"error": f"Teams API error: {e.response.status_code}"}

    async def _list_teams(self, params: dict[str, Any]) -> dict[str, Any]:
        """List joined teams."""
        if not self._client:
            return {"error": "Not connected"}
        try:
            resp = await self._client.get("/me/joinedTeams")
            resp.raise_for_status()
            teams = [
                {"id": t["id"], "name": t.get("displayName", "")}
                for t in resp.json().get("value", [])
            ]
            return {"teams": teams, "count": len(teams)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Teams API error: {e.response.status_code}"}

    async def _list_channels(self, params: dict[str, Any]) -> dict[str, Any]:
        """List channels in a team."""
        if not self._client:
            return {"error": "Not connected"}
        team_id = params.get("team_id", "")
        if not team_id:
            return {"error": "team_id is required"}
        try:
            resp = await self._client.get(f"/teams/{team_id}/channels")
            resp.raise_for_status()
            channels = [
                {"id": c["id"], "name": c.get("displayName", "")}
                for c in resp.json().get("value", [])
            ]
            return {"channels": channels, "count": len(channels)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Teams API error: {e.response.status_code}"}
