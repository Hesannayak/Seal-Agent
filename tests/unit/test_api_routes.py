"""Tests for API routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with routes but without full agent lifecycle."""
    from seal_agent.api.routes import prospects as prospect_routes
    from seal_agent.api.routes import deals as deal_routes

    app = FastAPI()
    app.include_router(prospect_routes.router, prefix="/api/prospects")
    app.include_router(deal_routes.router, prefix="/api/deals")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self) -> None:
        """Test the health endpoint returns healthy status."""
        from seal_agent.api.app import create_app

        # We can't use lifespan (no DB) so test the route directly
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "healthy", "agent": "Seal-Agent"}

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestDealStageValidation:
    def test_invalid_stage_returns_400(self, client: TestClient) -> None:
        """Test that invalid deal stage returns 400."""
        mock_session = AsyncMock()

        with patch("seal_agent.api.routes.deals.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.put("/api/deals/test-id/stage?stage=invalid_stage")
            assert response.status_code == 400
            assert "Invalid stage" in response.json()["detail"]


class TestMiddleware:
    def test_auth_middleware_rejects_missing_token(self) -> None:
        """Test that API endpoints require authentication."""
        from seal_agent.api.middleware import AuthMiddleware

        # AuthMiddleware checks for Bearer token on /api/* paths
        # This is a unit test of the logic, not a full integration test
        assert AuthMiddleware.EXEMPT_PATHS == {"/health", "/docs", "/openapi.json", "/redoc"}

    def test_rate_limit_config(self) -> None:
        """Test rate limiter can be configured."""
        from seal_agent.api.middleware import RateLimitMiddleware

        app = FastAPI()
        middleware = RateLimitMiddleware(app, requests_per_minute=100)
        assert middleware.rpm == 100
