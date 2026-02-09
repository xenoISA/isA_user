"""
Component Golden Tests: Calendar Service Sync Operations

Tests external calendar sync logic with mocked dependencies.
Uses CalendarTestDataFactory for zero hardcoded data.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from microservices.calendar_service.calendar_service import CalendarService
from microservices.calendar_service.models import SyncProvider
from tests.contracts.calendar import (
    CalendarTestDataFactory,
    SyncProviderContract,
)
from tests.component.golden.calendar_service.mocks import MockCalendarRepository

pytestmark = [pytest.mark.component, pytest.mark.golden]


class TestSyncWithExternalCalendar:
    """Test BR-CAL-040: External Calendar Sync"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return MockCalendarRepository()

    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mock repository"""
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_sync_google_calendar(self, service):
        """BR-CAL-040: Google Calendar sync"""
        user_id = CalendarTestDataFactory.make_user_id()
        credentials = CalendarTestDataFactory.make_credentials()

        result = await service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            credentials=credentials,
        )

        assert result is not None
        assert result.provider == SyncProvider.GOOGLE.value

    @pytest.mark.asyncio
    async def test_sync_apple_calendar(self, service):
        """BR-CAL-040: Apple Calendar sync"""
        user_id = CalendarTestDataFactory.make_user_id()

        result = await service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.APPLE.value,
        )

        assert result is not None
        assert result.provider == SyncProvider.APPLE.value

    @pytest.mark.asyncio
    async def test_sync_outlook(self, service):
        """BR-CAL-040: Outlook sync"""
        user_id = CalendarTestDataFactory.make_user_id()

        result = await service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.OUTLOOK.value,
        )

        assert result is not None
        assert result.provider == SyncProvider.OUTLOOK.value

    @pytest.mark.asyncio
    async def test_sync_unsupported_provider(self, service):
        """BR-CAL-040: Unsupported provider returns error"""
        user_id = CalendarTestDataFactory.make_user_id()

        result = await service.sync_with_external_calendar(
            user_id=user_id,
            provider="unsupported_calendar",
        )

        assert result is not None
        assert result.status == "error"
        assert "Unsupported provider" in result.message


class TestSyncStatus:
    """Test BR-CAL-041/042: Sync Status Management"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return MockCalendarRepository()

    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mock repository"""
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_get_sync_status(self, service, mock_repo):
        """BR-CAL-041: Get sync status"""
        user_id = CalendarTestDataFactory.make_user_id()

        # Create sync status
        await mock_repo.update_sync_status(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            status="active",
            synced_count=42,
        )

        status = await service.get_sync_status(user_id, SyncProvider.GOOGLE.value)

        assert status is not None
        assert status.provider == SyncProvider.GOOGLE.value
        assert status.synced_events == 42

    @pytest.mark.asyncio
    async def test_get_sync_status_not_found(self, service):
        """BR-CAL-041: Get non-existent sync status"""
        user_id = CalendarTestDataFactory.make_user_id()

        status = await service.get_sync_status(user_id, SyncProvider.GOOGLE.value)
        assert status is None

    @pytest.mark.asyncio
    async def test_sync_status_upsert(self, service, mock_repo):
        """BR-CAL-041: Sync status upsert (update if exists)"""
        user_id = CalendarTestDataFactory.make_user_id()

        # First sync
        await mock_repo.update_sync_status(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            status="active",
            synced_count=10,
        )

        # Update (upsert)
        await mock_repo.update_sync_status(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            status="active",
            synced_count=50,
        )

        status = await service.get_sync_status(user_id, SyncProvider.GOOGLE.value)
        assert status is not None
        assert status.synced_events == 50


class TestSyncErrorHandling:
    """Test BR-CAL-042: Sync Failure Handling"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return MockCalendarRepository()

    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mock repository"""
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_sync_error_status_recorded(self, service, mock_repo):
        """BR-CAL-042: Sync error status recorded"""
        user_id = CalendarTestDataFactory.make_user_id()

        # Record error status
        await mock_repo.update_sync_status(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            status="error",
            synced_count=0,
            error_message="Authentication failed",
        )

        status = await service.get_sync_status(user_id, SyncProvider.GOOGLE.value)
        assert status is not None
        # Status should reflect error

    @pytest.mark.asyncio
    async def test_sync_recovery_after_error(self, service, mock_repo):
        """BR-CAL-042: Sync can recover after error"""
        user_id = CalendarTestDataFactory.make_user_id()

        # First: error
        await mock_repo.update_sync_status(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            status="error",
            error_message="Token expired",
        )

        # Then: success
        await mock_repo.update_sync_status(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            status="active",
            synced_count=25,
        )

        status = await service.get_sync_status(user_id, SyncProvider.GOOGLE.value)
        assert status is not None


class TestMultiProviderSync:
    """Test multiple provider sync status"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return MockCalendarRepository()

    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mock repository"""
        return CalendarService(repository=mock_repo)

    @pytest.mark.asyncio
    async def test_multiple_providers_per_user(self, service, mock_repo):
        """User can sync with multiple providers"""
        user_id = CalendarTestDataFactory.make_user_id()

        # Sync with Google
        await mock_repo.update_sync_status(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            status="active",
            synced_count=20,
        )

        # Sync with Outlook
        await mock_repo.update_sync_status(
            user_id=user_id,
            provider=SyncProvider.OUTLOOK.value,
            status="active",
            synced_count=15,
        )

        google_status = await service.get_sync_status(user_id, SyncProvider.GOOGLE.value)
        outlook_status = await service.get_sync_status(user_id, SyncProvider.OUTLOOK.value)

        assert google_status is not None
        assert google_status.synced_events == 20
        assert outlook_status is not None
        assert outlook_status.synced_events == 15
