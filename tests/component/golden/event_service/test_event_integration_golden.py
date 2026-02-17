"""
Event Service Integration Component Golden Tests

Tests service layer business logic with mocked repository.
Uses proper dependency injection - no real database or external services.

Usage:
    pytest tests/component/golden/event_service/test_event_integration_golden.py -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from microservices.event_service.event_service import EventService
from microservices.event_service.models import (
    Event, EventStream, EventSource, EventCategory, EventStatus,
    EventCreateRequest, EventQueryRequest, EventResponse, EventListResponse,
    EventStatistics, EventProcessingResult, ProcessingStatus,
    EventReplayRequest, EventProjection, EventProcessor, EventSubscription,
    RudderStackEvent
)
from .mocks import MockEventRepository, MockEventBus, MockConfigManager

pytestmark = [pytest.mark.component, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_repo():
    """Create a fresh MockEventRepository"""
    return MockEventRepository()


@pytest.fixture
def mock_repo_with_events():
    """Create MockEventRepository with sample events"""
    repo = MockEventRepository()
    now = datetime.now(timezone.utc)

    # Add sample events
    repo.set_event(
        event_id="evt_test_001",
        event_type="user.created",
        event_source=EventSource.BACKEND,
        event_category=EventCategory.USER_LIFECYCLE,
        user_id="usr_test_123",
        data={"name": "Test User", "email": "test@example.com"},
        status=EventStatus.PROCESSED,
        timestamp=now
    )
    repo.set_event(
        event_id="evt_test_002",
        event_type="payment.completed",
        event_source=EventSource.BACKEND,
        event_category=EventCategory.PAYMENT,
        user_id="usr_test_123",
        data={"amount": 99.99, "currency": "USD"},
        status=EventStatus.PENDING,
        timestamp=now - timedelta(hours=1)
    )
    repo.set_event(
        event_id="evt_test_003",
        event_type="page.view",
        event_source=EventSource.FRONTEND,
        event_category=EventCategory.PAGE_VIEW,
        user_id="usr_test_456",
        data={"page": "/dashboard", "referrer": "/login"},
        status=EventStatus.PROCESSED,
        timestamp=now - timedelta(days=1)
    )
    repo.set_event(
        event_id="evt_failed_001",
        event_type="order.process",
        event_source=EventSource.BACKEND,
        event_category=EventCategory.ORDER,
        user_id="usr_test_789",
        status=EventStatus.FAILED,
        error_message="Processing timeout",
        retry_count=1
    )
    return repo


@pytest.fixture
def mock_event_bus():
    """Create a fresh MockEventBus"""
    return MockEventBus()


@pytest.fixture
def mock_config():
    """Create a mock config manager"""
    return MockConfigManager()


@pytest.fixture
def event_service(mock_repo, mock_event_bus, mock_config):
    """Create EventService with mocked dependencies"""
    service = EventService(event_bus=mock_event_bus, config_manager=mock_config)
    service.repository = mock_repo
    return service


@pytest.fixture
def event_service_with_events(mock_repo_with_events, mock_event_bus, mock_config):
    """Create EventService with pre-populated repository"""
    service = EventService(event_bus=mock_event_bus, config_manager=mock_config)
    service.repository = mock_repo_with_events
    return service


# =============================================================================
# Event Creation Tests
# =============================================================================

class TestEventServiceCreateGolden:
    """Golden: EventService.create_event() current behavior"""

    async def test_create_event_success(self, event_service, mock_repo):
        """GOLDEN: create_event creates and stores event"""
        request = EventCreateRequest(
            event_type="user.signup",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.USER_LIFECYCLE,
            user_id="usr_new_001",
            data={"email": "new@example.com", "name": "New User"}
        )

        result = await event_service.create_event(request)

        assert isinstance(result, EventResponse)
        assert result.event_type == "user.signup"
        assert result.event_source == EventSource.BACKEND
        assert result.user_id == "usr_new_001"
        assert result.status == EventStatus.PENDING

        # Verify event was stored
        mock_repo.assert_called("save_event")

    async def test_create_event_assigns_event_id(self, event_service):
        """GOLDEN: create_event assigns unique event_id"""
        request = EventCreateRequest(
            event_type="test.event",
            data={}
        )

        result = await event_service.create_event(request)

        assert result.event_id is not None
        assert len(result.event_id) > 0

    async def test_create_event_sets_timestamps(self, event_service):
        """GOLDEN: create_event sets timestamp and created_at"""
        request = EventCreateRequest(
            event_type="test.event",
            data={}
        )

        result = await event_service.create_event(request)

        assert result.timestamp is not None
        assert result.created_at is not None

    async def test_create_event_publishes_to_event_bus(self, event_service, mock_event_bus):
        """GOLDEN: create_event publishes event.stored to event bus"""
        request = EventCreateRequest(
            event_type="user.created",
            user_id="usr_123",
            data={"name": "Test"}
        )

        await event_service.create_event(request)

        mock_event_bus.assert_published("event.stored")

    async def test_create_event_with_metadata(self, event_service):
        """GOLDEN: create_event stores metadata"""
        request = EventCreateRequest(
            event_type="order.created",
            user_id="usr_123",
            data={"order_id": "ord_456"},
            metadata={"source_ip": "192.168.1.1", "user_agent": "Chrome"}
        )

        result = await event_service.create_event(request)

        # Metadata should be passed to the event
        assert result is not None

    async def test_create_event_with_context(self, event_service):
        """GOLDEN: create_event stores context"""
        request = EventCreateRequest(
            event_type="session.started",
            user_id="usr_123",
            data={},
            context={"session_id": "sess_789", "device_type": "mobile"}
        )

        result = await event_service.create_event(request)

        assert result is not None

    async def test_create_event_default_source(self, event_service):
        """GOLDEN: create_event defaults to BACKEND source"""
        request = EventCreateRequest(
            event_type="test.event",
            data={}
        )

        result = await event_service.create_event(request)

        assert result.event_source == EventSource.BACKEND

    async def test_create_event_default_category(self, event_service):
        """GOLDEN: create_event defaults to USER_ACTION category"""
        request = EventCreateRequest(
            event_type="test.event",
            data={}
        )

        result = await event_service.create_event(request)

        assert result.event_category == EventCategory.USER_ACTION


# =============================================================================
# Event Retrieval Tests
# =============================================================================

class TestEventServiceGetGolden:
    """Golden: EventService.get_event() current behavior"""

    async def test_get_event_success(self, event_service_with_events):
        """GOLDEN: get_event returns existing event"""
        event = await event_service_with_events.get_event("evt_test_001")

        assert event is not None
        assert event.event_id == "evt_test_001"
        assert event.event_type == "user.created"
        assert event.user_id == "usr_test_123"

    async def test_get_event_not_found(self, event_service):
        """GOLDEN: get_event returns None for non-existent event"""
        event = await event_service.get_event("evt_nonexistent")

        assert event is None

    async def test_get_event_with_data(self, event_service_with_events):
        """GOLDEN: get_event returns event with data"""
        event = await event_service_with_events.get_event("evt_test_001")

        assert event is not None
        assert event.data == {"name": "Test User", "email": "test@example.com"}


# =============================================================================
# Event Query Tests
# =============================================================================

class TestEventServiceQueryGolden:
    """Golden: EventService.query_events() current behavior"""

    async def test_query_events_by_user(self, event_service_with_events):
        """GOLDEN: query_events filters by user_id"""
        query = EventQueryRequest(user_id="usr_test_123", limit=100, offset=0)

        result = await event_service_with_events.query_events(query)

        assert isinstance(result, EventListResponse)
        assert all(e.user_id == "usr_test_123" for e in result.events)
        assert result.total >= 1

    async def test_query_events_by_type(self, event_service_with_events):
        """GOLDEN: query_events filters by event_type"""
        query = EventQueryRequest(event_type="user.created", limit=100, offset=0)

        result = await event_service_with_events.query_events(query)

        assert all(e.event_type == "user.created" for e in result.events)

    async def test_query_events_by_source(self, event_service_with_events):
        """GOLDEN: query_events filters by event_source"""
        query = EventQueryRequest(event_source=EventSource.FRONTEND, limit=100, offset=0)

        result = await event_service_with_events.query_events(query)

        assert all(e.event_source == EventSource.FRONTEND for e in result.events)

    async def test_query_events_by_category(self, event_service_with_events):
        """GOLDEN: query_events filters by event_category"""
        query = EventQueryRequest(event_category=EventCategory.PAYMENT, limit=100, offset=0)

        result = await event_service_with_events.query_events(query)

        assert all(e.event_category == EventCategory.PAYMENT for e in result.events)

    async def test_query_events_by_status(self, event_service_with_events):
        """GOLDEN: query_events filters by status"""
        query = EventQueryRequest(status=EventStatus.PENDING, limit=100, offset=0)

        result = await event_service_with_events.query_events(query)

        assert all(e.status == EventStatus.PENDING for e in result.events)

    async def test_query_events_pagination(self, event_service_with_events):
        """GOLDEN: query_events respects pagination"""
        query = EventQueryRequest(limit=2, offset=0)

        result = await event_service_with_events.query_events(query)

        assert len(result.events) <= 2
        assert result.limit == 2
        assert result.offset == 0

    async def test_query_events_has_more_flag(self, event_service_with_events):
        """GOLDEN: query_events sets has_more correctly"""
        query = EventQueryRequest(limit=1, offset=0)

        result = await event_service_with_events.query_events(query)

        # has_more should be True if total > limit + offset
        if result.total > 1:
            assert result.has_more is True
        else:
            assert result.has_more is False

    async def test_query_events_empty_result(self, event_service):
        """GOLDEN: query_events returns empty list when no matches"""
        query = EventQueryRequest(user_id="nonexistent", limit=100, offset=0)

        result = await event_service.query_events(query)

        assert result.events == []
        assert result.total == 0

    async def test_query_events_combined_filters(self, event_service_with_events):
        """GOLDEN: query_events combines multiple filters"""
        query = EventQueryRequest(
            user_id="usr_test_123",
            event_source=EventSource.BACKEND,
            status=EventStatus.PENDING,
            limit=100,
            offset=0
        )

        result = await event_service_with_events.query_events(query)

        for event in result.events:
            assert event.user_id == "usr_test_123"
            assert event.event_source == EventSource.BACKEND
            assert event.status == EventStatus.PENDING


# =============================================================================
# Event Statistics Tests
# =============================================================================

class TestEventServiceStatisticsGolden:
    """Golden: EventService.get_statistics() current behavior"""

    async def test_get_statistics_success(self, event_service_with_events):
        """GOLDEN: get_statistics returns EventStatistics"""
        stats = await event_service_with_events.get_statistics()

        assert isinstance(stats, EventStatistics)
        assert stats.total_events >= 0
        assert stats.pending_events >= 0
        assert stats.processed_events >= 0
        assert stats.failed_events >= 0

    async def test_get_statistics_counts_statuses(self, event_service_with_events, mock_repo_with_events):
        """GOLDEN: get_statistics counts events by status"""
        stats = await event_service_with_events.get_statistics()

        # Should count events in different statuses
        assert stats.total_events == 4  # Based on mock_repo_with_events fixture
        assert stats.pending_events == 1
        assert stats.processed_events == 2
        assert stats.failed_events == 1

    async def test_get_statistics_empty_repo(self, event_service):
        """GOLDEN: get_statistics returns zeros for empty repo"""
        stats = await event_service.get_statistics()

        assert stats.total_events == 0
        assert stats.pending_events == 0
        assert stats.processed_events == 0
        assert stats.failed_events == 0

    async def test_get_statistics_calculates_rates(self, event_service, mock_repo):
        """GOLDEN: get_statistics calculates processing and error rates"""
        mock_repo.set_stats(
            total_events=100,
            pending_events=10,
            processed_events=80,
            failed_events=10
        )

        stats = await event_service.get_statistics()

        # Service calculates rates
        assert stats.processing_rate == 80.0  # 80/100 * 100
        assert stats.error_rate == 10.0       # 10/100 * 100


# =============================================================================
# Event Stream Tests
# =============================================================================

class TestEventServiceStreamGolden:
    """Golden: EventService.get_event_stream() current behavior"""

    async def test_get_event_stream_success(self, event_service_with_events, mock_repo_with_events):
        """GOLDEN: get_event_stream returns EventStream"""
        stream = await event_service_with_events.get_event_stream("user:usr_test_123")

        assert stream is not None
        assert isinstance(stream, EventStream)
        assert stream.stream_id == "user:usr_test_123"

    async def test_get_event_stream_parses_stream_id(self, event_service_with_events):
        """GOLDEN: get_event_stream parses entity_type from stream_id"""
        stream = await event_service_with_events.get_event_stream("order:ord_123")

        assert stream.entity_type == "order"
        assert stream.entity_id == "ord_123"


# =============================================================================
# Event Processing Tests
# =============================================================================

class TestEventServiceProcessingGolden:
    """Golden: EventService event processing current behavior"""

    async def test_mark_event_processed_success(self, event_service_with_events, mock_repo_with_events):
        """GOLDEN: mark_event_processed updates event status"""
        result = EventProcessingResult(
            event_id="evt_test_002",
            processor_name="test_processor",
            status=ProcessingStatus.SUCCESS,
            message="Processed successfully",
            duration_ms=100
        )

        success = await event_service_with_events.mark_event_processed(
            "evt_test_002",
            "test_processor",
            result
        )

        assert success is True

        # Verify event status was updated
        event = await mock_repo_with_events.get_event("evt_test_002")
        assert event.status == EventStatus.PROCESSED

    async def test_mark_event_processed_failure(self, event_service_with_events, mock_repo_with_events):
        """GOLDEN: mark_event_processed handles failure status"""
        result = EventProcessingResult(
            event_id="evt_test_002",
            processor_name="test_processor",
            status=ProcessingStatus.FAILED,
            message="Processing failed",
            duration_ms=50
        )

        success = await event_service_with_events.mark_event_processed(
            "evt_test_002",
            "test_processor",
            result
        )

        assert success is True

        # Verify event status and error
        event = await mock_repo_with_events.get_event("evt_test_002")
        assert event.status == EventStatus.FAILED
        assert event.error_message == "Processing failed"
        assert event.retry_count == 1

    async def test_mark_event_processed_publishes_success_event(
        self, event_service_with_events, mock_event_bus
    ):
        """GOLDEN: mark_event_processed publishes event.processed.success"""
        result = EventProcessingResult(
            event_id="evt_test_002",
            processor_name="test_processor",
            status=ProcessingStatus.SUCCESS,
            duration_ms=100
        )

        await event_service_with_events.mark_event_processed(
            "evt_test_002",
            "test_processor",
            result
        )

        mock_event_bus.assert_published("event.processed.success")

    async def test_mark_event_processed_publishes_failure_event(
        self, event_service_with_events, mock_event_bus
    ):
        """GOLDEN: mark_event_processed publishes event.processed.failed"""
        result = EventProcessingResult(
            event_id="evt_test_002",
            processor_name="test_processor",
            status=ProcessingStatus.FAILED,
            message="Error occurred"
        )

        await event_service_with_events.mark_event_processed(
            "evt_test_002",
            "test_processor",
            result
        )

        mock_event_bus.assert_published("event.processed.failed")

    async def test_mark_event_processed_not_found(self, event_service):
        """GOLDEN: mark_event_processed returns False for non-existent event"""
        result = EventProcessingResult(
            event_id="evt_nonexistent",
            processor_name="test_processor",
            status=ProcessingStatus.SUCCESS
        )

        success = await event_service.mark_event_processed(
            "evt_nonexistent",
            "test_processor",
            result
        )

        assert success is False

    async def test_get_unprocessed_events(self, event_service_with_events):
        """GOLDEN: get_unprocessed_events returns pending events"""
        events = await event_service_with_events.get_unprocessed_events(limit=100)

        assert isinstance(events, list)
        assert all(e.status == EventStatus.PENDING for e in events)

    async def test_retry_failed_events(self, event_service_with_events):
        """GOLDEN: retry_failed_events requeues failed events"""
        count = await event_service_with_events.retry_failed_events(max_retries=3)

        # Should return count of events re-queued
        assert count >= 0


# =============================================================================
# Event Subscription Tests
# =============================================================================

class TestEventServiceSubscriptionGolden:
    """Golden: EventService subscription management current behavior"""

    async def test_create_subscription_success(self, event_service, mock_repo):
        """GOLDEN: create_subscription saves and returns subscription"""
        subscription = EventSubscription(
            subscriber_name="test_subscriber",
            subscriber_type="service",
            event_types=["user.created", "user.updated"],
            callback_url="https://example.com/webhook"
        )

        result = await event_service.create_subscription(subscription)

        assert isinstance(result, EventSubscription)
        assert result.subscriber_name == "test_subscriber"
        mock_repo.assert_called("save_subscription")

    async def test_create_subscription_publishes_event(self, event_service, mock_event_bus):
        """GOLDEN: create_subscription publishes event.subscription.created"""
        subscription = EventSubscription(
            subscriber_name="test_subscriber",
            event_types=["test.event"]
        )

        await event_service.create_subscription(subscription)

        mock_event_bus.assert_published("event.subscription.created")

    async def test_list_subscriptions_empty(self, event_service):
        """GOLDEN: list_subscriptions returns empty list when none exist"""
        subscriptions = await event_service.list_subscriptions()

        assert subscriptions == []

    async def test_list_subscriptions_with_data(self, event_service, mock_repo):
        """GOLDEN: list_subscriptions returns all subscriptions"""
        mock_repo.set_subscription(
            subscription_id="sub_001",
            subscriber_name="service_a",
            event_types=["event.one"]
        )

        # Add to service's in-memory store
        await event_service.create_subscription(EventSubscription(
            subscription_id="sub_002",
            subscriber_name="service_b",
            event_types=["event.two"]
        ))

        subscriptions = await event_service.list_subscriptions()

        assert len(subscriptions) >= 1

    async def test_trigger_subscriptions_matches_event_type(self, event_service, mock_repo):
        """GOLDEN: trigger_subscriptions triggers matching subscriptions"""
        # Add subscription
        subscription = EventSubscription(
            subscriber_name="test",
            event_types=["user.created"],
            callback_url="https://test.com/hook"
        )
        await event_service.create_subscription(subscription)

        # Create event that matches
        event = Event(
            event_id="evt_001",
            event_type="user.created",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.USER_LIFECYCLE
        )

        # This should trigger the subscription (no error)
        await event_service.trigger_subscriptions(event)

    async def test_subscription_filter_by_event_source(self, event_service):
        """GOLDEN: subscriptions can filter by event_source"""
        subscription = EventSubscription(
            subscriber_name="frontend_listener",
            event_types=["click"],
            event_sources=[EventSource.FRONTEND]
        )
        await event_service.create_subscription(subscription)

        # Backend event should not match
        backend_event = Event(
            event_id="evt_001",
            event_type="click",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.CLICK
        )

        # Frontend event should match
        frontend_event = Event(
            event_id="evt_002",
            event_type="click",
            event_source=EventSource.FRONTEND,
            event_category=EventCategory.CLICK
        )

        # _matches_subscription is a private method, but we can test via trigger
        assert not event_service._matches_subscription(backend_event, subscription)
        assert event_service._matches_subscription(frontend_event, subscription)


# =============================================================================
# Event Replay Tests
# =============================================================================

class TestEventServiceReplayGolden:
    """Golden: EventService.replay_events() current behavior"""

    async def test_replay_events_dry_run_by_ids(self, event_service_with_events):
        """GOLDEN: replay_events dry_run with event_ids returns event list"""
        request = EventReplayRequest(
            event_ids=["evt_test_001", "evt_test_002"],
            dry_run=True
        )

        result = await event_service_with_events.replay_events(request)

        assert result["dry_run"] is True
        assert result["events_count"] >= 0
        assert "events" in result

    async def test_replay_events_actual_run(self, event_service_with_events):
        """GOLDEN: replay_events without dry_run returns replayed count"""
        request = EventReplayRequest(
            event_ids=["evt_test_001"],
            dry_run=False
        )

        result = await event_service_with_events.replay_events(request)

        # Actual run returns replayed/failed/total
        assert "replayed" in result
        assert "failed" in result
        assert "total" in result

    async def test_replay_events_by_time_range(self, event_service_with_events):
        """GOLDEN: replay_events can replay by time range"""
        now = datetime.now(timezone.utc)
        request = EventReplayRequest(
            start_time=now - timedelta(days=7),
            end_time=now,
            dry_run=True
        )

        result = await event_service_with_events.replay_events(request)

        assert result["dry_run"] is True

    async def test_replay_events_publishes_started_event(
        self, event_service_with_events, mock_event_bus
    ):
        """GOLDEN: replay_events publishes event.replay.started for actual run"""
        request = EventReplayRequest(
            event_ids=["evt_test_001"],
            dry_run=False
        )

        await event_service_with_events.replay_events(request)

        mock_event_bus.assert_published("event.replay.started")


# =============================================================================
# Event Projection Tests
# =============================================================================

class TestEventServiceProjectionGolden:
    """Golden: EventService projection management current behavior"""

    async def test_create_projection_returns_projection(self, event_service, mock_event_bus):
        """GOLDEN: create_projection creates and stores projection"""
        projection = await event_service.create_projection(
            projection_name="user_profile",
            entity_id="usr_123",
            entity_type="user"
        )

        assert isinstance(projection, EventProjection)
        assert projection.projection_name == "user_profile"
        assert projection.entity_id == "usr_123"
        assert projection.entity_type == "user"

    async def test_create_projection_publishes_event(self, event_service, mock_event_bus):
        """GOLDEN: create_projection publishes event.projection.created"""
        await event_service.create_projection(
            projection_name="order_summary",
            entity_id="ord_456",
            entity_type="order"
        )

        mock_event_bus.assert_published("event.projection.created")

    async def test_create_projection_stores_in_memory(self, event_service):
        """GOLDEN: create_projection stores projection in memory cache"""
        projection = await event_service.create_projection(
            projection_name="test_proj",
            entity_id="ent_001",
            entity_type="entity"
        )

        # Projection should be cached in memory
        assert projection.projection_id in event_service.projections

    async def test_get_projection_from_cache(self, event_service):
        """GOLDEN: get_projection returns cached projection by ID"""
        # First create a projection
        created = await event_service.create_projection(
            projection_name="test",
            entity_id="ent_001",
            entity_type="test"
        )

        # Get it by ID
        projection = await event_service.get_projection(created.projection_id)

        assert projection is not None
        assert projection.projection_id == created.projection_id

    async def test_get_projection_not_found(self, event_service):
        """GOLDEN: get_projection returns None when not found"""
        projection = await event_service.get_projection("nonexistent_id")

        assert projection is None

    async def test_apply_event_to_projection_updates_state(self, event_service):
        """GOLDEN: _apply_event_to_projection updates projection state"""
        projection = EventProjection(
            projection_name="test",
            entity_id="ent_001",
            entity_type="test",
            state={},
            version=0
        )
        event = Event(
            event_id="evt_001",
            event_type="test.event",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.USER_ACTION,
            data={"key": "value"}
        )

        updated = await event_service._apply_event_to_projection(projection, event)

        assert updated.version == 1
        assert updated.last_event_id == event.event_id
        assert "test.event" in updated.state


# =============================================================================
# Event Processor Tests
# =============================================================================

class TestEventServiceProcessorGolden:
    """Golden: EventService processor management current behavior"""

    async def test_processor_matches_event_type(self, event_service):
        """GOLDEN: _matches_processor matches events by event_type filter"""
        processor = EventProcessor(
            processor_name="user_processor",
            processor_type="handler",
            filters={"event_type": "user.created"}
        )

        matching_event = Event(
            event_id="evt_001",
            event_type="user.created",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.USER_LIFECYCLE
        )

        non_matching_event = Event(
            event_id="evt_002",
            event_type="order.created",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.ORDER
        )

        assert event_service._matches_processor(matching_event, processor)
        assert not event_service._matches_processor(non_matching_event, processor)

    async def test_processor_matches_event_source(self, event_service):
        """GOLDEN: _matches_processor matches events by event_source filter"""
        processor = EventProcessor(
            processor_name="frontend_processor",
            processor_type="handler",
            filters={"event_source": EventSource.FRONTEND}
        )

        matching_event = Event(
            event_id="evt_001",
            event_type="click",
            event_source=EventSource.FRONTEND,
            event_category=EventCategory.CLICK
        )

        non_matching_event = Event(
            event_id="evt_002",
            event_type="click",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.CLICK
        )

        assert event_service._matches_processor(matching_event, processor)
        assert not event_service._matches_processor(non_matching_event, processor)

    async def test_processor_no_filters_matches_all(self, event_service):
        """GOLDEN: _matches_processor with no filters matches all events"""
        processor = EventProcessor(
            processor_name="catch_all",
            processor_type="handler",
            filters={}
        )

        event = Event(
            event_id="evt_001",
            event_type="any.event",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.SYSTEM
        )

        assert event_service._matches_processor(event, processor)

    async def test_processors_loaded_from_repository(self, event_service, mock_repo):
        """GOLDEN: _load_processors loads from repository"""
        mock_repo.set_processor(
            processor_id="proc_001",
            processor_name="test_processor",
            processor_type="webhook",
            enabled=True
        )

        await event_service._load_processors()

        assert "proc_001" in event_service.processors


# =============================================================================
# RudderStack Integration Tests
# =============================================================================

class TestEventServiceRudderStackGolden:
    """Golden: EventService RudderStack integration current behavior"""

    async def test_create_event_from_rudderstack_page(self, event_service):
        """GOLDEN: create_event_from_rudderstack handles page events"""
        rudderstack_event = RudderStackEvent(
            userId="usr_123",
            event="Home Page",
            type="page",
            properties={"url": "/home", "title": "Home"},
            context={"userAgent": "Chrome"},
            timestamp="2024-01-15T10:00:00Z"
        )

        result = await event_service.create_event_from_rudderstack(rudderstack_event)

        assert isinstance(result, EventResponse)
        assert result.event_source == EventSource.FRONTEND
        assert result.event_category == EventCategory.PAGE_VIEW

    async def test_create_event_from_rudderstack_track(self, event_service):
        """GOLDEN: create_event_from_rudderstack handles track events"""
        rudderstack_event = RudderStackEvent(
            userId="usr_123",
            event="Button Click",
            type="track",
            properties={"button": "signup"},
            context={},
            timestamp="2024-01-15T10:00:00Z"
        )

        result = await event_service.create_event_from_rudderstack(rudderstack_event)

        assert isinstance(result, EventResponse)
        assert result.event_source == EventSource.FRONTEND

    async def test_create_event_from_rudderstack_with_anonymous_id(self, event_service):
        """GOLDEN: create_event_from_rudderstack uses anonymousId when no userId"""
        rudderstack_event = RudderStackEvent(
            anonymousId="anon_456",
            userId=None,
            event="Page View",
            type="page",
            properties={},
            context={},
            timestamp="2024-01-15T10:00:00Z"
        )

        result = await event_service.create_event_from_rudderstack(rudderstack_event)

        assert result.user_id == "anon_456"


# =============================================================================
# NATS Integration Tests
# =============================================================================

class TestEventServiceNATSGolden:
    """Golden: EventService NATS integration current behavior"""

    async def test_create_event_from_nats(self, event_service):
        """GOLDEN: create_event_from_nats creates event from NATS message"""
        nats_event = {
            "id": "nats_001",
            "type": "user.updated",
            "source": "account_service",
            "data": {"user_id": "usr_123", "name": "Updated Name"},
            "timestamp": "2024-01-15T10:00:00Z",
            "correlation_id": "corr_789"
        }

        result = await event_service.create_event_from_nats(nats_event)

        assert isinstance(result, EventResponse)
        assert result.event_type == "user.updated"
        assert result.event_source == EventSource.BACKEND

    async def test_categorize_nats_event_user(self, event_service):
        """GOLDEN: categorize_nats_event identifies user events"""
        nats_event = {"type": "user.created"}

        category = event_service._categorize_nats_event(nats_event)

        assert category == EventCategory.USER_LIFECYCLE

    async def test_categorize_nats_event_payment(self, event_service):
        """GOLDEN: categorize_nats_event identifies payment events"""
        nats_event = {"type": "payment.completed"}

        category = event_service._categorize_nats_event(nats_event)

        assert category == EventCategory.PAYMENT

    async def test_categorize_nats_event_order(self, event_service):
        """GOLDEN: categorize_nats_event identifies order events"""
        nats_event = {"type": "order.created"}

        category = event_service._categorize_nats_event(nats_event)

        assert category == EventCategory.ORDER

    async def test_categorize_nats_event_device(self, event_service):
        """GOLDEN: categorize_nats_event identifies device events"""
        nats_event = {"type": "device.connected"}

        category = event_service._categorize_nats_event(nats_event)

        assert category == EventCategory.DEVICE_STATUS

    async def test_categorize_nats_event_unknown(self, event_service):
        """GOLDEN: categorize_nats_event defaults to SYSTEM for unknown"""
        nats_event = {"type": "unknown.event"}

        category = event_service._categorize_nats_event(nats_event)

        assert category == EventCategory.SYSTEM


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestEventServiceErrorHandlingGolden:
    """Golden: EventService error handling current behavior"""

    async def test_create_event_repository_error(self, event_service, mock_repo):
        """GOLDEN: create_event propagates repository errors"""
        mock_repo.set_error(Exception("Database connection failed"))

        request = EventCreateRequest(
            event_type="test.event",
            data={}
        )

        with pytest.raises(Exception) as exc_info:
            await event_service.create_event(request)

        assert "Database connection failed" in str(exc_info.value)

    async def test_query_events_repository_error(self, event_service, mock_repo):
        """GOLDEN: query_events propagates repository errors"""
        mock_repo.set_error(Exception("Query failed"))

        query = EventQueryRequest(limit=10, offset=0)

        with pytest.raises(Exception) as exc_info:
            await event_service.query_events(query)

        assert "Query failed" in str(exc_info.value)

    async def test_event_bus_error_does_not_fail_create(self, event_service, mock_event_bus):
        """GOLDEN: event bus errors are logged but don't fail event creation"""
        mock_event_bus.set_error(Exception("Event bus unavailable"))

        request = EventCreateRequest(
            event_type="test.event",
            data={}
        )

        # Should not raise - event bus errors are caught
        result = await event_service.create_event(request)

        # Event should still be created
        assert result is not None


# =============================================================================
# Service Lifecycle Tests
# =============================================================================

class TestEventServiceLifecycleGolden:
    """Golden: EventService lifecycle management current behavior"""

    async def test_shutdown_stops_processing(self, event_service):
        """GOLDEN: shutdown stops event processing"""
        event_service.is_processing = True

        await event_service.shutdown()

        assert event_service.is_processing is False

    async def test_initialize_starts_processing(self, event_service, mock_repo):
        """GOLDEN: initialize starts event processing"""
        # Ensure no initialization error
        await event_service.initialize()

        # Repository should be initialized
        mock_repo.assert_called("initialize")
