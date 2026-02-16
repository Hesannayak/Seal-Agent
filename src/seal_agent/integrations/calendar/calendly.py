"""Calendly integration — Scheduling links and event management."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

CALENDLY_API_BASE = "https://api.calendly.com"


class CalendlyIntegration(BaseIntegration):
    """Calendly integration for scheduling meetings with prospects."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False
        self._user_uri: str = ""
        self._org_uri: str = ""

    @property
    def name(self) -> str:
        return "calendly"

    @property
    def category(self) -> str:
        return "calendar"

    async def connect(self, credentials: dict[str, str]) -> bool:
        api_key = credentials.get("api_key", "")
        if not api_key:
            log.warning("Calendly integration not configured — missing API key")
            return False

        self._client = httpx.AsyncClient(
            base_url=CALENDLY_API_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

        try:
            resp = await self._client.get("/users/me")
            resp.raise_for_status()
            data = resp.json()
            resource = data.get("resource", {})
            self._user_uri = resource.get("uri", "")
            self._org_uri = resource.get("current_organization", "")
            self._connected = True
            log.info("Calendly integration connected", user=resource.get("name"))
            return True
        except Exception:
            log.exception("Failed to connect Calendly integration")
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
            "list_event_types": self._list_event_types,
            "get_scheduling_link": self._get_scheduling_link,
            "list_scheduled_events": self._list_scheduled_events,
            "get_event": self._get_event,
            "cancel_event": self._cancel_event,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for Calendly")
        return await handler(params)

    async def _list_event_types(self, params: dict[str, Any]) -> dict[str, Any]:
        """List available event types (meeting templates)."""
        if not self._client:
            return {"error": "Not connected"}

        try:
            resp = await self._client.get(
                "/event_types",
                params={
                    "user": self._user_uri,
                    "active": "true",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            event_types = [
                {
                    "uri": et["uri"],
                    "name": et["name"],
                    "duration": et.get("duration"),
                    "scheduling_url": et.get("scheduling_url"),
                    "active": et.get("active"),
                }
                for et in data.get("collection", [])
            ]
            return {"event_types": event_types, "count": len(event_types)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Calendly API error: {e.response.status_code}"}

    async def _get_scheduling_link(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get a one-time scheduling link for a prospect."""
        if not self._client:
            return {"error": "Not connected"}

        event_type_uri = params.get("event_type_uri")
        if not event_type_uri:
            # Default to first active event type
            types = await self._list_event_types({})
            event_types = types.get("event_types", [])
            if not event_types:
                return {"error": "No active event types found"}
            event_type_uri = event_types[0]["uri"]

        try:
            resp = await self._client.post(
                "/scheduling_links",
                json={
                    "max_event_count": 1,
                    "owner": event_type_uri,
                    "owner_type": "EventType",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            resource = data.get("resource", {})
            return {
                "booking_url": resource.get("booking_url"),
                "owner": resource.get("owner"),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"Calendly API error: {e.response.status_code}"}

    async def _list_scheduled_events(self, params: dict[str, Any]) -> dict[str, Any]:
        """List upcoming scheduled events."""
        if not self._client:
            return {"error": "Not connected"}

        try:
            query_params: dict[str, str] = {"user": self._user_uri, "status": "active"}
            if params.get("min_start_time"):
                query_params["min_start_time"] = params["min_start_time"]

            resp = await self._client.get("/scheduled_events", params=query_params)
            resp.raise_for_status()
            data = resp.json()
            events = [
                {
                    "uri": ev["uri"],
                    "name": ev.get("name"),
                    "start_time": ev.get("start_time"),
                    "end_time": ev.get("end_time"),
                    "status": ev.get("status"),
                    "location": ev.get("location", {}).get("location"),
                }
                for ev in data.get("collection", [])
            ]
            return {"events": events, "count": len(events)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Calendly API error: {e.response.status_code}"}

    async def _get_event(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get details of a specific scheduled event."""
        if not self._client:
            return {"error": "Not connected"}

        event_uri = params.get("event_uri")
        if not event_uri:
            return {"error": "event_uri is required"}

        try:
            # Extract UUID from URI
            event_uuid = event_uri.split("/")[-1]
            resp = await self._client.get(f"/scheduled_events/{event_uuid}")
            resp.raise_for_status()
            return resp.json().get("resource", {})
        except httpx.HTTPStatusError as e:
            return {"error": f"Calendly API error: {e.response.status_code}"}

    async def _cancel_event(self, params: dict[str, Any]) -> dict[str, Any]:
        """Cancel a scheduled event."""
        if not self._client:
            return {"error": "Not connected"}

        event_uuid = params.get("event_uuid")
        reason = params.get("reason", "Cancelled by sales agent")

        if not event_uuid:
            return {"error": "event_uuid is required"}

        try:
            resp = await self._client.post(
                f"/scheduled_events/{event_uuid}/cancellation",
                json={"reason": reason},
            )
            resp.raise_for_status()
            return {"cancelled": True, "event_uuid": event_uuid}
        except httpx.HTTPStatusError as e:
            return {"error": f"Calendly API error: {e.response.status_code}"}
