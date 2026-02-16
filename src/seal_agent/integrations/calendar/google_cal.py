"""Google Calendar integration — Meeting scheduling and availability."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

GOOGLE_CAL_API_BASE = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarIntegration(BaseIntegration):
    """Google Calendar integration for scheduling and event management."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False
        self._calendar_id: str = "primary"

    @property
    def name(self) -> str:
        return "google_calendar"

    @property
    def category(self) -> str:
        return "calendar"

    async def connect(self, credentials: dict[str, str]) -> bool:
        access_token = credentials.get("access_token", "")
        if not access_token:
            log.warning("Google Calendar not configured — missing access token")
            return False

        self._calendar_id = credentials.get("calendar_id", "primary")

        self._client = httpx.AsyncClient(
            base_url=GOOGLE_CAL_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=20.0,
        )

        try:
            resp = await self._client.get(f"/calendars/{self._calendar_id}")
            resp.raise_for_status()
            cal = resp.json()
            self._connected = True
            log.info("Google Calendar connected", calendar=cal.get("summary"))
            return True
        except Exception:
            log.exception("Failed to connect Google Calendar")
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
            resp = await self._client.get(f"/calendars/{self._calendar_id}")
            return resp.status_code == 200
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "create_event": self._create_event,
            "list_events": self._list_events,
            "get_event": self._get_event,
            "delete_event": self._delete_event,
            "get_free_busy": self._get_free_busy,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for Google Calendar")
        return await handler(params)

    async def _create_event(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a calendar event."""
        if not self._client:
            return {"error": "Not connected"}
        summary = params.get("summary", "")
        start = params.get("start", "")
        end = params.get("end", "")
        if not summary or not start or not end:
            return {"error": "summary, start, and end are required"}

        try:
            event_body: dict[str, Any] = {
                "summary": summary,
                "start": {"dateTime": start, "timeZone": params.get("timezone", "UTC")},
                "end": {"dateTime": end, "timeZone": params.get("timezone", "UTC")},
            }
            if params.get("description"):
                event_body["description"] = params["description"]
            if params.get("attendees"):
                event_body["attendees"] = [{"email": e} for e in params["attendees"]]
            if params.get("location"):
                event_body["location"] = params["location"]
            if params.get("conference"):
                event_body["conferenceData"] = {
                    "createRequest": {"requestId": f"seal-{start}", "conferenceSolutionKey": {"type": "hangoutsMeet"}},
                }

            query_params = {}
            if params.get("conference"):
                query_params["conferenceDataVersion"] = 1

            resp = await self._client.post(
                f"/calendars/{self._calendar_id}/events",
                json=event_body,
                params=query_params,
            )
            resp.raise_for_status()
            event = resp.json()
            return {
                "id": event.get("id"),
                "summary": event.get("summary"),
                "start": event.get("start", {}).get("dateTime"),
                "end": event.get("end", {}).get("dateTime"),
                "html_link": event.get("htmlLink"),
                "meet_link": event.get("hangoutLink"),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"Google Calendar API error: {e.response.status_code}"}

    async def _list_events(self, params: dict[str, Any]) -> dict[str, Any]:
        """List upcoming events."""
        if not self._client:
            return {"error": "Not connected"}
        try:
            query: dict[str, Any] = {
                "maxResults": params.get("limit", 10),
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if params.get("time_min"):
                query["timeMin"] = params["time_min"]
            if params.get("time_max"):
                query["timeMax"] = params["time_max"]

            resp = await self._client.get(
                f"/calendars/{self._calendar_id}/events",
                params=query,
            )
            resp.raise_for_status()
            data = resp.json()

            events = []
            for e in data.get("items", []):
                events.append({
                    "id": e.get("id"),
                    "summary": e.get("summary"),
                    "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
                    "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
                    "attendees": [a.get("email") for a in e.get("attendees", [])],
                    "status": e.get("status"),
                })
            return {"events": events, "count": len(events)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Google Calendar API error: {e.response.status_code}"}

    async def _get_event(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get a specific event."""
        if not self._client:
            return {"error": "Not connected"}
        event_id = params.get("event_id", "")
        if not event_id:
            return {"error": "event_id is required"}
        try:
            resp = await self._client.get(f"/calendars/{self._calendar_id}/events/{event_id}")
            resp.raise_for_status()
            e = resp.json()
            return {
                "id": e.get("id"),
                "summary": e.get("summary"),
                "description": e.get("description"),
                "start": e.get("start", {}).get("dateTime"),
                "end": e.get("end", {}).get("dateTime"),
                "attendees": [
                    {"email": a.get("email"), "status": a.get("responseStatus")}
                    for a in e.get("attendees", [])
                ],
                "html_link": e.get("htmlLink"),
            }
        except httpx.HTTPStatusError as e_http:
            return {"error": f"Google Calendar API error: {e_http.response.status_code}"}

    async def _delete_event(self, params: dict[str, Any]) -> dict[str, Any]:
        """Delete/cancel a calendar event."""
        if not self._client:
            return {"error": "Not connected"}
        event_id = params.get("event_id", "")
        if not event_id:
            return {"error": "event_id is required"}
        try:
            resp = await self._client.delete(f"/calendars/{self._calendar_id}/events/{event_id}")
            resp.raise_for_status()
            return {"deleted": True, "event_id": event_id}
        except httpx.HTTPStatusError as e:
            return {"error": f"Google Calendar API error: {e.response.status_code}"}

    async def _get_free_busy(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check free/busy availability."""
        if not self._client:
            return {"error": "Not connected"}
        time_min = params.get("time_min", "")
        time_max = params.get("time_max", "")
        if not time_min or not time_max:
            return {"error": "time_min and time_max are required"}

        try:
            resp = await self._client.post("/freeBusy", json={
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": self._calendar_id}],
            })
            resp.raise_for_status()
            data = resp.json()
            busy_slots = data.get("calendars", {}).get(self._calendar_id, {}).get("busy", [])
            return {
                "busy_slots": busy_slots,
                "count": len(busy_slots),
                "time_range": {"min": time_min, "max": time_max},
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"Google Calendar API error: {e.response.status_code}"}
