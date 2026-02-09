"""
Unit Golden Tests: Event Service Business Logic

Tests EventService methods with mocked repository and dependencies.
Focus: Pure function testing, business logic validation, edge cases.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from microservices.event_service.event_service import EventService
from microservices.event_service.models import (
    Event,
    EventSource,
    EventCategory,
    EventStatus,
    ProcessingStatus,
    EventCreateRequest,
    EventQueryRequest,
    EventListResponse,
    EventStatistics,
    EventProcessingResult,
    EventReplayRequest,
    EventProjection,
    EventProcessor,
    EventSubscription,
    RudderStackEvent,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_config_manager():
    """Create a mock config manager"""
    config = MagicMock()
    config.get_service_config.return_value = {"service_name": "event_service"}
    return config


@pytest.fixture
def mock_repository():
    """Create a mock event repository"""
    repo = AsyncMock()
    repo.initialize = AsyncMock()
    repo.save_event = AsyncMock()
    repo.get_event = AsyncMock()
    repo.query_events = AsyncMock()
    repo.update_event = AsyncMock()
    repo.get_event_stream = AsyncMock(return_value=[])
    repo.get_statistics = AsyncMock()
    repo.get_failed_events = AsyncMock(return_value=[])
    repo.save_processing_result = AsyncMock()
    repo.save_projection = AsyncMock()
    repo.get_projection = AsyncMock()
    repo.save_subscription = AsyncMock()
    repo.get_subscriptions = AsyncMock(return_value=[])
    repo.get_processors = AsyncMock(return_value=[])
    repo.get_events_by_time_range = AsyncMock(return_value=[])
    repo.close = AsyncMock()
    return repo


@pytest.fixture
def event_service(mock_config_manager, mock_repository):
    """Create EventService with mocked dependencies"""
    with patch('microservices.event_service.event_service.EventRepository') as MockRepo:
        MockRepo.return_value = mock_repository
        service = EventService(event_bus=None, config_manager=mock_config_manager)
        service.repository = mock_repository
    return service


@pytest.fixture
def sample_event():
    """Create a sample event for testing"""
    return Event(
        event_id="evt_test_123",
        event_type="user.registered",
        event_source=EventSource.BACKEND,
        event_category=EventCategory.USER_LIFECYCLE,
        user_id="user_456",
        data={"email": "test@example.com"},
        status=EventStatus.PENDING,
        timestamp=datetime.utcnow(),
    )


# ==================== Event Creation Tests ====================

class TestEventCreation:
    """Test event creation business logic"""

    @pytest.mark.asyncio
    async def test_create_event_sets_pending_status(self, event_service, mock_repository):
        """Test that created events have PENDING status"""
        request = EventCreateRequest(
            event_type="user.login",
            event_source=EventSource.FRONTEND,
            event_category=EventCategory.USER_ACTION,
            user_id="user_123",
        )
        expected_event = Event(
            event_id="evt_new",
            event_type=request.event_type,
            event_source=request.event_source,
            event_category=request.event_category,
            user_id=request.user_id,
            status=EventStatus.PENDING,
            timestamp=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        mock_repository.save_event.return_value = expected_event

        response = await event_service.create_event(request)

        assert response.status == EventStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_event_adds_to_processing_queue(self, event_service, mock_repository):
        """Test that created event is added to processing queue"""
        request = EventCreateRequest(event_type="test.event")
        expected_event = Event(
            event_id="evt_queue",
            event_type=request.event_type,
            event_source=EventSource.BACKEND,
            event_category=EventCategory.USER_ACTION,
            status=EventStatus.PENDING,
            timestamp=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        mock_repository.save_event.return_value = expected_event

        assert event_service.processing_queue.empty()
        await event_service.create_event(request)
        assert not event_service.processing_queue.empty()


# ==================== Event Categorization Tests ====================

class TestEventCategorization:
    """Test event categorization helper methods"""

    def test_categorize_rudderstack_page_event(self, event_service):
        """Test RudderStack page event categorization"""
        event = RudderStackEvent(
            event="Home Page", type="page", timestamp=datetime.utcnow().isoformat() + "Z"
        )
        assert event_service._categorize_rudderstack_event(event) == EventCategory.PAGE_VIEW

    def test_categorize_rudderstack_click_event(self, event_service):
        """Test RudderStack click event categorization"""
        event = RudderStackEvent(
            event="Button Click", type="track", timestamp=datetime.utcnow().isoformat() + "Z"
        )
        assert event_service._categorize_rudderstack_event(event) == EventCategory.CLICK

    def test_categorize_rudderstack_form_event(self, event_service):
        """Test RudderStack form event categorization"""
        event = RudderStackEvent(
            event="Form Submitted", type="track", timestamp=datetime.utcnow().isoformat() + "Z"
        )
        assert event_service._categorize_rudderstack_event(event) == EventCategory.FORM_SUBMIT

    def test_categorize_nats_user_event(self, event_service):
        """Test NATS user event categorization"""
        assert event_service._categorize_nats_event({"type": "user.registered"}) == EventCategory.USER_LIFECYCLE

    def test_categorize_nats_payment_event(self, event_service):
        """Test NATS payment event categorization"""
        assert event_service._categorize_nats_event({"type": "payment.completed"}) == EventCategory.PAYMENT

    def test_categorize_nats_device_event(self, event_service):
        """Test NATS device event categorization"""
        assert event_service._categorize_nats_event({"type": "device.connected"}) == EventCategory.DEVICE_STATUS

    def test_categorize_nats_unknown_event_defaults_to_system(self, event_service):
        """Test NATS unknown event defaults to SYSTEM category"""
        assert event_service._categorize_nats_event({"type": "unknown.event"}) == EventCategory.SYSTEM


# ==================== Subscription Matching Tests ====================

class TestSubscriptionMatching:
    """Test subscription matching logic"""

    def test_matches_subscription_by_event_type(self, event_service):
        """Test subscription matches by event type"""
        event = Event(
            event_type="user.registered",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.USER_LIFECYCLE,
        )
        subscription = EventSubscription(event_types=["user.registered", "user.login"])
        assert event_service._matches_subscription(event, subscription) is True

    def test_subscription_mismatch_event_type(self, event_service):
        """Test subscription does not match wrong event type"""
        event = Event(
            event_type="order.created",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.ORDER,
        )
        subscription = EventSubscription(event_types=["user.registered"])
        assert event_service._matches_subscription(event, subscription) is False

    def test_matches_subscription_by_event_source(self, event_service):
        """Test subscription matches by event source"""
        event = Event(
            event_type="test.event",
            event_source=EventSource.FRONTEND,
            event_category=EventCategory.USER_ACTION,
        )
        subscription = EventSubscription(
            event_types=["test.event"],
            event_sources=[EventSource.FRONTEND],
        )
        assert event_service._matches_subscription(event, subscription) is True

    def test_subscription_mismatch_event_source(self, event_service):
        """Test subscription does not match wrong event source"""
        event = Event(
            event_type="test.event",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.SYSTEM,
        )
        subscription = EventSubscription(
            event_types=["test.event"],
            event_sources=[EventSource.FRONTEND],
        )
        assert event_service._matches_subscription(event, subscription) is False


# ==================== Statistics Calculation Tests ====================

class TestStatisticsCalculation:
    """Test statistics calculation logic"""

    @pytest.mark.asyncio
    async def test_statistics_processing_rate_calculation(self, event_service, mock_repository):
        """Test processing rate calculation"""
        mock_repository.get_statistics.return_value = EventStatistics(
            total_events=100, pending_events=10, processed_events=80, failed_events=10
        )
        stats = await event_service.get_statistics()
        assert stats.processing_rate == 80.0  # 80/100 * 100

    @pytest.mark.asyncio
    async def test_statistics_error_rate_calculation(self, event_service, mock_repository):
        """Test error rate calculation"""
        mock_repository.get_statistics.return_value = EventStatistics(
            total_events=100, pending_events=10, processed_events=80, failed_events=10
        )
        stats = await event_service.get_statistics()
        assert stats.error_rate == 10.0  # 10/100 * 100

    @pytest.mark.asyncio
    async def test_statistics_zero_events_no_division_error(self, event_service, mock_repository):
        """Test statistics with zero events does not cause division error"""
        mock_repository.get_statistics.return_value = EventStatistics(
            total_events=0, pending_events=0, processed_events=0, failed_events=0
        )
        stats = await event_service.get_statistics()
        assert stats.processing_rate == 0.0
        assert stats.error_rate == 0.0


# ==================== Event Processing Tests ====================

class TestEventProcessing:
    """Test event processing logic"""

    @pytest.mark.asyncio
    async def test_mark_event_processed_success_updates_status(self, event_service, mock_repository, sample_event):
        """Test successful processing updates event status"""
        mock_repository.get_event.return_value = sample_event
        mock_repository.update_event.return_value = True
        result = EventProcessingResult(
            event_id=sample_event.event_id,
            processor_name="test_processor",
            status=ProcessingStatus.SUCCESS,
        )

        success = await event_service.mark_event_processed(sample_event.event_id, "test_processor", result)

        assert success is True
        mock_repository.update_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_event_processed_failure_increments_retry(self, event_service, mock_repository, sample_event):
        """Test failed processing increments retry count"""
        sample_event.retry_count = 0
        mock_repository.get_event.return_value = sample_event
        mock_repository.update_event.return_value = True
        result = EventProcessingResult(
            event_id=sample_event.event_id,
            processor_name="test_processor",
            status=ProcessingStatus.FAILED,
            message="Error occurred",
        )

        await event_service.mark_event_processed(sample_event.event_id, "test_processor", result)

        call_args = mock_repository.update_event.call_args
        updated_event = call_args[0][0]
        assert updated_event.retry_count == 1

    @pytest.mark.asyncio
    async def test_mark_event_processed_not_found_returns_false(self, event_service, mock_repository):
        """Test marking non-existent event returns False"""
        mock_repository.get_event.return_value = None
        result = EventProcessingResult(
            event_id="evt_nonexistent",
            processor_name="test_processor",
            status=ProcessingStatus.SUCCESS,
        )

        success = await event_service.mark_event_processed("evt_nonexistent", "test_processor", result)

        assert success is False


# ==================== Event Replay Tests ====================

class TestEventReplay:
    """Test event replay logic"""

    @pytest.mark.asyncio
    async def test_replay_dry_run_does_not_republish(self, event_service, mock_repository):
        """Test dry run mode does not actually replay events"""
        events = [
            Event(
                event_id=f"evt_{i}",
                event_type="test",
                event_source=EventSource.BACKEND,
                event_category=EventCategory.SYSTEM,
                timestamp=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            for i in range(3)
        ]
        mock_repository.get_event.side_effect = events

        request = EventReplayRequest(
            event_ids=["evt_0", "evt_1", "evt_2"],
            dry_run=True,
        )

        result = await event_service.replay_events(request)

        assert result["dry_run"] is True
        assert result["events_count"] == 3


if __name__ == "__main__":
    pytest.main([__file__])
