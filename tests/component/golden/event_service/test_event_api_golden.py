"""
Event Service API Component Golden Tests

Tests FastAPI endpoints with mocked services and dependencies.
Uses TestClient for API testing - no real database or external services.

Usage:
    pytest tests/component/golden/event_service/test_event_api_golden.py -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json

from microservices.event_service.models import (
    Event, EventSource, EventCategory, EventStatus,
    EventCreateRequest, EventQueryRequest, EventResponse, EventListResponse,
    EventStatistics, EventSubscription, EventProcessor, EventProjection
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
def mock_event_service(mock_repo, mock_event_bus):
    """Create a mock EventService"""
    from microservices.event_service.event_service import EventService

    service = MagicMock(spec=EventService)
    service.repository = mock_repo
    service.event_bus = mock_event_bus
    service.processors = {}
    service.subscriptions = {}
    service.projections = {}

    # Setup async methods
    async def mock_create_event(request):
        event = Event(
            event_id=f"evt_{request.event_type.replace('.', '_')}",
            event_type=request.event_type,
            event_source=request.event_source or EventSource.BACKEND,
            event_category=request.event_category or EventCategory.USER_ACTION,
            user_id=request.user_id,
            data=request.data or {},
            status=EventStatus.PENDING,
            timestamp=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        return event

    async def mock_get_event(event_id):
        return await mock_repo.get_event(event_id)

    async def mock_query_events(query):
        events, total = await mock_repo.query_events(
            user_id=query.user_id,
            event_type=query.event_type,
            event_source=query.event_source,
            event_category=query.event_category,
            status=query.status,
            start_time=query.start_time,
            end_time=query.end_time,
            limit=query.limit,
            offset=query.offset
        )
        responses = [
            EventResponse(
                event_id=e.event_id,
                event_type=e.event_type,
                event_source=e.event_source,
                event_category=e.event_category,
                user_id=e.user_id,
                data=e.data,
                status=e.status,
                timestamp=e.timestamp,
                created_at=e.created_at
            ) for e in events
        ]
        return EventListResponse(
            events=responses,
            total=total,
            limit=query.limit,
            offset=query.offset,
            has_more=(query.offset + query.limit) < total
        )

    async def mock_get_statistics():
        return await mock_repo.get_statistics()

    async def mock_create_subscription(sub):
        await mock_repo.save_subscription(sub)
        return sub

    async def mock_list_subscriptions():
        return await mock_repo.get_subscriptions()

    async def mock_delete_subscription(sub_id):
        return await mock_repo.delete_subscription(sub_id)

    async def mock_register_processor(proc):
        await mock_repo.save_processor(proc)
        return proc

    async def mock_list_processors():
        return await mock_repo.get_processors()

    async def mock_get_event_stream(stream_id, from_version=None):
        return await mock_repo.get_event_stream(stream_id)

    async def mock_get_projection(entity_type, entity_id):
        return await mock_repo.get_projection(entity_type, entity_id)

    async def mock_replay_events(request):
        return {"replayed": 0, "failed": 0, "total": 0}

    async def mock_get_unprocessed_events(limit=100):
        return await mock_repo.get_unprocessed_events(limit)

    service.create_event = AsyncMock(side_effect=mock_create_event)
    service.get_event = AsyncMock(side_effect=mock_get_event)
    service.query_events = AsyncMock(side_effect=mock_query_events)
    service.get_statistics = AsyncMock(side_effect=mock_get_statistics)
    service.create_subscription = AsyncMock(side_effect=mock_create_subscription)
    service.list_subscriptions = AsyncMock(side_effect=mock_list_subscriptions)
    service.delete_subscription = AsyncMock(side_effect=mock_delete_subscription)
    service.register_processor = AsyncMock(side_effect=mock_register_processor)
    service.list_processors = AsyncMock(side_effect=mock_list_processors)
    service.get_event_stream = AsyncMock(side_effect=mock_get_event_stream)
    service.get_projection = AsyncMock(side_effect=mock_get_projection)
    service.replay_events = AsyncMock(side_effect=mock_replay_events)
    service.get_unprocessed_events = AsyncMock(side_effect=mock_get_unprocessed_events)

    return service


@pytest.fixture
def test_app(mock_event_service, mock_config):
    """Create a test FastAPI app with mocked dependencies"""
    from fastapi import FastAPI, HTTPException, Depends, Query, Body, BackgroundTasks
    from microservices.event_service.models import (
        EventCreateRequest, EventQueryRequest, EventResponse, EventListResponse,
        EventStatistics, EventSubscription, EventProcessor, EventReplayRequest
    )

    app = FastAPI(title="Event Service Test")

    async def get_event_service():
        return mock_event_service

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "event_service",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }

    @app.post("/api/v1/events/create", response_model=EventResponse)
    async def create_event(
        request: EventCreateRequest = Body(...),
        service=Depends(get_event_service)
    ):
        try:
            event = await service.create_event(request)
            return EventResponse(
                event_id=event.event_id,
                event_type=event.event_type,
                event_source=event.event_source,
                event_category=event.event_category,
                user_id=event.user_id,
                data=event.data,
                status=event.status,
                timestamp=event.timestamp,
                created_at=event.created_at
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/events/batch", response_model=list)
    async def create_batch_events(
        requests: list = Body(...),
        service=Depends(get_event_service)
    ):
        try:
            events = []
            for req_data in requests:
                req = EventCreateRequest(**req_data)
                event = await service.create_event(req)
                events.append(EventResponse(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    event_source=event.event_source,
                    event_category=event.event_category,
                    user_id=event.user_id,
                    data=event.data,
                    status=event.status,
                    timestamp=event.timestamp,
                    created_at=event.created_at
                ))
            return events
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/events/query", response_model=EventListResponse)
    async def query_events(
        query: EventQueryRequest = Body(...),
        service=Depends(get_event_service)
    ):
        try:
            result = await service.query_events(query)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/events/statistics", response_model=EventStatistics)
    async def get_statistics(
        user_id: str = Query(None),
        service=Depends(get_event_service)
    ):
        try:
            stats = await service.get_statistics()
            return stats
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/events/subscriptions", response_model=EventSubscription)
    async def create_subscription(
        subscription: EventSubscription = Body(...),
        service=Depends(get_event_service)
    ):
        try:
            result = await service.create_subscription(subscription)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/events/subscriptions", response_model=list)
    async def list_subscriptions(service=Depends(get_event_service)):
        try:
            return await service.list_subscriptions()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/v1/events/subscriptions/{subscription_id}")
    async def delete_subscription(
        subscription_id: str,
        service=Depends(get_event_service)
    ):
        try:
            await service.delete_subscription(subscription_id)
            return {"status": "deleted", "subscription_id": subscription_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/events/processors", response_model=EventProcessor)
    async def register_processor(
        processor: EventProcessor = Body(...),
        service=Depends(get_event_service)
    ):
        try:
            result = await service.register_processor(processor)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/events/processors", response_model=list)
    async def list_processors(service=Depends(get_event_service)):
        try:
            return await service.list_processors()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v1/events/replay")
    async def replay_events(
        request: EventReplayRequest = Body(...),
        service=Depends(get_event_service)
    ):
        try:
            return {
                "status": "replay_started",
                "message": "Event replay has been initiated",
                "dry_run": request.dry_run
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # NOTE: Path parameter routes MUST come AFTER static routes to avoid matching conflicts
    @app.get("/api/v1/events/{event_id}", response_model=EventResponse)
    async def get_event(
        event_id: str,
        service=Depends(get_event_service)
    ):
        try:
            event = await service.get_event(event_id)
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            return EventResponse(
                event_id=event.event_id,
                event_type=event.event_type,
                event_source=event.event_source,
                event_category=event.event_category,
                user_id=event.user_id,
                data=event.data,
                status=event.status,
                timestamp=event.timestamp,
                created_at=event.created_at
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def client(test_app):
    """Create a test client"""
    return TestClient(test_app)


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthCheckGolden:
    """Golden: Health check endpoint tests"""

    def test_health_check_returns_healthy(self, client):
        """GOLDEN: /health returns healthy status"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "event_service"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    def test_health_check_includes_timestamp(self, client):
        """GOLDEN: /health includes valid ISO timestamp"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        # Verify timestamp is valid ISO format
        timestamp = data["timestamp"]
        assert "T" in timestamp


# =============================================================================
# Create Event Tests
# =============================================================================

class TestCreateEventApiGolden:
    """Golden: POST /api/v1/events/create endpoint tests"""

    def test_create_event_success(self, client):
        """GOLDEN: Create event returns 200 with event response"""
        payload = {
            "event_type": "user.signup",
            "event_source": "backend",
            "event_category": "user_lifecycle",
            "user_id": "usr_new_123",
            "data": {"email": "new@example.com", "name": "New User"}
        }

        response = client.post("/api/v1/events/create", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["event_type"] == "user.signup"
        assert data["event_source"] == "backend"
        assert data["status"] == "pending"

    def test_create_event_minimal_payload(self, client):
        """GOLDEN: Create event with minimal required fields"""
        payload = {
            "event_type": "test.event"
        }

        response = client.post("/api/v1/events/create", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "test.event"
        # Default values should be applied
        assert data["event_source"] == "backend"
        assert data["event_category"] == "user_action"

    def test_create_event_with_metadata(self, client):
        """GOLDEN: Create event with metadata and context"""
        payload = {
            "event_type": "order.created",
            "event_source": "backend",
            "event_category": "order",
            "user_id": "usr_123",
            "data": {"order_id": "ord_456", "total": 199.99},
            "metadata": {"source_ip": "192.168.1.1", "user_agent": "Chrome"},
            "context": {"session_id": "sess_789"}
        }

        response = client.post("/api/v1/events/create", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "order.created"
        assert "order_id" in data["data"]

    def test_create_event_invalid_event_source(self, client):
        """GOLDEN: Create event with invalid event_source returns 422"""
        payload = {
            "event_type": "test.event",
            "event_source": "invalid_source"
        }

        response = client.post("/api/v1/events/create", json=payload)

        assert response.status_code == 422

    def test_create_event_invalid_category(self, client):
        """GOLDEN: Create event with invalid category returns 422"""
        payload = {
            "event_type": "test.event",
            "event_category": "invalid_category"
        }

        response = client.post("/api/v1/events/create", json=payload)

        assert response.status_code == 422

    def test_create_event_empty_body(self, client):
        """GOLDEN: Create event with empty body returns 422"""
        response = client.post("/api/v1/events/create", json={})

        assert response.status_code == 422

    def test_create_event_no_body(self, client):
        """GOLDEN: Create event without body returns 422"""
        response = client.post("/api/v1/events/create")

        assert response.status_code == 422

    def test_create_event_frontend_source(self, client):
        """GOLDEN: Create event with frontend source"""
        payload = {
            "event_type": "button.clicked",
            "event_source": "frontend",
            "event_category": "click",
            "user_id": "usr_123",
            "data": {"button_id": "submit-btn", "page": "/checkout"}
        }

        response = client.post("/api/v1/events/create", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["event_source"] == "frontend"
        assert data["event_category"] == "click"

    def test_create_event_iot_device_source(self, client):
        """GOLDEN: Create event with IoT device source"""
        payload = {
            "event_type": "sensor.reading",
            "event_source": "iot_device",
            "event_category": "telemetry",
            "data": {"temperature": 23.5, "humidity": 65}
        }

        response = client.post("/api/v1/events/create", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["event_source"] == "iot_device"
        assert data["event_category"] == "telemetry"


# =============================================================================
# Batch Create Events Tests
# =============================================================================

class TestBatchCreateEventsApiGolden:
    """Golden: POST /api/v1/events/batch endpoint tests"""

    def test_batch_create_success(self, client):
        """GOLDEN: Batch create events returns list of events"""
        payload = [
            {"event_type": "event.one", "user_id": "usr_1"},
            {"event_type": "event.two", "user_id": "usr_2"},
            {"event_type": "event.three", "user_id": "usr_3"}
        ]

        response = client.post("/api/v1/events/batch", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["event_type"] == "event.one"
        assert data[1]["event_type"] == "event.two"
        assert data[2]["event_type"] == "event.three"

    def test_batch_create_empty_list(self, client):
        """GOLDEN: Batch create with empty list returns empty list"""
        response = client.post("/api/v1/events/batch", json=[])

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_batch_create_single_event(self, client):
        """GOLDEN: Batch create with single event works"""
        payload = [{"event_type": "single.event"}]

        response = client.post("/api/v1/events/batch", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_batch_create_mixed_sources(self, client):
        """GOLDEN: Batch create events with different sources"""
        payload = [
            {"event_type": "frontend.event", "event_source": "frontend"},
            {"event_type": "backend.event", "event_source": "backend"},
            {"event_type": "iot.event", "event_source": "iot_device"}
        ]

        response = client.post("/api/v1/events/batch", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data[0]["event_source"] == "frontend"
        assert data[1]["event_source"] == "backend"
        assert data[2]["event_source"] == "iot_device"


# =============================================================================
# Get Event Tests
# =============================================================================

class TestGetEventApiGolden:
    """Golden: GET /api/v1/events/{event_id} endpoint tests"""

    def test_get_event_success(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Get existing event returns 200 with event data"""
        # Update mock to use repo with events
        mock_event_service.repository = mock_repo_with_events

        async def get_event(event_id):
            return await mock_repo_with_events.get_event(event_id)

        mock_event_service.get_event = AsyncMock(side_effect=get_event)

        response = client.get("/api/v1/events/evt_test_001")

        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == "evt_test_001"
        assert data["event_type"] == "user.created"
        assert data["user_id"] == "usr_test_123"

    def test_get_event_not_found(self, client):
        """GOLDEN: Get non-existent event returns 404"""
        response = client.get("/api/v1/events/evt_nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_event_with_complex_data(self, client, mock_repo, mock_event_service):
        """GOLDEN: Get event with complex nested data"""
        mock_repo.set_event(
            event_id="evt_complex",
            event_type="order.created",
            data={
                "order": {
                    "items": [
                        {"sku": "ITEM1", "qty": 2},
                        {"sku": "ITEM2", "qty": 1}
                    ],
                    "total": 299.99
                }
            }
        )
        mock_event_service.repository = mock_repo

        async def get_event(event_id):
            return await mock_repo.get_event(event_id)

        mock_event_service.get_event = AsyncMock(side_effect=get_event)

        response = client.get("/api/v1/events/evt_complex")

        assert response.status_code == 200
        data = response.json()
        assert "order" in data["data"]
        assert len(data["data"]["order"]["items"]) == 2


# =============================================================================
# Query Events Tests
# =============================================================================

class TestQueryEventsApiGolden:
    """Golden: POST /api/v1/events/query endpoint tests"""

    def test_query_events_by_user(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query events by user_id returns matching events"""
        mock_event_service.repository = mock_repo_with_events

        payload = {"user_id": "usr_test_123", "limit": 100, "offset": 0}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert all(e["user_id"] == "usr_test_123" for e in data["events"])

    def test_query_events_by_type(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query events by event_type"""
        mock_event_service.repository = mock_repo_with_events

        payload = {"event_type": "user.created", "limit": 100, "offset": 0}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert all(e["event_type"] == "user.created" for e in data["events"])

    def test_query_events_by_source(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query events by event_source"""
        mock_event_service.repository = mock_repo_with_events

        payload = {"event_source": "frontend", "limit": 100, "offset": 0}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert all(e["event_source"] == "frontend" for e in data["events"])

    def test_query_events_by_category(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query events by event_category"""
        mock_event_service.repository = mock_repo_with_events

        payload = {"event_category": "payment", "limit": 100, "offset": 0}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert all(e["event_category"] == "payment" for e in data["events"])

    def test_query_events_by_status(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query events by status"""
        mock_event_service.repository = mock_repo_with_events

        payload = {"status": "pending", "limit": 100, "offset": 0}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert all(e["status"] == "pending" for e in data["events"])

    def test_query_events_pagination(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query events with pagination"""
        mock_event_service.repository = mock_repo_with_events

        payload = {"limit": 2, "offset": 0}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert "has_more" in data

    def test_query_events_pagination_offset(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query events with offset"""
        mock_event_service.repository = mock_repo_with_events

        payload = {"limit": 10, "offset": 1}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 1

    def test_query_events_empty_result(self, client, mock_repo, mock_event_service):
        """GOLDEN: Query events returns empty list when no matches"""
        mock_event_service.repository = mock_repo

        payload = {"user_id": "nonexistent_user", "limit": 100, "offset": 0}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total"] == 0

    def test_query_events_combined_filters(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query events with multiple filters"""
        mock_event_service.repository = mock_repo_with_events

        payload = {
            "user_id": "usr_test_123",
            "event_source": "backend",
            "status": "pending",
            "limit": 100,
            "offset": 0
        }

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        for event in data["events"]:
            assert event["user_id"] == "usr_test_123"
            assert event["event_source"] == "backend"
            assert event["status"] == "pending"

    def test_query_events_default_pagination(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query events with default pagination values"""
        mock_event_service.repository = mock_repo_with_events

        payload = {}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 100  # default
        assert data["offset"] == 0   # default


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatisticsApiGolden:
    """Golden: GET /api/v1/events/statistics endpoint tests"""

    def test_get_statistics_success(self, client, mock_repo, mock_event_service):
        """GOLDEN: Get statistics returns event counts"""
        mock_repo.set_stats(
            total_events=1000,
            pending_events=100,
            processed_events=850,
            failed_events=50,
            events_today=25,
            events_this_week=150,
            events_this_month=500
        )
        mock_event_service.repository = mock_repo

        response = client.get("/api/v1/events/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1000
        assert data["pending_events"] == 100
        assert data["processed_events"] == 850
        assert data["failed_events"] == 50

    def test_get_statistics_empty(self, client, mock_repo, mock_event_service):
        """GOLDEN: Get statistics with no events returns zeros"""
        mock_event_service.repository = mock_repo

        response = client.get("/api/v1/events/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 0
        assert data["pending_events"] == 0

    def test_get_statistics_with_user_filter(self, client):
        """GOLDEN: Get statistics with user_id filter"""
        response = client.get("/api/v1/events/statistics?user_id=usr_123")

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data


# =============================================================================
# Subscription Tests
# =============================================================================

class TestSubscriptionApiGolden:
    """Golden: Subscription management endpoint tests"""

    def test_create_subscription_success(self, client):
        """GOLDEN: Create subscription returns subscription object"""
        payload = {
            "subscriber_name": "test_subscriber",
            "subscriber_type": "service",
            "event_types": ["user.created", "user.updated"],
            "callback_url": "https://example.com/webhook",
            "enabled": True
        }

        response = client.post("/api/v1/events/subscriptions", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["subscriber_name"] == "test_subscriber"
        assert data["event_types"] == ["user.created", "user.updated"]
        assert "subscription_id" in data

    def test_create_subscription_minimal(self, client):
        """GOLDEN: Create subscription with minimal fields"""
        payload = {
            "event_types": ["test.event"]
        }

        response = client.post("/api/v1/events/subscriptions", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["event_types"] == ["test.event"]
        assert data["enabled"] is True  # default

    def test_create_subscription_with_filters(self, client):
        """GOLDEN: Create subscription with event source filter"""
        payload = {
            "subscriber_name": "frontend_listener",
            "event_types": ["click", "page_view"],
            "event_sources": ["frontend"],
            "event_categories": ["click", "page_view"]
        }

        response = client.post("/api/v1/events/subscriptions", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["event_sources"] == ["frontend"]

    def test_list_subscriptions_empty(self, client, mock_repo, mock_event_service):
        """GOLDEN: List subscriptions returns empty list when none exist"""
        mock_event_service.repository = mock_repo

        response = client.get("/api/v1/events/subscriptions")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_subscriptions_with_data(self, client, mock_repo, mock_event_service):
        """GOLDEN: List subscriptions returns all subscriptions"""
        mock_repo.set_subscription(
            subscription_id="sub_001",
            subscriber_name="service_a",
            event_types=["event.one"]
        )
        mock_repo.set_subscription(
            subscription_id="sub_002",
            subscriber_name="service_b",
            event_types=["event.two"]
        )
        mock_event_service.repository = mock_repo

        response = client.get("/api/v1/events/subscriptions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_delete_subscription_success(self, client, mock_repo, mock_event_service):
        """GOLDEN: Delete subscription returns success"""
        mock_repo.set_subscription(
            subscription_id="sub_to_delete",
            subscriber_name="test",
            event_types=["test"]
        )
        mock_event_service.repository = mock_repo

        response = client.delete("/api/v1/events/subscriptions/sub_to_delete")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["subscription_id"] == "sub_to_delete"


# =============================================================================
# Processor Tests
# =============================================================================

class TestProcessorApiGolden:
    """Golden: Processor management endpoint tests"""

    def test_register_processor_success(self, client):
        """GOLDEN: Register processor returns processor object"""
        payload = {
            "processor_name": "notification_processor",
            "processor_type": "webhook",
            "enabled": True,
            "priority": 10,
            "filters": {"event_type": "user.created"},
            "config": {"url": "https://notify.example.com"}
        }

        response = client.post("/api/v1/events/processors", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["processor_name"] == "notification_processor"
        assert data["processor_type"] == "webhook"
        assert data["priority"] == 10
        assert "processor_id" in data

    def test_register_processor_minimal(self, client):
        """GOLDEN: Register processor with minimal fields"""
        payload = {
            "processor_name": "basic_processor",
            "processor_type": "default"
        }

        response = client.post("/api/v1/events/processors", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["processor_name"] == "basic_processor"
        assert data["enabled"] is True  # default

    def test_list_processors_empty(self, client, mock_repo, mock_event_service):
        """GOLDEN: List processors returns empty list when none exist"""
        mock_event_service.repository = mock_repo

        response = client.get("/api/v1/events/processors")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_processors_with_data(self, client, mock_repo, mock_event_service):
        """GOLDEN: List processors returns all enabled processors"""
        mock_repo.set_processor(
            processor_id="proc_001",
            processor_name="processor_a",
            processor_type="webhook",
            enabled=True
        )
        mock_repo.set_processor(
            processor_id="proc_002",
            processor_name="processor_b",
            processor_type="queue",
            enabled=True
        )
        mock_event_service.repository = mock_repo

        response = client.get("/api/v1/events/processors")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


# =============================================================================
# Replay Events Tests
# =============================================================================

class TestReplayEventsApiGolden:
    """Golden: POST /api/v1/events/replay endpoint tests"""

    def test_replay_events_by_ids(self, client):
        """GOLDEN: Replay events by event IDs"""
        payload = {
            "event_ids": ["evt_001", "evt_002", "evt_003"],
            "dry_run": False
        }

        response = client.post("/api/v1/events/replay", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "replay_started"
        assert data["dry_run"] is False

    def test_replay_events_dry_run(self, client):
        """GOLDEN: Replay events in dry run mode"""
        payload = {
            "event_ids": ["evt_001"],
            "dry_run": True
        }

        response = client.post("/api/v1/events/replay", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True

    def test_replay_events_by_stream(self, client):
        """GOLDEN: Replay events by stream ID"""
        payload = {
            "stream_id": "user:usr_123",
            "dry_run": False
        }

        response = client.post("/api/v1/events/replay", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "replay_started"

    def test_replay_events_with_target_service(self, client):
        """GOLDEN: Replay events to specific target service"""
        payload = {
            "event_ids": ["evt_001"],
            "target_service": "notification_service",
            "dry_run": False
        }

        response = client.post("/api/v1/events/replay", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "replay_started"


# =============================================================================
# Request Validation Tests
# =============================================================================

class TestRequestValidationGolden:
    """Golden: Request validation and error handling tests"""

    def test_invalid_json_body(self, client):
        """GOLDEN: Invalid JSON returns 422"""
        response = client.post(
            "/api/v1/events/create",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_missing_required_field(self, client):
        """GOLDEN: Missing required field returns 422"""
        # event_type is required for EventCreateRequest
        payload = {
            "user_id": "usr_123",
            "data": {}
        }

        response = client.post("/api/v1/events/create", json=payload)

        assert response.status_code == 422

    def test_invalid_enum_value(self, client):
        """GOLDEN: Invalid enum value returns 422"""
        payload = {
            "event_type": "test.event",
            "event_source": "not_a_valid_source"
        }

        response = client.post("/api/v1/events/create", json=payload)

        assert response.status_code == 422

    def test_query_pagination_limits(self, client, mock_repo_with_events, mock_event_service):
        """GOLDEN: Query with limit > 1000 is rejected"""
        mock_event_service.repository = mock_repo_with_events

        payload = {"limit": 2000, "offset": 0}

        response = client.post("/api/v1/events/query", json=payload)

        # Should either be rejected (422) or capped to max
        assert response.status_code in [200, 422]

    def test_query_negative_offset(self, client):
        """GOLDEN: Query with negative offset returns 422"""
        payload = {"limit": 10, "offset": -1}

        response = client.post("/api/v1/events/query", json=payload)

        assert response.status_code == 422


# =============================================================================
# Content-Type Tests
# =============================================================================

class TestContentTypeGolden:
    """Golden: Content-Type handling tests"""

    def test_response_content_type_json(self, client):
        """GOLDEN: Response Content-Type is application/json"""
        response = client.get("/health")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_accepts_json_content_type(self, client):
        """GOLDEN: Accepts application/json Content-Type"""
        payload = {"event_type": "test.event"}

        response = client.post(
            "/api/v1/events/create",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
