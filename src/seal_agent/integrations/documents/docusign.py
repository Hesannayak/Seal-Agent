"""DocuSign integration — Electronic signature and contract management."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

DOCUSIGN_API_BASE = "https://demo.docusign.net/restapi/v2.1"  # Use na1.docusign.net for production


class DocuSignIntegration(BaseIntegration):
    """DocuSign integration for electronic signatures and contract management."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False
        self._account_id: str = ""

    @property
    def name(self) -> str:
        return "docusign"

    @property
    def category(self) -> str:
        return "documents"

    async def connect(self, credentials: dict[str, str]) -> bool:
        access_token = credentials.get("access_token", "")
        self._account_id = credentials.get("account_id", "")
        base_url = credentials.get("base_url", DOCUSIGN_API_BASE)

        if not access_token or not self._account_id:
            log.warning("DocuSign not configured — missing access_token or account_id")
            return False

        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        try:
            resp = await self._client.get(f"/accounts/{self._account_id}")
            resp.raise_for_status()
            account = resp.json()
            self._connected = True
            log.info("DocuSign connected", account=account.get("accountName"))
            return True
        except Exception:
            log.exception("Failed to connect DocuSign")
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
            resp = await self._client.get(f"/accounts/{self._account_id}")
            return resp.status_code == 200
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "create_envelope": self._create_envelope,
            "get_envelope": self._get_envelope,
            "list_envelopes": self._list_envelopes,
            "void_envelope": self._void_envelope,
            "get_signing_url": self._get_signing_url,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for DocuSign")
        return await handler(params)

    async def _create_envelope(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create and send an envelope for signing."""
        if not self._client:
            return {"error": "Not connected"}

        subject = params.get("subject", "Please sign this document")
        signer_email = params.get("signer_email", "")
        signer_name = params.get("signer_name", "")
        document_name = params.get("document_name", "contract.pdf")
        document_base64 = params.get("document_base64", "")

        if not signer_email or not signer_name:
            return {"error": "signer_email and signer_name are required"}

        try:
            envelope_def: dict[str, Any] = {
                "emailSubject": subject,
                "status": params.get("status", "sent"),
                "recipients": {
                    "signers": [
                        {
                            "email": signer_email,
                            "name": signer_name,
                            "recipientId": "1",
                            "routingOrder": "1",
                        }
                    ]
                },
            }

            if document_base64:
                envelope_def["documents"] = [
                    {
                        "documentBase64": document_base64,
                        "name": document_name,
                        "fileExtension": document_name.split(".")[-1],
                        "documentId": "1",
                    }
                ]

            if params.get("cc_email"):
                envelope_def["recipients"]["carbonCopies"] = [
                    {
                        "email": params["cc_email"],
                        "name": params.get("cc_name", params["cc_email"]),
                        "recipientId": "2",
                        "routingOrder": "2",
                    }
                ]

            resp = await self._client.post(
                f"/accounts/{self._account_id}/envelopes",
                json=envelope_def,
            )
            resp.raise_for_status()
            envelope = resp.json()

            return {
                "envelope_id": envelope.get("envelopeId"),
                "status": envelope.get("status"),
                "uri": envelope.get("uri"),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"DocuSign API error: {e.response.status_code}"}

    async def _get_envelope(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get envelope status and details."""
        if not self._client:
            return {"error": "Not connected"}
        envelope_id = params.get("envelope_id", "")
        if not envelope_id:
            return {"error": "envelope_id is required"}

        try:
            resp = await self._client.get(
                f"/accounts/{self._account_id}/envelopes/{envelope_id}"
            )
            resp.raise_for_status()
            env = resp.json()
            return {
                "envelope_id": env.get("envelopeId"),
                "status": env.get("status"),
                "subject": env.get("emailSubject"),
                "sent_at": env.get("sentDateTime"),
                "completed_at": env.get("completedDateTime"),
                "voided_at": env.get("voidedDateTime"),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"DocuSign API error: {e.response.status_code}"}

    async def _list_envelopes(self, params: dict[str, Any]) -> dict[str, Any]:
        """List envelopes with optional filters."""
        if not self._client:
            return {"error": "Not connected"}

        try:
            query: dict[str, Any] = {"count": params.get("limit", 25)}
            if params.get("from_date"):
                query["from_date"] = params["from_date"]
            if params.get("status"):
                query["status"] = params["status"]

            resp = await self._client.get(
                f"/accounts/{self._account_id}/envelopes",
                params=query,
            )
            resp.raise_for_status()
            data = resp.json()

            envelopes = []
            for env in data.get("envelopes", []):
                envelopes.append({
                    "envelope_id": env.get("envelopeId"),
                    "status": env.get("status"),
                    "subject": env.get("emailSubject"),
                    "sent_at": env.get("sentDateTime"),
                })

            return {
                "envelopes": envelopes,
                "count": len(envelopes),
                "total": data.get("totalSetSize"),
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"DocuSign API error: {e.response.status_code}"}

    async def _void_envelope(self, params: dict[str, Any]) -> dict[str, Any]:
        """Void/cancel an envelope."""
        if not self._client:
            return {"error": "Not connected"}
        envelope_id = params.get("envelope_id", "")
        reason = params.get("reason", "Voided by Seal-Agent")
        if not envelope_id:
            return {"error": "envelope_id is required"}

        try:
            resp = await self._client.put(
                f"/accounts/{self._account_id}/envelopes/{envelope_id}",
                json={"status": "voided", "voidedReason": reason},
            )
            resp.raise_for_status()
            return {"envelope_id": envelope_id, "status": "voided", "reason": reason}
        except httpx.HTTPStatusError as e:
            return {"error": f"DocuSign API error: {e.response.status_code}"}

    async def _get_signing_url(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get an embedded signing URL for a recipient."""
        if not self._client:
            return {"error": "Not connected"}
        envelope_id = params.get("envelope_id", "")
        signer_email = params.get("signer_email", "")
        signer_name = params.get("signer_name", "")
        return_url = params.get("return_url", "https://example.com/signing-complete")

        if not envelope_id or not signer_email or not signer_name:
            return {"error": "envelope_id, signer_email, and signer_name are required"}

        try:
            resp = await self._client.post(
                f"/accounts/{self._account_id}/envelopes/{envelope_id}/views/recipient",
                json={
                    "email": signer_email,
                    "userName": signer_name,
                    "returnUrl": return_url,
                    "authenticationMethod": "none",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {"url": data.get("url"), "envelope_id": envelope_id}
        except httpx.HTTPStatusError as e:
            return {"error": f"DocuSign API error: {e.response.status_code}"}
