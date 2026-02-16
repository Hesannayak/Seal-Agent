"""Salesforce CRM integration."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.config import settings
from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()


class SalesforceIntegration(BaseIntegration):
    """Salesforce CRM integration for leads, contacts, opportunities, and activities."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False
        self._instance_url: str = ""

    @property
    def name(self) -> str:
        return "salesforce"

    @property
    def category(self) -> str:
        return "crm"

    async def connect(self, credentials: dict[str, str]) -> bool:
        """Authenticate via OAuth 2.0 password flow or pre-supplied access token."""
        access_token = credentials.get("access_token", "")
        instance_url = credentials.get("instance_url", "")

        # If no access token provided, try OAuth password flow
        if not access_token:
            client_id = credentials.get("client_id", "")
            client_secret = credentials.get("client_secret", "")
            username = credentials.get("username", "")
            password = credentials.get("password", "")
            security_token = credentials.get("security_token", "")

            if not all([client_id, client_secret, username, password]):
                log.warning("Salesforce integration not configured — missing credentials")
                return False

            try:
                async with httpx.AsyncClient() as auth_client:
                    resp = await auth_client.post(
                        "https://login.salesforce.com/services/oauth2/token",
                        data={
                            "grant_type": "password",
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "username": username,
                            "password": f"{password}{security_token}",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    access_token = data["access_token"]
                    instance_url = data["instance_url"]
            except Exception:
                log.exception("Salesforce OAuth authentication failed")
                return False

        if not instance_url:
            log.error("Salesforce instance_url is required")
            return False

        self._instance_url = instance_url
        self._client = httpx.AsyncClient(
            base_url=f"{instance_url}/services/data/v59.0",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        try:
            resp = await self._client.get("/sobjects")
            resp.raise_for_status()
            self._connected = True
            log.info("Salesforce integration connected", instance=instance_url)
            return True
        except Exception:
            log.exception("Salesforce connection verification failed")
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
            resp = await self._client.get("/limits")
            return resp.status_code == 200
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "create_lead": self._create_lead,
            "get_lead": self._get_lead,
            "create_opportunity": self._create_opportunity,
            "update_opportunity": self._update_opportunity,
            "search": self._search,
            "create_task": self._create_task,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for Salesforce")
        return await handler(params)

    async def _create_lead(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}

        try:
            resp = await self._client.post(
                "/sobjects/Lead",
                json={
                    "FirstName": params.get("first_name", ""),
                    "LastName": params.get("last_name", ""),
                    "Email": params.get("email", ""),
                    "Phone": params.get("phone", ""),
                    "Title": params.get("title", ""),
                    "Company": params.get("company", "Unknown"),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {"id": data.get("id"), "success": data.get("success", True)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Salesforce API error: {e.response.status_code}"}

    async def _get_lead(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}

        lead_id = params.get("lead_id")
        if not lead_id:
            return {"error": "lead_id is required"}

        try:
            resp = await self._client.get(f"/sobjects/Lead/{lead_id}")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"Salesforce API error: {e.response.status_code}"}

    async def _create_opportunity(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}

        try:
            resp = await self._client.post(
                "/sobjects/Opportunity",
                json={
                    "Name": params.get("name", ""),
                    "StageName": params.get("stage", "Prospecting"),
                    "Amount": params.get("amount", 0),
                    "CloseDate": params.get("close_date", ""),
                    "AccountId": params.get("account_id"),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {"id": data.get("id"), "success": data.get("success", True)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Salesforce API error: {e.response.status_code}"}

    async def _update_opportunity(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"error": "Not connected"}

        opp_id = params.get("opportunity_id")
        if not opp_id:
            return {"error": "opportunity_id is required"}

        update_fields = {}
        if "stage" in params:
            update_fields["StageName"] = params["stage"]
        if "amount" in params:
            update_fields["Amount"] = params["amount"]

        try:
            resp = await self._client.patch(
                f"/sobjects/Opportunity/{opp_id}",
                json=update_fields,
            )
            resp.raise_for_status()
            return {"id": opp_id, "updated": True}
        except httpx.HTTPStatusError as e:
            return {"error": f"Salesforce API error: {e.response.status_code}"}

    async def _search(self, params: dict[str, Any]) -> dict[str, Any]:
        """SOSL search across Salesforce objects."""
        if not self._client:
            return {"error": "Not connected"}

        query = params.get("query", "")
        if not query:
            return {"error": "query is required"}

        try:
            resp = await self._client.get(
                "/search",
                params={"q": f"FIND {{{query}}} IN ALL FIELDS RETURNING Lead, Contact, Opportunity"},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"Salesforce API error: {e.response.status_code}"}

    async def _create_task(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a task (follow-up, call, etc.) in Salesforce."""
        if not self._client:
            return {"error": "Not connected"}

        try:
            resp = await self._client.post(
                "/sobjects/Task",
                json={
                    "Subject": params.get("subject", "Follow up"),
                    "Description": params.get("description", ""),
                    "WhoId": params.get("who_id"),
                    "WhatId": params.get("what_id"),
                    "Status": params.get("status", "Not Started"),
                    "Priority": params.get("priority", "Normal"),
                    "ActivityDate": params.get("due_date"),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {"id": data.get("id"), "success": data.get("success", True)}
        except httpx.HTTPStatusError as e:
            return {"error": f"Salesforce API error: {e.response.status_code}"}
