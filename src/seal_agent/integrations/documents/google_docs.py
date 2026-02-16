"""Google Docs integration — Document creation and management."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from seal_agent.integrations.base import BaseIntegration

log = structlog.get_logger()

DOCS_API_BASE = "https://docs.googleapis.com/v1"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"


class GoogleDocsIntegration(BaseIntegration):
    """Google Docs integration for proposal and document generation."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._connected = False

    @property
    def name(self) -> str:
        return "google_docs"

    @property
    def category(self) -> str:
        return "documents"

    async def connect(self, credentials: dict[str, str]) -> bool:
        access_token = credentials.get("access_token", "")
        if not access_token:
            log.warning("Google Docs not configured — missing access token")
            return False

        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=20.0,
        )

        try:
            resp = await self._client.get(f"{DRIVE_API_BASE}/about", params={"fields": "user"})
            resp.raise_for_status()
            user = resp.json().get("user", {})
            self._connected = True
            log.info("Google Docs connected", user=user.get("displayName"))
            return True
        except Exception:
            log.exception("Failed to connect Google Docs")
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
            resp = await self._client.get(f"{DRIVE_API_BASE}/about", params={"fields": "user"})
            return resp.status_code == 200
        except Exception:
            return False

    async def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        actions = {
            "create_document": self._create_document,
            "get_document": self._get_document,
            "append_text": self._append_text,
            "share_document": self._share_document,
        }
        handler = actions.get(action)
        if not handler:
            raise NotImplementedError(f"Action '{action}' not implemented for Google Docs")
        return await handler(params)

    async def _create_document(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a new Google Doc."""
        if not self._client:
            return {"error": "Not connected"}
        title = params.get("title", "Untitled Document")
        body_text = params.get("body", "")

        try:
            # Create the document
            resp = await self._client.post(f"{DOCS_API_BASE}/documents", json={"title": title})
            resp.raise_for_status()
            doc = resp.json()
            doc_id = doc["documentId"]

            # Insert body text if provided
            if body_text:
                await self._client.post(
                    f"{DOCS_API_BASE}/documents/{doc_id}:batchUpdate",
                    json={
                        "requests": [
                            {
                                "insertText": {
                                    "location": {"index": 1},
                                    "text": body_text,
                                }
                            }
                        ]
                    },
                )

            return {
                "document_id": doc_id,
                "title": title,
                "url": f"https://docs.google.com/document/d/{doc_id}/edit",
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"Google Docs API error: {e.response.status_code}"}

    async def _get_document(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get document metadata and content."""
        if not self._client:
            return {"error": "Not connected"}
        doc_id = params.get("document_id", "")
        if not doc_id:
            return {"error": "document_id is required"}

        try:
            resp = await self._client.get(f"{DOCS_API_BASE}/documents/{doc_id}")
            resp.raise_for_status()
            doc = resp.json()

            # Extract plain text from document body
            text_parts = []
            for element in doc.get("body", {}).get("content", []):
                paragraph = element.get("paragraph")
                if paragraph:
                    for elem in paragraph.get("elements", []):
                        text_run = elem.get("textRun")
                        if text_run:
                            text_parts.append(text_run.get("content", ""))

            return {
                "document_id": doc_id,
                "title": doc.get("title", ""),
                "content": "".join(text_parts),
                "url": f"https://docs.google.com/document/d/{doc_id}/edit",
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"Google Docs API error: {e.response.status_code}"}

    async def _append_text(self, params: dict[str, Any]) -> dict[str, Any]:
        """Append text to an existing document."""
        if not self._client:
            return {"error": "Not connected"}
        doc_id = params.get("document_id", "")
        text = params.get("text", "")
        if not doc_id or not text:
            return {"error": "document_id and text are required"}

        try:
            # Get document to find the end index
            resp = await self._client.get(f"{DOCS_API_BASE}/documents/{doc_id}")
            resp.raise_for_status()
            doc = resp.json()
            end_index = doc["body"]["content"][-1]["endIndex"] - 1

            resp = await self._client.post(
                f"{DOCS_API_BASE}/documents/{doc_id}:batchUpdate",
                json={
                    "requests": [
                        {
                            "insertText": {
                                "location": {"index": end_index},
                                "text": text,
                            }
                        }
                    ]
                },
            )
            resp.raise_for_status()
            return {"document_id": doc_id, "appended": True}
        except httpx.HTTPStatusError as e:
            return {"error": f"Google Docs API error: {e.response.status_code}"}

    async def _share_document(self, params: dict[str, Any]) -> dict[str, Any]:
        """Share a document with specific users."""
        if not self._client:
            return {"error": "Not connected"}
        doc_id = params.get("document_id", "")
        email = params.get("email", "")
        role = params.get("role", "reader")  # reader, writer, commenter
        if not doc_id or not email:
            return {"error": "document_id and email are required"}

        try:
            resp = await self._client.post(
                f"{DRIVE_API_BASE}/files/{doc_id}/permissions",
                json={
                    "type": "user",
                    "role": role,
                    "emailAddress": email,
                },
            )
            resp.raise_for_status()
            return {"document_id": doc_id, "shared_with": email, "role": role}
        except httpx.HTTPStatusError as e:
            return {"error": f"Google API error: {e.response.status_code}"}
