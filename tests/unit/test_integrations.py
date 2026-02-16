"""Tests for integration modules — verify imports, names, categories, initial state."""

from __future__ import annotations

import pytest

from seal_agent.integrations.crm.pipedrive import PipedriveIntegration
from seal_agent.integrations.communication.teams import TeamsIntegration
from seal_agent.integrations.communication.whatsapp import WhatsAppIntegration
from seal_agent.integrations.sales_tools.apollo import ApolloIntegration
from seal_agent.integrations.sales_tools.zoominfo import ZoomInfoIntegration
from seal_agent.integrations.calendar.google_cal import GoogleCalendarIntegration
from seal_agent.integrations.documents.google_docs import GoogleDocsIntegration
from seal_agent.integrations.documents.docusign import DocuSignIntegration


class TestPipedrive:
    def test_name_and_category(self) -> None:
        i = PipedriveIntegration()
        assert i.name == "pipedrive"
        assert i.category == "crm"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self) -> None:
        i = PipedriveIntegration()
        assert await i.health_check() is False

    @pytest.mark.asyncio
    async def test_connect_missing_credentials(self) -> None:
        i = PipedriveIntegration()
        result = await i.connect({})
        assert result is False


class TestTeams:
    def test_name_and_category(self) -> None:
        i = TeamsIntegration()
        assert i.name == "teams"
        assert i.category == "communication"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self) -> None:
        i = TeamsIntegration()
        assert await i.health_check() is False

    @pytest.mark.asyncio
    async def test_connect_missing_credentials(self) -> None:
        i = TeamsIntegration()
        result = await i.connect({})
        assert result is False


class TestWhatsApp:
    def test_name_and_category(self) -> None:
        i = WhatsAppIntegration()
        assert i.name == "whatsapp"
        assert i.category == "communication"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self) -> None:
        i = WhatsAppIntegration()
        assert await i.health_check() is False

    @pytest.mark.asyncio
    async def test_connect_missing_credentials(self) -> None:
        i = WhatsAppIntegration()
        result = await i.connect({})
        assert result is False


class TestApollo:
    def test_name_and_category(self) -> None:
        i = ApolloIntegration()
        assert i.name == "apollo"
        assert i.category == "sales_tools"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self) -> None:
        i = ApolloIntegration()
        assert await i.health_check() is False

    @pytest.mark.asyncio
    async def test_connect_missing_credentials(self) -> None:
        i = ApolloIntegration()
        result = await i.connect({})
        assert result is False


class TestZoomInfo:
    def test_name_and_category(self) -> None:
        i = ZoomInfoIntegration()
        assert i.name == "zoominfo"
        assert i.category == "sales_tools"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self) -> None:
        i = ZoomInfoIntegration()
        assert await i.health_check() is False

    @pytest.mark.asyncio
    async def test_connect_missing_credentials(self) -> None:
        i = ZoomInfoIntegration()
        result = await i.connect({})
        assert result is False


class TestGoogleCalendar:
    def test_name_and_category(self) -> None:
        i = GoogleCalendarIntegration()
        assert i.name == "google_calendar"
        assert i.category == "calendar"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self) -> None:
        i = GoogleCalendarIntegration()
        assert await i.health_check() is False

    @pytest.mark.asyncio
    async def test_connect_missing_credentials(self) -> None:
        i = GoogleCalendarIntegration()
        result = await i.connect({})
        assert result is False


class TestGoogleDocs:
    def test_name_and_category(self) -> None:
        i = GoogleDocsIntegration()
        assert i.name == "google_docs"
        assert i.category == "documents"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self) -> None:
        i = GoogleDocsIntegration()
        assert await i.health_check() is False

    @pytest.mark.asyncio
    async def test_connect_missing_credentials(self) -> None:
        i = GoogleDocsIntegration()
        result = await i.connect({})
        assert result is False


class TestDocuSign:
    def test_name_and_category(self) -> None:
        i = DocuSignIntegration()
        assert i.name == "docusign"
        assert i.category == "documents"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self) -> None:
        i = DocuSignIntegration()
        assert await i.health_check() is False

    @pytest.mark.asyncio
    async def test_connect_missing_credentials(self) -> None:
        i = DocuSignIntegration()
        result = await i.connect({})
        assert result is False
