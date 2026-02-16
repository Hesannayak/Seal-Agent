"""ZoomInfo integration — B2B contact and company intelligence."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

ZOOMINFO_API_BASE = "https://api.zoominfo.com"


class ZoomInfoIntegration(BaseIntegration):
    """ZoomInfo integration for B2B contact and company intelligence."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    @property
    def name(self) -> str:
        return "zoominfo"

    @property
    def category(self) -> str:
        return "sales_tools"

    async def connect(self, credentials: dict[str, str]) -> bool:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        client_id = credentials.get("client_id", "")
        if not username or not password:
            log.warning("ZoomInfo not configured — missing credentials")
            return False

        try:
            async with httpx.AsyncClient(timeout=20.0) as temp_client:
                resp = await temp_client.post(
                    f"{ZOOMINFO_API_BASE}/authenticate",
                    json={"username": username, "password": password, "client_id": client_id},
                )
                resp.raise_for_status()
                token = resp.json().get("jwt", "")

            self._client = httpx.AsyncClient(
                base_url=ZOOMINFO_API_BASE,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=20.0,
            )
            self._connected = True
            log.info("ZoomInfo connected")
            return True
        except Exception:
            log.exception("Failed to connect ZoomInfo")
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
            resp = await self._client.post("/lookup/inputfields/contact/enrich")
            return resp.status_code in (200, 400)  # 400 means auth OK but bad params
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "search_contacts": self._search_contacts,
            "enrich_contact": self._enrich_contact,
            "search_companies": self._search_companies,
            "enrich_company": self._enrich_company,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for ZoomInfo")
        return await handler(params)

    async def _search_contacts(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search for contacts."""
        if not self._client:
            return {"error": "Not connected"}
        try:
            body: dict[str, Any] = {
                "rpp": params.get("limit", 25),
                "page": params.get("page", 1),
            }
            if params.get("company"):
                body["companyName"] = params["company"]
            if params.get("title"):
                body["jobTitle"] = params["title"]
            if params.get("location"):
                body["locationSearchType"] = "Person"
                body["metroRegion"] = params["location"]

            resp = await self._client.post("/search/contact", json=body)
            resp.raise_for_status()
            data = resp.json()

            contacts = []
            for c in data.get("data", []):
                contacts.append({
                    "id": c.get("id"),
                    "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
                    "title": c.get("jobTitle"),
                    "company": c.get("companyName"),
                    "email": c.get("email"),
                    "phone": c.get("directPhoneNumber"),
                    "linkedin_url": c.get("linkedinUrl"),
                })
            return {"results": contacts, "count": len(contacts), "total": data.get("totalResults", 0)}
        except httpx.HTTPStatusError as e:
            return {"error": f"ZoomInfo API error: {e.response.status_code}"}

    async def _enrich_contact(self, params: dict[str, Any]) -> dict[str, Any]:
        """Enrich a contact by email or person ID."""
        if not self._client:
            return {"error": "Not connected"}
        match_input = {}
        if params.get("email"):
            match_input["emailAddress"] = params["email"]
        elif params.get("person_id"):
            match_input["personId"] = params["person_id"]
        else:
            return {"error": "email or person_id is required"}

        try:
            resp = await self._client.post("/enrich/contact", json={
                "matchPersonInput": [match_input],
                "outputFields": [
                    "id", "firstName", "lastName", "jobTitle", "companyName",
                    "email", "directPhoneNumber", "linkedinUrl", "city", "state",
                ],
            })
            resp.raise_for_status()
            results = resp.json().get("data", [])
            if not results:
                return {"error": "No match found"}

            c = results[0]
            return {
                "id": c.get("id"),
                "first_name": c.get("firstName"),
                "last_name": c.get("lastName"),
                "title": c.get("jobTitle"),
                "company": c.get("companyName"),
                "email": c.get("email"),
                "phone": c.get("directPhoneNumber"),
                "linkedin_url": c.get("linkedinUrl"),
                "city": c.get("city"),
                "state": c.get("state"),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"ZoomInfo API error: {e.response.status_code}"}

    async def _search_companies(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search for companies."""
        if not self._client:
            return {"error": "Not connected"}
        try:
            body: dict[str, Any] = {
                "rpp": params.get("limit", 25),
                "page": params.get("page", 1),
            }
            if params.get("name"):
                body["companyName"] = params["name"]
            if params.get("industry"):
                body["industry"] = params["industry"]
            if params.get("min_employees"):
                body["employeeCount"] = f"{params['min_employees']}+"

            resp = await self._client.post("/search/company", json=body)
            resp.raise_for_status()
            data = resp.json()

            companies = []
            for co in data.get("data", []):
                companies.append({
                    "id": co.get("id"),
                    "name": co.get("companyName"),
                    "domain": co.get("website"),
                    "industry": co.get("industry"),
                    "employee_count": co.get("employeeCount"),
                    "revenue": co.get("revenue"),
                    "city": co.get("city"),
                    "state": co.get("state"),
                })
            return {"results": companies, "count": len(companies), "total": data.get("totalResults", 0)}
        except httpx.HTTPStatusError as e:
            return {"error": f"ZoomInfo API error: {e.response.status_code}"}

    async def _enrich_company(self, params: dict[str, Any]) -> dict[str, Any]:
        """Enrich a company by domain or company ID."""
        if not self._client:
            return {"error": "Not connected"}
        match_input = {}
        if params.get("domain"):
            match_input["companyWebsite"] = params["domain"]
        elif params.get("company_id"):
            match_input["companyId"] = params["company_id"]
        else:
            return {"error": "domain or company_id is required"}

        try:
            resp = await self._client.post("/enrich/company", json={
                "matchCompanyInput": [match_input],
                "outputFields": [
                    "id", "companyName", "website", "industry", "employeeCount",
                    "revenue", "city", "state", "country", "description",
                ],
            })
            resp.raise_for_status()
            results = resp.json().get("data", [])
            if not results:
                return {"error": "No match found"}

            co = results[0]
            return {
                "id": co.get("id"),
                "name": co.get("companyName"),
                "domain": co.get("website"),
                "industry": co.get("industry"),
                "employee_count": co.get("employeeCount"),
                "revenue": co.get("revenue"),
                "city": co.get("city"),
                "state": co.get("state"),
                "country": co.get("country"),
                "description": co.get("description"),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"ZoomInfo API error: {e.response.status_code}"}
