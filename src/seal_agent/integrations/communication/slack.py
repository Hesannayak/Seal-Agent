"""Slack integration — Send notifications and receive messages via Slack."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.config import settings
from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

SLACK_API_BASE = "https://slack.com/api"


class SlackIntegration(BaseIntegration):
    """Slack integration for team notifications and internal communication."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False
        self._bot_user_id: str | None = None

    @property
    def name(self) -> str:
        return "slack"

    @property
    def category(self) -> str:
        return "communication"

    async def connect(self, credentials: dict[str, str]) -> bool:
        token = credentials.get("bot_token", settings.slack_bot_token)
        if not token:
            log.warning("Slack integration not configured — missing bot token")
            return False

        self._client = httpx.AsyncClient(
            base_url=SLACK_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            timeout=15.0,
        )

        try:
            response = await self._client.post("auth.test")
            data = response.json()
            if data.get("ok"):
                self._connected = True
                self._bot_user_id = data.get("user_id")
                log.info("Slack integration connected", bot_user=self._bot_user_id)
                return True
            else:
                log.error("Slack auth failed", error=data.get("error"))
                return False
        except Exception:
            log.exception("Failed to connect Slack integration")
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        log.info("Slack integration disconnected")

    async def health_check(self) -> bool:
        if not self._client or not self._connected:
            return False
        try:
            response = await self._client.post("auth.test")
            return response.json().get("ok", False)
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "send_message": self._send_message,
            "send_notification": self._send_notification,
            "list_channels": self._list_channels,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for Slack")
        return await handler(params)

    async def _send_message(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send a message to a Slack channel."""
        if not self._client:
            return {"error": "Not connected"}

        channel = params.get("channel")
        text = params.get("text", "")
        blocks = params.get("blocks")

        if not channel:
            return {"error": "channel is required"}

        payload: dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks

        try:
            response = await self._client.post("chat.postMessage", json=payload)
            data = response.json()
            if data.get("ok"):
                return {
                    "sent": True,
                    "channel": data.get("channel"),
                    "ts": data.get("ts"),
                }
            else:
                return {"sent": False, "error": data.get("error")}
        except Exception as e:
            return {"sent": False, "error": str(e)}

    async def _send_notification(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send a formatted notification to a Slack channel."""
        if not self._client:
            return {"error": "Not connected"}

        channel = params.get("channel")
        title = params.get("title", "Notification")
        message = params.get("message", "")
        level = params.get("level", "info")  # info, warning, success, error

        color_map = {
            "info": "#2196F3",
            "warning": "#FF9800",
            "success": "#4CAF50",
            "error": "#F44336",
        }

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n{message}",
                },
            },
        ]

        return await self._send_message({
            "channel": channel,
            "text": f"{title}: {message}",
            "blocks": blocks,
        })

    async def _list_channels(self, params: dict[str, Any]) -> dict[str, Any]:
        """List available Slack channels."""
        if not self._client:
            return {"error": "Not connected"}

        try:
            response = await self._client.get(
                "conversations.list",
                params={"limit": params.get("limit", 100), "types": "public_channel"},
            )
            data = response.json()
            if data.get("ok"):
                channels = [
                    {"id": ch["id"], "name": ch["name"]}
                    for ch in data.get("channels", [])
                ]
                return {"channels": channels, "count": len(channels)}
            else:
                return {"error": data.get("error"), "channels": []}
        except Exception as e:
            return {"error": str(e), "channels": []}
