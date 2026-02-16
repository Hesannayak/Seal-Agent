"""Tests for new API routes and modules: analytics, integrations, websocket, auth."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from seal_agent.api.auth import APIKeyManager, verify_webhook_signature


class TestAPIKeyManager:
    def setup_method(self) -> None:
        self.manager = APIKeyManager()

    def test_generate_key(self) -> None:
        key = self.manager.generate_key("test-app")
        assert key.startswith("seal_")
        assert len(key) > 10

    def test_validate_key(self) -> None:
        key = self.manager.generate_key("test-app")
        meta = self.manager.validate_key(key)
        assert meta is not None
        assert meta["name"] == "test-app"
        assert "read" in meta["scopes"]
        assert "write" in meta["scopes"]

    def test_validate_invalid_key(self) -> None:
        meta = self.manager.validate_key("invalid_key")
        assert meta is None

    def test_generate_key_with_scopes(self) -> None:
        key = self.manager.generate_key("reader", scopes=["read"])
        meta = self.manager.validate_key(key)
        assert meta is not None
        assert meta["scopes"] == ["read"]

    def test_revoke_key(self) -> None:
        key = self.manager.generate_key("to-revoke")
        assert self.manager.revoke_key(key) is True
        assert self.manager.validate_key(key) is None

    def test_revoke_nonexistent_key(self) -> None:
        assert self.manager.revoke_key("nope") is False

    def test_list_keys(self) -> None:
        self.manager.generate_key("app-1")
        self.manager.generate_key("app-2")
        keys = self.manager.list_keys()
        assert len(keys) == 2
        names = {k["name"] for k in keys}
        assert "app-1" in names
        assert "app-2" in names


class TestWebhookSignature:
    def test_valid_signature(self) -> None:
        import hashlib
        import hmac

        secret = "test_secret"
        payload = b'{"event": "test"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert verify_webhook_signature(payload, sig, secret) is True

    def test_invalid_signature(self) -> None:
        assert verify_webhook_signature(b"payload", "wrong_sig", "secret") is False


class TestAnalyticsRoutes:
    """Test analytics route module loads correctly."""

    def test_analytics_routes_importable(self) -> None:
        from seal_agent.api.routes.analytics import router
        routes = [r.path for r in router.routes]
        assert "/pipeline" in routes
        assert "/activity" in routes
        assert "/funnel" in routes
        assert "/forecast" in routes
        assert "/report" in routes


class TestIntegrationRoutes:
    """Test integration route module loads correctly."""

    def test_integration_routes_importable(self) -> None:
        from seal_agent.api.routes.integrations import router
        routes = [r.path for r in router.routes]
        assert "/" in routes

    def test_register_integrations(self) -> None:
        from seal_agent.api.routes.integrations import register_integrations
        mock_integration = MagicMock()
        mock_integration.name = "test"
        mock_integration.category = "crm"
        register_integrations({"test": mock_integration})


class TestWebSocketModule:
    def test_websocket_module_importable(self) -> None:
        from seal_agent.api.websocket import router, manager
        assert manager.active_count == 0

    def test_connection_manager_initial_state(self) -> None:
        from seal_agent.api.websocket import ConnectionManager
        mgr = ConnectionManager()
        assert mgr.active_count == 0
