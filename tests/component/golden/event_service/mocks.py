"""
Event Service - Mock Dependencies

Mock implementations for component testing.
Provides mocked repository, event bus, and other dependencies.
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
import uuid

from microservices.event_service.models import (
    Event, EventStream, EventSource, EventCategory, EventStatus,
    EventStatistics, EventProcessingResult, ProcessingStatus,
    EventProjection, EventProcessor, EventSubscription
)


class MockEventRepository:
    """Mock event repository for component testing

    Implements the EventRepository interface.
    Returns Event model objects, not dicts.
    """

    def __init__(self):
        self._events: Dict[str, Event] = {}
        self._projections: Dict[str, EventProjection] = {}
        self._processors: Dict[str, EventProcessor] = {}
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._processing_results: List[EventProcessingResult] = []
        self._error: Optional[Exception] = None
        self._call_log: List[Dict] = []
        self._stats: Optional[EventStatistics] = None

    def set_event(
        self,
        event_id: str,
        event_type: str,
        event_source: EventSource = EventSource.BACKEND,
        event_category: EventCategory = EventCategory.USER_ACTION,
        user_id: Optional[str] = None,
        data: Optional[Dict] = None,
        status: EventStatus = EventStatus.PENDING,
        timestamp: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict] = None,
        context: Optional[Dict] = None,
        processors: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ):
        """Add an event to the mock repository"""
        now = datetime.now(timezone.utc)
        event = Event(
            event_id=event_id,
            event_type=event_type,
            event_source=event_source,
            event_category=event_category,
            user_id=user_id,
            data=data or {},
            metadata=metadata or {},
            context=context or {},
            status=status,
            timestamp=timestamp or now,
            created_at=created_at or now,
            updated_at=now,
            processors=processors or [],
            error_message=error_message,
            retry_count=retry_count
        )
        self._events[event_id] = event
        return event

    def set_processor(
        self,
        processor_id: str,
        processor_name: str,
        processor_type: str = "default",
        enabled: bool = True,
        priority: int = 0,
        filters: Optional[Dict] = None
    ):
        """Add a processor to the mock repository"""
        processor = EventProcessor(
            processor_id=processor_id,
            processor_name=processor_name,
            processor_type=processor_type,
            enabled=enabled,
            priority=priority,
            filters=filters or {}
        )
        self._processors[processor_id] = processor
        return processor

    def set_subscription(
        self,
        subscription_id: str,
        subscriber_name: str,
        event_types: List[str],
        subscriber_type: str = "service",
        event_sources: Optional[List[EventSource]] = None,
        event_categories: Optional[List[EventCategory]] = None,
        callback_url: Optional[str] = None,
        enabled: bool = True
    ):
        """Add a subscription to the mock repository"""
        subscription = EventSubscription(
            subscription_id=subscription_id,
            subscriber_name=subscriber_name,
            subscriber_type=subscriber_type,
            event_types=event_types,
            event_sources=event_sources,
            event_categories=event_categories,
            callback_url=callback_url,
            enabled=enabled
        )
        self._subscriptions[subscription_id] = subscription
        return subscription

    def set_projection(
        self,
        projection_id: str,
        projection_name: str,
        entity_id: str,
        entity_type: str,
        state: Optional[Dict] = None,
        version: int = 0
    ):
        """Add a projection to the mock repository"""
        projection = EventProjection(
            projection_id=projection_id,
            projection_name=projection_name,
            entity_id=entity_id,
            entity_type=entity_type,
            state=state or {},
            version=version
        )
        self._projections[projection_id] = projection
        return projection

    def set_stats(
        self,
        total_events: int = 0,
        pending_events: int = 0,
        processed_events: int = 0,
        failed_events: int = 0,
        events_today: int = 0,
        events_this_week: int = 0,
        events_this_month: int = 0
    ):
        """Set statistics for the mock repository"""
        self._stats = EventStatistics(
            total_events=total_events,
            pending_events=pending_events,
            processed_events=processed_events,
            failed_events=failed_events,
            events_today=events_today,
            events_this_week=events_this_week,
            events_this_month=events_this_month,
            events_by_type={},
            events_by_source={},
            events_by_category={}
        )

    def set_error(self, error: Exception):
        """Set an error to be raised on operations"""
        self._error = error

    def clear_error(self):
        """Clear any set error"""
        self._error = None

    def _log_call(self, method: str, **kwargs):
        """Log method calls for assertions"""
        self._call_log.append({"method": method, "kwargs": kwargs})

    def assert_called(self, method: str):
        """Assert that a method was called"""
        called_methods = [c["method"] for c in self._call_log]
        assert method in called_methods, f"Expected {method} to be called, but got {called_methods}"

    def assert_called_with(self, method: str, **kwargs):
        """Assert that a method was called with specific kwargs"""
        for call in self._call_log:
            if call["method"] == method:
                for key, value in kwargs.items():
                    assert key in call["kwargs"], f"Expected kwarg {key} not found"
                    assert call["kwargs"][key] == value, f"Expected {key}={value}, got {call['kwargs'][key]}"
                return
        raise AssertionError(f"Expected {method} to be called with {kwargs}")

    def get_call_count(self, method: str) -> int:
        """Get the number of times a method was called"""
        return sum(1 for c in self._call_log if c["method"] == method)

    async def initialize(self):
        """Initialize repository"""
        self._log_call("initialize")
        if self._error:
            raise self._error

    async def close(self):
        """Close repository"""
        self._log_call("close")

    async def save_event(self, event: Event) -> Event:
        """Save event"""
        self._log_call("save_event", event_id=event.event_id, event_type=event.event_type)
        if self._error:
            raise self._error
        self._events[event.event_id] = event
        return event

    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get single event by ID"""
        self._log_call("get_event", event_id=event_id)
        if self._error:
            raise self._error
        return self._events.get(event_id)

    async def query_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        event_source: Optional[EventSource] = None,
        event_category: Optional[EventCategory] = None,
        status: Optional[EventStatus] = None,
        correlation_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Event], int]:
        """Query events with filters"""
        self._log_call(
            "query_events",
            user_id=user_id,
            event_type=event_type,
            event_source=event_source,
            event_category=event_category,
            status=status,
            limit=limit,
            offset=offset
        )
        if self._error:
            raise self._error

        results = []
        for event in self._events.values():
            if user_id and event.user_id != user_id:
                continue
            if event_type and event.event_type != event_type:
                continue
            if event_source and event.event_source != event_source:
                continue
            if event_category and event.event_category != event_category:
                continue
            if status and event.status != status:
                continue
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            results.append(event)

        total = len(results)
        results = results[offset:offset + limit]
        return results, total

    async def update_event(self, event: Event) -> bool:
        """Update event"""
        self._log_call("update_event", event_id=event.event_id)
        if self._error:
            raise self._error
        if event.event_id not in self._events:
            return False
        self._events[event.event_id] = event
        return True

    async def update_event_status(
        self,
        event_id: str,
        status: EventStatus,
        error_message: Optional[str] = None,
        processed_at: Optional[datetime] = None
    ) -> bool:
        """Update event status"""
        self._log_call("update_event_status", event_id=event_id, status=status)
        if self._error:
            raise self._error
        if event_id not in self._events:
            return False
        event = self._events[event_id]
        event.status = status
        event.error_message = error_message
        event.processed_at = processed_at
        return True

    async def get_unprocessed_events(self, limit: int = 100) -> List[Event]:
        """Get unprocessed events"""
        self._log_call("get_unprocessed_events", limit=limit)
        if self._error:
            raise self._error
        results = [e for e in self._events.values() if e.status == EventStatus.PENDING]
        return results[:limit]

    async def get_failed_events(self, max_retries: int = 3) -> List[Event]:
        """Get failed events for retry"""
        self._log_call("get_failed_events", max_retries=max_retries)
        if self._error:
            raise self._error
        results = [
            e for e in self._events.values()
            if e.status == EventStatus.FAILED and e.retry_count < max_retries
        ]
        return results

    async def get_user_events(self, user_id: str, limit: int = 100) -> List[Event]:
        """Get events for a user"""
        self._log_call("get_user_events", user_id=user_id, limit=limit)
        if self._error:
            raise self._error
        results = [e for e in self._events.values() if e.user_id == user_id]
        return results[:limit]

    async def get_statistics(self, user_id: Optional[str] = None) -> EventStatistics:
        """Get event statistics"""
        self._log_call("get_statistics", user_id=user_id)
        if self._error:
            raise self._error
        if self._stats:
            return self._stats

        # Calculate from data
        total = len(self._events)
        pending = sum(1 for e in self._events.values() if e.status == EventStatus.PENDING)
        processed = sum(1 for e in self._events.values() if e.status == EventStatus.PROCESSED)
        failed = sum(1 for e in self._events.values() if e.status == EventStatus.FAILED)

        return EventStatistics(
            total_events=total,
            pending_events=pending,
            processed_events=processed,
            failed_events=failed,
            events_today=0,
            events_this_week=0,
            events_this_month=0,
            events_by_type={},
            events_by_source={},
            events_by_category={}
        )

    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        self._log_call("get_user_statistics", user_id=user_id)
        if self._error:
            raise self._error
        user_events = [e for e in self._events.values() if e.user_id == user_id]
        return {
            "total_events": len(user_events),
            "pending_events": sum(1 for e in user_events if e.status == EventStatus.PENDING),
            "processed_events": sum(1 for e in user_events if e.status == EventStatus.PROCESSED)
        }

    async def get_event_stream(
        self,
        stream_id: str,
        from_version: Optional[int] = None
    ) -> List[Event]:
        """Get event stream - returns list of events"""
        self._log_call("get_event_stream", stream_id=stream_id, from_version=from_version)
        if self._error:
            raise self._error
        # Return list of events (service converts to EventStream)
        return list(self._events.values())[:10]

    async def get_events_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Event]:
        """Get events in time range"""
        self._log_call("get_events_by_time_range", start_time=start_time, end_time=end_time)
        if self._error:
            raise self._error
        return [
            e for e in self._events.values()
            if start_time <= e.timestamp <= end_time
        ]

    async def save_processing_result(self, result: EventProcessingResult):
        """Save processing result"""
        self._log_call("save_processing_result", event_id=result.event_id)
        if self._error:
            raise self._error
        self._processing_results.append(result)

    async def save_projection(self, projection: EventProjection):
        """Save event projection"""
        self._log_call("save_projection", projection_id=projection.projection_id)
        if self._error:
            raise self._error
        self._projections[projection.projection_id] = projection

    async def get_projection(
        self,
        entity_type_or_id: str,
        entity_id: Optional[str] = None,
        projection_name: str = "default"
    ) -> Optional[EventProjection]:
        """Get event projection

        Supports both:
        - get_projection(projection_id) - for service fallback calls
        - get_projection(entity_type, entity_id) - for repository interface
        """
        if entity_id is None:
            # Called with single argument (projection_id) - service fallback
            projection_id = entity_type_or_id
            self._log_call("get_projection", projection_id=projection_id)
            if self._error:
                raise self._error
            return self._projections.get(projection_id)
        else:
            # Called with entity_type and entity_id - repository interface
            entity_type = entity_type_or_id
            self._log_call("get_projection", entity_type=entity_type, entity_id=entity_id)
            if self._error:
                raise self._error
            for p in self._projections.values():
                if p.entity_type == entity_type and p.entity_id == entity_id:
                    return p
            return None

    async def update_projection(self, projection: EventProjection):
        """Update projection"""
        self._log_call("update_projection", projection_id=projection.projection_id)
        if self._error:
            raise self._error
        self._projections[projection.projection_id] = projection

    async def save_processor(self, processor: EventProcessor):
        """Save event processor"""
        self._log_call("save_processor", processor_id=processor.processor_id)
        if self._error:
            raise self._error
        self._processors[processor.processor_id] = processor

    async def get_processors(self) -> List[EventProcessor]:
        """Get all event processors"""
        self._log_call("get_processors")
        if self._error:
            raise self._error
        return [p for p in self._processors.values() if p.enabled]

    async def save_subscription(self, subscription: EventSubscription):
        """Save event subscription"""
        self._log_call("save_subscription", subscription_id=subscription.subscription_id)
        if self._error:
            raise self._error
        self._subscriptions[subscription.subscription_id] = subscription
        return subscription

    async def get_subscriptions(self) -> List[EventSubscription]:
        """Get all event subscriptions"""
        self._log_call("get_subscriptions")
        if self._error:
            raise self._error
        return [s for s in self._subscriptions.values() if s.enabled]

    async def delete_subscription(self, subscription_id: str) -> bool:
        """Delete subscription"""
        self._log_call("delete_subscription", subscription_id=subscription_id)
        if self._error:
            raise self._error
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return True
        return False


class MockEventBus:
    """Mock NATS event bus for testing"""

    def __init__(self):
        self.published_events: List[Any] = []
        self._call_log: List[Dict] = []
        self._error: Optional[Exception] = None

    def set_error(self, error: Exception):
        """Set an error to be raised on publish"""
        self._error = error

    def clear_error(self):
        """Clear any set error"""
        self._error = None

    async def publish(self, event: Any):
        """Publish event"""
        self._call_log.append({"method": "publish", "event": event})
        if self._error:
            raise self._error
        self.published_events.append(event)

    async def publish_event(self, event: Any):
        """Publish event (alias)"""
        await self.publish(event)

    async def close(self):
        """Close the event bus"""
        self._call_log.append({"method": "close"})

    def assert_published(self, event_type: str = None):
        """Assert that an event was published"""
        assert len(self.published_events) > 0, "No events were published"
        if event_type:
            event_types = [getattr(e, "event_type", str(e)) for e in self.published_events]
            assert event_type in str(event_types), f"Expected {event_type} event, got {event_types}"

    def assert_not_published(self):
        """Assert that no events were published"""
        assert len(self.published_events) == 0, f"Expected no events, but {len(self.published_events)} were published"

    def get_published_events(self) -> List[Any]:
        """Get all published events"""
        return self.published_events

    def get_published_event_types(self) -> List[str]:
        """Get all published event types"""
        return [getattr(e, "event_type", str(e)) for e in self.published_events]

    def clear(self):
        """Clear all published events"""
        self.published_events.clear()
        self._call_log.clear()


class MockConfigManager:
    """Mock config manager for testing"""

    def __init__(self, service_name: str = "event_service"):
        self.service_name = service_name
        self.service_host = "0.0.0.0"
        self.service_port = 8000
        self.consul_enabled = False
        self.consul_host = "localhost"
        self.consul_port = 8500
        self.debug = True
        self._config: Dict[str, Any] = {
            "batch_size": 100,
            "processing_interval": 5,
            "RUDDERSTACK_WEBHOOK_SECRET": None
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value"""
        return self._config.get(key, default)

    def get_service_config(self):
        """Get service config"""
        return self

    def discover_service(
        self,
        service_name: str,
        default_host: str,
        default_port: int,
        env_host_key: str = None,
        env_port_key: str = None
    ) -> Tuple[str, int]:
        """Discover service (mock)"""
        return default_host, default_port
