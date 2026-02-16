"""Pipedrive CRM integration."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

PIPEDRIVE_API_BASE = "https://api.pipedrive.com/v1"


class PipedriveIntegration(BaseIntegration):
    """Pipedrive CRM integration for managing deals, contacts, and activities."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    @property
    def name(self) -> str:
        return "pipedrive"

    @property
    def category(self) -> str:
        return "crm"

    async def connect(self, credentials: dict[str, str]) -> bool:
        api_token = credentials.get("api_token", "")
        if not api_token:
            log.warning("Pipedrive not configured — missing API token")
            return False

        self._client = httpx.AsyncClient(
            base_url=PIPEDRIVE_API_BASE,
            params={"api_token": api_token},
            headers={"Content-Type": "application/json"},
            timeout=20.0,
        )

        try:
            resp = await self._client.get("/users/me")
            resp.raise_for_status()
            data = resp.json()
            if data.get("success"):
                self._connected = True
                log.info("Pipedrive connected", user=data["data"].get("name"))
                return True
            return False
        except Exception:
            log.exception("Failed to connect Pipedrive")
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
            resp = await self._client.get("/users/me")
            return resp.status_code == 200
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "create_person": self._create_person,
            "get_person": self._get_person,
            "create_deal": self._create_deal,
            "update_deal": self._update_deal,
            "search": self._search,
            "create_activity": self._create_activity,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for Pipedrive")
        return await handler(params)

    async def _create_person(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}
        try:
            resp = await self._client.post("/persons", json={
                "name": params.get("name", ""),
                "email": [{"value": params["email"], "primary": True}] if params.get("email") else [],
                "phone": [{"value": params["phone"], "primary": True}] if params.get("phone") else [],
                "org_id": params.get("org_id"),
            })
            resp.raise_for_status()
            data = resp.json()
            return {"id": data["data"]["id"], "name": data["data"]["name"]}
        except httpx.HTTPStatusError as e:
            return {"error": f"Pipedrive API error: {e.response.status_code}"}

    async def _get_person(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}
        person_id = params.get("person_id")
        if not person_id:
            return {"error": "person_id is required"}
        try:
            resp = await self._client.get(f"/persons/{person_id}")
            resp.raise_for_status()
            data = resp.json()["data"]
            return {
                "id": data["id"],
                "name": data["name"],
                "email": data.get("email", [{}])[0].get("value", "") if data.get("email") else "",
                "phone": data.get("phone", [{}])[0].get("value", "") if data.get("phone") else "",
                "org_name": data.get("org_name", ""),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"Pipedrive API error: {e.response.status_code}"}

    async def _create_deal(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}
        try:
            resp = await self._client.post("/deals", json={
                "title": params.get("title", ""),
                "value": params.get("value", 0),
                "currency": params.get("currency", "USD"),
                "person_id": params.get("person_id"),
                "org_id": params.get("org_id"),
                "stage_id": params.get("stage_id"),
            })
            resp.raise_for_status()
            data = resp.json()["data"]
            return {"id": data["id"], "title": data["title"], "value": data.get("value")}
        except httpx.HTTPStatusError as e:
            return {"error": f"Pipedrive API error: {e.response.status_code}"}

    async def _update_deal(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}
        deal_id = params.get("deal_id")
        if not deal_id:
            return {"error": "deal_id is required"}
        try:
            update_data: dict[str, Any] = {}
            for field in ("title", "value", "stage_id", "status"):
                if field in params:
                    update_data[field] = params[field]
            resp = await self._client.put(f"/deals/{deal_id}", json=update_data)
            resp.raise_for_status()
            data = resp.json()["data"]
            return {"id": data["id"], "title": data["title"], "stage_id": data.get("stage_id")}
        except httpx.HTTPStatusError as e:
            return {"error": f"Pipedrive API error: {e.response.status_code}"}

    async def _search(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}
        term = params.get("term", "")
        item_types = params.get("item_types", "person,deal")
        if not term:
            return {"error": "term is required"}
        try:
            resp = await self._client.get("/itemSearch", params={
                "term": term,
                "item_types": item_types,
                "limit": params.get("limit", 10),
            })
            resp.raise_for_status()
            data = resp.json()
            items = [
                {"type": i["item"]["type"], "id": i["item"]["id"], "title": i["item"]["title"]}
                for i in data.get("data", {}).get("items", [])
            ]
            return {"results": items, "count": len(items)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Pipedrive API error: {e.response.status_code}"}

    async def _create_activity(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}
        try:
            resp = await self._client.post("/activities", json={
                "subject": params.get("subject", ""),
                "type": params.get("type", "call"),
                "deal_id": params.get("deal_id"),
                "person_id": params.get("person_id"),
                "note": params.get("note", ""),
                "due_date": params.get("due_date"),
                "due_time": params.get("due_time"),
            })
            resp.raise_for_status()
            data = resp.json()["data"]
            return {"id": data["id"], "subject": data["subject"]}
        except httpx.HTTPStatusError as e:
            return {"error": f"Pipedrive API error: {e.response.status_code}"}
