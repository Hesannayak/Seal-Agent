"""HubSpot CRM integration."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.config import settings
from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()


class HubSpotIntegration(BaseIntegration):
    """HubSpot CRM integration for syncing contacts, deals, and activities."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    @property
    def name(self) -> str:
        return "hubspot"

    @property
    def category(self) -> str:
        return "crm"

    async def connect(self, credentials: dict[str, str]) -> bool:
        api_key = credentials.get("api_key", settings.hubspot_api_key)
        if not api_key:
            log.warning("HubSpot integration not configured — missing API key")
            return False

        self._client = httpx.AsyncClient(
            base_url=settings.hubspot_base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        # Verify connection
        try:
            response = await self._client.get("/crm/v3/objects/contacts?limit=1")
            response.raise_for_status()
            self._connected = True
            log.info("HubSpot integration connected")
            return True
        except Exception:
            log.exception("Failed to connect HubSpot integration")
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        log.info("HubSpot integration disconnected")

    async def health_check(self) -> bool:
        if not self._client or not self._connected:
            return False
        try:
            response = await self._client.get("/crm/v3/objects/contacts?limit=1")
            return response.status_code == 200
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "create_contact": self._create_contact,
            "get_contact": self._get_contact,
            "search_contacts": self._search_contacts,
            "create_deal": self._create_deal,
            "update_deal": self._update_deal,
            "log_activity": self._log_activity,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for HubSpot")
        return await handler(params)

    async def _create_contact(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a contact in HubSpot."""
        if not self._client:
            return {"error": "Not connected"}

        properties = {
            "firstname": params.get("first_name", ""),
            "lastname": params.get("last_name", ""),
            "email": params.get("email", ""),
            "phone": params.get("phone", ""),
            "jobtitle": params.get("title", ""),
            "company": params.get("company", ""),
        }
        # Remove empty values
        properties = {k: v for k, v in properties.items() if v}

        try:
            response = await self._client.post(
                "/crm/v3/objects/contacts",
                json={"properties": properties},
            )
            response.raise_for_status()
            data = response.json()
            return {"id": data["id"], "properties": data.get("properties", {})}
        except httpx.HTTPStatusError as e:
            return {"error": f"HubSpot API error: {e.response.status_code}"}

    async def _get_contact(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get a contact from HubSpot."""
        if not self._client:
            return {"error": "Not connected"}

        contact_id = params.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}

        try:
            response = await self._client.get(f"/crm/v3/objects/contacts/{contact_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HubSpot API error: {e.response.status_code}"}

    async def _search_contacts(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search contacts in HubSpot."""
        if not self._client:
            return {"error": "Not connected"}

        query = params.get("query", "")
        try:
            response = await self._client.post(
                "/crm/v3/objects/contacts/search",
                json={
                    "query": query,
                    "limit": params.get("limit", 10),
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "contacts": data.get("results", []),
                "total": data.get("total", 0),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"HubSpot API error: {e.response.status_code}"}

    async def _create_deal(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a deal in HubSpot."""
        if not self._client:
            return {"error": "Not connected"}

        properties = {
            "dealname": params.get("title", ""),
            "amount": str(params.get("value", 0)),
            "pipeline": params.get("pipeline", "default"),
            "dealstage": params.get("stage", "appointmentscheduled"),
        }

        try:
            response = await self._client.post(
                "/crm/v3/objects/deals",
                json={"properties": properties},
            )
            response.raise_for_status()
            data = response.json()
            return {"id": data["id"], "properties": data.get("properties", {})}
        except httpx.HTTPStatusError as e:
            return {"error": f"HubSpot API error: {e.response.status_code}"}

    async def _update_deal(self, params: dict[str, Any]) -> dict[str, Any]:
        """Update a deal in HubSpot."""
        if not self._client:
            return {"error": "Not connected"}

        deal_id = params.get("deal_id")
        if not deal_id:
            return {"error": "deal_id is required"}

        properties = {}
        if "stage" in params:
            properties["dealstage"] = params["stage"]
        if "value" in params:
            properties["amount"] = str(params["value"])

        try:
            response = await self._client.patch(
                f"/crm/v3/objects/deals/{deal_id}",
                json={"properties": properties},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HubSpot API error: {e.response.status_code}"}

    async def _log_activity(self, params: dict[str, Any]) -> dict[str, Any]:
        """Log an activity (note/email) against a contact in HubSpot."""
        if not self._client:
            return {"error": "Not connected"}

        try:
            response = await self._client.post(
                "/crm/v3/objects/notes",
                json={
                    "properties": {
                        "hs_note_body": params.get("content", ""),
                        "hs_timestamp": params.get("timestamp", ""),
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return {"id": data["id"], "status": "created"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HubSpot API error: {e.response.status_code}"}
