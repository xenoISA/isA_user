"""
Event Service API Golden Tests

Layer 4: API Contract Tests with real HTTP calls.
Tests validate HTTP contracts, status codes, and response schemas.

Endpoints tested:
- GET /health - Health check
- POST /api/v1/events/create - Create event
- POST /api/v1/events/batch - Batch create events
- GET /api/v1/events/statistics - Get event statistics
- POST /api/v1/events/subscriptions - Create subscription
- GET /api/v1/events/subscriptions - List subscriptions
- DELETE /api/v1/events/subscriptions/{subscription_id} - Delete subscription
- GET /api/v1/events/frontend/health - Frontend health check
- POST /api/v1/events/frontend - Collect frontend event
- POST /api/v1/events/frontend/batch - Batch collect frontend events
- GET /api/v1/events/{event_id} - Get event by ID
- POST /api/v1/events/query - Query events
- POST /api/v1/events/replay - Replay events
- POST /api/v1/events/processors - Register processor
- GET /api/v1/events/processors - List processors
- POST /webhooks/rudderstack - RudderStack webhook

Usage:
    pytest tests/api/golden/event_service -v
    pytest tests/api/golden/event_service -v -k "health"
"""
import pytest
import pytest_asyncio
import uuid
import httpx
from datetime import datetime, timezone
from typing import AsyncGenerator

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Configuration
# =============================================================================

EVENT_SERVICE_URL = "http://localhost:8230"
HTTP_TIMEOUT = 30.0


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_id() -> str:
    """Generate unique ID for tests"""
    return f"api_test_{uuid.uuid4().hex[:12]}"


def unique_user_id() -> str:
    """Generate unique user ID for tests"""
    return f"usr_test_{uuid.uuid4().hex[:12]}"


def unique_email() -> str:
    """Generate unique email for tests"""
    return f"api_test_{uuid.uuid4().hex[:8]}@example.com"


# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client for API tests"""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture
async def auth_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client with JWT authentication"""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        # Get a dev token from auth service
        auth_url = "http://localhost:8201"
        try:
            response = await client.post(
                f"{auth_url}/api/v1/auth/dev-token",
                json={
                    "user_id": "api_test_user",
                    "email": "api_test@example.com",
                    "expires_in": 3600,
                },
            )
            if response.status_code == 200:
                token = response.json().get("token")
                client.headers["Authorization"] = f"Bearer {token}"
        except Exception:
            pass  # Continue without auth if service unavailable
        yield client


# =============================================================================
# Assertion Helpers
# =============================================================================

class APIAssertions:
    """API-specific assertion helpers"""

    @staticmethod
    def assert_success(response: httpx.Response, expected_status: int = 200):
        """Assert response is successful"""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
        )

    @staticmethod
    def assert_created(response: httpx.Response):
        """Assert resource was created"""
        assert response.status_code in [200, 201], (
            f"Expected 200/201, got {response.status_code}: {response.text}"
        )

    @staticmethod
    def assert_not_found(response: httpx.Response):
        """Assert resource not found"""
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    @staticmethod
    def assert_validation_error(response: httpx.Response):
        """Assert validation error"""
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @staticmethod
    def assert_unauthorized(response: httpx.Response):
        """Assert unauthorized"""
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    @staticmethod
    def assert_server_error(response: httpx.Response):
        """Assert server error (503 for service unavailable)"""
        assert response.status_code in [500, 503], f"Expected 500/503, got {response.status_code}"

    @staticmethod
    def assert_has_fields(data: dict, fields: list):
        """Assert response has required fields"""
        missing = [f for f in fields if f not in data]
        assert not missing, f"Missing fields: {missing}"


@pytest.fixture
def api_assert() -> APIAssertions:
    """Provide API assertion helpers"""
    return APIAssertions()


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestEventHealthAPIGolden:
    """GOLDEN: Event service health endpoint contracts"""

    async def test_health_endpoint_returns_200(self, http_client: httpx.AsyncClient):
        """GOLDEN: GET /health returns 200 OK"""
        response = await http_client.get(f"{EVENT_SERVICE_URL}/health")
        assert response.status_code == 200

    async def test_health_returns_expected_fields(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /health returns service status fields"""
        response = await http_client.get(f"{EVENT_SERVICE_URL}/health")
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, ["status", "service", "version", "timestamp"])
        assert data["status"] == "healthy"
        assert data["service"] == "event_service"

    async def test_frontend_health_returns_200(self, http_client: httpx.AsyncClient):
        """GOLDEN: GET /api/v1/events/frontend/health returns 200 OK"""
        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/api/v1/events/frontend/health"
        )
        assert response.status_code == 200

    async def test_frontend_health_returns_expected_fields(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /api/v1/events/frontend/health returns frontend service status"""
        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/api/v1/events/frontend/health"
        )
        api_assert.assert_success(response)

        data = response.json()
        api_assert.assert_has_fields(data, ["status", "service", "nats_connected", "timestamp"])
        assert data["status"] == "healthy"
        assert data["service"] == "frontend-event-collection"


# =============================================================================
# Event Create Tests
# =============================================================================

class TestEventCreateAPIGolden:
    """GOLDEN: POST /api/v1/events/create endpoint contracts"""

    async def test_create_event_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/create creates event and returns response"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            json={
                "event_type": "user.login",
                "event_source": "backend",
                "event_category": "user_lifecycle",
                "user_id": user_id,
                "data": {"ip_address": "192.168.1.1", "device": "web"}
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        api_assert.assert_has_fields(data, [
            "event_id", "event_type", "event_source", "event_category",
            "user_id", "data", "status", "timestamp", "created_at"
        ])
        assert data["event_type"] == "user.login"
        assert data["user_id"] == user_id

    async def test_create_event_with_minimal_data(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/create with only required fields"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            json={
                "event_type": "page.view"
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["event_type"] == "page.view"
        # Default values should be applied
        assert data["event_source"] == "backend"
        assert data["event_category"] == "user_action"

    async def test_create_event_with_all_fields(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/create with all optional fields"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            json={
                "event_type": "order.created",
                "event_source": "backend",
                "event_category": "order",
                "user_id": user_id,
                "data": {"order_id": "ORD-123", "amount": 99.99},
                "metadata": {"source": "mobile_app", "version": "2.0.0"},
                "context": {"session_id": "sess_abc123"}
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["event_type"] == "order.created"
        assert data["data"]["order_id"] == "ORD-123"

    async def test_create_event_missing_event_type_returns_422(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/create without event_type returns 422"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            json={
                "event_source": "backend",
                "user_id": unique_user_id()
            }
        )

        api_assert.assert_validation_error(response)


# =============================================================================
# Batch Event Create Tests
# =============================================================================

class TestEventBatchCreateAPIGolden:
    """GOLDEN: POST /api/v1/events/batch endpoint contracts"""

    async def test_batch_create_events_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/batch creates multiple events"""
        user_id = unique_user_id()

        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/batch",
            json=[
                {
                    "event_type": "page.view",
                    "event_source": "frontend",
                    "event_category": "page_view",
                    "user_id": user_id,
                    "data": {"page": "/home"}
                },
                {
                    "event_type": "button.click",
                    "event_source": "frontend",
                    "event_category": "click",
                    "user_id": user_id,
                    "data": {"button": "subscribe"}
                }
            ]
        )

        api_assert.assert_success(response)
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["event_type"] == "page.view"
        assert data[1]["event_type"] == "button.click"

    async def test_batch_create_empty_array_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/batch with empty array returns empty list"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/batch",
            json=[]
        )

        api_assert.assert_success(response)
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


# =============================================================================
# Event Get Tests
# =============================================================================

class TestEventGetAPIGolden:
    """GOLDEN: GET /api/v1/events/{event_id} endpoint contracts"""

    async def test_get_event_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /api/v1/events/{event_id} returns event details"""
        # First create an event
        create_response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            json={
                "event_type": "test.get_event",
                "user_id": unique_user_id(),
                "data": {"test": "data"}
            }
        )
        api_assert.assert_success(create_response)
        event_id = create_response.json()["event_id"]

        # Now retrieve it
        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/api/v1/events/{event_id}"
        )

        api_assert.assert_success(response)
        data = response.json()
        api_assert.assert_has_fields(data, [
            "event_id", "event_type", "event_source", "event_category",
            "data", "status", "timestamp", "created_at"
        ])
        assert data["event_id"] == event_id
        assert data["event_type"] == "test.get_event"

    async def test_get_nonexistent_event_returns_404(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /api/v1/events/{nonexistent_id} returns 404"""
        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/api/v1/events/nonexistent_{uuid.uuid4().hex}"
        )
        api_assert.assert_not_found(response)


# =============================================================================
# Event Query Tests
# =============================================================================

class TestEventQueryAPIGolden:
    """GOLDEN: POST /api/v1/events/query endpoint contracts"""

    async def test_query_events_returns_list(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/query returns event list response"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/query",
            json={
                "limit": 10,
                "offset": 0
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        api_assert.assert_has_fields(data, ["events", "total", "limit", "offset", "has_more"])
        assert isinstance(data["events"], list)

    async def test_query_events_by_user_id(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/query with user_id filter"""
        user_id = unique_user_id()

        # Create an event for this user
        await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            json={
                "event_type": "user.query_test",
                "user_id": user_id,
                "data": {}
            }
        )

        # Query events for this user
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/query",
            json={
                "user_id": user_id,
                "limit": 100
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        assert isinstance(data["events"], list)
        # All returned events should belong to the specified user
        for event in data["events"]:
            assert event["user_id"] == user_id

    async def test_query_events_by_event_type(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/query with event_type filter"""
        unique_event_type = f"test.unique_{uuid.uuid4().hex[:8]}"

        # Create an event with unique type
        await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            json={
                "event_type": unique_event_type,
                "user_id": unique_user_id(),
                "data": {}
            }
        )

        # Query events by type
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/query",
            json={
                "event_type": unique_event_type,
                "limit": 100
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        for event in data["events"]:
            assert event["event_type"] == unique_event_type

    async def test_query_events_with_pagination(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/query respects pagination parameters"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/query",
            json={
                "limit": 5,
                "offset": 0
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["events"]) <= 5

    async def test_query_events_by_status(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/query with status filter"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/query",
            json={
                "status": "pending",
                "limit": 10
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        # All returned events should have the specified status
        for event in data["events"]:
            assert event["status"] == "pending"


# =============================================================================
# Event Statistics Tests
# =============================================================================

class TestEventStatisticsAPIGolden:
    """GOLDEN: GET /api/v1/events/statistics endpoint contracts"""

    async def test_statistics_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /api/v1/events/statistics returns statistics"""
        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/api/v1/events/statistics"
        )

        api_assert.assert_success(response)
        data = response.json()
        api_assert.assert_has_fields(data, [
            "total_events", "pending_events", "processed_events", "failed_events",
            "events_by_source", "events_by_category", "events_by_type",
            "processing_rate", "error_rate", "calculated_at"
        ])

    async def test_statistics_with_user_id_filter(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /api/v1/events/statistics with user_id query param"""
        user_id = unique_user_id()

        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/api/v1/events/statistics",
            params={"user_id": user_id}
        )

        api_assert.assert_success(response)


# =============================================================================
# Event Subscription Tests
# =============================================================================

class TestEventSubscriptionAPIGolden:
    """GOLDEN: Subscription endpoint contracts"""

    async def test_create_subscription_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/subscriptions creates subscription"""
        subscription_name = f"test_sub_{uuid.uuid4().hex[:8]}"

        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/subscriptions",
            json={
                "subscriber_name": subscription_name,
                "subscriber_type": "service",
                "event_types": ["user.created", "user.updated"],
                "callback_url": "http://localhost:8000/webhook",
                "enabled": True
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        api_assert.assert_has_fields(data, [
            "subscription_id", "subscriber_name", "subscriber_type",
            "event_types", "enabled"
        ])
        assert data["subscriber_name"] == subscription_name

    async def test_list_subscriptions_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /api/v1/events/subscriptions returns subscription list"""
        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/api/v1/events/subscriptions"
        )

        api_assert.assert_success(response)
        data = response.json()
        assert isinstance(data, list)

    async def test_delete_subscription_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: DELETE /api/v1/events/subscriptions/{id} deletes subscription"""
        # First create a subscription
        subscription_name = f"test_sub_delete_{uuid.uuid4().hex[:8]}"
        create_response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/subscriptions",
            json={
                "subscriber_name": subscription_name,
                "subscriber_type": "service",
                "event_types": ["test.event"],
                "enabled": True
            }
        )
        api_assert.assert_success(create_response)
        subscription_id = create_response.json()["subscription_id"]

        # Delete the subscription
        response = await http_client.delete(
            f"{EVENT_SERVICE_URL}/api/v1/events/subscriptions/{subscription_id}"
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["status"] == "deleted"
        assert data["subscription_id"] == subscription_id


# =============================================================================
# Event Processor Tests
# =============================================================================

class TestEventProcessorAPIGolden:
    """GOLDEN: Processor endpoint contracts"""

    async def test_register_processor_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/processors registers processor"""
        processor_name = f"test_processor_{uuid.uuid4().hex[:8]}"

        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/processors",
            json={
                "processor_name": processor_name,
                "processor_type": "analytics",
                "enabled": True,
                "priority": 10,
                "filters": {"event_type": "user.*"},
                "config": {"batch_size": 100}
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        api_assert.assert_has_fields(data, [
            "processor_id", "processor_name", "processor_type",
            "enabled", "priority", "filters", "config"
        ])
        assert data["processor_name"] == processor_name

    async def test_list_processors_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /api/v1/events/processors returns processor list"""
        response = await http_client.get(
            f"{EVENT_SERVICE_URL}/api/v1/events/processors"
        )

        api_assert.assert_success(response)
        data = response.json()
        assert isinstance(data, list)


# =============================================================================
# Event Replay Tests
# =============================================================================

class TestEventReplayAPIGolden:
    """GOLDEN: POST /api/v1/events/replay endpoint contracts"""

    async def test_replay_events_dry_run_returns_200(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/replay with dry_run returns preview"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/replay",
            json={
                "dry_run": True,
                "stream_id": "user:test_user_123"
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        api_assert.assert_has_fields(data, ["status", "message", "dry_run"])
        assert data["dry_run"] is True

    async def test_replay_events_by_event_ids(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /api/v1/events/replay with event_ids"""
        # First create some events
        event_ids = []
        for i in range(2):
            create_response = await http_client.post(
                f"{EVENT_SERVICE_URL}/api/v1/events/create",
                json={
                    "event_type": f"test.replay_{i}",
                    "user_id": unique_user_id(),
                    "data": {"index": i}
                }
            )
            if create_response.status_code == 200:
                event_ids.append(create_response.json()["event_id"])

        # Request replay of these events
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/replay",
            json={
                "event_ids": event_ids,
                "dry_run": True
            }
        )

        api_assert.assert_success(response)


# =============================================================================
# Frontend Event Collection Tests
# =============================================================================

class TestFrontendEventAPIGolden:
    """GOLDEN: Frontend event collection endpoint contracts"""

    async def test_collect_frontend_event_returns_response(
        self, http_client: httpx.AsyncClient
    ):
        """GOLDEN: POST /api/v1/events/frontend collects frontend event"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/frontend",
            json={
                "event_type": "page_view",
                "category": "user_interaction",
                "page_url": "/home",
                "user_id": unique_user_id(),
                "session_id": f"sess_{uuid.uuid4().hex[:8]}",
                "data": {"referrer": "google.com"},
                "metadata": {"browser": "Chrome"}
            }
        )

        # May return 200 (success) or error if NATS not available
        assert response.status_code in [200, 500, 503]
        data = response.json()
        assert "status" in data

    async def test_collect_frontend_event_minimal(
        self, http_client: httpx.AsyncClient
    ):
        """GOLDEN: POST /api/v1/events/frontend with minimal data"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/frontend",
            json={
                "event_type": "button_click"
            }
        )

        assert response.status_code in [200, 500, 503]

    async def test_collect_frontend_events_batch(
        self, http_client: httpx.AsyncClient
    ):
        """GOLDEN: POST /api/v1/events/frontend/batch collects batch of events"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/frontend/batch",
            json={
                "events": [
                    {
                        "event_type": "page_view",
                        "category": "user_interaction",
                        "page_url": "/products",
                        "data": {}
                    },
                    {
                        "event_type": "scroll",
                        "category": "user_interaction",
                        "data": {"depth": 50}
                    }
                ],
                "client_info": {
                    "app_version": "1.0.0",
                    "platform": "web"
                }
            }
        )

        # May return 200 (success) or 503 if NATS not available
        assert response.status_code in [200, 500, 503]


# =============================================================================
# RudderStack Webhook Tests
# =============================================================================

class TestRudderStackWebhookAPIGolden:
    """GOLDEN: POST /webhooks/rudderstack endpoint contracts"""

    async def test_rudderstack_webhook_single_event(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /webhooks/rudderstack accepts single event"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/webhooks/rudderstack",
            json={
                "anonymousId": f"anon_{uuid.uuid4().hex[:8]}",
                "userId": unique_user_id(),
                "event": "Product Viewed",
                "type": "track",
                "properties": {
                    "product_id": "prod_123",
                    "product_name": "Test Product"
                },
                "context": {
                    "page": {"url": "https://example.com/products"}
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["status"] == "accepted"

    async def test_rudderstack_webhook_batch_events(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /webhooks/rudderstack accepts batch of events"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/webhooks/rudderstack",
            json=[
                {
                    "anonymousId": f"anon_{uuid.uuid4().hex[:8]}",
                    "event": "Page Viewed",
                    "type": "page",
                    "properties": {"page": "/home"},
                    "context": {},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "anonymousId": f"anon_{uuid.uuid4().hex[:8]}",
                    "event": "Button Clicked",
                    "type": "track",
                    "properties": {"button": "signup"},
                    "context": {},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        )

        api_assert.assert_success(response)
        data = response.json()
        assert data["status"] == "accepted"

    async def test_rudderstack_webhook_invalid_payload(
        self, http_client: httpx.AsyncClient
    ):
        """GOLDEN: POST /webhooks/rudderstack rejects invalid payload"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/webhooks/rudderstack",
            json={
                "invalid": "payload"
            }
        )

        # Should return 400 for bad request or 422 for validation error
        assert response.status_code in [400, 422]


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestEventErrorHandlingAPIGolden:
    """GOLDEN: Error handling contracts"""

    async def test_invalid_json_returns_422(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: Invalid JSON body returns 422"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        api_assert.assert_validation_error(response)

    async def test_invalid_event_source_returns_422(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: Invalid event_source enum value returns 422"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            json={
                "event_type": "test.event",
                "event_source": "invalid_source"
            }
        )
        api_assert.assert_validation_error(response)

    async def test_invalid_event_category_returns_422(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: Invalid event_category enum value returns 422"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/create",
            json={
                "event_type": "test.event",
                "event_category": "invalid_category"
            }
        )
        api_assert.assert_validation_error(response)


# =============================================================================
# Request Validation Tests
# =============================================================================

class TestEventValidationAPIGolden:
    """GOLDEN: Request validation contracts"""

    async def test_query_limit_validation(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: Query with limit > 1000 returns 422"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/query",
            json={
                "limit": 10000  # Exceeds max limit of 1000
            }
        )
        api_assert.assert_validation_error(response)

    async def test_query_negative_offset_returns_422(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: Query with negative offset returns 422"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/query",
            json={
                "offset": -1
            }
        )
        api_assert.assert_validation_error(response)

    async def test_subscription_without_event_types_returns_422(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: Creating subscription without event_types returns 422"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/subscriptions",
            json={
                "subscriber_name": "test_sub",
                "subscriber_type": "service"
                # Missing event_types
            }
        )
        api_assert.assert_validation_error(response)

    async def test_processor_without_name_returns_422(
        self, http_client: httpx.AsyncClient, api_assert: APIAssertions
    ):
        """GOLDEN: Creating processor without processor_name returns 422"""
        response = await http_client.post(
            f"{EVENT_SERVICE_URL}/api/v1/events/processors",
            json={
                "processor_type": "analytics"
                # Missing processor_name
            }
        )
        api_assert.assert_validation_error(response)
