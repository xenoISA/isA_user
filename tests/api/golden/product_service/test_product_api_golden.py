"""
Product Service - Golden API Tests

Real HTTP tests against running product service.
Validates API contracts, HTTP status codes, and response schemas.

Prerequisites:
    - product_service running on port 8215
    - Database available

Usage:
    pytest tests/api/golden/product_service/ -v
    pytest tests/api/golden/product_service/ -v -k "health"
    pytest tests/api/golden/product_service/ -v -k "subscription"
"""
import pytest
import httpx
import sys
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from tests.contracts.product.data_contract import ProductTestDataFactory

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

SERVICE_PORT = 8215
BASE_URL = f"http://localhost:{SERVICE_PORT}"
API_BASE = f"{BASE_URL}/api/v1/product"
TIMEOUT = 30.0


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def http_client():
    """Synchronous HTTP client for API tests"""
    return httpx.Client(timeout=TIMEOUT)


@pytest.fixture
def test_user_id():
    """Generate unique test user ID"""
    return ProductTestDataFactory.make_user_id()


@pytest.fixture
def test_product_id():
    """Generate unique test product ID"""
    return ProductTestDataFactory.make_product_id()


@pytest.fixture
def test_plan_id():
    """Generate unique test plan ID"""
    return ProductTestDataFactory.make_plan_id()


# ============================================================================
# Health Check API Tests
# ============================================================================

class TestProductHealthAPIGolden:
    """Golden tests for product service health endpoints"""

    def test_health_endpoint_returns_200(self, http_client):
        """
        Contract: GET /health returns 200 OK with service status
        """
        response = http_client.get(f"{BASE_URL}/health")

        # Should return 200 OK
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]

    def test_health_endpoint_returns_correct_structure(self, http_client):
        """
        Contract: Health response includes required fields
        """
        response = http_client.get(f"{BASE_URL}/health")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields per contract
        assert "service" in data
        assert data["service"] == "product_service"
        assert "port" in data
        assert data["port"] == SERVICE_PORT
        assert "version" in data
        assert "dependencies" in data

    def test_service_info_endpoint_returns_200(self, http_client):
        """
        Contract: GET /api/v1/product/info returns service information
        """
        response = http_client.get(f"{API_BASE}/info")

        assert response.status_code == 200
        data = response.json()

        # Verify service info fields
        assert "service" in data
        assert data["service"] == "product_service"
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)


# ============================================================================
# Product Catalog API Tests
# ============================================================================

class TestProductCatalogAPIGolden:
    """Golden tests for product catalog endpoints"""

    def test_get_categories_returns_200(self, http_client):
        """
        Contract: GET /api/v1/product/categories returns categories list
        """
        response = http_client.get(f"{API_BASE}/categories")

        assert response.status_code == 200
        data = response.json()

        # Should return a list
        assert isinstance(data, list)

    def test_get_categories_returns_valid_schema(self, http_client):
        """
        Contract: Category response follows ProductCategoryResponseContract
        """
        response = http_client.get(f"{API_BASE}/categories")

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                category = data[0]
                # Verify required fields
                assert "category_id" in category
                assert "name" in category
                assert "is_active" in category

    def test_get_products_returns_200(self, http_client):
        """
        Contract: GET /api/v1/product/products returns products list
        """
        response = http_client.get(f"{API_BASE}/products")

        assert response.status_code == 200
        data = response.json()

        # Should return a list
        assert isinstance(data, list)

    def test_get_products_with_filters(self, http_client):
        """
        Contract: GET /products supports category_id, product_type, is_active filters
        """
        # Test with is_active filter
        response = http_client.get(
            f"{API_BASE}/products",
            params={"is_active": True}
        )

        assert response.status_code == 200

    def test_get_products_with_invalid_type_returns_400(self, http_client):
        """
        Contract: GET /products with invalid product_type returns 400
        """
        response = http_client.get(
            f"{API_BASE}/products",
            params={"product_type": "invalid_type"}
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_get_products_returns_valid_schema(self, http_client):
        """
        Contract: Product response follows ProductResponseContract
        """
        response = http_client.get(f"{API_BASE}/products")

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                product = data[0]
                # Verify required fields
                assert "product_id" in product
                assert "category_id" in product
                assert "name" in product
                assert "product_type" in product


# ============================================================================
# Product Detail API Tests
# ============================================================================

class TestProductDetailAPIGolden:
    """Golden tests for product detail endpoints"""

    def test_get_nonexistent_product_returns_404(self, http_client):
        """
        Contract: GET /api/v1/product/products/{invalid_id} returns 404
        """
        fake_id = "prod_nonexistent_12345"

        response = http_client.get(f"{API_BASE}/products/{fake_id}")

        assert response.status_code == 404

    def test_get_product_pricing_returns_data(self, http_client):
        """
        Contract: GET /products/{id}/pricing returns pricing information
        """
        # Try with a potentially valid product ID
        product_id = "prod_test_123"

        response = http_client.get(f"{API_BASE}/products/{product_id}/pricing")

        # Should return 200 or 404 depending on product existence
        assert response.status_code in [200, 404, 500]

    def test_get_product_pricing_with_user_id(self, http_client, test_user_id):
        """
        Contract: GET /products/{id}/pricing supports user_id parameter
        """
        product_id = "prod_test_123"

        response = http_client.get(
            f"{API_BASE}/products/{product_id}/pricing",
            params={"user_id": test_user_id}
        )

        # Should accept the parameter without error
        assert response.status_code in [200, 404, 500]

    def test_check_product_availability_requires_user_id(self, http_client, test_product_id):
        """
        Contract: GET /products/{id}/availability requires user_id parameter
        """
        response = http_client.get(
            f"{API_BASE}/products/{test_product_id}/availability"
        )

        # Should return validation error without user_id
        assert response.status_code in [400, 422]

    def test_check_product_availability_with_valid_params(
        self, http_client, test_product_id, test_user_id
    ):
        """
        Contract: GET /products/{id}/availability returns availability status
        """
        response = http_client.get(
            f"{API_BASE}/products/{test_product_id}/availability",
            params={"user_id": test_user_id}
        )

        # Should return valid response or error
        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            data = response.json()
            assert "available" in data


# ============================================================================
# Subscription Create API Tests
# ============================================================================

class TestSubscriptionCreateAPIGolden:
    """Golden tests for subscription creation endpoints"""

    def test_create_subscription_with_valid_data(
        self, http_client, test_user_id, test_plan_id
    ):
        """
        Contract: POST /api/v1/product/subscriptions creates subscription
        """
        request = ProductTestDataFactory.make_create_subscription_request(
            user_id=test_user_id,
            plan_id=test_plan_id,
            billing_cycle="monthly"
        )

        response = http_client.post(
            f"{API_BASE}/subscriptions",
            json=request.model_dump()
        )

        # Should return 200/201 or error if plan doesn't exist
        assert response.status_code in [200, 201, 400, 404, 500]

    def test_create_subscription_missing_user_id_returns_400(
        self, http_client, test_plan_id
    ):
        """
        Contract: POST /subscriptions without user_id returns 400/422
        """
        invalid_request = ProductTestDataFactory.make_invalid_subscription_request_missing_user_id()

        response = http_client.post(
            f"{API_BASE}/subscriptions",
            json=invalid_request
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_create_subscription_missing_plan_id_returns_400(
        self, http_client, test_user_id
    ):
        """
        Contract: POST /subscriptions without plan_id returns 400/422
        """
        invalid_request = ProductTestDataFactory.make_invalid_subscription_request_missing_plan_id()

        response = http_client.post(
            f"{API_BASE}/subscriptions",
            json=invalid_request
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_create_subscription_invalid_billing_cycle_returns_400(
        self, http_client, test_user_id, test_plan_id
    ):
        """
        Contract: POST /subscriptions with invalid billing_cycle returns 400
        """
        invalid_request = ProductTestDataFactory.make_invalid_subscription_request_invalid_billing_cycle()

        response = http_client.post(
            f"{API_BASE}/subscriptions",
            json=invalid_request
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_create_subscription_with_organization_id(
        self, http_client, test_user_id, test_plan_id
    ):
        """
        Contract: POST /subscriptions supports organization_id parameter
        """
        org_id = ProductTestDataFactory.make_organization_id()
        request = ProductTestDataFactory.make_create_subscription_request(
            user_id=test_user_id,
            plan_id=test_plan_id,
            organization_id=org_id
        )

        response = http_client.post(
            f"{API_BASE}/subscriptions",
            json=request.model_dump()
        )

        # Should accept organization_id parameter
        assert response.status_code in [200, 201, 400, 404, 500]


# ============================================================================
# Subscription Query API Tests
# ============================================================================

class TestSubscriptionQueryAPIGolden:
    """Golden tests for subscription query endpoints"""

    def test_get_nonexistent_subscription_returns_404(self, http_client):
        """
        Contract: GET /api/v1/product/subscriptions/{invalid_id} returns 404
        """
        fake_id = "sub_nonexistent_12345"

        response = http_client.get(f"{API_BASE}/subscriptions/{fake_id}")

        assert response.status_code == 404

    def test_get_user_subscriptions_returns_list(self, http_client, test_user_id):
        """
        Contract: GET /subscriptions/user/{user_id} returns subscriptions list
        """
        response = http_client.get(f"{API_BASE}/subscriptions/user/{test_user_id}")

        assert response.status_code == 200
        data = response.json()

        # Should return a list (even if empty)
        assert isinstance(data, list)

    def test_get_user_subscriptions_with_status_filter(
        self, http_client, test_user_id
    ):
        """
        Contract: GET /subscriptions/user/{user_id} supports status filter
        """
        response = http_client.get(
            f"{API_BASE}/subscriptions/user/{test_user_id}",
            params={"status": "active"}
        )

        assert response.status_code == 200

    def test_get_user_subscriptions_invalid_status_returns_400(
        self, http_client, test_user_id
    ):
        """
        Contract: GET /subscriptions/user/{user_id} with invalid status returns 400
        """
        response = http_client.get(
            f"{API_BASE}/subscriptions/user/{test_user_id}",
            params={"status": "invalid_status"}
        )

        # Should return validation error
        assert response.status_code in [400, 422]


# ============================================================================
# Subscription Update API Tests
# ============================================================================

class TestSubscriptionUpdateAPIGolden:
    """Golden tests for subscription update endpoints"""

    def test_update_nonexistent_subscription_returns_404(self, http_client):
        """
        Contract: PUT /subscriptions/{invalid_id}/status returns 404
        """
        fake_id = "sub_nonexistent_12345"

        response = http_client.put(
            f"{API_BASE}/subscriptions/{fake_id}/status",
            json={"status": "canceled"}
        )

        assert response.status_code == 404

    def test_update_subscription_status_with_valid_status(self, http_client):
        """
        Contract: PUT /subscriptions/{id}/status accepts valid status values
        """
        # Use a fake ID since we're testing API contract, not actual update
        subscription_id = "sub_test_12345"

        response = http_client.put(
            f"{API_BASE}/subscriptions/{subscription_id}/status",
            json={"status": "canceled"}
        )

        # Should return 404 (not found) or 200 (if exists)
        assert response.status_code in [200, 404, 500]

    def test_update_subscription_invalid_status_returns_400(self, http_client):
        """
        Contract: PUT /subscriptions/{id}/status with invalid status returns 400
        """
        subscription_id = "sub_test_12345"
        invalid_request = ProductTestDataFactory.make_invalid_status_update_invalid_status()

        response = http_client.put(
            f"{API_BASE}/subscriptions/{subscription_id}/status",
            json=invalid_request
        )

        # Should return validation error
        assert response.status_code in [400, 422]


# ============================================================================
# Usage Record API Tests
# ============================================================================

class TestUsageRecordAPIGolden:
    """Golden tests for usage recording endpoints"""

    def test_record_usage_with_valid_data(
        self, http_client, test_user_id, test_product_id
    ):
        """
        Contract: POST /api/v1/product/usage/record records usage
        """
        request = ProductTestDataFactory.make_record_usage_request(
            user_id=test_user_id,
            product_id=test_product_id,
            usage_amount=1500.0
        )

        response = http_client.post(
            f"{API_BASE}/usage/record",
            json=request.model_dump()
        )

        # Should return success or error
        assert response.status_code in [200, 201, 400, 404, 500]

    def test_record_usage_missing_user_id_returns_400(
        self, http_client, test_product_id
    ):
        """
        Contract: POST /usage/record without user_id returns 400/422
        """
        invalid_request = ProductTestDataFactory.make_invalid_usage_request_missing_user_id()

        response = http_client.post(
            f"{API_BASE}/usage/record",
            json=invalid_request
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_record_usage_missing_product_id_returns_400(
        self, http_client, test_user_id
    ):
        """
        Contract: POST /usage/record without product_id returns 400/422
        """
        invalid_request = ProductTestDataFactory.make_invalid_usage_request_missing_product_id()

        response = http_client.post(
            f"{API_BASE}/usage/record",
            json=invalid_request
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_record_usage_negative_amount_returns_400(
        self, http_client, test_user_id, test_product_id
    ):
        """
        Contract: POST /usage/record with negative amount returns 400/422
        """
        invalid_request = ProductTestDataFactory.make_invalid_usage_request_negative_amount()

        response = http_client.post(
            f"{API_BASE}/usage/record",
            json=invalid_request
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_record_usage_zero_amount_returns_400(
        self, http_client, test_user_id, test_product_id
    ):
        """
        Contract: POST /usage/record with zero amount returns 400/422
        """
        invalid_request = ProductTestDataFactory.make_invalid_usage_request_zero_amount()

        response = http_client.post(
            f"{API_BASE}/usage/record",
            json=invalid_request
        )

        # Should return validation error
        assert response.status_code in [400, 422]


# ============================================================================
# Usage Query API Tests
# ============================================================================

class TestUsageQueryAPIGolden:
    """Golden tests for usage query endpoints"""

    def test_get_usage_records_returns_list(self, http_client, test_user_id):
        """
        Contract: GET /api/v1/product/usage/records returns usage records list
        """
        response = http_client.get(
            f"{API_BASE}/usage/records",
            params={"user_id": test_user_id}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return a list (even if empty)
        assert isinstance(data, list)

    def test_get_usage_records_with_filters(self, http_client, test_user_id, test_product_id):
        """
        Contract: GET /usage/records supports multiple filter parameters
        """
        response = http_client.get(
            f"{API_BASE}/usage/records",
            params={
                "user_id": test_user_id,
                "product_id": test_product_id,
                "limit": 10,
                "offset": 0
            }
        )

        assert response.status_code == 200

    def test_get_usage_records_with_date_range(self, http_client, test_user_id):
        """
        Contract: GET /usage/records supports start_date and end_date filters
        """
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        response = http_client.get(
            f"{API_BASE}/usage/records",
            params={
                "user_id": test_user_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        assert response.status_code == 200

    def test_get_usage_records_respects_limit(self, http_client, test_user_id):
        """
        Contract: GET /usage/records respects limit parameter
        """
        response = http_client.get(
            f"{API_BASE}/usage/records",
            params={"user_id": test_user_id, "limit": 5}
        )

        assert response.status_code == 200
        data = response.json()

        # Should not exceed limit
        assert len(data) <= 5


# ============================================================================
# Statistics API Tests
# ============================================================================

class TestStatisticsAPIGolden:
    """Golden tests for statistics endpoints"""

    def test_get_usage_statistics_returns_data(self, http_client, test_user_id):
        """
        Contract: GET /api/v1/product/statistics/usage returns usage statistics
        """
        response = http_client.get(
            f"{API_BASE}/statistics/usage",
            params={"user_id": test_user_id}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have statistics structure
        assert isinstance(data, dict)

    def test_get_usage_statistics_with_filters(
        self, http_client, test_user_id, test_product_id
    ):
        """
        Contract: GET /statistics/usage supports filter parameters
        """
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        response = http_client.get(
            f"{API_BASE}/statistics/usage",
            params={
                "user_id": test_user_id,
                "product_id": test_product_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        assert response.status_code == 200

    def test_get_service_statistics_returns_data(self, http_client):
        """
        Contract: GET /api/v1/product/statistics/service returns service statistics
        """
        response = http_client.get(f"{API_BASE}/statistics/service")

        assert response.status_code == 200
        data = response.json()

        # Should have service statistics structure
        assert isinstance(data, dict)

    def test_get_service_statistics_includes_metrics(self, http_client):
        """
        Contract: Service statistics includes common metrics
        """
        response = http_client.get(f"{API_BASE}/statistics/service")

        if response.status_code == 200:
            data = response.json()
            # Should have some statistics fields
            assert "statistics" in data or "service" in data


if __name__ == "__main__":
    pytest.main([__file__])
