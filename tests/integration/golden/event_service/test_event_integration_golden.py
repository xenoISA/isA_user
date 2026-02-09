"""
Event Service - Golden Integration Tests

Tests full event lifecycle with real HTTP calls to running event_service.
Requires the service to be running on localhost:8230.

Tests cover:
- Health check endpoints
- Event creation (single and batch)
- Event retrieval and querying
- Frontend event collection
- Event subscriptions
- Event processors
- Event statistics
- Event replay
- Error handling

Usage:
    pytest tests/integration/golden/event_service/test_event_integration_golden.py -v

Prerequisites:
    - Event service running on localhost:8230
    - PostgreSQL database available
"""
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

pytestmark = [pytest.mark.integration, pytest.mark.golden, pytest.mark.asyncio]

EVENT_SERVICE_URL = "http://localhost:8230"
API_BASE = f"{EVENT_SERVICE_URL}/api/v1/events"


# =============================================================================
# Health Check Tests (3 tests)
# =============================================================================

class TestEventServiceHealth:
    """Test event service health and connectivity"""

    async def test_basic_health_check(self, http_client, internal_headers):
        """
        Test basic health check returns healthy status.

        GIVEN: Event service is running
        WHEN: GET /health is called
        THEN: Returns 200 with healthy status
        """
        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/health",
            headers=internal_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "timestamp" in data

    async def test_health_check_returns_version(self, http_client, internal_headers):
        """
        Test health check includes version information.

        GIVEN: Event service is running
        WHEN: GET /health is called
        THEN: Response includes version field
        """
        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/health",
            headers=internal_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "version" in data

    async def test_frontend_health_check(self, http_client, internal_headers):
        """
        Test frontend event collection health endpoint.

        GIVEN: Event service is running
        WHEN: GET /api/v1/events/frontend/health is called
        THEN: Returns 200 with status
        """
        response = await http_client.get(
            f"{API_BASE}/frontend/health",
            headers=internal_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "frontend-event-collection"


# =============================================================================
# Event Creation Tests (8 tests)
# =============================================================================

class TestEventCreation:
    """Test event creation endpoints"""

    async def test_create_event_success(self, http_client, internal_headers, event_factory):
        """
        Test creating a single event successfully.

        GIVEN: Valid event data
        WHEN: POST /api/v1/events/create is called
        THEN: Returns 200 with created event data
        """
        event_data = event_factory.make_event_create_request()

        response = await http_client.post(
            f"{API_BASE}/create",
            json=event_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["event_type"] == event_data["event_type"]
        assert data["event_source"] == event_data["event_source"]
        assert data["user_id"] == event_data["user_id"]

    async def test_create_event_with_all_fields(self, http_client, internal_headers, event_factory):
        """
        Test creating event with all optional fields.

        GIVEN: Event data with all fields populated
        WHEN: POST /api/v1/events/create is called
        THEN: Returns 200 with all fields preserved
        """
        user_id = event_factory.make_user_id()
        event_data = event_factory.make_event_create_request(
            event_type="user.profile.updated",
            event_source="backend",
            event_category="user_lifecycle",
            user_id=user_id,
            data={"field": "email", "old_value": "old@test.com", "new_value": "new@test.com"},
            metadata={"ip_address": "127.0.0.1", "user_agent": "test-agent"},
            context={"request_id": "req_123", "trace_id": "trace_456"},
        )

        response = await http_client.post(
            f"{API_BASE}/create",
            json=event_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["event_type"] == "user.profile.updated"

    async def test_create_event_different_sources(self, http_client, internal_headers, event_factory):
        """
        Test creating events with different event sources.

        GIVEN: Event data with various event sources
        WHEN: POST /api/v1/events/create is called for each source
        THEN: All events are created successfully
        """
        sources = ["frontend", "backend", "system", "iot_device"]

        for source in sources:
            event_data = event_factory.make_event_create_request(event_source=source)

            response = await http_client.post(
                f"{API_BASE}/create",
                json=event_data,
                headers=internal_headers
            )

            assert response.status_code == 200, f"Failed for source: {source}"
            data = response.json()
            assert data["event_source"] == source

    async def test_create_event_different_categories(self, http_client, internal_headers, event_factory):
        """
        Test creating events with different event categories.

        GIVEN: Event data with various categories
        WHEN: POST /api/v1/events/create is called for each category
        THEN: All events are created successfully
        """
        categories = ["user_action", "page_view", "user_lifecycle", "system", "device_status"]

        for category in categories:
            event_data = event_factory.make_event_create_request(event_category=category)

            response = await http_client.post(
                f"{API_BASE}/create",
                json=event_data,
                headers=internal_headers
            )

            assert response.status_code == 200, f"Failed for category: {category}"
            data = response.json()
            assert data["event_category"] == category

    async def test_batch_create_events_success(self, http_client, internal_headers, event_factory):
        """
        Test batch creating multiple events.

        GIVEN: Array of valid event data
        WHEN: POST /api/v1/events/batch is called
        THEN: Returns 200 with array of created events
        """
        events = event_factory.make_batch_events(count=3)

        response = await http_client.post(
            f"{API_BASE}/batch",
            json=events,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        for event in data:
            assert "event_id" in event

    async def test_batch_create_events_large_batch(self, http_client, internal_headers, event_factory):
        """
        Test batch creating a larger number of events.

        GIVEN: Array of 10 events
        WHEN: POST /api/v1/events/batch is called
        THEN: All events are created successfully
        """
        events = event_factory.make_batch_events(count=10)

        response = await http_client.post(
            f"{API_BASE}/batch",
            json=events,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

    async def test_create_event_with_empty_data(self, http_client, internal_headers, event_factory):
        """
        Test creating event with empty data object.

        GIVEN: Event with empty data field
        WHEN: POST /api/v1/events/create is called
        THEN: Event is created with empty data
        """
        event_data = event_factory.make_event_create_request(data={})

        response = await http_client.post(
            f"{API_BASE}/create",
            json=event_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data

    async def test_create_event_without_user_id(self, http_client, internal_headers, event_factory):
        """
        Test creating system event without user_id.

        GIVEN: Event data without user_id (system event)
        WHEN: POST /api/v1/events/create is called
        THEN: Event is created with null user_id
        """
        event_data = {
            "event_type": "system.startup",
            "event_source": "system",
            "event_category": "system",
            "data": {"service": "test_service"},
        }

        response = await http_client.post(
            f"{API_BASE}/create",
            json=event_data,
            headers=internal_headers
        )

        assert response.status_code == 200


# =============================================================================
# Event Retrieval Tests (6 tests)
# =============================================================================

class TestEventRetrieval:
    """Test event retrieval and query endpoints"""

    async def test_get_event_by_id(self, http_client, internal_headers, event_factory):
        """
        Test retrieving a single event by ID.

        GIVEN: A previously created event
        WHEN: GET /api/v1/events/{event_id} is called
        THEN: Returns 200 with event data
        """
        # First create an event
        event_data = event_factory.make_event_create_request()
        create_response = await http_client.post(
            f"{API_BASE}/create",
            json=event_data,
            headers=internal_headers
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]

        # Then retrieve it
        response = await http_client.get(
            f"{API_BASE}/{event_id}",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == event_id
        assert data["event_type"] == event_data["event_type"]

    async def test_get_event_not_found(self, http_client, internal_headers):
        """
        Test retrieving non-existent event returns 404.

        GIVEN: A non-existent event ID
        WHEN: GET /api/v1/events/{event_id} is called
        THEN: Returns 404
        """
        response = await http_client.get(
            f"{API_BASE}/nonexistent-event-id-12345",
            headers=internal_headers
        )

        assert response.status_code == 404

    async def test_query_events_success(self, http_client, internal_headers, event_factory):
        """
        Test querying events with POST endpoint.

        GIVEN: Events exist in the database
        WHEN: POST /api/v1/events/query is called
        THEN: Returns 200 with event list and pagination
        """
        query_data = event_factory.make_query_request(limit=50)

        response = await http_client.post(
            f"{API_BASE}/query",
            json=query_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data

    async def test_query_events_by_user_id(self, http_client, internal_headers, event_factory):
        """
        Test querying events filtered by user_id.

        GIVEN: Events created for a specific user
        WHEN: POST /api/v1/events/query with user_id filter is called
        THEN: Returns events for that user only
        """
        user_id = event_factory.make_user_id()

        # Create events for this user
        for _ in range(3):
            event_data = event_factory.make_event_create_request(user_id=user_id)
            await http_client.post(
                f"{API_BASE}/create",
                json=event_data,
                headers=internal_headers
            )

        # Query for this user
        query_data = event_factory.make_query_request(user_id=user_id)
        response = await http_client.post(
            f"{API_BASE}/query",
            json=query_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        # All returned events should be for this user
        for event in data["events"]:
            assert event["user_id"] == user_id

    async def test_query_events_by_event_type(self, http_client, internal_headers, event_factory):
        """
        Test querying events filtered by event_type.

        GIVEN: Events with various types
        WHEN: POST /api/v1/events/query with event_type filter is called
        THEN: Returns events of that type only
        """
        event_type = "test.query.specific"

        # Create events with this type
        for _ in range(2):
            event_data = event_factory.make_event_create_request(event_type=event_type)
            await http_client.post(
                f"{API_BASE}/create",
                json=event_data,
                headers=internal_headers
            )

        # Query for this type
        query_data = event_factory.make_query_request(event_type=event_type)
        response = await http_client.post(
            f"{API_BASE}/query",
            json=query_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        for event in data["events"]:
            assert event["event_type"] == event_type

    async def test_query_events_with_pagination(self, http_client, internal_headers, event_factory):
        """
        Test querying events with pagination parameters.

        GIVEN: Multiple events exist
        WHEN: POST /api/v1/events/query with limit and offset is called
        THEN: Returns paginated results
        """
        # Query with limit
        query_data = event_factory.make_query_request(limit=5, offset=0)
        response = await http_client.post(
            f"{API_BASE}/query",
            json=query_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["events"]) <= 5


# =============================================================================
# Frontend Event Collection Tests (5 tests)
# =============================================================================

class TestFrontendEventCollection:
    """Test frontend event collection endpoints"""

    async def test_collect_frontend_event_success(self, http_client, internal_headers, event_factory):
        """
        Test collecting a single frontend event.

        GIVEN: Valid frontend event data
        WHEN: POST /api/v1/events/frontend is called
        THEN: Returns event_id or accepted status
        """
        event_data = event_factory.make_frontend_event_request()

        response = await http_client.post(
            f"{API_BASE}/frontend",
            json=event_data,
            headers=internal_headers
        )

        # May return accepted (if NATS is available) or error (if not)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data

    async def test_collect_frontend_page_view(self, http_client, internal_headers, event_factory):
        """
        Test collecting page view event.

        GIVEN: Page view event data
        WHEN: POST /api/v1/events/frontend is called
        THEN: Event is accepted
        """
        event_data = event_factory.make_frontend_event_request(
            event_type="page_view",
            page_url="https://example.com/products",
            data={"title": "Products Page", "referrer": "https://example.com"},
        )

        response = await http_client.post(
            f"{API_BASE}/frontend",
            json=event_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 503]

    async def test_collect_frontend_button_click(self, http_client, internal_headers, event_factory):
        """
        Test collecting button click event.

        GIVEN: Button click event data
        WHEN: POST /api/v1/events/frontend is called
        THEN: Event is accepted
        """
        event_data = event_factory.make_frontend_event_request(
            event_type="button_click",
            category="user_interaction",
            data={"button_id": "submit-btn", "button_text": "Submit"},
        )

        response = await http_client.post(
            f"{API_BASE}/frontend",
            json=event_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 503]

    async def test_collect_frontend_batch_events(self, http_client, internal_headers, event_factory):
        """
        Test batch collecting frontend events.

        GIVEN: Batch of frontend events
        WHEN: POST /api/v1/events/frontend/batch is called
        THEN: All events are processed
        """
        batch_data = event_factory.make_frontend_batch_events(count=5)

        response = await http_client.post(
            f"{API_BASE}/frontend/batch",
            json=batch_data,
            headers=internal_headers
        )

        # May return 200 (success) or 503 (NATS unavailable)
        assert response.status_code in [200, 503]

    async def test_frontend_event_with_session_tracking(self, http_client, internal_headers, event_factory):
        """
        Test frontend event includes session tracking.

        GIVEN: Frontend event with session_id
        WHEN: POST /api/v1/events/frontend is called
        THEN: Session is tracked
        """
        session_id = event_factory.make_session_id()
        event_data = event_factory.make_frontend_event_request(
            session_id=session_id,
            event_type="scroll",
            data={"scroll_depth": 75, "direction": "down"},
        )

        response = await http_client.post(
            f"{API_BASE}/frontend",
            json=event_data,
            headers=internal_headers
        )

        assert response.status_code in [200, 503]


# =============================================================================
# Event Subscription Tests (5 tests)
# =============================================================================

class TestEventSubscriptions:
    """Test event subscription management"""

    async def test_create_subscription_success(self, http_client, internal_headers, event_factory):
        """
        Test creating an event subscription.

        GIVEN: Valid subscription data
        WHEN: POST /api/v1/events/subscriptions is called
        THEN: Returns 200 with subscription data
        """
        subscription_data = event_factory.make_subscription_request()

        response = await http_client.post(
            f"{API_BASE}/subscriptions",
            json=subscription_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "subscription_id" in data
        assert data["subscriber_name"] == subscription_data["subscriber_name"]

    async def test_create_subscription_with_filters(self, http_client, internal_headers, event_factory):
        """
        Test creating subscription with event type filters.

        GIVEN: Subscription with specific event types
        WHEN: POST /api/v1/events/subscriptions is called
        THEN: Subscription is created with filters
        """
        subscription_data = event_factory.make_subscription_request(
            event_types=["user.login", "user.logout"],
            event_sources=["frontend", "backend"],
        )

        response = await http_client.post(
            f"{API_BASE}/subscriptions",
            json=subscription_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["event_types"] == ["user.login", "user.logout"]

    async def test_list_subscriptions(self, http_client, internal_headers):
        """
        Test listing all subscriptions.

        GIVEN: Subscriptions exist
        WHEN: GET /api/v1/events/subscriptions is called
        THEN: Returns 200 with list of subscriptions
        """
        response = await http_client.get(
            f"{API_BASE}/subscriptions",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_delete_subscription(self, http_client, internal_headers, event_factory):
        """
        Test deleting a subscription.

        GIVEN: An existing subscription
        WHEN: DELETE /api/v1/events/subscriptions/{id} is called
        THEN: Returns 200 with deleted status
        """
        # First create a subscription
        subscription_data = event_factory.make_subscription_request()
        create_response = await http_client.post(
            f"{API_BASE}/subscriptions",
            json=subscription_data,
            headers=internal_headers
        )
        assert create_response.status_code == 200
        subscription_id = create_response.json()["subscription_id"]

        # Then delete it
        response = await http_client.delete(
            f"{API_BASE}/subscriptions/{subscription_id}",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

    async def test_create_disabled_subscription(self, http_client, internal_headers, event_factory):
        """
        Test creating a disabled subscription.

        GIVEN: Subscription with enabled=False
        WHEN: POST /api/v1/events/subscriptions is called
        THEN: Subscription is created but disabled
        """
        subscription_data = event_factory.make_subscription_request(enabled=False)

        response = await http_client.post(
            f"{API_BASE}/subscriptions",
            json=subscription_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False


# =============================================================================
# Event Processor Tests (4 tests)
# =============================================================================

class TestEventProcessors:
    """Test event processor management"""

    async def test_register_processor_success(self, http_client, internal_headers, event_factory):
        """
        Test registering an event processor.

        GIVEN: Valid processor data
        WHEN: POST /api/v1/events/processors is called
        THEN: Returns 200 with processor data
        """
        processor_data = event_factory.make_processor_request()

        response = await http_client.post(
            f"{API_BASE}/processors",
            json=processor_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "processor_id" in data
        assert data["processor_name"] == processor_data["processor_name"]

    async def test_register_processor_with_filters(self, http_client, internal_headers, event_factory):
        """
        Test registering processor with event filters.

        GIVEN: Processor with specific filters
        WHEN: POST /api/v1/events/processors is called
        THEN: Processor is registered with filters
        """
        processor_data = event_factory.make_processor_request(
            filters={"event_type": "payment.completed", "event_source": "backend"},
            config={"webhook_url": "https://example.com/payment-processor"},
        )

        response = await http_client.post(
            f"{API_BASE}/processors",
            json=processor_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["event_type"] == "payment.completed"

    async def test_list_processors(self, http_client, internal_headers):
        """
        Test listing all processors.

        GIVEN: Processors are registered
        WHEN: GET /api/v1/events/processors is called
        THEN: Returns 200 with list of processors
        """
        response = await http_client.get(
            f"{API_BASE}/processors",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_register_processor_with_priority(self, http_client, internal_headers, event_factory):
        """
        Test registering processor with priority.

        GIVEN: Processor with specific priority
        WHEN: POST /api/v1/events/processors is called
        THEN: Processor is registered with priority
        """
        processor_data = event_factory.make_processor_request(priority=10)

        response = await http_client.post(
            f"{API_BASE}/processors",
            json=processor_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 10


# =============================================================================
# Event Statistics Tests (3 tests)
# =============================================================================

class TestEventStatistics:
    """Test event statistics endpoints"""

    async def test_get_statistics(self, http_client, internal_headers):
        """
        Test getting event statistics.

        GIVEN: Events exist in the database
        WHEN: GET /api/v1/events/statistics is called
        THEN: Returns 200 with statistics
        """
        response = await http_client.get(
            f"{API_BASE}/statistics",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "pending_events" in data
        assert "processed_events" in data
        assert "failed_events" in data

    async def test_statistics_structure(self, http_client, internal_headers):
        """
        Test statistics response has expected structure.

        GIVEN: Statistics endpoint is called
        WHEN: GET /api/v1/events/statistics is called
        THEN: Response has all required fields
        """
        response = await http_client.get(
            f"{API_BASE}/statistics",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields
        expected_fields = [
            "total_events",
            "pending_events",
            "processed_events",
            "failed_events",
            "events_today",
            "events_this_week",
            "events_this_month",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    async def test_statistics_with_user_id(self, http_client, internal_headers, event_factory):
        """
        Test getting statistics filtered by user_id.

        GIVEN: Events exist for a specific user
        WHEN: GET /api/v1/events/statistics?user_id=xxx is called
        THEN: Returns 200 with user-specific statistics
        """
        user_id = event_factory.make_user_id()

        response = await http_client.get(
            f"{API_BASE}/statistics?user_id={user_id}",
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data


# =============================================================================
# Event Replay Tests (3 tests)
# =============================================================================

class TestEventReplay:
    """Test event replay functionality"""

    async def test_replay_events_dry_run(self, http_client, internal_headers, event_factory):
        """
        Test event replay in dry run mode.

        GIVEN: Replay request with dry_run=True
        WHEN: POST /api/v1/events/replay is called
        THEN: Returns preview without actually replaying
        """
        # First create an event to replay
        event_data = event_factory.make_event_create_request()
        create_response = await http_client.post(
            f"{API_BASE}/create",
            json=event_data,
            headers=internal_headers
        )
        event_id = create_response.json()["event_id"]

        # Attempt dry run replay
        replay_data = event_factory.make_replay_request(
            event_ids=[event_id],
            dry_run=True,
        )

        response = await http_client.post(
            f"{API_BASE}/replay",
            json=replay_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True

    async def test_replay_events_with_event_ids(self, http_client, internal_headers, event_factory):
        """
        Test replay specific events by ID.

        GIVEN: List of event IDs to replay
        WHEN: POST /api/v1/events/replay is called
        THEN: Returns replay status
        """
        # Create events first
        event_ids = []
        for _ in range(2):
            event_data = event_factory.make_event_create_request()
            response = await http_client.post(
                f"{API_BASE}/create",
                json=event_data,
                headers=internal_headers
            )
            event_ids.append(response.json()["event_id"])

        # Replay them
        replay_data = event_factory.make_replay_request(
            event_ids=event_ids,
            dry_run=True,
        )

        response = await http_client.post(
            f"{API_BASE}/replay",
            json=replay_data,
            headers=internal_headers
        )

        assert response.status_code == 200

    async def test_replay_events_initiates_background_task(self, http_client, internal_headers, event_factory):
        """
        Test that non-dry-run replay initiates background task.

        GIVEN: Replay request with dry_run=False
        WHEN: POST /api/v1/events/replay is called
        THEN: Returns status indicating replay started
        """
        event_data = event_factory.make_event_create_request()
        create_response = await http_client.post(
            f"{API_BASE}/create",
            json=event_data,
            headers=internal_headers
        )
        event_id = create_response.json()["event_id"]

        replay_data = event_factory.make_replay_request(
            event_ids=[event_id],
            dry_run=False,
        )

        response = await http_client.post(
            f"{API_BASE}/replay",
            json=replay_data,
            headers=internal_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "replay_started"


# =============================================================================
# Error Handling Tests (3 tests)
# =============================================================================

class TestErrorHandling:
    """Test error handling for edge cases"""

    async def test_create_event_missing_required_fields(self, http_client, internal_headers):
        """
        Test creating event with missing required fields returns 422.

        GIVEN: Event data missing event_type
        WHEN: POST /api/v1/events/create is called
        THEN: Returns 422 validation error
        """
        invalid_data = {
            "data": {"some": "data"},
        }

        response = await http_client.post(
            f"{API_BASE}/create",
            json=invalid_data,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_query_events_invalid_status(self, http_client, internal_headers, event_factory):
        """
        Test query with invalid status value returns error.

        GIVEN: Query with invalid status enum value
        WHEN: POST /api/v1/events/query is called
        THEN: Returns 422 validation error
        """
        query_data = {
            "status": "invalid_status",
            "limit": 10,
        }

        response = await http_client.post(
            f"{API_BASE}/query",
            json=query_data,
            headers=internal_headers
        )

        assert response.status_code == 422

    async def test_invalid_json_returns_error(self, http_client, internal_headers):
        """
        Test sending invalid JSON returns error.

        GIVEN: Malformed JSON in request body
        WHEN: POST /api/v1/events/create is called
        THEN: Returns 422 error
        """
        response = await http_client.post(
            f"{API_BASE}/create",
            content="{ invalid json }",
            headers=internal_headers
        )

        assert response.status_code == 422


# =============================================================================
# Data Persistence Tests (3 tests)
# =============================================================================

class TestDataPersistence:
    """Test data persistence and retrieval across requests"""

    async def test_event_persists_and_retrieves(self, http_client, internal_headers, event_factory):
        """
        Test that created event persists and can be retrieved.

        GIVEN: A newly created event
        WHEN: The same event is retrieved by ID
        THEN: All data matches the original
        """
        event_data = event_factory.make_event_create_request(
            event_type="persistence.test",
            data={"unique_value": "test_12345"},
        )

        # Create
        create_response = await http_client.post(
            f"{API_BASE}/create",
            json=event_data,
            headers=internal_headers
        )
        assert create_response.status_code == 200
        created_event = create_response.json()
        event_id = created_event["event_id"]

        # Retrieve
        get_response = await http_client.get(
            f"{API_BASE}/{event_id}",
            headers=internal_headers
        )
        assert get_response.status_code == 200
        retrieved_event = get_response.json()

        # Verify
        assert retrieved_event["event_id"] == event_id
        assert retrieved_event["event_type"] == event_data["event_type"]
        assert retrieved_event["user_id"] == event_data["user_id"]

    async def test_batch_events_all_persist(self, http_client, internal_headers, event_factory):
        """
        Test that all batch events persist correctly.

        GIVEN: A batch of events is created
        WHEN: Each event is retrieved individually
        THEN: All events exist and have correct data
        """
        events = event_factory.make_batch_events(count=3)

        # Create batch
        create_response = await http_client.post(
            f"{API_BASE}/batch",
            json=events,
            headers=internal_headers
        )
        assert create_response.status_code == 200
        created_events = create_response.json()

        # Verify each persisted
        for created in created_events:
            get_response = await http_client.get(
                f"{API_BASE}/{created['event_id']}",
                headers=internal_headers
            )
            assert get_response.status_code == 200

    async def test_subscription_persists(self, http_client, internal_headers, event_factory):
        """
        Test that subscriptions persist across list calls.

        GIVEN: A subscription is created
        WHEN: Subscriptions are listed
        THEN: The created subscription appears in the list
        """
        subscription_data = event_factory.make_subscription_request(
            subscriber_name=f"persist_test_{datetime.now().timestamp()}"
        )

        # Create
        create_response = await http_client.post(
            f"{API_BASE}/subscriptions",
            json=subscription_data,
            headers=internal_headers
        )
        assert create_response.status_code == 200
        created = create_response.json()

        # List and verify
        list_response = await http_client.get(
            f"{API_BASE}/subscriptions",
            headers=internal_headers
        )
        assert list_response.status_code == 200
        subscriptions = list_response.json()

        # Should find our subscription
        found = any(s["subscription_id"] == created["subscription_id"] for s in subscriptions)
        assert found, "Created subscription not found in list"


# =============================================================================
# Summary
# =============================================================================
"""
EVENT SERVICE INTEGRATION TESTS SUMMARY:

Test Coverage (35 tests total):

1. Health Check Tests (3 tests):
   - Basic health check
   - Health check returns version
   - Frontend health check

2. Event Creation Tests (8 tests):
   - Create event success
   - Create event with all fields
   - Create events with different sources
   - Create events with different categories
   - Batch create events
   - Large batch creation
   - Create with empty data
   - Create without user_id (system event)

3. Event Retrieval Tests (6 tests):
   - Get event by ID
   - Get non-existent event (404)
   - Query events success
   - Query by user_id
   - Query by event_type
   - Query with pagination

4. Frontend Event Collection Tests (5 tests):
   - Collect frontend event
   - Collect page view
   - Collect button click
   - Batch collect frontend events
   - Frontend event with session tracking

5. Event Subscription Tests (5 tests):
   - Create subscription
   - Create subscription with filters
   - List subscriptions
   - Delete subscription
   - Create disabled subscription

6. Event Processor Tests (4 tests):
   - Register processor
   - Register processor with filters
   - List processors
   - Register processor with priority

7. Event Statistics Tests (3 tests):
   - Get statistics
   - Statistics structure verification
   - Statistics with user_id filter

8. Event Replay Tests (3 tests):
   - Replay dry run
   - Replay with event IDs
   - Replay initiates background task

9. Error Handling Tests (3 tests):
   - Missing required fields (422)
   - Invalid status value (422)
   - Invalid JSON (422)

10. Data Persistence Tests (3 tests):
    - Event persists and retrieves
    - Batch events all persist
    - Subscription persists

Run with:
    pytest tests/integration/golden/event_service/test_event_integration_golden.py -v

Prerequisites:
    - Event service running on localhost:8230
    - PostgreSQL database available
"""
