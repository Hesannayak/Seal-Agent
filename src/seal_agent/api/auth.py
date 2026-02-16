"""API authentication module."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import hashlib
import hmac
import secrets

import structlog
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from seal_agent.config import settings

log = structlog.get_logger()

security = HTTPBearer(auto_error=False)


class APIKeyManager:
    """Manages API keys for authentication."""

    def __init__(self) -> None:
        self._keys: dict[str, dict[str, Any]] = {}

    def generate_key(self, name: str, scopes: list[str] | None = None) -> str:
        """Generate a new API key."""
        key = f"seal_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(key)
        self._keys[key_hash] = {
            "name": name,
            "scopes": scopes or ["read", "write"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
        }
        return key

    def validate_key(self, key: str) -> dict[str, Any] | None:
        """Validate an API key and return its metadata."""
        key_hash = self._hash_key(key)
        meta = self._keys.get(key_hash)
        if meta:
            meta["last_used"] = datetime.now(timezone.utc).isoformat()
            return meta
        return None

    def revoke_key(self, key: str) -> bool:
        """Revoke an API key."""
        key_hash = self._hash_key(key)
        return self._keys.pop(key_hash, None) is not None

    def list_keys(self) -> list[dict[str, Any]]:
        """List all API keys (without the actual key values)."""
        return [
            {"name": v["name"], "scopes": v["scopes"], "created_at": v["created_at"], "last_used": v["last_used"]}
            for v in self._keys.values()
        ]

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()


# Global key manager instance
key_manager = APIKeyManager()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """Dependency to authenticate API requests.

    Supports two modes:
    1. Bearer token matching settings.api_key (simple mode)
    2. API key via key_manager (managed mode)
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication")

    token = credentials.credentials

    # Check against configured API key first
    if settings.api_key and token == settings.api_key:
        return {"name": "admin", "scopes": ["read", "write", "admin"]}

    # Check against managed keys
    meta = key_manager.validate_key(token)
    if meta:
        return meta

    raise HTTPException(status_code=401, detail="Invalid authentication token")


def require_scope(scope: str):
    """Dependency factory to require a specific scope."""
    async def check_scope(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if scope not in user.get("scopes", []):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions — requires '{scope}' scope",
            )
        return user
    return check_scope


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """Verify a webhook HMAC signature."""
    expected = hmac.new(
        secret.encode(),
        payload,
        getattr(hashlib, algorithm),
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
