"""
NATS Event Bus Mock for Component Testing

Mocks the event bus for testing event publishing and subscription.
"""
import asyncio
import fnmatch
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


class MockEventBus:
    """Mock for NATS event bus"""

    def __init__(self):
        self.published_events: List[Dict[str, Any]] = []
        self.subscriptions: Dict[str, Callable] = {}
        self._should_raise: Optional[Exception] = None

    async def publish_event(self, event: Any):
        """Mock event publishing"""
        if self._should_raise:
            raise self._should_raise

        event_data = {
            "id": getattr(event, 'id', 'mock_event_id'),
            "type": getattr(event, 'type', str(getattr(event, 'event_type', 'unknown'))),
            "source": str(getattr(event, 'source', 'unknown')),
            "data": getattr(event, 'data', {}),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.published_events.append(event_data)

    async def publish(self, subject: str, data: Dict[str, Any]):
        """Alternative publish method"""
        if self._should_raise:
            raise self._should_raise

        self.published_events.append({
            "subject": subject,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def subscribe(self, pattern: str, handler: Callable):
        """Mock subscription"""
        self.subscriptions[pattern] = handler

    async def subscribe_to_events(self, pattern: str, handler: Callable):
        """Mock event subscription"""
        self.subscriptions[pattern] = handler

    async def close(self):
        """Mock close"""
        pass

    # Test helper methods

    def get_published(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get published events, optionally filtered by type"""
        if event_type:
            return [e for e in self.published_events if e.get("type") == event_type]
        return self.published_events

    def get_published_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Alias for get_published for backward compatibility"""
        return self.get_published(event_type)

    def get_published_by_subject(self, subject: str) -> List[Dict[str, Any]]:
        """Get published events by subject"""
        return [e for e in self.published_events if e.get("subject") == subject]

    def get_last_event(self) -> Optional[Dict[str, Any]]:
        """Get the last published event"""
        return self.published_events[-1] if self.published_events else None

    def clear(self):
        """Clear published events and subscriptions"""
        self.published_events.clear()
        self.subscriptions.clear()

    def set_error(self, error: Exception):
        """Set an error to be raised on publish"""
        self._should_raise = error

    def clear_error(self):
        """Clear any pending error"""
        self._should_raise = None

    def assert_event_published(self, event_type: str, data_match: Optional[Dict] = None):
        """Assert that an event was published"""
        events = self.get_published(event_type)
        assert len(events) > 0, f"No events of type '{event_type}' were published. Published: {self.published_events}"

        if data_match:
            for event in events:
                if all(event.get("data", {}).get(k) == v for k, v in data_match.items()):
                    return event
            raise AssertionError(
                f"No event of type '{event_type}' matched data {data_match}. Events: {events}"
            )
        return events[0]

    def assert_no_events_published(self, event_type: Optional[str] = None):
        """Assert that no events were published"""
        if event_type:
            events = self.get_published(event_type)
            assert len(events) == 0, f"Expected no events of type '{event_type}', but got: {events}"
        else:
            assert len(self.published_events) == 0, f"Expected no events, but got: {self.published_events}"

    async def simulate_event(self, subject: str, data: Dict[str, Any]):
        """Simulate receiving an event for handler testing"""
        for pattern, handler in self.subscriptions.items():
            if self._matches_pattern(pattern, subject):
                # Create a mock event object
                class MockEvent:
                    def __init__(self, data):
                        self.data = data
                        self.type = subject
                        self.source = "test"
                        self.id = "mock_id"
                        self.timestamp = datetime.utcnow().isoformat()

                await handler(MockEvent(data))

    def _matches_pattern(self, pattern: str, subject: str) -> bool:
        """Check if subject matches pattern (NATS-style wildcards)"""
        # Convert NATS patterns to fnmatch patterns
        fnmatch_pattern = pattern.replace(".", "/").replace(">", "**").replace("*", "*")
        fnmatch_subject = subject.replace(".", "/")
        return fnmatch.fnmatch(fnmatch_subject, fnmatch_pattern)
