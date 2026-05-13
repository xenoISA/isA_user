"""
Component Golden Tests: Calendar Service Sync Operations

Tests external calendar sync logic with mocked dependencies.
Uses CalendarTestDataFactory for zero hardcoded data.
"""
import pytest
from datetime import datetime, timezone

from microservices.calendar_service.calendar_service import CalendarService
from microservices.calendar_service.models import SyncProvider
from microservices.calendar_service.clients.provider_models import (
    ProviderCalendarEvent,
    ProviderSyncResult,
)
from tests.contracts.calendar import CalendarTestDataFactory
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

    @pytest.fixture
    def provider_event(self):
        now = datetime.now(timezone.utc)
        return ProviderCalendarEvent(
            external_event_id="provider-event-1",
            title="Provider Event",
            start_time=now,
            end_time=now,
            location="Remote",
            metadata={"source": "test"},
        )

    @pytest.mark.asyncio
    async def test_sync_google_calendar(self, mock_repo, provider_event):
        """BR-CAL-040: Google Calendar sync"""
        user_id = CalendarTestDataFactory.make_user_id()
        credentials = CalendarTestDataFactory.make_credentials()
        provider_client = StubProviderClient(
            ProviderSyncResult(events=[provider_event], sync_token="google-token-1")
        )
        service = CalendarService(
            repository=mock_repo,
            provider_clients={SyncProvider.GOOGLE.value: provider_client},
        )

        result = await service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            credentials=credentials,
        )

        assert result is not None
        assert result.provider == SyncProvider.GOOGLE.value
        assert result.synced_events == 1
        assert result.sync_token == "google-token-1"
        assert provider_client.calls[0]["sync_token"] is None

        events = await mock_repo.get_events_by_user(user_id)
        assert len(events) == 1
        assert events[0].sync_provider == SyncProvider.GOOGLE.value
        assert events[0].external_event_id == provider_event.external_event_id

    @pytest.mark.asyncio
    async def test_sync_apple_calendar(self, service):
        """BR-CAL-040: Apple Calendar is explicitly unsupported for now"""
        user_id = CalendarTestDataFactory.make_user_id()

        result = await service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.APPLE.value,
        )

        assert result is not None
        assert result.provider == SyncProvider.APPLE.value
        assert result.status == "error"
        assert "CalDAV" in result.message

    @pytest.mark.asyncio
    async def test_sync_outlook(self, mock_repo, provider_event):
        """BR-CAL-040: Outlook sync"""
        user_id = CalendarTestDataFactory.make_user_id()
        provider_client = StubProviderClient(
            ProviderSyncResult(events=[provider_event], sync_token="outlook-delta-link")
        )
        service = CalendarService(
            repository=mock_repo,
            provider_clients={SyncProvider.OUTLOOK.value: provider_client},
        )

        result = await service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.OUTLOOK.value,
            credentials=CalendarTestDataFactory.make_credentials(),
        )

        assert result is not None
        assert result.provider == SyncProvider.OUTLOOK.value
        assert result.synced_events == 1
        assert result.sync_token == "outlook-delta-link"

    @pytest.mark.asyncio
    async def test_sync_reuses_saved_sync_token(self, mock_repo, provider_event):
        user_id = CalendarTestDataFactory.make_user_id()
        await mock_repo.update_sync_status(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            status="active",
            synced_count=1,
            sync_token="saved-token",
        )
        provider_client = StubProviderClient(
            ProviderSyncResult(events=[provider_event], sync_token="next-token")
        )
        service = CalendarService(
            repository=mock_repo,
            provider_clients={SyncProvider.GOOGLE.value: provider_client},
        )

        result = await service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            credentials=CalendarTestDataFactory.make_credentials(),
        )

        assert result.status == "success"
        assert provider_client.calls[0]["sync_token"] == "saved-token"
        status = await service.get_sync_status(user_id, SyncProvider.GOOGLE.value)
        assert status.sync_token == "next-token"

    @pytest.mark.asyncio
    async def test_repeated_sync_upserts_existing_external_event(
        self, mock_repo, provider_event
    ):
        user_id = CalendarTestDataFactory.make_user_id()
        provider_client = StubProviderClient(
            ProviderSyncResult(events=[provider_event], sync_token="token")
        )
        service = CalendarService(
            repository=mock_repo,
            provider_clients={SyncProvider.GOOGLE.value: provider_client},
        )

        await service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            credentials=CalendarTestDataFactory.make_credentials(),
        )
        await service.sync_with_external_calendar(
            user_id=user_id,
            provider=SyncProvider.GOOGLE.value,
            credentials=CalendarTestDataFactory.make_credentials(),
        )

        events = await mock_repo.get_events_by_user(user_id)
        assert len(events) == 1
        assert events[0].external_event_id == provider_event.external_event_id

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


class StubProviderClient:
    def __init__(self, result: ProviderSyncResult):
        self.result = result
        self.calls = []

    async def list_events(self, credentials, *, sync_token=None):
        self.calls.append({"credentials": credentials, "sync_token": sync_token})
        return self.result


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

        google_status = await service.get_sync_status(
            user_id, SyncProvider.GOOGLE.value
        )
        outlook_status = await service.get_sync_status(
            user_id, SyncProvider.OUTLOOK.value
        )

        assert google_status is not None
        assert google_status.synced_events == 20
        assert outlook_status is not None
        assert outlook_status.synced_events == 15
