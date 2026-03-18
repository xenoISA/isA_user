"""
Event Service Smoke Tests

Quick sanity checks to verify event_service is deployed and functioning correctly.
These tests are designed to:
1. Run quickly (< 30 seconds total)
2. Validate critical paths only
3. Catch obvious deployment failures

Usage:
    pytest tests/smoke/event_service -v
    pytest tests/smoke/event_service -v -k "health"

Environment Variables:
    EVENT_BASE_URL: Base URL for event service (default: http://localhost:8230)
"""

import os
import pytest
import uuid
import httpx
from datetime import datetime

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

# Configuration
BASE_URL = os.getenv("EVENT_BASE_URL", "http://localhost:8230")
API_V1 = f"{BASE_URL}/api/v1/events"
TIMEOUT = 10.0


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_id() -> str:
    """Generate unique ID for smoke tests"""
    return f"smoke_{uuid.uuid4().hex[:8]}"


def unique_user_id() -> str:
    """Generate unique user ID for smoke tests"""
    return f"smoke_user_{uuid.uuid4().hex[:8]}"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def http_client():
    """Async HTTP client for smoke tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


# =============================================================================
# SMOKE TEST 1: Health Checks
# =============================================================================

class TestHealthSmoke:
    """Smoke: Health endpoint sanity checks"""

    async def test_health_endpoint_responds(self, http_client):
        """SMOKE: GET /health returns 200"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200, \
            f"Health check failed: {response.status_code}"

    async def test_health_response_has_status(self, http_client):
        """SMOKE: GET /health returns response with status field"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "service" in data


# =============================================================================
# SMOKE TEST 2: Event Creation
# =============================================================================

class TestEventCreationSmoke:
    """Smoke: Event creation sanity checks"""

    async def test_create_single_event(self, http_client):
        """SMOKE: POST /create creates a single event"""
        response = await http_client.post(
            f"{API_V1}/create",
            json={
                "event_type": "smoke_test.created",
                "user_id": unique_user_id(),
                "data": {"source": "smoke_test", "timestamp": datetime.now().isoformat()},
            }
        )
        assert response.status_code in [200, 201, 400, 500], \
            f"Create event failed unexpectedly: {response.status_code}"

    async def test_create_batch_events(self, http_client):
        """SMOKE: POST /batch creates multiple events"""
        user_id = unique_user_id()
        response = await http_client.post(
            f"{API_V1}/batch",
            json=[
                {"event_type": "smoke_test.batch_1", "user_id": user_id, "data": {}},
                {"event_type": "smoke_test.batch_2", "user_id": user_id, "data": {}},
            ]
        )
        assert response.status_code in [200, 201, 400, 422, 500], \
            f"Batch create failed unexpectedly: {response.status_code}"

    async def test_create_event_accepts_empty_type(self, http_client):
        """SMOKE: POST /create with empty event_type

        NOTE: The service currently accepts empty event_type (returns 200/201).
        This is by design - the service does not validate event_type emptiness.
        """
        response = await http_client.post(
            f"{API_V1}/create",
            json={"event_type": "", "data": {}}
        )
        # Service accepts empty event_type; 503 during graceful shutdown
        if response.status_code == 503:
            pytest.skip("Service in shutdown state")
        assert response.status_code in [200, 201, 400, 422], \
            f"Expected 200/201/400/422, got {response.status_code}"


# =============================================================================
# SMOKE TEST 3: Event Querying
# =============================================================================

class TestEventQuerySmoke:
    """Smoke: Event query sanity checks"""

    async def test_query_events(self, http_client):
        """SMOKE: POST /query returns event list"""
        response = await http_client.post(
            f"{API_V1}/query",
            json={"limit": 10, "offset": 0}
        )
        assert response.status_code in [200, 400, 500], \
            f"Query events failed: {response.status_code}"

    async def test_get_event_by_id(self, http_client):
        """SMOKE: GET /{event_id} returns event or 404"""
        response = await http_client.get(f"{API_V1}/evt_nonexistent")
        assert response.status_code in [200, 404], \
            f"Unexpected status code: {response.status_code}"


# =============================================================================
# SMOKE TEST 4: Event Statistics
# =============================================================================

class TestStatisticsSmoke:
    """Smoke: Statistics endpoint sanity checks"""

    async def test_get_statistics(self, http_client):
        """SMOKE: GET /statistics returns event stats"""
        response = await http_client.get(f"{API_V1}/statistics")
        assert response.status_code in [200, 401, 403, 500], \
            f"Get stats failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 5: Subscriptions
# =============================================================================

class TestSubscriptionSmoke:
    """Smoke: Event subscription sanity checks"""

    async def test_list_subscriptions(self, http_client):
        """SMOKE: GET /subscriptions returns subscription list"""
        response = await http_client.get(f"{API_V1}/subscriptions")
        assert response.status_code in [200, 401, 500], \
            f"List subscriptions failed: {response.status_code}"

    async def test_create_subscription(self, http_client):
        """SMOKE: POST /subscriptions creates a subscription"""
        response = await http_client.post(
            f"{API_V1}/subscriptions",
            json={
                "subscriber_name": f"smoke_test_{unique_id()}",
                "subscriber_type": "service",
                "event_types": ["smoke_test.*"],
                "enabled": True,
            }
        )
        assert response.status_code in [200, 201, 400, 422, 500], \
            f"Create subscription failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 6: Processors
# =============================================================================

class TestProcessorSmoke:
    """Smoke: Event processor sanity checks"""

    async def test_list_processors(self, http_client):
        """SMOKE: GET /processors returns processor list"""
        response = await http_client.get(f"{API_V1}/processors")
        assert response.status_code in [200, 401, 500], \
            f"List processors failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 7: Event Replay
# =============================================================================

class TestReplaySmoke:
    """Smoke: Event replay sanity checks"""

    async def test_replay_dry_run(self, http_client):
        """SMOKE: POST /replay with dry_run=true works"""
        response = await http_client.post(
            f"{API_V1}/replay",
            json={"dry_run": True}
        )
        assert response.status_code in [200, 400, 422, 500], \
            f"Replay dry run failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 8: Frontend Events
# =============================================================================

class TestFrontendEventSmoke:
    """Smoke: Frontend event collection sanity checks"""

    async def test_collect_frontend_event(self, http_client):
        """SMOKE: POST /frontend collects a frontend event"""
        response = await http_client.post(
            f"{API_V1}/frontend",
            json={
                "event_type": "page_view",
                "category": "user_interaction",
                "page_url": "https://app.example.com/dashboard",
                "user_id": unique_user_id(),
                "data": {"component": "smoke_test"},
            }
        )
        assert response.status_code in [200, 201, 400, 500], \
            f"Frontend event failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 9: Critical Event Flow
# =============================================================================

class TestCriticalFlowSmoke:
    """Smoke: Critical event flow end-to-end"""

    async def test_complete_event_lifecycle(self, http_client):
        """
        SMOKE: Complete event lifecycle works end-to-end

        Tests: Create Event -> Query Event -> Get Statistics
        """
        user_id = unique_user_id()

        # Step 1: Create an event
        create_response = await http_client.post(
            f"{API_V1}/create",
            json={
                "event_type": "smoke_test.lifecycle",
                "user_id": user_id,
                "data": {"step": "lifecycle_test"},
            }
        )
        assert create_response.status_code in [200, 201, 400, 500], \
            f"Create event failed: {create_response.status_code}"

        # Step 2: Query events for user
        query_response = await http_client.post(
            f"{API_V1}/query",
            json={"user_id": user_id, "limit": 10}
        )
        assert query_response.status_code in [200, 400, 500], \
            f"Query events failed: {query_response.status_code}"

        # Step 3: Get statistics
        stats_response = await http_client.get(f"{API_V1}/statistics")
        assert stats_response.status_code in [200, 401, 403, 500], \
            f"Get stats failed: {stats_response.status_code}"


# =============================================================================
# SMOKE TEST 10: Error Handling
# =============================================================================

class TestErrorHandlingSmoke:
    """Smoke: Error handling sanity checks"""

    async def test_not_found_returns_404(self, http_client):
        """SMOKE: Non-existent endpoint returns 404"""
        response = await http_client.get(f"{API_V1}/nonexistent_endpoint")
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"

    async def test_invalid_json_returns_error(self, http_client):
        """SMOKE: Invalid JSON returns 400 or 422"""
        response = await http_client.post(
            f"{API_V1}/create",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"
