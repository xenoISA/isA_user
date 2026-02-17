"""
Calendar Service Smoke Tests

Quick validation tests that verify core functionality works.
These tests should run fast and catch obvious failures.
Target: 15-18 tests covering critical paths.

Usage:
    pytest tests/smoke/calendar_service/test_calendar_smoke.py -v --tb=short
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from tests.contracts.calendar import (
    CalendarTestDataFactory,
    EventCreateRequestContract,
    EventCategoryContract,
    RecurrenceTypeContract,
    SyncProviderContract,
)
from microservices.calendar_service.calendar_service import CalendarService
from microservices.calendar_service.models import (
    EventCreateRequest,
    EventUpdateRequest,
    EventQueryRequest,
    EventCategory,
)
from tests.component.golden.calendar_service.mocks import MockCalendarRepository

pytestmark = [pytest.mark.smoke]


# ============================================================================
# Service Instantiation Smoke Tests
# ============================================================================

class TestServiceInstantiation:
    """Smoke tests for service instantiation"""

    def test_service_can_be_created(self):
        """CalendarService can be instantiated"""
        repo = MockCalendarRepository()
        service = CalendarService(repository=repo)
        assert service is not None

    def test_service_with_event_bus(self):
        """CalendarService can be created with event bus"""
        repo = MockCalendarRepository()
        event_bus = AsyncMock()
        service = CalendarService(repository=repo, event_bus=event_bus)
        assert service is not None


# ============================================================================
# Event CRUD Smoke Tests
# ============================================================================

class TestEventCRUDSmoke:
    """Smoke tests for event CRUD operations"""

    @pytest.fixture
    def service(self):
        """Create service with mock repository"""
        return CalendarService(repository=MockCalendarRepository())

    @pytest.mark.asyncio
    async def test_create_event_smoke(self, service):
        """Event creation works"""
        request_data = CalendarTestDataFactory.make_create_request_minimal()

        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
        )

        result = await service.create_event(request)
        assert result is not None
        assert result.event_id is not None

    @pytest.mark.asyncio
    async def test_get_event_smoke(self, service):
        """Event retrieval works"""
        # Create an event first
        request_data = CalendarTestDataFactory.make_create_request_minimal()
        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
        )
        created = await service.create_event(request)

        # Retrieve it
        result = await service.get_event(created.event_id)
        assert result is not None
        assert result.event_id == created.event_id

    @pytest.mark.asyncio
    async def test_update_event_smoke(self, service):
        """Event update works"""
        # Create an event first
        request_data = CalendarTestDataFactory.make_create_request_minimal()
        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
        )
        created = await service.create_event(request)

        # Update it
        update = EventUpdateRequest(title="Updated Title")
        result = await service.update_event(created.event_id, update)
        assert result is not None
        assert result.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_event_smoke(self, service):
        """Event deletion works"""
        # Create an event first
        request_data = CalendarTestDataFactory.make_create_request_minimal()
        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
        )
        created = await service.create_event(request)

        # Delete it
        result = await service.delete_event(created.event_id)
        assert result is True

        # Verify deleted
        get_result = await service.get_event(created.event_id)
        assert get_result is None


# ============================================================================
# Query Smoke Tests
# ============================================================================

class TestQuerySmoke:
    """Smoke tests for query operations"""

    @pytest.fixture
    def service(self):
        """Create service with mock repository"""
        return CalendarService(repository=MockCalendarRepository())

    @pytest.mark.asyncio
    async def test_query_events_smoke(self, service):
        """Event query works"""
        user_id = CalendarTestDataFactory.make_user_id()

        request = EventQueryRequest(user_id=user_id)
        result = await service.query_events(request)

        assert result is not None
        assert hasattr(result, "events")
        assert hasattr(result, "total")

    @pytest.mark.asyncio
    async def test_today_events_smoke(self, service):
        """Today events query works"""
        user_id = CalendarTestDataFactory.make_user_id()

        result = await service.get_today_events(user_id)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_upcoming_events_smoke(self, service):
        """Upcoming events query works"""
        user_id = CalendarTestDataFactory.make_user_id()

        result = await service.get_upcoming_events(user_id)
        assert isinstance(result, list)


# ============================================================================
# Model Smoke Tests
# ============================================================================

class TestModelSmoke:
    """Smoke tests for model creation"""

    def test_create_request_model(self):
        """EventCreateRequest model works"""
        request_data = CalendarTestDataFactory.make_create_request()
        assert request_data is not None
        assert request_data.title is not None

    def test_update_request_model(self):
        """EventUpdateRequest model works"""
        request = EventUpdateRequest(title="Test")
        assert request is not None
        assert request.title == "Test"

    def test_query_request_model(self):
        """EventQueryRequest model works"""
        user_id = CalendarTestDataFactory.make_user_id()
        request = EventQueryRequest(user_id=user_id)
        assert request is not None
        assert request.user_id == user_id


# ============================================================================
# Factory Smoke Tests
# ============================================================================

class TestFactorySmoke:
    """Smoke tests for test data factory"""

    def test_factory_make_event_id(self):
        """Factory generates event IDs"""
        event_id = CalendarTestDataFactory.make_event_id()
        assert event_id is not None
        assert event_id.startswith("evt_")

    def test_factory_make_user_id(self):
        """Factory generates user IDs"""
        user_id = CalendarTestDataFactory.make_user_id()
        assert user_id is not None
        assert user_id.startswith("usr_")

    def test_factory_make_time_range(self):
        """Factory generates time ranges"""
        start, end = CalendarTestDataFactory.make_time_range()
        assert start is not None
        assert end is not None
        assert end > start

    def test_factory_make_create_request(self):
        """Factory generates create requests"""
        request = CalendarTestDataFactory.make_create_request()
        assert request is not None
        assert request.user_id is not None
        assert request.title is not None
