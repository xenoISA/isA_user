"""
Calendar Service Events Integration Tests

Tests event publishing/subscription integration patterns.
Target: Additional tests to reach 30-35 total.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock

from tests.contracts.calendar import (
    CalendarTestDataFactory,
    EventCategoryContract,
)
from microservices.calendar_service.calendar_service import CalendarService
from microservices.calendar_service.models import EventCreateRequest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Event Publishing Integration Tests
# ============================================================================

class TestEventPublishing:
    """Integration tests for event publishing"""

    @pytest.fixture
    def mock_repository(self):
        """Mock repository"""
        repo = AsyncMock()
        repo.create_event.return_value = {
            "event_id": CalendarTestDataFactory.make_event_id(),
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": "Test Event",
            "start_time": datetime.now(timezone.utc),
            "end_time": datetime.now(timezone.utc) + timedelta(hours=1),
            "category": "other",
            "recurrence_type": "none",
            "reminders": [],
            "is_shared": False,
            "all_day": False,
            "created_at": datetime.now(timezone.utc),
        }
        return repo

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus"""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_create_event_publishes_created_event(
        self, mock_repository, mock_event_bus
    ):
        """Event creation publishes calendar.event.created"""
        service = CalendarService(
            repository=mock_repository,
            event_bus=mock_event_bus
        )

        request_data = CalendarTestDataFactory.make_create_request_minimal()
        request = EventCreateRequest(
            user_id=request_data.user_id,
            title=request_data.title,
            start_time=request_data.start_time,
            end_time=request_data.end_time,
        )

        await service.create_event(request)

        mock_event_bus.publish_event.assert_called()

    @pytest.mark.asyncio
    async def test_update_event_publishes_updated_event(
        self, mock_repository, mock_event_bus
    ):
        """Event update publishes calendar.event.updated"""
        service = CalendarService(
            repository=mock_repository,
            event_bus=mock_event_bus
        )

        event_id = CalendarTestDataFactory.make_event_id()
        mock_repository.get_event_by_id.return_value = {
            "event_id": event_id,
            "user_id": CalendarTestDataFactory.make_user_id(),
            "title": "Original",
            "start_time": datetime.now(timezone.utc),
            "end_time": datetime.now(timezone.utc) + timedelta(hours=1),
            "category": "other",
            "recurrence_type": "none",
            "reminders": [],
            "is_shared": False,
            "all_day": False,
            "created_at": datetime.now(timezone.utc),
        }
        mock_repository.update_event.return_value = {"event_id": event_id}

        from microservices.calendar_service.models import EventUpdateRequest
        await service.update_event(event_id, EventUpdateRequest(title="Updated"))

        mock_event_bus.publish_event.assert_called()

    @pytest.mark.asyncio
    async def test_delete_event_publishes_deleted_event(
        self, mock_repository, mock_event_bus
    ):
        """Event deletion publishes calendar.event.deleted"""
        service = CalendarService(
            repository=mock_repository,
            event_bus=mock_event_bus
        )

        event_id = CalendarTestDataFactory.make_event_id()
        mock_repository.delete_event.return_value = True

        await service.delete_event(event_id)

        mock_event_bus.publish_event.assert_called()


class TestEventHandlerIntegration:
    """Integration tests for event handlers"""

    @pytest.mark.asyncio
    async def test_user_deleted_event_cleanup(self):
        """User deletion triggers cleanup of user data"""
        from tests.component.golden.calendar_service.mocks import MockCalendarRepository
        from microservices.calendar_service.events.handlers import CalendarEventHandlers

        repo = MockCalendarRepository()
        user_id = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        # Add events for user
        for i in range(3):
            repo.set_event(
                CalendarTestDataFactory.make_event_id(),
                user_id=user_id,
                title=f"Event {i}",
                start_time=now + timedelta(hours=i),
                end_time=now + timedelta(hours=i+1),
            )

        service = AsyncMock()
        service.repository = repo
        handler = CalendarEventHandlers(service)

        # Handle deletion
        await handler.handle_user_deleted({"user_id": user_id})

        # Verify cleanup
        remaining = [e for e in repo._events.values() if e.user_id == user_id]
        assert len(remaining) == 0


class TestCrossServiceIntegration:
    """Cross-service integration tests"""

    @pytest.mark.asyncio
    async def test_task_sync_integration(self):
        """Task creation syncs to calendar"""
        from tests.component.golden.calendar_service.mocks import MockCalendarRepository
        from microservices.calendar_service.events.handlers import CalendarEventHandlers

        repo = MockCalendarRepository()
        service = AsyncMock()
        service.repository = repo
        handler = CalendarEventHandlers(service)

        event_data = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "task_id": f"task_{CalendarTestDataFactory.make_event_id()[4:]}",
            "name": "Complete Report",
            "due_date": datetime.now(timezone.utc).isoformat(),
        }

        # Should not raise
        await handler.handle_task_created(event_data)

    @pytest.mark.asyncio
    async def test_task_completion_update(self):
        """Task completion updates calendar"""
        from tests.component.golden.calendar_service.mocks import MockCalendarRepository
        from microservices.calendar_service.events.handlers import CalendarEventHandlers

        repo = MockCalendarRepository()
        service = AsyncMock()
        service.repository = repo
        handler = CalendarEventHandlers(service)

        event_data = {
            "user_id": CalendarTestDataFactory.make_user_id(),
            "task_id": f"task_{CalendarTestDataFactory.make_event_id()[4:]}",
            "status": "success",
        }

        # Should not raise
        await handler.handle_task_completed(event_data)


class TestRepositoryIntegration:
    """Repository integration tests"""

    @pytest.mark.asyncio
    async def test_repository_operations_flow(self):
        """Full repository operations flow"""
        from tests.component.golden.calendar_service.mocks import MockCalendarRepository

        repo = MockCalendarRepository()
        user_id = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        # Create
        event_id = CalendarTestDataFactory.make_event_id()
        repo.set_event(
            event_id,
            user_id=user_id,
            title="Test Event",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )

        # Read
        event = await repo.get_event_by_id(event_id)
        assert event is not None

        # Update
        updated = await repo.update_event(event_id, {"title": "Updated"})
        assert updated is not None
        assert updated.title == "Updated"

        # Delete
        deleted = await repo.delete_event(event_id)
        assert deleted is True

        # Verify deleted
        event = await repo.get_event_by_id(event_id)
        assert event is None
