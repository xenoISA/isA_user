"""
Unit Golden Tests: Event Service Models

Tests model validation and serialization without external dependencies.
"""
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.event_service.models import (
    EventSource,
    EventCategory,
    EventStatus,
    ProcessingStatus,
    Event,
    EventStream,
    RudderStackEvent,
    EventCreateRequest,
    EventQueryRequest,
    EventResponse,
    EventListResponse,
    EventStatistics,
    EventProcessingResult,
    EventReplayRequest,
    EventProjection,
    EventProcessor,
    EventSubscription,
)


class TestEventSource:
    """Test EventSource enum"""

    def test_event_source_values(self):
        """Test all event source values are defined"""
        assert EventSource.FRONTEND.value == "frontend"
        assert EventSource.BACKEND.value == "backend"
        assert EventSource.SYSTEM.value == "system"
        assert EventSource.IOT_DEVICE.value == "iot_device"
        assert EventSource.EXTERNAL_API.value == "external_api"
        assert EventSource.SCHEDULED.value == "scheduled"

    def test_event_source_comparison(self):
        """Test event source comparison"""
        assert EventSource.FRONTEND.value == "frontend"
        assert EventSource.FRONTEND != EventSource.BACKEND
        assert EventSource.SYSTEM != EventSource.IOT_DEVICE


class TestEventCategory:
    """Test EventCategory enum"""

    def test_event_category_user_action_values(self):
        """Test user action category values"""
        assert EventCategory.USER_ACTION.value == "user_action"
        assert EventCategory.PAGE_VIEW.value == "page_view"
        assert EventCategory.FORM_SUBMIT.value == "form_submit"
        assert EventCategory.CLICK.value == "click"

    def test_event_category_business_values(self):
        """Test business category values"""
        assert EventCategory.USER_LIFECYCLE.value == "user_lifecycle"
        assert EventCategory.PAYMENT.value == "payment"
        assert EventCategory.ORDER.value == "order"
        assert EventCategory.TASK.value == "task"

    def test_event_category_system_values(self):
        """Test system category values"""
        assert EventCategory.SYSTEM.value == "system"
        assert EventCategory.SECURITY.value == "security"
        assert EventCategory.PERFORMANCE.value == "performance"
        assert EventCategory.ERROR.value == "error"

    def test_event_category_iot_values(self):
        """Test IoT category values"""
        assert EventCategory.DEVICE.value == "device"
        assert EventCategory.DEVICE_STATUS.value == "device_status"
        assert EventCategory.TELEMETRY.value == "telemetry"
        assert EventCategory.COMMAND.value == "command"
        assert EventCategory.ALERT.value == "alert"


class TestEventStatus:
    """Test EventStatus enum"""

    def test_event_status_values(self):
        """Test all event status values"""
        assert EventStatus.PENDING.value == "pending"
        assert EventStatus.PROCESSING.value == "processing"
        assert EventStatus.PROCESSED.value == "processed"
        assert EventStatus.FAILED.value == "failed"
        assert EventStatus.ARCHIVED.value == "archived"

    def test_event_status_workflow(self):
        """Test event status workflow transitions"""
        # Verify status flow: pending -> processing -> processed
        assert EventStatus.PENDING.value == "pending"
        assert EventStatus.PROCESSING.value == "processing"
        assert EventStatus.PROCESSED.value == "processed"
        # Failed is a terminal state
        assert EventStatus.FAILED.value == "failed"
        # Archived is a terminal state
        assert EventStatus.ARCHIVED.value == "archived"


class TestProcessingStatus:
    """Test ProcessingStatus enum"""

    def test_processing_status_values(self):
        """Test all processing status values"""
        assert ProcessingStatus.SUCCESS.value == "success"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.SKIPPED.value == "skipped"
        assert ProcessingStatus.RETRY.value == "retry"

    def test_processing_status_comparison(self):
        """Test processing status comparison"""
        assert ProcessingStatus.SUCCESS != ProcessingStatus.FAILED
        assert ProcessingStatus.SKIPPED != ProcessingStatus.RETRY


class TestEventModel:
    """Test Event model validation"""

    def test_event_creation_with_all_fields(self):
        """Test creating event with all fields"""
        now = datetime.utcnow()

        event = Event(
            event_id="evt_123",
            event_type="user.registered",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.USER_LIFECYCLE,
            user_id="user_456",
            session_id="session_789",
            organization_id="org_101",
            device_id="device_202",
            correlation_id="corr_303",
            data={"email": "test@example.com", "name": "Test User"},
            metadata={"ip": "192.168.1.1", "user_agent": "Chrome/90.0"},
            context={"page": "/signup", "referrer": "/home"},
            properties={"plan": "premium", "trial": True},
            status=EventStatus.PENDING,
            processed_at=None,
            processors=[],
            error_message=None,
            retry_count=0,
            timestamp=now,
            created_at=now,
            updated_at=now,
            version="1.0.0",
            schema_version="1.0.0",
        )

        assert event.event_id == "evt_123"
        assert event.event_type == "user.registered"
        assert event.event_source == EventSource.BACKEND
        assert event.event_category == EventCategory.USER_LIFECYCLE
        assert event.user_id == "user_456"
        assert event.session_id == "session_789"
        assert event.organization_id == "org_101"
        assert event.device_id == "device_202"
        assert event.data["email"] == "test@example.com"
        assert event.metadata["ip"] == "192.168.1.1"
        assert event.status == EventStatus.PENDING
        assert event.retry_count == 0
        assert event.version == "1.0.0"

    def test_event_creation_with_minimal_fields(self):
        """Test creating event with only required fields"""
        event = Event(
            event_type="test.event",
            event_source=EventSource.SYSTEM,
            event_category=EventCategory.SYSTEM,
        )

        # Auto-generated event_id
        assert event.event_id is not None
        assert len(event.event_id) > 0
        assert event.event_type == "test.event"
        assert event.event_source == EventSource.SYSTEM
        assert event.event_category == EventCategory.SYSTEM
        # Default values
        assert event.data == {}
        assert event.metadata == {}
        assert event.status == EventStatus.PENDING
        assert event.retry_count == 0
        assert event.processors == []
        assert event.version == "1.0.0"
        assert event.schema_version == "1.0.0"

    def test_event_with_processing_info(self):
        """Test event with processing information"""
        now = datetime.utcnow()

        event = Event(
            event_type="order.created",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.ORDER,
            status=EventStatus.PROCESSED,
            processed_at=now,
            processors=["order_processor", "notification_processor"],
            retry_count=2,
        )

        assert event.status == EventStatus.PROCESSED
        assert event.processed_at == now
        assert len(event.processors) == 2
        assert "order_processor" in event.processors
        assert event.retry_count == 2

    def test_event_with_error_info(self):
        """Test event with error information"""
        event = Event(
            event_type="payment.failed",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.PAYMENT,
            status=EventStatus.FAILED,
            error_message="Payment gateway timeout",
            retry_count=3,
        )

        assert event.status == EventStatus.FAILED
        assert event.error_message == "Payment gateway timeout"
        assert event.retry_count == 3

    def test_event_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Event(event_type="test.event")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "event_source" in missing_fields
        assert "event_category" in missing_fields

    def test_event_iot_device_event(self):
        """Test IoT device event"""
        event = Event(
            event_type="device.telemetry",
            event_source=EventSource.IOT_DEVICE,
            event_category=EventCategory.TELEMETRY,
            device_id="device_001",
            data={
                "temperature": 22.5,
                "humidity": 65.0,
                "battery": 85,
            },
        )

        assert event.event_source == EventSource.IOT_DEVICE
        assert event.event_category == EventCategory.TELEMETRY
        assert event.device_id == "device_001"
        assert event.data["temperature"] == 22.5


class TestEventStreamModel:
    """Test EventStream model validation"""

    def test_event_stream_creation(self):
        """Test creating event stream"""
        now = datetime.utcnow()
        events = [
            Event(
                event_type="user.created",
                event_source=EventSource.BACKEND,
                event_category=EventCategory.USER_LIFECYCLE,
            ),
            Event(
                event_type="user.updated",
                event_source=EventSource.BACKEND,
                event_category=EventCategory.USER_LIFECYCLE,
            ),
        ]

        stream = EventStream(
            stream_id="stream_123",
            stream_type="user_lifecycle",
            entity_id="user_456",
            entity_type="user",
            events=events,
            version=2,
            created_at=now,
            updated_at=now,
        )

        assert stream.stream_id == "stream_123"
        assert stream.stream_type == "user_lifecycle"
        assert stream.entity_id == "user_456"
        assert stream.entity_type == "user"
        assert len(stream.events) == 2
        assert stream.version == 2

    def test_event_stream_empty_events(self):
        """Test event stream with empty events list"""
        stream = EventStream(
            stream_id="stream_empty",
            stream_type="test",
            entity_id="entity_123",
            entity_type="test_entity",
        )

        assert stream.stream_id == "stream_empty"
        assert stream.events == []
        assert stream.version == 0

    def test_event_stream_missing_required_fields(self):
        """Test that missing required fields raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            EventStream(stream_id="stream_123")

        errors = exc_info.value.errors()
        missing_fields = {err["loc"][0] for err in errors}
        assert "stream_type" in missing_fields
        assert "entity_id" in missing_fields
        assert "entity_type" in missing_fields


class TestRudderStackEventModel:
    """Test RudderStackEvent model validation"""

    def test_rudderstack_event_creation_full(self):
        """Test creating RudderStack event with all fields"""
        timestamp = datetime.utcnow().isoformat()

        event = RudderStackEvent(
            anonymousId="anon_123",
            userId="user_456",
            event="Product Viewed",
            type="track",
            properties={
                "product_id": "prod_789",
                "name": "Widget",
                "price": 29.99,
            },
            context={
                "ip": "192.168.1.1",
                "library": {"name": "analytics.js", "version": "4.0.0"},
            },
            timestamp=timestamp,
            sentAt=timestamp,
            receivedAt=timestamp,
            originalTimestamp=timestamp,
        )

        assert event.anonymousId == "anon_123"
        assert event.userId == "user_456"
        assert event.event == "Product Viewed"
        assert event.type == "track"
        assert event.properties["product_id"] == "prod_789"
        assert event.context["ip"] == "192.168.1.1"

    def test_rudderstack_event_minimal(self):
        """Test creating RudderStack event with minimal fields"""
        timestamp = datetime.utcnow().isoformat()

        event = RudderStackEvent(
            event="Page Viewed",
            type="page",
            timestamp=timestamp,
        )

        assert event.event == "Page Viewed"
        assert event.type == "page"
        assert event.timestamp == timestamp
        assert event.properties == {}
        assert event.context == {}
        assert event.anonymousId is None
        assert event.userId is None

    def test_rudderstack_event_anonymous_user(self):
        """Test RudderStack event with anonymous user"""
        timestamp = datetime.utcnow().isoformat()

        event = RudderStackEvent(
            anonymousId="anon_abc",
            event="Button Clicked",
            type="track",
            timestamp=timestamp,
        )

        assert event.anonymousId == "anon_abc"
        assert event.userId is None
        assert event.event == "Button Clicked"


class TestEventCreateRequest:
    """Test EventCreateRequest model validation"""

    def test_event_create_request_valid(self):
        """Test valid event creation request"""
        request = EventCreateRequest(
            event_type="user.login",
            event_source=EventSource.FRONTEND,
            event_category=EventCategory.USER_ACTION,
            user_id="user_123",
            data={"method": "oauth", "provider": "google"},
            metadata={"ip": "10.0.0.1"},
            context={"page": "/dashboard"},
        )

        assert request.event_type == "user.login"
        assert request.event_source == EventSource.FRONTEND
        assert request.event_category == EventCategory.USER_ACTION
        assert request.user_id == "user_123"
        assert request.data["method"] == "oauth"

    def test_event_create_request_with_defaults(self):
        """Test event creation request with default values"""
        request = EventCreateRequest(
            event_type="test.event",
        )

        assert request.event_type == "test.event"
        assert request.event_source == EventSource.BACKEND
        assert request.event_category == EventCategory.USER_ACTION
        assert request.data == {}
        assert request.user_id is None
        assert request.metadata is None
        assert request.context is None

    def test_event_create_request_minimal(self):
        """Test minimal event creation request"""
        request = EventCreateRequest(
            event_type="simple.event",
            event_source=EventSource.SYSTEM,
            event_category=EventCategory.SYSTEM,
        )

        assert request.event_type == "simple.event"
        assert request.event_source == EventSource.SYSTEM
        assert request.event_category == EventCategory.SYSTEM


class TestEventQueryRequest:
    """Test EventQueryRequest model validation"""

    def test_event_query_request_defaults(self):
        """Test default query parameters"""
        request = EventQueryRequest()

        assert request.user_id is None
        assert request.event_type is None
        assert request.event_source is None
        assert request.event_category is None
        assert request.status is None
        assert request.start_time is None
        assert request.end_time is None
        assert request.limit == 100
        assert request.offset == 0

    def test_event_query_request_with_user_filter(self):
        """Test query request with user filter"""
        request = EventQueryRequest(
            user_id="user_123",
            limit=50,
            offset=10,
        )

        assert request.user_id == "user_123"
        assert request.limit == 50
        assert request.offset == 10

    def test_event_query_request_with_all_filters(self):
        """Test query request with all filters"""
        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()

        request = EventQueryRequest(
            user_id="user_123",
            event_type="user.login",
            event_source=EventSource.FRONTEND,
            event_category=EventCategory.USER_ACTION,
            status=EventStatus.PROCESSED,
            start_time=start,
            end_time=end,
            limit=200,
            offset=50,
        )

        assert request.user_id == "user_123"
        assert request.event_type == "user.login"
        assert request.event_source == EventSource.FRONTEND
        assert request.event_category == EventCategory.USER_ACTION
        assert request.status == EventStatus.PROCESSED
        assert request.start_time == start
        assert request.end_time == end
        assert request.limit == 200
        assert request.offset == 50

    def test_event_query_request_limit_validation(self):
        """Test limit validation (min/max constraints)"""
        # Test minimum limit
        with pytest.raises(ValidationError):
            EventQueryRequest(limit=0)

        # Test maximum limit
        with pytest.raises(ValidationError):
            EventQueryRequest(limit=1001)

        # Test valid limits
        request_min = EventQueryRequest(limit=1)
        assert request_min.limit == 1

        request_max = EventQueryRequest(limit=1000)
        assert request_max.limit == 1000

    def test_event_query_request_offset_validation(self):
        """Test offset validation (non-negative)"""
        with pytest.raises(ValidationError):
            EventQueryRequest(offset=-1)

        # Test valid offset
        request = EventQueryRequest(offset=0)
        assert request.offset == 0


class TestEventResponse:
    """Test EventResponse model"""

    def test_event_response_creation(self):
        """Test creating event response"""
        now = datetime.utcnow()

        response = EventResponse(
            event_id="evt_123",
            event_type="user.registered",
            event_source=EventSource.BACKEND,
            event_category=EventCategory.USER_LIFECYCLE,
            user_id="user_456",
            data={"email": "test@example.com"},
            status=EventStatus.PROCESSED,
            timestamp=now,
            created_at=now,
        )

        assert response.event_id == "evt_123"
        assert response.event_type == "user.registered"
        assert response.event_source == EventSource.BACKEND
        assert response.event_category == EventCategory.USER_LIFECYCLE
        assert response.user_id == "user_456"
        assert response.data["email"] == "test@example.com"
        assert response.status == EventStatus.PROCESSED

    def test_event_response_without_user(self):
        """Test event response without user_id"""
        now = datetime.utcnow()

        response = EventResponse(
            event_id="evt_system",
            event_type="system.health_check",
            event_source=EventSource.SYSTEM,
            event_category=EventCategory.SYSTEM,
            user_id=None,
            data={"status": "healthy"},
            status=EventStatus.PROCESSED,
            timestamp=now,
            created_at=now,
        )

        assert response.user_id is None
        assert response.event_type == "system.health_check"


class TestEventListResponse:
    """Test EventListResponse model"""

    def test_event_list_response(self):
        """Test event list response"""
        now = datetime.utcnow()

        events = [
            EventResponse(
                event_id=f"evt_{i}",
                event_type="test.event",
                event_source=EventSource.BACKEND,
                event_category=EventCategory.SYSTEM,
                user_id="user_123",
                data={},
                status=EventStatus.PROCESSED,
                timestamp=now,
                created_at=now,
            )
            for i in range(3)
        ]

        response = EventListResponse(
            events=events,
            total=100,
            limit=3,
            offset=0,
            has_more=True,
        )

        assert len(response.events) == 3
        assert response.total == 100
        assert response.limit == 3
        assert response.offset == 0
        assert response.has_more is True

    def test_event_list_response_last_page(self):
        """Test event list response for last page"""
        now = datetime.utcnow()

        events = [
            EventResponse(
                event_id=f"evt_{i}",
                event_type="test.event",
                event_source=EventSource.BACKEND,
                event_category=EventCategory.SYSTEM,
                user_id=None,
                data={},
                status=EventStatus.PROCESSED,
                timestamp=now,
                created_at=now,
            )
            for i in range(2)
        ]

        response = EventListResponse(
            events=events,
            total=2,
            limit=10,
            offset=0,
            has_more=False,
        )

        assert len(response.events) == 2
        assert response.total == 2
        assert response.has_more is False

    def test_event_list_response_empty(self):
        """Test empty event list response"""
        response = EventListResponse(
            events=[],
            total=0,
            limit=100,
            offset=0,
            has_more=False,
        )

        assert len(response.events) == 0
        assert response.total == 0
        assert response.has_more is False


class TestEventStatistics:
    """Test EventStatistics model"""

    def test_event_statistics_creation(self):
        """Test creating event statistics"""
        now = datetime.utcnow()

        stats = EventStatistics(
            total_events=1000,
            pending_events=50,
            processed_events=900,
            failed_events=50,
            events_by_source={
                "frontend": 400,
                "backend": 500,
                "system": 100,
            },
            events_by_category={
                "user_action": 300,
                "user_lifecycle": 200,
                "payment": 150,
            },
            events_by_type={
                "user.login": 200,
                "user.registered": 100,
            },
            events_today=150,
            events_this_week=800,
            events_this_month=1000,
            average_processing_time=1.5,
            processing_rate=90.0,
            error_rate=5.0,
            top_users=[
                {"user_id": "user_1", "event_count": 50},
                {"user_id": "user_2", "event_count": 45},
            ],
            top_event_types=[
                {"event_type": "user.login", "count": 200},
                {"event_type": "page.view", "count": 180},
            ],
            calculated_at=now,
        )

        assert stats.total_events == 1000
        assert stats.pending_events == 50
        assert stats.processed_events == 900
        assert stats.failed_events == 50
        assert stats.events_by_source["frontend"] == 400
        assert stats.events_by_category["user_action"] == 300
        assert stats.events_today == 150
        assert stats.average_processing_time == 1.5
        assert stats.processing_rate == 90.0
        assert stats.error_rate == 5.0
        assert len(stats.top_users) == 2
        assert len(stats.top_event_types) == 2

    def test_event_statistics_defaults(self):
        """Test event statistics with default values"""
        stats = EventStatistics(
            total_events=0,
            pending_events=0,
            processed_events=0,
            failed_events=0,
        )

        assert stats.total_events == 0
        assert stats.events_by_source == {}
        assert stats.events_by_category == {}
        assert stats.events_by_type == {}
        assert stats.events_today == 0
        assert stats.events_this_week == 0
        assert stats.events_this_month == 0
        assert stats.average_processing_time == 0.0
        assert stats.processing_rate == 0.0
        assert stats.error_rate == 0.0
        assert stats.top_users == []
        assert stats.top_event_types == []


class TestEventProcessingResult:
    """Test EventProcessingResult model"""

    def test_processing_result_success(self):
        """Test successful processing result"""
        now = datetime.utcnow()

        result = EventProcessingResult(
            event_id="evt_123",
            processor_name="notification_processor",
            status=ProcessingStatus.SUCCESS,
            message="Notification sent successfully",
            processed_at=now,
            duration_ms=250,
        )

        assert result.event_id == "evt_123"
        assert result.processor_name == "notification_processor"
        assert result.status == ProcessingStatus.SUCCESS
        assert result.message == "Notification sent successfully"
        assert result.duration_ms == 250

    def test_processing_result_failed(self):
        """Test failed processing result"""
        now = datetime.utcnow()

        result = EventProcessingResult(
            event_id="evt_456",
            processor_name="payment_processor",
            status=ProcessingStatus.FAILED,
            message="Payment gateway timeout",
            processed_at=now,
            duration_ms=5000,
        )

        assert result.event_id == "evt_456"
        assert result.processor_name == "payment_processor"
        assert result.status == ProcessingStatus.FAILED
        assert result.message == "Payment gateway timeout"
        assert result.duration_ms == 5000

    def test_processing_result_skipped(self):
        """Test skipped processing result"""
        result = EventProcessingResult(
            event_id="evt_789",
            processor_name="analytics_processor",
            status=ProcessingStatus.SKIPPED,
        )

        assert result.status == ProcessingStatus.SKIPPED
        assert result.message is None
        assert result.duration_ms is None

    def test_processing_result_retry(self):
        """Test retry processing result"""
        result = EventProcessingResult(
            event_id="evt_retry",
            processor_name="webhook_processor",
            status=ProcessingStatus.RETRY,
            message="Connection timeout, will retry",
        )

        assert result.status == ProcessingStatus.RETRY
        assert result.message == "Connection timeout, will retry"


class TestEventReplayRequest:
    """Test EventReplayRequest model"""

    def test_replay_request_by_stream(self):
        """Test replay request by stream ID"""
        request = EventReplayRequest(
            stream_id="stream_123",
            target_service="notification_service",
            dry_run=False,
        )

        assert request.stream_id == "stream_123"
        assert request.target_service == "notification_service"
        assert request.dry_run is False

    def test_replay_request_by_event_ids(self):
        """Test replay request by event IDs"""
        request = EventReplayRequest(
            event_ids=["evt_1", "evt_2", "evt_3"],
            target_service="analytics_service",
        )

        assert len(request.event_ids) == 3
        assert "evt_1" in request.event_ids
        assert request.dry_run is False

    def test_replay_request_by_time_range(self):
        """Test replay request by time range"""
        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()

        request = EventReplayRequest(
            start_time=start,
            end_time=end,
            target_service="billing_service",
            dry_run=True,
        )

        assert request.start_time == start
        assert request.end_time == end
        assert request.dry_run is True

    def test_replay_request_defaults(self):
        """Test replay request with defaults"""
        request = EventReplayRequest()

        assert request.stream_id is None
        assert request.event_ids is None
        assert request.start_time is None
        assert request.end_time is None
        assert request.target_service is None
        assert request.dry_run is False


class TestEventProjection:
    """Test EventProjection model"""

    def test_event_projection_creation(self):
        """Test creating event projection"""
        now = datetime.utcnow()

        projection = EventProjection(
            projection_id="proj_123",
            projection_name="user_profile",
            entity_id="user_456",
            entity_type="user",
            state={
                "name": "John Doe",
                "email": "john@example.com",
                "total_orders": 5,
            },
            version=3,
            last_event_id="evt_789",
            created_at=now,
            updated_at=now,
        )

        assert projection.projection_id == "proj_123"
        assert projection.projection_name == "user_profile"
        assert projection.entity_id == "user_456"
        assert projection.entity_type == "user"
        assert projection.state["name"] == "John Doe"
        assert projection.version == 3
        assert projection.last_event_id == "evt_789"

    def test_event_projection_defaults(self):
        """Test event projection with defaults"""
        projection = EventProjection(
            projection_name="order_summary",
            entity_id="order_123",
            entity_type="order",
        )

        # Auto-generated projection_id
        assert projection.projection_id is not None
        assert len(projection.projection_id) > 0
        assert projection.projection_name == "order_summary"
        assert projection.state == {}
        assert projection.version == 0
        assert projection.last_event_id is None

    def test_event_projection_state_update(self):
        """Test updating projection state"""
        projection = EventProjection(
            projection_name="cart_state",
            entity_id="cart_123",
            entity_type="cart",
            state={"items": [], "total": 0.0},
            version=0,
        )

        # Simulate state update
        projection.state = {"items": [{"id": "item_1"}], "total": 29.99}
        projection.version = 1
        projection.last_event_id = "evt_add_item"

        assert len(projection.state["items"]) == 1
        assert projection.state["total"] == 29.99
        assert projection.version == 1
        assert projection.last_event_id == "evt_add_item"


class TestEventProcessor:
    """Test EventProcessor model"""

    def test_event_processor_creation(self):
        """Test creating event processor"""
        now = datetime.utcnow()

        processor = EventProcessor(
            processor_id="proc_123",
            processor_name="notification_processor",
            processor_type="async",
            enabled=True,
            priority=10,
            filters={"event_category": "user_lifecycle"},
            config={"smtp_host": "smtp.example.com"},
            error_count=0,
            last_error=None,
            last_processed_at=now,
        )

        assert processor.processor_id == "proc_123"
        assert processor.processor_name == "notification_processor"
        assert processor.processor_type == "async"
        assert processor.enabled is True
        assert processor.priority == 10
        assert processor.filters["event_category"] == "user_lifecycle"
        assert processor.config["smtp_host"] == "smtp.example.com"

    def test_event_processor_defaults(self):
        """Test event processor with defaults"""
        processor = EventProcessor(
            processor_name="analytics_processor",
            processor_type="sync",
        )

        # Auto-generated processor_id
        assert processor.processor_id is not None
        assert len(processor.processor_id) > 0
        assert processor.enabled is True
        assert processor.priority == 0
        assert processor.filters == {}
        assert processor.config == {}
        assert processor.error_count == 0
        assert processor.last_error is None
        assert processor.last_processed_at is None

    def test_event_processor_with_errors(self):
        """Test event processor with error tracking"""
        now = datetime.utcnow()

        processor = EventProcessor(
            processor_name="webhook_processor",
            processor_type="webhook",
            enabled=True,
            error_count=5,
            last_error="Connection timeout",
            last_processed_at=now,
        )

        assert processor.error_count == 5
        assert processor.last_error == "Connection timeout"
        assert processor.last_processed_at == now

    def test_event_processor_disabled(self):
        """Test disabled event processor"""
        processor = EventProcessor(
            processor_name="disabled_processor",
            processor_type="custom",
            enabled=False,
        )

        assert processor.enabled is False


class TestEventSubscription:
    """Test EventSubscription model"""

    def test_event_subscription_creation(self):
        """Test creating event subscription"""
        now = datetime.utcnow()

        subscription = EventSubscription(
            subscription_id="sub_123",
            subscriber_name="notification_service",
            subscriber_type="microservice",
            event_types=["user.registered", "user.login"],
            event_sources=[EventSource.FRONTEND, EventSource.BACKEND],
            event_categories=[EventCategory.USER_LIFECYCLE, EventCategory.USER_ACTION],
            callback_url="https://notification.example.com/events",
            webhook_secret="secret_xyz",
            enabled=True,
            retry_policy={
                "max_retries": 3,
                "backoff_multiplier": 2,
                "initial_delay": 1000,
            },
            created_at=now,
            updated_at=now,
        )

        assert subscription.subscription_id == "sub_123"
        assert subscription.subscriber_name == "notification_service"
        assert len(subscription.event_types) == 2
        assert "user.registered" in subscription.event_types
        assert EventSource.FRONTEND in subscription.event_sources
        assert EventCategory.USER_LIFECYCLE in subscription.event_categories
        assert subscription.callback_url == "https://notification.example.com/events"
        assert subscription.enabled is True
        assert subscription.retry_policy["max_retries"] == 3

    def test_event_subscription_minimal(self):
        """Test minimal event subscription"""
        subscription = EventSubscription(
            event_types=["order.created"],
        )

        # Auto-generated subscription_id
        assert subscription.subscription_id is not None
        assert len(subscription.subscription_id) > 0
        assert subscription.subscriber_name == "default_subscriber"
        assert subscription.subscriber_type == "service"
        assert len(subscription.event_types) == 1
        assert subscription.event_sources is None
        assert subscription.event_categories is None
        assert subscription.callback_url is None
        assert subscription.enabled is True
        assert subscription.retry_policy == {}

    def test_event_subscription_webhook(self):
        """Test webhook event subscription"""
        subscription = EventSubscription(
            subscriber_name="external_webhook",
            subscriber_type="webhook",
            event_types=["payment.completed", "payment.failed"],
            callback_url="https://external.example.com/webhook",
            webhook_secret="webhook_secret_abc",
            retry_policy={"max_retries": 5},
        )

        assert subscription.subscriber_type == "webhook"
        assert subscription.callback_url == "https://external.example.com/webhook"
        assert subscription.webhook_secret == "webhook_secret_abc"
        assert subscription.retry_policy["max_retries"] == 5

    def test_event_subscription_disabled(self):
        """Test disabled event subscription"""
        subscription = EventSubscription(
            event_types=["test.event"],
            enabled=False,
        )

        assert subscription.enabled is False

    def test_event_subscription_with_filters(self):
        """Test event subscription with specific filters"""
        subscription = EventSubscription(
            subscriber_name="analytics_service",
            event_types=["user.action"],
            event_sources=[EventSource.FRONTEND],
            event_categories=[EventCategory.USER_ACTION, EventCategory.CLICK],
        )

        assert len(subscription.event_sources) == 1
        assert EventSource.FRONTEND in subscription.event_sources
        assert len(subscription.event_categories) == 2
        assert EventCategory.USER_ACTION in subscription.event_categories
        assert EventCategory.CLICK in subscription.event_categories


if __name__ == "__main__":
    pytest.main([__file__])
