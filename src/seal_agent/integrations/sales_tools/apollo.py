"""Apollo.io integration — Lead enrichment and prospecting data."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

APOLLO_API_BASE = "https://api.apollo.io/v1"


class ApolloIntegration(BaseIntegration):
    """Apollo.io integration for lead enrichment and prospecting data."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    @property
    def name(self) -> str:
        return "apollo"

    @property
    def category(self) -> str:
        return "sales_tools"

    async def connect(self, credentials: dict[str, str]) -> bool:
        api_key = credentials.get("api_key", "")
        if not api_key:
            log.warning("Apollo not configured — missing API key")
            return False

        self._client = httpx.AsyncClient(
            base_url=APOLLO_API_BASE,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            },
            timeout=20.0,
        )
        # Apollo uses api_key in request body, store it
        self._api_key = api_key

        try:
            resp = await self._client.post("/auth/health", json={"api_key": api_key})
            if resp.status_code == 200:
                self._connected = True
                log.info("Apollo connected")
                return True
            # Some Apollo endpoints don't have a health check — try a search
            resp = await self._client.post("/mixed_people/search", json={
                "api_key": api_key,
                "q_organization_name": "test",
                "page": 1,
                "per_page": 1,
            })
            self._connected = resp.status_code == 200
            return self._connected
        except Exception:
            log.exception("Failed to connect Apollo")
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def health_check(self) -> bool:
        return self._connected and self._client is not None

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "search_people": self._search_people,
            "enrich_person": self._enrich_person,
            "enrich_company": self._enrich_company,
            "search_organizations": self._search_organizations,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for Apollo")
        return await handler(params)

    async def _search_people(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search for people/leads on Apollo."""
        if not self._client:
            return {"error": "Not connected"}
        try:
            body: dict[str, Any] = {"api_key": self._api_key, "page": 1, "per_page": params.get("limit", 25)}
            if params.get("title"):
                body["person_titles"] = [params["title"]]
            if params.get("company"):
                body["q_organization_name"] = params["company"]
            if params.get("location"):
                body["person_locations"] = [params["location"]]
            if params.get("seniority"):
                body["person_seniorities"] = [params["seniority"]]

            resp = await self._client.post("/mixed_people/search", json=body)
            resp.raise_for_status()
            data = resp.json()

            people = []
            for p in data.get("people", []):
                people.append({
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "title": p.get("title"),
                    "company": p.get("organization", {}).get("name"),
                    "email": p.get("email"),
                    "linkedin_url": p.get("linkedin_url"),
                    "city": p.get("city"),
                })
            return {"results": people, "count": len(people), "total": data.get("pagination", {}).get("total_entries", 0)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Apollo API error: {e.response.status_code}"}

    async def _enrich_person(self, params: dict[str, Any]) -> dict[str, Any]:
        """Enrich a person's data by email or LinkedIn URL."""
        if not self._client:
            return {"error": "Not connected"}
        email = params.get("email")
        linkedin_url = params.get("linkedin_url")
        if not email and not linkedin_url:
            return {"error": "email or linkedin_url is required"}

        try:
            body: dict[str, Any] = {"api_key": self._api_key}
            if email:
                body["email"] = email
            if linkedin_url:
                body["linkedin_url"] = linkedin_url

            resp = await self._client.post("/people/match", json=body)
            resp.raise_for_status()
            person = resp.json().get("person", {})
            return {
                "id": person.get("id"),
                "name": person.get("name"),
                "title": person.get("title"),
                "company": person.get("organization", {}).get("name"),
                "email": person.get("email"),
                "phone": person.get("phone_numbers", [{}])[0].get("sanitized_number") if person.get("phone_numbers") else None,
                "linkedin_url": person.get("linkedin_url"),
                "city": person.get("city"),
                "state": person.get("state"),
                "country": person.get("country"),
                "seniority": person.get("seniority"),
                "departments": person.get("departments", []),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"Apollo API error: {e.response.status_code}"}

    async def _enrich_company(self, params: dict[str, Any]) -> dict[str, Any]:
        """Enrich a company/organization."""
        if not self._client:
            return {"error": "Not connected"}
        domain = params.get("domain")
        if not domain:
            return {"error": "domain is required"}

        try:
            resp = await self._client.post("/organizations/enrich", json={
                "api_key": self._api_key,
                "domain": domain,
            })
            resp.raise_for_status()
            org = resp.json().get("organization", {})
            return {
                "id": org.get("id"),
                "name": org.get("name"),
                "domain": org.get("website_url"),
                "industry": org.get("industry"),
                "employee_count": org.get("estimated_num_employees"),
                "annual_revenue": org.get("annual_revenue_printed"),
                "founded_year": org.get("founded_year"),
                "linkedin_url": org.get("linkedin_url"),
                "description": org.get("short_description"),
                "technologies": org.get("current_technologies", []),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"Apollo API error: {e.response.status_code}"}

    async def _search_organizations(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search for organizations/companies."""
        if not self._client:
            return {"error": "Not connected"}
        try:
            body: dict[str, Any] = {
                "api_key": self._api_key,
                "page": 1,
                "per_page": params.get("limit", 25),
            }
            if params.get("keywords"):
                body["q_organization_name"] = params["keywords"]
            if params.get("industry"):
                body["organization_industry_tag_ids"] = [params["industry"]]
            if params.get("min_employees"):
                body["organization_num_employees_ranges"] = [f"{params['min_employees']},"]

            resp = await self._client.post("/mixed_companies/search", json=body)
            resp.raise_for_status()
            data = resp.json()

            orgs = []
            for o in data.get("organizations", []):
                orgs.append({
                    "id": o.get("id"),
                    "name": o.get("name"),
                    "domain": o.get("website_url"),
                    "industry": o.get("industry"),
                    "employee_count": o.get("estimated_num_employees"),
                })
            return {"results": orgs, "count": len(orgs)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Apollo API error: {e.response.status_code}"}
