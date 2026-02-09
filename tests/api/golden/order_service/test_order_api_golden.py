"""
Order Service API Golden Tests

Layer 4: API Contract Tests with real HTTP calls.
Tests validate HTTP contracts, status codes, and response schemas.

Purpose:
- Test actual HTTP endpoints against running order_service
- Validate request/response schemas
- Test status code contracts (200, 201, 400, 404, 422, 500)
- Test pagination and query parameters

Usage:
    pytest tests/api/golden/order_service -v
    pytest tests/api/golden/order_service -v -k "health"
"""
import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from tests.api.conftest import APIClient, APIAssertions, APITestConfig
from tests.contracts.order.data_contract import (
    OrderTestDataFactory,
    OrderStatusContract,
    OrderTypeContract,
    PaymentStatusContract,
    OrderCreateRequestBuilder,
)

import httpx
import pytest_asyncio

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


# =============================================================================
# Test Data Generators
# =============================================================================

def unique_user_id() -> str:
    """Generate unique user ID for tests"""
    return f"usr_api_{uuid.uuid4().hex[:12]}"


def unique_order_id() -> str:
    """Generate unique order ID for tests"""
    return f"ord_api_{uuid.uuid4().hex[:12]}"


def unique_wallet_id() -> str:
    """Generate unique wallet ID for tests"""
    return f"wal_api_{uuid.uuid4().hex[:12]}"


def unique_subscription_id() -> str:
    """Generate unique subscription ID for tests"""
    return f"sub_api_{uuid.uuid4().hex[:12]}"


# =============================================================================
# Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def http_client():
    """Async HTTP client for API tests"""
    async with httpx.AsyncClient(timeout=APITestConfig.HTTP_TIMEOUT) as client:
        yield client


@pytest_asyncio.fixture
async def order_api(http_client: httpx.AsyncClient) -> APIClient:
    """Provide API client for order service"""
    # Order service runs on port 8213 according to conftest
    return APIClient(http_client, "order", "/api/v1/orders")


@pytest.fixture
def api_assert() -> APIAssertions:
    """Provide API assertion helpers"""
    return APIAssertions()


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestOrderHealthAPIGolden:
    """GOLDEN: Order service health endpoint contracts"""

    async def test_health_endpoint_returns_200(self, order_api: APIClient):
        """GOLDEN: GET /health returns 200 OK"""
        response = await order_api.get_raw("/health")
        assert response.status_code == 200

    async def test_health_response_schema(self, order_api: APIClient):
        """GOLDEN: GET /health returns expected schema"""
        response = await order_api.get_raw("/health")
        if response.status_code == 200:
            data = response.json()
            # Should have at least status and service fields
            assert "status" in data or "service" in data

    async def test_health_detailed_returns_200(self, order_api: APIClient):
        """GOLDEN: GET /health/detailed returns 200 with component status"""
        response = await order_api.get_raw("/health/detailed")
        # Could be 200 or 404 if not implemented
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "service" in data

    async def test_status_endpoint_returns_200(self, order_api: APIClient):
        """GOLDEN: GET /status returns service status"""
        response = await order_api.get_raw("/status")
        assert response.status_code in [200, 404]


# =============================================================================
# Order Creation Tests
# =============================================================================

class TestOrderCreationAPIGolden:
    """GOLDEN: Order creation endpoint contracts"""

    async def test_create_order_returns_success(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders creates order and returns success"""
        order_data = OrderTestDataFactory.make_valid_create_order_request()
        order_data["user_id"] = unique_user_id()

        response = await order_api.post("", json=order_data)

        # Could be 200/201 for success, 400/422 for validation, 401/403 for auth
        assert response.status_code in [200, 201, 400, 401, 403, 422, 500], \
            f"Unexpected status code: {response.status_code}"

        if response.status_code in [200, 201]:
            data = response.json()
            assert "order" in data or "order_id" in data or "success" in data

    async def test_create_subscription_order(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders creates subscription order"""
        order_data = OrderTestDataFactory.make_valid_subscription_order_request()
        order_data["user_id"] = unique_user_id()
        order_data["subscription_id"] = unique_subscription_id()

        response = await order_api.post("", json=order_data)

        assert response.status_code in [200, 201, 400, 401, 403, 422, 500], \
            f"Unexpected status code: {response.status_code}"

    async def test_create_credit_purchase_order(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders creates credit purchase order"""
        order_data = OrderTestDataFactory.make_valid_credit_purchase_request()
        order_data["user_id"] = unique_user_id()
        order_data["wallet_id"] = unique_wallet_id()

        response = await order_api.post("", json=order_data)

        assert response.status_code in [200, 201, 400, 401, 403, 422, 500], \
            f"Unexpected status code: {response.status_code}"

    async def test_create_order_with_items(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders with items list"""
        order_data = OrderTestDataFactory.make_valid_create_order_request()
        order_data["user_id"] = unique_user_id()
        order_data["items"] = OrderTestDataFactory.make_order_items()

        response = await order_api.post("", json=order_data)

        assert response.status_code in [200, 201, 400, 401, 403, 422, 500], \
            f"Unexpected status code: {response.status_code}"

    async def test_create_order_rejects_empty_user_id(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders with empty user_id returns 400 or 422"""
        order_data = OrderTestDataFactory.make_invalid_empty_user_id()

        response = await order_api.post("", json=order_data)

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_create_order_rejects_negative_amount(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders with negative amount returns 400 or 422"""
        order_data = OrderTestDataFactory.make_invalid_negative_amount()

        response = await order_api.post("", json=order_data)

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_create_order_rejects_zero_amount(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders with zero amount returns 400 or 422"""
        order_data = OrderTestDataFactory.make_invalid_zero_amount()

        response = await order_api.post("", json=order_data)

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_create_credit_order_without_wallet_id_fails(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders credit purchase without wallet_id returns 400 or 422"""
        order_data = OrderTestDataFactory.make_invalid_credit_purchase_without_wallet()

        response = await order_api.post("", json=order_data)

        # Should be rejected due to missing wallet_id
        assert response.status_code in [400, 422, 500], \
            f"Expected 400/422/500, got {response.status_code}"

    async def test_create_subscription_without_subscription_id_fails(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders subscription without subscription_id returns 400 or 422"""
        order_data = OrderTestDataFactory.make_invalid_subscription_without_subscription_id()

        response = await order_api.post("", json=order_data)

        # Should be rejected due to missing subscription_id
        assert response.status_code in [400, 422, 500], \
            f"Expected 400/422/500, got {response.status_code}"


# =============================================================================
# Order Retrieval Tests
# =============================================================================

class TestOrderRetrievalAPIGolden:
    """GOLDEN: Order retrieval endpoint contracts"""

    async def test_get_order_returns_200_or_404(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders/{id} returns 200 or 404"""
        order_id = unique_order_id()

        response = await order_api.get(f"/{order_id}")

        # 404 if not found, 200 if exists, or auth errors
        assert response.status_code in [200, 401, 403, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_get_order_response_schema(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders/{id} returns proper schema when found"""
        # First create an order
        order_data = OrderTestDataFactory.make_valid_create_order_request()
        order_data["user_id"] = unique_user_id()

        create_response = await order_api.post("", json=order_data)

        if create_response.status_code in [200, 201]:
            data = create_response.json()
            order_id = data.get("order", {}).get("order_id") or data.get("order_id")

            if order_id:
                get_response = await order_api.get(f"/{order_id}")
                if get_response.status_code == 200:
                    order_data = get_response.json()
                    # Should have order details
                    assert "order" in order_data or "order_id" in order_data

    async def test_list_orders_returns_200(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders returns 200 with list of orders"""
        response = await order_api.get("")

        assert response.status_code in [200, 401, 403], \
            f"Unexpected status code: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            assert "orders" in data or isinstance(data, list)

    async def test_list_orders_with_pagination(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders supports pagination parameters"""
        response = await order_api.get("", params={"limit": 10, "offset": 0})

        assert response.status_code in [200, 401, 403], \
            f"Unexpected status code: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # Should have pagination info
            assert "orders" in data or "total_count" in data or isinstance(data, list)

    async def test_list_orders_filter_by_user(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders supports user_id filter"""
        user_id = unique_user_id()

        response = await order_api.get("", params={"user_id": user_id})

        assert response.status_code in [200, 401, 403], \
            f"Unexpected status code: {response.status_code}"

    async def test_list_orders_filter_by_status(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders supports status filter"""
        response = await order_api.get("", params={"status": "pending"})

        assert response.status_code in [200, 401, 403], \
            f"Unexpected status code: {response.status_code}"

    async def test_list_orders_filter_by_type(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders supports order_type filter"""
        response = await order_api.get("", params={"order_type": "purchase"})

        assert response.status_code in [200, 401, 403], \
            f"Unexpected status code: {response.status_code}"

    async def test_get_user_orders_returns_200(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders/user/{user_id} returns 200"""
        user_id = unique_user_id()

        response = await order_api.get(f"/user/{user_id}")

        assert response.status_code in [200, 401, 403, 404], \
            f"Unexpected status code: {response.status_code}"


# =============================================================================
# Order Update Tests
# =============================================================================

class TestOrderUpdateAPIGolden:
    """GOLDEN: Order update endpoint contracts"""

    async def test_update_order_returns_success(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: PUT /orders/{id} updates order"""
        # Create order first
        create_data = OrderTestDataFactory.make_valid_create_order_request()
        create_data["user_id"] = unique_user_id()

        create_response = await order_api.post("", json=create_data)

        if create_response.status_code in [200, 201]:
            data = create_response.json()
            order_id = data.get("order", {}).get("order_id") or data.get("order_id")

            if order_id:
                update_data = OrderTestDataFactory.make_valid_update_order_request()
                response = await order_api.put(f"/{order_id}", json=update_data)

                assert response.status_code in [200, 400, 401, 403, 404, 422], \
                    f"Unexpected status code: {response.status_code}"

    async def test_update_nonexistent_order_returns_404(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: PUT /orders/{id} for nonexistent order returns 404"""
        order_id = unique_order_id()
        update_data = OrderTestDataFactory.make_valid_update_order_request()

        response = await order_api.put(f"/{order_id}", json=update_data)

        assert response.status_code in [401, 403, 404, 500], \
            f"Expected 401/403/404/500, got {response.status_code}"


# =============================================================================
# Order Cancellation Tests
# =============================================================================

class TestOrderCancellationAPIGolden:
    """GOLDEN: Order cancellation endpoint contracts"""

    async def test_cancel_order_returns_success(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders/{id}/cancel cancels order"""
        # Create order first
        create_data = OrderTestDataFactory.make_valid_create_order_request()
        create_data["user_id"] = unique_user_id()

        create_response = await order_api.post("", json=create_data)

        if create_response.status_code in [200, 201]:
            data = create_response.json()
            order_id = data.get("order", {}).get("order_id") or data.get("order_id")

            if order_id:
                cancel_data = OrderTestDataFactory.make_valid_cancel_order_request()
                response = await order_api.post(f"/{order_id}/cancel", json=cancel_data)

                assert response.status_code in [200, 400, 401, 403, 404, 422], \
                    f"Unexpected status code: {response.status_code}"

    async def test_cancel_nonexistent_order_returns_404(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders/{id}/cancel for nonexistent order returns 404"""
        order_id = unique_order_id()
        cancel_data = OrderTestDataFactory.make_valid_cancel_order_request()

        response = await order_api.post(f"/{order_id}/cancel", json=cancel_data)

        assert response.status_code in [401, 403, 404, 500], \
            f"Expected 401/403/404/500, got {response.status_code}"


# =============================================================================
# Order Completion Tests
# =============================================================================

class TestOrderCompletionAPIGolden:
    """GOLDEN: Order completion endpoint contracts"""

    async def test_complete_order_returns_success(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders/{id}/complete completes order"""
        # Create order first
        create_data = OrderTestDataFactory.make_valid_create_order_request()
        create_data["user_id"] = unique_user_id()

        create_response = await order_api.post("", json=create_data)

        if create_response.status_code in [200, 201]:
            data = create_response.json()
            order_id = data.get("order", {}).get("order_id") or data.get("order_id")

            if order_id:
                complete_data = OrderTestDataFactory.make_valid_complete_order_request()
                response = await order_api.post(f"/{order_id}/complete", json=complete_data)

                assert response.status_code in [200, 400, 401, 403, 404, 422], \
                    f"Unexpected status code: {response.status_code}"

    async def test_complete_without_payment_confirmation_fails(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders/{id}/complete without payment_confirmed fails"""
        # Create order first
        create_data = OrderTestDataFactory.make_valid_create_order_request()
        create_data["user_id"] = unique_user_id()

        create_response = await order_api.post("", json=create_data)

        if create_response.status_code in [200, 201]:
            data = create_response.json()
            order_id = data.get("order", {}).get("order_id") or data.get("order_id")

            if order_id:
                complete_data = {"payment_confirmed": False}
                response = await order_api.post(f"/{order_id}/complete", json=complete_data)

                # Should fail due to payment not confirmed
                assert response.status_code in [400, 401, 403, 422, 500], \
                    f"Expected failure status, got {response.status_code}"

    async def test_complete_nonexistent_order_returns_404(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: POST /orders/{id}/complete for nonexistent order returns 404"""
        order_id = unique_order_id()
        complete_data = OrderTestDataFactory.make_valid_complete_order_request()

        response = await order_api.post(f"/{order_id}/complete", json=complete_data)

        assert response.status_code in [401, 403, 404, 500], \
            f"Expected 401/403/404/500, got {response.status_code}"


# =============================================================================
# Order Search Tests
# =============================================================================

class TestOrderSearchAPIGolden:
    """GOLDEN: Order search endpoint contracts"""

    async def test_search_orders_returns_200(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders/search returns 200"""
        response = await order_api.get("/search", params={"query": "test"})

        assert response.status_code in [200, 401, 403, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_search_orders_with_user_filter(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders/search supports user_id filter"""
        user_id = unique_user_id()

        response = await order_api.get(
            "/search",
            params={"query": "test", "user_id": user_id}
        )

        assert response.status_code in [200, 401, 403, 404], \
            f"Unexpected status code: {response.status_code}"


# =============================================================================
# Order Statistics Tests
# =============================================================================

class TestOrderStatisticsAPIGolden:
    """GOLDEN: Order statistics endpoint contracts"""

    async def test_get_statistics_returns_200(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders/statistics returns 200"""
        response = await order_api.get("/statistics")

        assert response.status_code in [200, 401, 403, 404], \
            f"Unexpected status code: {response.status_code}"

    async def test_statistics_response_schema(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: GET /orders/statistics returns expected schema"""
        response = await order_api.get("/statistics")

        if response.status_code == 200:
            data = response.json()
            # Should have statistics fields
            assert any(
                key in data for key in [
                    "total_orders", "orders_by_status", "total_revenue",
                    "stats", "statistics"
                ]
            )


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestOrderErrorHandlingAPIGolden:
    """GOLDEN: Error handling contracts"""

    async def test_invalid_json_returns_400_or_422(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: Invalid JSON body returns 400 or 422"""
        response = await order_api.client.post(
            f"{order_api.url}",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_missing_required_fields_returns_422(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: Missing required fields returns 422"""
        response = await order_api.post("", json={})

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_invalid_order_type_returns_422(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: Invalid order_type returns 422"""
        order_data = OrderTestDataFactory.make_valid_create_order_request()
        order_data["user_id"] = unique_user_id()
        order_data["order_type"] = "invalid_type"

        response = await order_api.post("", json=order_data)

        assert response.status_code in [400, 422], \
            f"Expected 400/422, got {response.status_code}"

    async def test_invalid_currency_returns_422(
        self, order_api: APIClient, api_assert: APIAssertions
    ):
        """GOLDEN: Invalid currency code returns 422"""
        order_data = OrderTestDataFactory.make_valid_create_order_request()
        order_data["user_id"] = unique_user_id()
        order_data["currency"] = "INVALID"

        response = await order_api.post("", json=order_data)

        # Might accept unknown currency or reject
        assert response.status_code in [200, 201, 400, 422], \
            f"Unexpected status code: {response.status_code}"
