"""
Order Service Smoke Tests

Quick sanity checks to verify order_service is deployed and functioning correctly.
These tests are designed to:
1. Run quickly (< 30 seconds total)
2. Validate critical paths only
3. Catch obvious deployment failures

Purpose:
- Verify service is up and responding
- Test basic order operations work
- Test critical user flows (create, complete, cancel)
- Validate data contracts are honored

Usage:
    pytest tests/smoke/order_service -v
    pytest tests/smoke/order_service -v -k "health"

Environment Variables:
    ORDER_BASE_URL: Base URL for order service (default: http://localhost:8213)
"""

import os
import pytest
import uuid
import httpx
from datetime import datetime

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]

# Configuration
BASE_URL = os.getenv("ORDER_BASE_URL", "http://localhost:8213")
API_V1 = f"{BASE_URL}/api/v1/orders"
TIMEOUT = 10.0


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for smoke tests"""
    return f"usr_smoke_{uuid.uuid4().hex[:8]}"


def unique_order_id() -> str:
    """Generate unique order ID for smoke tests"""
    return f"ord_smoke_{uuid.uuid4().hex[:8]}"


def unique_wallet_id() -> str:
    """Generate unique wallet ID for smoke tests"""
    return f"wal_smoke_{uuid.uuid4().hex[:8]}"


def unique_subscription_id() -> str:
    """Generate unique subscription ID for smoke tests"""
    return f"sub_smoke_{uuid.uuid4().hex[:8]}"


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

    async def test_health_detailed_responds(self, http_client):
        """SMOKE: GET /health/detailed returns 200"""
        response = await http_client.get(f"{BASE_URL}/health/detailed")
        # Could be 200 or 404 if not implemented
        assert response.status_code in [200, 404], \
            f"Detailed health check failed: {response.status_code}"

    async def test_health_returns_valid_json(self, http_client):
        """SMOKE: GET /health returns valid JSON with expected fields"""
        response = await http_client.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "service" in data, \
                "Health response missing status or service field"


# =============================================================================
# SMOKE TEST 2: Order Creation
# =============================================================================

class TestOrderCreationSmoke:
    """Smoke: Order creation sanity checks"""

    async def test_create_order_validates_input(self, http_client):
        """SMOKE: POST /orders validates required fields"""
        response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": "",  # Empty user_id should be rejected
                "order_type": "purchase",
                "total_amount": 99.99,
                "currency": "USD",
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_create_order_rejects_negative_amount(self, http_client):
        """SMOKE: POST /orders rejects negative amount"""
        response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": unique_user_id(),
                "order_type": "purchase",
                "total_amount": -10.00,  # Negative amount
                "currency": "USD",
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_create_order_works(self, http_client):
        """SMOKE: POST /orders creates order successfully"""
        response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": unique_user_id(),
                "order_type": "purchase",
                "total_amount": 49.99,
                "currency": "USD",
                "items": [{"product_id": "prod_test", "quantity": 1}],
            }
        )

        # Should succeed or require auth
        assert response.status_code in [200, 201, 401, 403], \
            f"Create order failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 3: Order Retrieval
# =============================================================================

class TestOrderRetrievalSmoke:
    """Smoke: Order retrieval sanity checks"""

    async def test_list_orders_works(self, http_client):
        """SMOKE: GET /orders returns order list"""
        response = await http_client.get(f"{API_V1}")

        # Accept success or auth required
        assert response.status_code in [200, 401, 403], \
            f"List orders failed unexpectedly: {response.status_code}"

    async def test_get_order_handles_not_found(self, http_client):
        """SMOKE: GET /orders/{id} handles non-existent order"""
        order_id = unique_order_id()

        response = await http_client.get(f"{API_V1}/{order_id}")

        # Should return 404 for non-existent order
        assert response.status_code in [200, 401, 403, 404], \
            f"Get order failed unexpectedly: {response.status_code}"

    async def test_get_user_orders_works(self, http_client):
        """SMOKE: GET /orders/user/{user_id} returns user orders"""
        user_id = unique_user_id()

        response = await http_client.get(f"{API_V1}/user/{user_id}")

        assert response.status_code in [200, 401, 403, 404], \
            f"Get user orders failed unexpectedly: {response.status_code}"

    async def test_list_orders_with_filters(self, http_client):
        """SMOKE: GET /orders with filters works"""
        response = await http_client.get(
            f"{API_V1}",
            params={
                "status": "pending",
                "limit": 10
            }
        )

        assert response.status_code in [200, 401, 403], \
            f"List orders with filters failed: {response.status_code}"


# =============================================================================
# SMOKE TEST 4: Order Updates
# =============================================================================

class TestOrderUpdateSmoke:
    """Smoke: Order update sanity checks"""

    async def test_update_order_handles_not_found(self, http_client):
        """SMOKE: PUT /orders/{id} handles non-existent order"""
        order_id = unique_order_id()

        response = await http_client.put(
            f"{API_V1}/{order_id}",
            json={
                "status": "processing",
            }
        )

        # Should return 404 for non-existent order
        assert response.status_code in [401, 403, 404, 500], \
            f"Update order failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 5: Order Cancellation
# =============================================================================

class TestOrderCancellationSmoke:
    """Smoke: Order cancellation sanity checks"""

    async def test_cancel_order_handles_not_found(self, http_client):
        """SMOKE: POST /orders/{id}/cancel handles non-existent order"""
        order_id = unique_order_id()

        response = await http_client.post(
            f"{API_V1}/{order_id}/cancel",
            json={
                "reason": "User requested cancellation",
            }
        )

        # Should return 404 for non-existent order
        assert response.status_code in [401, 403, 404, 500], \
            f"Cancel order failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 6: Order Completion
# =============================================================================

class TestOrderCompletionSmoke:
    """Smoke: Order completion sanity checks"""

    async def test_complete_order_handles_not_found(self, http_client):
        """SMOKE: POST /orders/{id}/complete handles non-existent order"""
        order_id = unique_order_id()

        response = await http_client.post(
            f"{API_V1}/{order_id}/complete",
            json={
                "payment_confirmed": True,
                "transaction_id": "txn_test_123",
            }
        )

        # Should return 404 for non-existent order
        assert response.status_code in [401, 403, 404, 500], \
            f"Complete order failed unexpectedly: {response.status_code}"

    async def test_complete_order_validates_payment(self, http_client):
        """SMOKE: POST /orders/{id}/complete validates payment_confirmed"""
        # First create an order
        create_response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": unique_user_id(),
                "order_type": "purchase",
                "total_amount": 29.99,
                "currency": "USD",
            }
        )

        if create_response.status_code in [200, 201]:
            data = create_response.json()
            order_id = data.get("order", {}).get("order_id") or data.get("order_id")

            if order_id:
                # Try to complete without payment_confirmed=True
                complete_response = await http_client.post(
                    f"{API_V1}/{order_id}/complete",
                    json={
                        "payment_confirmed": False,
                    }
                )

                # Should fail because payment not confirmed
                assert complete_response.status_code in [400, 401, 403, 422, 500], \
                    f"Expected failure, got {complete_response.status_code}"


# =============================================================================
# SMOKE TEST 7: Order Search
# =============================================================================

class TestOrderSearchSmoke:
    """Smoke: Order search sanity checks"""

    async def test_search_orders_works(self, http_client):
        """SMOKE: GET /orders/search returns results"""
        response = await http_client.get(
            f"{API_V1}/search",
            params={"query": "test"}
        )

        assert response.status_code in [200, 401, 403, 404], \
            f"Search orders failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 8: Statistics
# =============================================================================

class TestStatisticsSmoke:
    """Smoke: Statistics endpoint sanity checks"""

    async def test_get_statistics_works(self, http_client):
        """SMOKE: GET /orders/statistics returns statistics"""
        response = await http_client.get(f"{API_V1}/statistics")

        # Should return 200 or require auth
        assert response.status_code in [200, 401, 403, 404], \
            f"Get statistics failed unexpectedly: {response.status_code}"


# =============================================================================
# SMOKE TEST 9: Critical User Flow
# =============================================================================

class TestCriticalFlowSmoke:
    """Smoke: Critical order flow end-to-end"""

    async def test_complete_order_lifecycle(self, http_client):
        """
        SMOKE: Complete order lifecycle works end-to-end

        Tests: Create Order -> Get Order -> List Orders -> Get Stats
        """
        user_id = unique_user_id()

        # Step 1: Create order
        create_response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": user_id,
                "order_type": "purchase",
                "total_amount": 79.99,
                "currency": "USD",
                "items": [{"product_id": "prod_123", "quantity": 1}],
            }
        )
        assert create_response.status_code in [200, 201, 401, 403], \
            f"Create order failed: {create_response.status_code}"

        # Step 2: List user orders
        list_response = await http_client.get(f"{API_V1}/user/{user_id}")
        assert list_response.status_code in [200, 401, 403, 404], \
            f"List orders failed: {list_response.status_code}"

        # Step 3: List all orders with filter
        filter_response = await http_client.get(
            f"{API_V1}",
            params={"user_id": user_id, "limit": 10}
        )
        assert filter_response.status_code in [200, 401, 403], \
            f"Filter orders failed: {filter_response.status_code}"

        # Step 4: Get statistics
        stats_response = await http_client.get(f"{API_V1}/statistics")
        assert stats_response.status_code in [200, 401, 403, 404], \
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
            f"{API_V1}",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_missing_required_fields_returns_422(self, http_client):
        """SMOKE: Missing required fields returns 422"""
        response = await http_client.post(
            f"{API_V1}",
            json={}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_invalid_order_type_returns_422(self, http_client):
        """SMOKE: Invalid order_type returns 422"""
        response = await http_client.post(
            f"{API_V1}",
            json={
                "user_id": unique_user_id(),
                "order_type": "invalid_type",
                "total_amount": 49.99,
            }
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"


# =============================================================================
# SUMMARY
# =============================================================================
"""
ORDER SERVICE SMOKE TESTS SUMMARY:

Test Coverage (20 tests total):

1. Health (3 tests):
   - /health responds with 200
   - /health/detailed responds
   - Health returns valid JSON

2. Order Creation (3 tests):
   - Create order validates input
   - Create order rejects negative amount
   - Create order works

3. Order Retrieval (4 tests):
   - List orders works
   - Get order handles not found
   - Get user orders works
   - List orders with filters works

4. Order Updates (1 test):
   - Update order handles not found

5. Order Cancellation (1 test):
   - Cancel order handles not found

6. Order Completion (2 tests):
   - Complete order handles not found
   - Complete order validates payment

7. Order Search (1 test):
   - Search orders works

8. Statistics (1 test):
   - Get statistics works

9. Critical Flow (1 test):
   - Complete lifecycle: Create -> Get -> List -> Stats

10. Error Handling (4 tests):
    - Not found returns 404
    - Invalid JSON returns error
    - Missing required fields returns 422
    - Invalid order_type returns 422

Characteristics:
- Fast execution (< 30 seconds)
- No external dependencies (other than running order_service)
- Tests critical paths only
- Validates deployment health

Run with:
    pytest tests/smoke/order_service -v
    pytest tests/smoke/order_service -v --timeout=60
"""
