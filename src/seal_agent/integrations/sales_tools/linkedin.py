"""LinkedIn Sales Navigator integration — Prospect research and outreach."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


class LinkedInSalesNavIntegration(BaseIntegration):
    """LinkedIn Sales Navigator integration for prospect research and outreach.

    Uses the LinkedIn Marketing/Sales Navigator API for:
    - Prospect profile lookup and enrichment
    - Sending InMail / connection requests
    - Searching for leads by company, title, industry
    - Tracking profile views and engagement
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    @property
    def name(self) -> str:
        return "linkedin_sales_nav"

    @property
    def category(self) -> str:
        return "sales_tools"

    async def connect(self, credentials: dict[str, str]) -> bool:
        access_token = credentials.get("access_token", "")
        if not access_token:
            log.warning("LinkedIn Sales Nav not configured — missing access token")
            return False

        self._client = httpx.AsyncClient(
            base_url=LINKEDIN_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
                "LinkedIn-Version": "202401",
            },
            timeout=20.0,
        )

        try:
            resp = await self._client.get("/me")
            resp.raise_for_status()
            profile = resp.json()
            name = f"{profile.get('localizedFirstName', '')} {profile.get('localizedLastName', '')}"
            self._connected = True
            log.info("LinkedIn Sales Nav connected", user=name.strip())
            return True
        except Exception:
            log.exception("Failed to connect LinkedIn Sales Nav")
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
            "search_people": self._search_people,
            "get_profile": self._get_profile,
            "send_inmail": self._send_inmail,
            "send_connection_request": self._send_connection_request,
            "get_company": self._get_company,
            "search_companies": self._search_companies,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(
                f"Action '{action}' not implemented for LinkedIn Sales Nav"
            )
        return await handler(params)

    async def _search_people(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search for people on LinkedIn by keywords, title, company, etc."""
        if not self._client:
            return {"error": "Not connected"}

        keywords = params.get("keywords", "")
        title = params.get("title", "")
        company = params.get("company", "")
        industry = params.get("industry", "")
        limit = min(params.get("limit", 25), 50)

        # Build search query using LinkedIn People Search API
        query_parts = []
        if keywords:
            query_parts.append(f"keywords={keywords}")
        if title:
            query_parts.append(f"title={title}")

        try:
            search_params: dict[str, Any] = {
                "q": "people",
                "count": limit,
            }
            if keywords:
                search_params["keywords"] = keywords

            # Use the search endpoint
            resp = await self._client.get(
                "/search/blended",
                params=search_params,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for element in data.get("elements", []):
                for item in element.get("elements", []):
                    entity = item.get("entity", item)
                    profile_info = {
                        "urn": entity.get("entityUrn", entity.get("urn", "")),
                        "first_name": entity.get("firstName", {}).get("text", ""),
                        "last_name": entity.get("lastName", {}).get("text", ""),
                        "headline": entity.get("headline", {}).get("text", ""),
                        "location": entity.get("location", ""),
                    }
                    # Filter by title/company if specified
                    headline = profile_info["headline"].lower()
                    if title and title.lower() not in headline:
                        continue
                    if company and company.lower() not in headline:
                        continue
                    results.append(profile_info)

            return {"results": results[:limit], "count": len(results[:limit])}
        except httpx.HTTPStatusError as e:
            return {"error": f"LinkedIn API error: {e.response.status_code}"}

    async def _get_profile(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get a person's LinkedIn profile details."""
        if not self._client:
            return {"error": "Not connected"}

        person_id = params.get("person_id", "")
        if not person_id:
            return {"error": "person_id is required"}

        try:
            # Fetch profile with projection for key fields
            resp = await self._client.get(
                f"/people/{person_id}",
                params={
                    "projection": (
                        "(id,firstName,lastName,headline,vanityName,"
                        "profilePicture,positions,industryName,summary)"
                    ),
                },
            )
            resp.raise_for_status()
            profile = resp.json()

            # Extract position history
            positions = []
            for pos in profile.get("positions", {}).get("elements", []):
                positions.append({
                    "title": pos.get("title", ""),
                    "company": pos.get("companyName", ""),
                    "start_date": pos.get("startDate", {}),
                    "end_date": pos.get("endDate"),
                    "is_current": pos.get("isCurrent", False),
                })

            return {
                "id": profile.get("id", ""),
                "first_name": profile.get("firstName", {}).get("localized", {}).get("en_US", ""),
                "last_name": profile.get("lastName", {}).get("localized", {}).get("en_US", ""),
                "headline": profile.get("headline", {}).get("localized", {}).get("en_US", ""),
                "vanity_name": profile.get("vanityName", ""),
                "industry": profile.get("industryName", ""),
                "summary": profile.get("summary", {}).get("localized", {}).get("en_US", ""),
                "positions": positions,
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"LinkedIn API error: {e.response.status_code}"}

    async def _send_inmail(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send an InMail message to a prospect."""
        if not self._client:
            return {"error": "Not connected"}

        recipient_urn = params.get("recipient_urn", "")
        subject = params.get("subject", "")
        body = params.get("body", "")

        if not recipient_urn or not body:
            return {"error": "recipient_urn and body are required"}

        try:
            message_payload = {
                "recipients": [recipient_urn],
                "subject": subject,
                "body": body,
                "messageType": "INMAIL",
            }

            resp = await self._client.post(
                "/messages",
                json=message_payload,
            )
            resp.raise_for_status()

            log.info("InMail sent", recipient=recipient_urn, subject=subject)
            return {
                "sent": True,
                "recipient": recipient_urn,
                "subject": subject,
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"LinkedIn API error: {e.response.status_code}"}

    async def _send_connection_request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send a connection request with an optional message."""
        if not self._client:
            return {"error": "Not connected"}

        person_urn = params.get("person_urn", "")
        message = params.get("message", "")

        if not person_urn:
            return {"error": "person_urn is required"}

        if message and len(message) > 300:
            return {"error": "Connection request message must be 300 characters or fewer"}

        try:
            payload: dict[str, Any] = {
                "inviteeUrn": person_urn,
                "invitationType": "CONNECTION",
            }
            if message:
                payload["message"] = message

            resp = await self._client.post(
                "/invitations",
                json=payload,
            )
            resp.raise_for_status()

            log.info("Connection request sent", person_urn=person_urn)
            return {
                "sent": True,
                "person_urn": person_urn,
                "message_included": bool(message),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"LinkedIn API error: {e.response.status_code}"}

    async def _get_company(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get company (organization) details from LinkedIn."""
        if not self._client:
            return {"error": "Not connected"}

        company_id = params.get("company_id", "")
        if not company_id:
            return {"error": "company_id is required"}

        try:
            resp = await self._client.get(
                f"/organizations/{company_id}",
                params={
                    "projection": (
                        "(id,localizedName,vanityName,localizedDescription,"
                        "staffCountRange,industries,headquarter,logoV2)"
                    ),
                },
            )
            resp.raise_for_status()
            org = resp.json()

            hq = org.get("headquarter", {})
            return {
                "id": org.get("id", ""),
                "name": org.get("localizedName", ""),
                "vanity_name": org.get("vanityName", ""),
                "description": org.get("localizedDescription", ""),
                "staff_count_range": org.get("staffCountRange", ""),
                "industries": org.get("industries", []),
                "headquarters": {
                    "city": hq.get("city", ""),
                    "country": hq.get("country", ""),
                    "region": hq.get("geographicArea", ""),
                },
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"LinkedIn API error: {e.response.status_code}"}

    async def _search_companies(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search for companies on LinkedIn."""
        if not self._client:
            return {"error": "Not connected"}

        keywords = params.get("keywords", "")
        industry = params.get("industry", "")
        limit = min(params.get("limit", 25), 50)

        if not keywords:
            return {"error": "keywords is required"}

        try:
            search_params: dict[str, Any] = {
                "q": "search",
                "keywords": keywords,
                "count": limit,
            }

            resp = await self._client.get(
                "/search/companies",
                params=search_params,
            )
            resp.raise_for_status()
            data = resp.json()

            companies = []
            for element in data.get("elements", []):
                entity = element.get("entity", element)
                company_info = {
                    "urn": entity.get("entityUrn", ""),
                    "name": entity.get("name", {}).get("text", ""),
                    "industry": entity.get("primaryIndustry", {}).get("text", ""),
                    "staff_count": entity.get("staffCount", ""),
                    "headquarters": entity.get("headquarters", ""),
                }
                if industry and industry.lower() not in company_info.get("industry", "").lower():
                    continue
                companies.append(company_info)

            return {"results": companies[:limit], "count": len(companies[:limit])}
        except httpx.HTTPStatusError as e:
            return {"error": f"LinkedIn API error: {e.response.status_code}"}
