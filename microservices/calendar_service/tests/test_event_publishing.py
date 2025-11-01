"""
Calendar Service Event Publishing Tests

Tests that Calendar Service correctly publishes events for calendar operations
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.calendar_service.calendar_service import CalendarService
from microservices.calendar_service.models import (
    EventCreateRequest, EventUpdateRequest, EventCategory
)


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event: Event):
        """Mock publish event"""
        self.published_events.append(event)

    def get_events_by_type(self, event_type: str):
        """Get events by type"""
        return [e for e in self.published_events if e.type == event_type]

    def clear(self):
        """Clear published events"""
        self.published_events = []


class MockCalendarRepository:
    """Mock calendar repository for testing"""

    def __init__(self):
        self.events = {}

    async def create_event(self, event_data):
        """Create event"""
        class MockEvent:
            def __init__(self, data):
                self.event_id = str(uuid.uuid4())
                self.user_id = data.get("user_id")
                self.title = data.get("title")
                self.start_time = data.get("start_time")
                self.end_time = data.get("end_time")

        event = MockEvent(event_data)
        self.events[event.event_id] = event
        return event

    async def get_event_by_id(self, event_id, user_id=None):
        """Get event by ID"""
        return self.events.get(event_id)

    async def update_event(self, event_id, updates):
        """Update event"""
        event = self.events.get(event_id)
        if event:
            for key, value in updates.items():
                setattr(event, key, value)
        return event

    async def delete_event(self, event_id, user_id=None):
        """Delete event"""
        if event_id in self.events:
            del self.events[event_id]
            return True
        return False


async def test_calendar_event_created_event():
    """Test that calendar.event.created event is published"""
    print("\n📝 Testing calendar.event.created event...")

    mock_event_bus = MockEventBus()
    service = CalendarService(event_bus=mock_event_bus)

    # Replace repository with mock
    service.repository = MockCalendarRepository()

    request = EventCreateRequest(
        user_id="user123",
        title="Team Meeting",
        description="Weekly team sync",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        location="Conference Room A",
        category=EventCategory.WORK
    )

    result = await service.create_event(request)

    # Check event was created
    assert result is not None, "Calendar event should be created"
    assert result.event_id is not None, "Event ID should be set"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.CALENDAR_EVENT_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.CALENDAR_SERVICE.value, "Event source should be calendar_service"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert event.data["title"] == "Team Meeting", "Event should contain title"

    print("✅ TEST PASSED: calendar.event.created event published correctly")
    return True


async def test_calendar_event_updated_event():
    """Test that calendar.event.updated event is published"""
    print("\n📝 Testing calendar.event.updated event...")

    mock_event_bus = MockEventBus()
    service = CalendarService(event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockCalendarRepository()
    service.repository = mock_repo

    # Create an event first
    request = EventCreateRequest(
        user_id="user123",
        title="Original Title",
        description="Original description",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        category=EventCategory.PERSONAL
    )
    created = await service.create_event(request)

    # Clear previous events
    mock_event_bus.clear()

    # Update the event
    update_request = EventUpdateRequest(
        title="Updated Title",
        description="Updated description"
    )
    result = await service.update_event(created.event_id, update_request, user_id="user123")

    # Check update was successful
    assert result is not None, "Event update should succeed"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.CALENDAR_EVENT_UPDATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.CALENDAR_SERVICE.value, "Event source should be calendar_service"
    assert event.data["event_id"] == created.event_id, "Event should contain event_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"
    assert "title" in event.data["updated_fields"], "Event should contain updated_fields"

    print("✅ TEST PASSED: calendar.event.updated event published correctly")
    return True


async def test_calendar_event_deleted_event():
    """Test that calendar.event.deleted event is published"""
    print("\n📝 Testing calendar.event.deleted event...")

    mock_event_bus = MockEventBus()
    service = CalendarService(event_bus=mock_event_bus)

    # Replace repository with mock
    mock_repo = MockCalendarRepository()
    service.repository = mock_repo

    # Create an event first
    request = EventCreateRequest(
        user_id="user123",
        title="Event to Delete",
        description="This will be deleted",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        category=EventCategory.WORK
    )
    created = await service.create_event(request)

    # Clear previous events
    mock_event_bus.clear()

    # Delete the event
    result = await service.delete_event(created.event_id, user_id="user123")

    # Check deletion was successful
    assert result is True, "Event deletion should succeed"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.CALENDAR_EVENT_DELETED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.CALENDAR_SERVICE.value, "Event source should be calendar_service"
    assert event.data["event_id"] == created.event_id, "Event should contain event_id"
    assert event.data["user_id"] == "user123", "Event should contain user_id"

    print("✅ TEST PASSED: calendar.event.deleted event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("CALENDAR SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Calendar Event Created", test_calendar_event_created_event),
        ("Calendar Event Updated", test_calendar_event_updated_event),
        ("Calendar Event Deleted", test_calendar_event_deleted_event),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
