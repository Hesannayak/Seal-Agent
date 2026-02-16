"""WhatsApp Business integration — Send messages via WhatsApp Cloud API."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

WHATSAPP_API_BASE = "https://graph.facebook.com/v18.0"


class WhatsAppIntegration(BaseIntegration):
    """WhatsApp Business integration for messaging prospects via Cloud API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False
        self._phone_number_id: str = ""

    @property
    def name(self) -> str:
        return "whatsapp"

    @property
    def category(self) -> str:
        return "communication"

    async def connect(self, credentials: dict[str, str]) -> bool:
        access_token = credentials.get("access_token", "")
        self._phone_number_id = credentials.get("phone_number_id", "")
        if not access_token or not self._phone_number_id:
            log.warning("WhatsApp not configured — missing access_token or phone_number_id")
            return False

        self._client = httpx.AsyncClient(
            base_url=WHATSAPP_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=20.0,
        )

        try:
            resp = await self._client.get(f"/{self._phone_number_id}")
            resp.raise_for_status()
            data = resp.json()
            self._connected = True
            log.info("WhatsApp connected", phone=data.get("display_phone_number"))
            return True
        except Exception:
            log.exception("Failed to connect WhatsApp")
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
            resp = await self._client.get(f"/{self._phone_number_id}")
            return resp.status_code == 200
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "send_text": self._send_text,
            "send_template": self._send_template,
            "mark_read": self._mark_read,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for WhatsApp")
        return await handler(params)

    async def _send_text(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send a text message to a WhatsApp number."""
        if not self._client:
            return {"error": "Not connected"}
        to = params.get("to", "")
        body = params.get("body", "")
        if not to or not body:
            return {"error": "to and body are required"}

        try:
            resp = await self._client.post(
                f"/{self._phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to,
                    "type": "text",
                    "text": {"body": body},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("messages", [{}])[0].get("id", "")
            return {"message_id": msg_id, "sent": True, "to": to}
        except httpx.HTTPStatusError as e:
            return {"error": f"WhatsApp API error: {e.response.status_code}"}

    async def _send_template(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send a template message (required for business-initiated conversations)."""
        if not self._client:
            return {"error": "Not connected"}
        to = params.get("to", "")
        template_name = params.get("template", "")
        language = params.get("language", "en_US")
        if not to or not template_name:
            return {"error": "to and template are required"}

        components = []
        if params.get("parameters"):
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": p} for p in params["parameters"]
                ],
            })

        try:
            resp = await self._client.post(
                f"/{self._phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": language},
                        "components": components,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("messages", [{}])[0].get("id", "")
            return {"message_id": msg_id, "sent": True, "to": to, "template": template_name}
        except httpx.HTTPStatusError as e:
            return {"error": f"WhatsApp API error: {e.response.status_code}"}

    async def _mark_read(self, params: dict[str, Any]) -> dict[str, Any]:
        """Mark a message as read."""
        if not self._client:
            return {"error": "Not connected"}
        message_id = params.get("message_id", "")
        if not message_id:
            return {"error": "message_id is required"}

        try:
            resp = await self._client.post(
                f"/{self._phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id,
                },
            )
            resp.raise_for_status()
            return {"marked_read": True, "message_id": message_id}
        except httpx.HTTPStatusError as e:
            return {"error": f"WhatsApp API error: {e.response.status_code}"}
