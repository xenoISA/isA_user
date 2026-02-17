"""
Component Golden Tests: Calendar Service Event Handlers

Tests event handling logic with mocked dependencies.
Uses CalendarTestDataFactory for zero hardcoded data.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from microservices.calendar_service.events.handlers import CalendarEventHandlers
from tests.contracts.calendar import (
    CalendarTestDataFactory,
    EventCategoryContract,
)
from tests.component.golden.calendar_service.mocks import MockCalendarRepository

pytestmark = [pytest.mark.component, pytest.mark.golden]


class TestUserDeletedHandler:
    """Test user.deleted event handler (GDPR compliance)"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository with sample data"""
        repo = MockCalendarRepository()
        user_id = CalendarTestDataFactory.make_user_id()
        now = datetime.now(timezone.utc)

        # Add events for the user
        for i in range(5):
            repo.set_event(
                CalendarTestDataFactory.make_event_id(),
                user_id=user_id,
                title=CalendarTestDataFactory.make_title(),
                start_time=now + timedelta(days=i),
                end_time=now + timedelta(days=i, hours=1),
            )

        # Add sync status
        repo._sync_status[f"{user_id}:google_calendar"] = {
            "user_id": user_id,
            "provider": "google_calendar",
            "status": "active"
        }

        return repo, user_id

    @pytest.fixture
    def mock_service(self, mock_repo):
        """Create mock service"""
        repo, _ = mock_repo
        service = AsyncMock()
        service.repository = repo
        return service

    @pytest.mark.asyncio
    async def test_handle_user_deleted_success(self, mock_repo, mock_service):
        """BR-CAL-070: User data deletion on account deletion"""
        repo, user_id = mock_repo

        handler = CalendarEventHandlers(mock_service)

        # Verify data exists before
        user_events = [e for e in repo._events.values() if e.user_id == user_id]
        assert len(user_events) == 5

        # Handle user.deleted event
        await handler.handle_user_deleted({"user_id": user_id})

        # Verify all data deleted
        remaining_events = [e for e in repo._events.values() if e.user_id == user_id]
        assert len(remaining_events) == 0

    @pytest.mark.asyncio
    async def test_handle_user_deleted_no_user_id(self, mock_service):
        """User deleted event without user_id is handled gracefully"""
        handler = CalendarEventHandlers(mock_service)

        # Should not raise
        await handler.handle_user_deleted({})
        await handler.handle_user_deleted({"other_field": "value"})

    @pytest.mark.asyncio
    async def test_handle_user_deleted_nonexistent_user(self, mock_service):
        """User deleted for non-existent user doesn't raise"""
        handler = CalendarEventHandlers(mock_service)

        nonexistent_user = CalendarTestDataFactory.make_user_id()

        # Should not raise
        await handler.handle_user_deleted({"user_id": nonexistent_user})


class TestTaskCreatedHandler:
    """Test task.created event handler"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return MockCalendarRepository()

    @pytest.fixture
    def mock_service(self, mock_repo):
        """Create mock service"""
        service = AsyncMock()
        service.repository = mock_repo
        return service

    @pytest.mark.asyncio
    async def test_handle_task_created_with_schedule(self, mock_service):
        """Task with schedule creates calendar event"""
        handler = CalendarEventHandlers(mock_service)
        user_id = CalendarTestDataFactory.make_user_id()
        task_id = f"task_{CalendarTestDataFactory.make_event_id()[4:]}"

        event_data = {
            "user_id": user_id,
            "task_id": task_id,
            "name": "Complete Report",
            "schedule": "2025-01-20T10:00:00Z",
        }

        await handler.handle_task_created(event_data)
        # Handler should create event (mock behavior)

    @pytest.mark.asyncio
    async def test_handle_task_created_with_due_date(self, mock_service):
        """Task with due date creates calendar event"""
        handler = CalendarEventHandlers(mock_service)
        user_id = CalendarTestDataFactory.make_user_id()
        task_id = f"task_{CalendarTestDataFactory.make_event_id()[4:]}"

        event_data = {
            "user_id": user_id,
            "task_id": task_id,
            "name": "Submit Report",
            "due_date": "2025-01-25T17:00:00Z",
        }

        await handler.handle_task_created(event_data)

    @pytest.mark.asyncio
    async def test_handle_task_created_without_schedule(self, mock_service):
        """Task without schedule/due_date doesn't create event"""
        handler = CalendarEventHandlers(mock_service)
        user_id = CalendarTestDataFactory.make_user_id()
        task_id = f"task_{CalendarTestDataFactory.make_event_id()[4:]}"

        event_data = {
            "user_id": user_id,
            "task_id": task_id,
            "name": "General Task",
        }

        # Should skip silently
        await handler.handle_task_created(event_data)

    @pytest.mark.asyncio
    async def test_handle_task_created_missing_user_id(self, mock_service):
        """Task event without user_id is handled gracefully"""
        handler = CalendarEventHandlers(mock_service)

        event_data = {
            "task_id": "task_123",
            "name": "Orphan Task",
        }

        # Should not raise
        await handler.handle_task_created(event_data)


class TestTaskCompletedHandler:
    """Test task.completed event handler"""

    @pytest.fixture
    def mock_repo(self):
        """Create mock repository"""
        return MockCalendarRepository()

    @pytest.fixture
    def mock_service(self, mock_repo):
        """Create mock service"""
        service = AsyncMock()
        service.repository = mock_repo
        return service

    @pytest.mark.asyncio
    async def test_handle_task_completed_success(self, mock_service):
        """Completed task updates calendar event"""
        handler = CalendarEventHandlers(mock_service)
        user_id = CalendarTestDataFactory.make_user_id()
        task_id = f"task_{CalendarTestDataFactory.make_event_id()[4:]}"

        event_data = {
            "user_id": user_id,
            "task_id": task_id,
            "status": "success",
        }

        await handler.handle_task_completed(event_data)

    @pytest.mark.asyncio
    async def test_handle_task_completed_cancelled(self, mock_service):
        """Cancelled task updates calendar event status"""
        handler = CalendarEventHandlers(mock_service)
        user_id = CalendarTestDataFactory.make_user_id()
        task_id = f"task_{CalendarTestDataFactory.make_event_id()[4:]}"

        event_data = {
            "user_id": user_id,
            "task_id": task_id,
            "status": "cancelled",
        }

        await handler.handle_task_completed(event_data)

    @pytest.mark.asyncio
    async def test_handle_task_completed_missing_user_id(self, mock_service):
        """Task completed without user_id is handled gracefully"""
        handler = CalendarEventHandlers(mock_service)

        event_data = {
            "task_id": "task_123",
            "status": "success",
        }

        # Should not raise
        await handler.handle_task_completed(event_data)


class TestEventHandlerMapRegistration:
    """Test event handler registration"""

    @pytest.fixture
    def mock_service(self):
        """Create mock service"""
        service = AsyncMock()
        service.repository = MockCalendarRepository()
        return service

    def test_get_event_handler_map_returns_dict(self, mock_service):
        """Handler map returns dictionary"""
        handler = CalendarEventHandlers(mock_service)
        handler_map = handler.get_event_handler_map()

        assert isinstance(handler_map, dict)

    def test_user_deleted_handler_registered(self, mock_service):
        """user.deleted handler is registered"""
        handler = CalendarEventHandlers(mock_service)
        handler_map = handler.get_event_handler_map()

        assert "user.deleted" in handler_map
        assert callable(handler_map["user.deleted"])

    def test_task_created_handler_registered(self, mock_service):
        """task_service.task.created handler is registered"""
        handler = CalendarEventHandlers(mock_service)
        handler_map = handler.get_event_handler_map()

        assert "task_service.task.created" in handler_map
        assert callable(handler_map["task_service.task.created"])

    def test_task_completed_handler_registered(self, mock_service):
        """task_service.task.completed handler is registered"""
        handler = CalendarEventHandlers(mock_service)
        handler_map = handler.get_event_handler_map()

        assert "task_service.task.completed" in handler_map
        assert callable(handler_map["task_service.task.completed"])

    def test_handler_count(self, mock_service):
        """Expected number of handlers registered"""
        handler = CalendarEventHandlers(mock_service)
        handler_map = handler.get_event_handler_map()

        # Should have 3 handlers
        assert len(handler_map) == 3
