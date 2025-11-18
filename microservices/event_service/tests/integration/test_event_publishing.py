"""
Event Service Event Publishing Tests

Tests that Event Service correctly publishes events for event management operations
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.event_service.event_service import EventService
from microservices.event_service.models import (
    EventCreateRequest, EventSource, EventCategory, EventStatus,
    EventProcessingResult, ProcessingStatus, EventSubscription,
    EventProjection, EventReplayRequest
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


class MockEvent:
    """Mock Event for testing"""
    def __init__(self, event_id=None, event_type="test.event", event_source=EventSource.BACKEND,
                 event_category=EventCategory.SYSTEM, user_id=None):
        self.event_id = event_id or str(uuid.uuid4())
        self.event_type = event_type
        self.event_source = event_source
        self.event_category = event_category
        self.user_id = user_id
        self.status = EventStatus.PENDING
        self.timestamp = datetime.utcnow()
        self.created_at = datetime.utcnow()
        self.processed_at = None
        self.processors = []
        self.error_message = None
        self.retry_count = 0
        self.data = {}
        self.metadata = {}
        self.context = {}


class MockEventRepository:
    """Mock event repository for testing"""

    def __init__(self):
        self.events = {}
        self.subscriptions = {}
        self.projections = {}
        self.processing_results = []

    async def initialize(self):
        """Initialize mock repository"""
        pass

    async def save_event(self, event):
        """Save event"""
        if not hasattr(event, 'event_id') or not event.event_id:
            event.event_id = str(uuid.uuid4())
        if not hasattr(event, 'created_at'):
            event.created_at = datetime.utcnow()
        self.events[event.event_id] = event
        return event

    async def get_event(self, event_id: str):
        """Get event"""
        return self.events.get(event_id)

    async def update_event(self, event):
        """Update event"""
        self.events[event.event_id] = event
        return event

    async def save_processing_result(self, result):
        """Save processing result"""
        self.processing_results.append(result)

    async def save_subscription(self, subscription):
        """Save subscription"""
        if not hasattr(subscription, 'subscription_id') or not subscription.subscription_id:
            subscription.subscription_id = str(uuid.uuid4())
        self.subscriptions[subscription.subscription_id] = subscription
        return subscription

    async def save_projection(self, projection):
        """Save projection"""
        self.projections[projection.projection_id] = projection
        return projection

    async def get_event_stream(self, stream_id, from_version=None):
        """Get event stream"""
        return []

    async def get_events_by_time_range(self, start_time, end_time):
        """Get events by time range"""
        return []

    async def get_subscriptions(self):
        """Get all subscriptions"""
        return list(self.subscriptions.values())

    async def get_processors(self):
        """Get all processors"""
        return []

    async def close(self):
        """Close repository"""
        pass


async def test_event_stored_event():
    """Test that event.stored event is published"""
    print("\n📝 Testing event.stored event...")

    mock_event_bus = MockEventBus()
    service = EventService(event_bus=mock_event_bus)

    # Replace repository with mock
    service.repository = MockEventRepository()
    await service.repository.initialize()

    request = EventCreateRequest(
        event_type="user.clicked",
        event_source=EventSource.FRONTEND,
        event_category=EventCategory.USER_ACTION,
        user_id="user123",
        data={"button": "submit"},
        metadata={"page": "login"}
    )

    result = await service.create_event(request)

    # Check event was created
    assert result.event_id is not None, "Event should be created"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.EVENT_STORED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.EVENT_SERVICE.value, "Event source should be event_service"
    assert event.data["event_type"] == "user.clicked", "Event should contain event_type"
    assert event.data["event_source"] == "frontend", "Event should contain event_source"
    assert event.data["user_id"] == "user123", "Event should contain user_id"

    print("✅ TEST PASSED: event.stored event published correctly")
    return True


async def test_event_processed_success_event():
    """Test that event.processed.success event is published"""
    print("\n📝 Testing event.processed.success event...")

    mock_event_bus = MockEventBus()
    service = EventService(event_bus=mock_event_bus)

    # Replace repository with mock
    service.repository = MockEventRepository()
    await service.repository.initialize()

    # Create a mock event
    mock_event = MockEvent(event_id="evt123", event_type="test.event", user_id="user123")
    service.repository.events[mock_event.event_id] = mock_event

    # Clear any previous events
    mock_event_bus.clear()

    # Process event successfully
    result = EventProcessingResult(
        event_id=mock_event.event_id,
        processor_name="test_processor",
        status=ProcessingStatus.SUCCESS,
        message="Processed successfully",
        duration_ms=100,
        processed_at=datetime.utcnow()
    )

    success = await service.mark_event_processed(mock_event.event_id, "test_processor", result)

    # Check processing succeeded
    assert success is True, "Event processing should succeed"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.EVENT_PROCESSED_SUCCESS.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.EVENT_SERVICE.value, "Event source should be event_service"
    assert event.data["event_id"] == "evt123", "Event should contain event_id"
    assert event.data["processor_name"] == "test_processor", "Event should contain processor_name"
    assert event.data["duration_ms"] == 100, "Event should contain duration_ms"

    print("✅ TEST PASSED: event.processed.success event published correctly")
    return True


async def test_event_processed_failed_event():
    """Test that event.processed.failed event is published"""
    print("\n📝 Testing event.processed.failed event...")

    mock_event_bus = MockEventBus()
    service = EventService(event_bus=mock_event_bus)

    # Replace repository with mock
    service.repository = MockEventRepository()
    await service.repository.initialize()

    # Create a mock event
    mock_event = MockEvent(event_id="evt456", event_type="test.event", user_id="user123")
    service.repository.events[mock_event.event_id] = mock_event

    # Clear any previous events
    mock_event_bus.clear()

    # Process event with failure
    result = EventProcessingResult(
        event_id=mock_event.event_id,
        processor_name="test_processor",
        status=ProcessingStatus.FAILED,
        message="Processing failed: timeout",
        duration_ms=5000,
        processed_at=datetime.utcnow()
    )

    success = await service.mark_event_processed(mock_event.event_id, "test_processor", result)

    # Check processing completed (even though it failed)
    assert success is True, "Event processing mark should succeed"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.EVENT_PROCESSED_FAILED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.EVENT_SERVICE.value, "Event source should be event_service"
    assert event.data["event_id"] == "evt456", "Event should contain event_id"
    assert event.data["processor_name"] == "test_processor", "Event should contain processor_name"
    assert "timeout" in event.data["error_message"], "Event should contain error_message"

    print("✅ TEST PASSED: event.processed.failed event published correctly")
    return True


async def test_subscription_created_event():
    """Test that event.subscription.created event is published"""
    print("\n📝 Testing event.subscription.created event...")

    mock_event_bus = MockEventBus()
    service = EventService(event_bus=mock_event_bus)

    # Replace repository with mock
    service.repository = MockEventRepository()
    await service.repository.initialize()

    subscription = EventSubscription(
        subscriber_name="test_subscriber",
        event_types=["user.created", "user.updated"],
        event_sources=[EventSource.BACKEND],
        event_categories=[EventCategory.USER_LIFECYCLE],
        enabled=True,
        callback_url="https://example.com/webhook"
    )

    result = await service.create_subscription(subscription)

    # Check subscription was created
    assert result.subscription_id is not None, "Subscription should be created"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.EVENT_SUBSCRIPTION_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.EVENT_SERVICE.value, "Event source should be event_service"
    assert event.data["subscriber_name"] == "test_subscriber", "Event should contain subscriber_name"
    assert "user.created" in event.data["event_types"], "Event should contain event_types"
    assert event.data["enabled"] is True, "Event should contain enabled flag"

    print("✅ TEST PASSED: event.subscription.created event published correctly")
    return True


async def test_projection_created_event():
    """Test that event.projection.created event is published"""
    print("\n📝 Testing event.projection.created event...")

    mock_event_bus = MockEventBus()
    service = EventService(event_bus=mock_event_bus)

    # Replace repository with mock
    service.repository = MockEventRepository()
    await service.repository.initialize()

    result = await service.create_projection(
        projection_name="user_state",
        entity_id="user123",
        entity_type="user"
    )

    # Check projection was created
    assert result.projection_id is not None, "Projection should be created"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.EVENT_PROJECTION_CREATED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.EVENT_SERVICE.value, "Event source should be event_service"
    assert event.data["projection_name"] == "user_state", "Event should contain projection_name"
    assert event.data["entity_id"] == "user123", "Event should contain entity_id"
    assert event.data["entity_type"] == "user", "Event should contain entity_type"

    print("✅ TEST PASSED: event.projection.created event published correctly")
    return True


async def test_replay_started_event():
    """Test that event.replay.started event is published"""
    print("\n📝 Testing event.replay.started event...")

    mock_event_bus = MockEventBus()
    service = EventService(event_bus=mock_event_bus)

    # Replace repository with mock
    service.repository = MockEventRepository()
    await service.repository.initialize()

    request = EventReplayRequest(
        stream_id="user:user123",
        target_service="notification_service",
        dry_run=False
    )

    result = await service.replay_events(request)

    # Check replay was initiated
    assert "replayed" in result, "Replay should return results"

    # Check event was published
    events = mock_event_bus.get_events_by_type(EventType.EVENT_REPLAY_STARTED.value)
    assert len(events) == 1, f"Should publish 1 event, got {len(events)}"

    event = events[0]
    assert event.source == ServiceSource.EVENT_SERVICE.value, "Event source should be event_service"
    assert event.data["stream_id"] == "user:user123", "Event should contain stream_id"
    assert event.data["target_service"] == "notification_service", "Event should contain target_service"

    print("✅ TEST PASSED: event.replay.started event published correctly")
    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("EVENT SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)

    tests = [
        ("Event Stored Event", test_event_stored_event),
        ("Event Processed Success Event", test_event_processed_success_event),
        ("Event Processed Failed Event", test_event_processed_failed_event),
        ("Subscription Created Event", test_subscription_created_event),
        ("Projection Created Event", test_projection_created_event),
        ("Replay Started Event", test_replay_started_event),
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
