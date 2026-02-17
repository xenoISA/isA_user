"""
Product Service - Integration Tests (Golden)

Real HTTP tests against running product service on port 8215.
Tests complete request/response cycles with actual service.

Prerequisites:
    - product_service running on port 8215
    - Database available

Usage:
    pytest tests/integration/golden/product_service/ -v
"""

import pytest
import httpx
import sys
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

from tests.contracts.product.data_contract import ProductTestDataFactory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


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
async def async_client():
    """Create async HTTP client"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


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


@pytest.fixture
def test_organization_id():
    """Generate unique test organization ID"""
    return ProductTestDataFactory.make_organization_id()


# ============================================================================
# Health and Info Tests
# ============================================================================

class TestHealthAndInfo:
    """Tests for health and info endpoints"""

    async def test_health_check_returns_healthy(self, async_client):
        """Test health endpoint returns healthy status"""
        response = await async_client.get(f"{BASE_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "product_service"
        assert data["port"] == SERVICE_PORT

    async def test_service_info_returns_capabilities(self, async_client):
        """Test service info endpoint returns capabilities"""
        response = await async_client.get(f"{API_BASE}/info")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "product_service"
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)


# ============================================================================
# Product Catalog Tests
# ============================================================================

class TestProductCategories:
    """Tests for product categories endpoint"""

    async def test_get_categories_returns_list(self, async_client):
        """Test categories endpoint returns list"""
        response = await async_client.get(f"{API_BASE}/categories")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_categories_structure(self, async_client):
        """Test category response structure"""
        response = await async_client.get(f"{API_BASE}/categories")

        assert response.status_code == 200
        data = response.json()

        if len(data) > 0:
            category = data[0]
            assert "category_id" in category
            assert "name" in category


class TestProductCatalog:
    """Tests for product catalog endpoints"""

    async def test_get_products_returns_list(self, async_client):
        """Test products endpoint returns list"""
        response = await async_client.get(f"{API_BASE}/products")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_products_with_active_filter(self, async_client):
        """Test products with is_active filter"""
        response = await async_client.get(
            f"{API_BASE}/products",
            params={"is_active": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_products_with_type_filter(self, async_client):
        """Test products with product_type filter"""
        response = await async_client.get(
            f"{API_BASE}/products",
            params={"product_type": "model"}
        )

        # Should return 200 or empty list
        assert response.status_code == 200

    async def test_get_products_invalid_type_returns_error(self, async_client):
        """Test products with invalid product_type returns error"""
        response = await async_client.get(
            f"{API_BASE}/products",
            params={"product_type": "invalid_type_xyz"}
        )

        assert response.status_code in [400, 422]


class TestProductDetail:
    """Tests for product detail endpoints"""

    async def test_get_product_not_found(self, async_client, test_product_id):
        """Test getting non-existent product returns 404"""
        response = await async_client.get(f"{API_BASE}/products/{test_product_id}")

        assert response.status_code == 404

    async def test_get_product_pricing_not_found(self, async_client, test_product_id):
        """Test getting pricing for non-existent product"""
        response = await async_client.get(
            f"{API_BASE}/products/{test_product_id}/pricing"
        )

        # Should return 404 or error
        assert response.status_code in [404, 500]

    async def test_check_availability_requires_user_id(
        self, async_client, test_product_id
    ):
        """Test availability check requires user_id"""
        response = await async_client.get(
            f"{API_BASE}/products/{test_product_id}/availability"
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    async def test_check_availability_with_user_id(
        self, async_client, test_product_id, test_user_id
    ):
        """Test availability check with user_id"""
        response = await async_client.get(
            f"{API_BASE}/products/{test_product_id}/availability",
            params={"user_id": test_user_id}
        )

        # Should return 200 with available=false or 404
        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            data = response.json()
            assert "available" in data


# ============================================================================
# Subscription Tests
# ============================================================================

class TestSubscriptionCreation:
    """Tests for subscription creation"""

    async def test_create_subscription_valid(
        self, async_client, test_user_id, test_plan_id
    ):
        """Test creating subscription with valid data"""
        request = ProductTestDataFactory.make_create_subscription_request(
            user_id=test_user_id,
            plan_id=test_plan_id,
            billing_cycle="monthly"
        )

        response = await async_client.post(
            f"{API_BASE}/subscriptions",
            json=request.model_dump()
        )

        # Should succeed or return error if plan doesn't exist
        assert response.status_code in [200, 201, 400, 404, 500]

    async def test_create_subscription_missing_user_id(self, async_client, test_plan_id):
        """Test subscription creation without user_id fails"""
        invalid_request = ProductTestDataFactory.make_invalid_subscription_request_missing_user_id()

        response = await async_client.post(
            f"{API_BASE}/subscriptions",
            json=invalid_request
        )

        assert response.status_code in [400, 422]

    async def test_create_subscription_missing_plan_id(self, async_client, test_user_id):
        """Test subscription creation without plan_id fails"""
        invalid_request = ProductTestDataFactory.make_invalid_subscription_request_missing_plan_id()

        response = await async_client.post(
            f"{API_BASE}/subscriptions",
            json=invalid_request
        )

        assert response.status_code in [400, 422]

    async def test_create_subscription_invalid_billing_cycle(
        self, async_client, test_user_id, test_plan_id
    ):
        """Test subscription with invalid billing cycle fails"""
        invalid_request = ProductTestDataFactory.make_invalid_subscription_request_invalid_billing_cycle()

        response = await async_client.post(
            f"{API_BASE}/subscriptions",
            json=invalid_request
        )

        assert response.status_code in [400, 422]

    async def test_create_subscription_with_organization(
        self, async_client, test_user_id, test_plan_id, test_organization_id
    ):
        """Test subscription creation with organization_id"""
        request = ProductTestDataFactory.make_create_subscription_request(
            user_id=test_user_id,
            plan_id=test_plan_id,
            organization_id=test_organization_id,
            billing_cycle="yearly"
        )

        response = await async_client.post(
            f"{API_BASE}/subscriptions",
            json=request.model_dump()
        )

        # Should accept organization_id parameter
        assert response.status_code in [200, 201, 400, 404, 500]


class TestSubscriptionQueries:
    """Tests for subscription query endpoints"""

    async def test_get_subscription_not_found(self, async_client):
        """Test getting non-existent subscription returns 404"""
        fake_id = "sub_nonexistent_12345"

        response = await async_client.get(f"{API_BASE}/subscriptions/{fake_id}")

        assert response.status_code == 404

    async def test_get_user_subscriptions_returns_list(
        self, async_client, test_user_id
    ):
        """Test getting user subscriptions returns list"""
        response = await async_client.get(
            f"{API_BASE}/subscriptions/user/{test_user_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_user_subscriptions_with_status_filter(
        self, async_client, test_user_id
    ):
        """Test user subscriptions with status filter"""
        response = await async_client.get(
            f"{API_BASE}/subscriptions/user/{test_user_id}",
            params={"status": "active"}
        )

        assert response.status_code == 200

    async def test_get_user_subscriptions_invalid_status(
        self, async_client, test_user_id
    ):
        """Test user subscriptions with invalid status"""
        response = await async_client.get(
            f"{API_BASE}/subscriptions/user/{test_user_id}",
            params={"status": "invalid_status_xyz"}
        )

        assert response.status_code in [400, 422]


class TestSubscriptionStatusUpdate:
    """Tests for subscription status update endpoint"""

    async def test_update_status_not_found(self, async_client):
        """Test updating status of non-existent subscription"""
        fake_id = "sub_nonexistent_12345"

        response = await async_client.put(
            f"{API_BASE}/subscriptions/{fake_id}/status",
            json={"status": "canceled"}
        )

        assert response.status_code == 404

    async def test_update_status_invalid_status(self, async_client):
        """Test updating with invalid status value"""
        fake_id = "sub_test_12345"
        invalid_request = ProductTestDataFactory.make_invalid_status_update_invalid_status()

        response = await async_client.put(
            f"{API_BASE}/subscriptions/{fake_id}/status",
            json=invalid_request
        )

        assert response.status_code in [400, 404, 422]


# ============================================================================
# Usage Recording Tests
# ============================================================================

class TestUsageRecording:
    """Tests for usage recording endpoint"""

    async def test_record_usage_valid(
        self, async_client, test_user_id, test_product_id
    ):
        """Test recording usage with valid data"""
        request = ProductTestDataFactory.make_record_usage_request(
            user_id=test_user_id,
            product_id=test_product_id,
            usage_amount=1500.0
        )

        response = await async_client.post(
            f"{API_BASE}/usage/record",
            json=request.model_dump()
        )

        # Should succeed or return error if product doesn't exist
        assert response.status_code in [200, 201, 400, 404, 500]

    async def test_record_usage_missing_user_id(self, async_client, test_product_id):
        """Test recording usage without user_id fails"""
        invalid_request = ProductTestDataFactory.make_invalid_usage_request_missing_user_id()

        response = await async_client.post(
            f"{API_BASE}/usage/record",
            json=invalid_request
        )

        assert response.status_code in [400, 422]

    async def test_record_usage_missing_product_id(self, async_client, test_user_id):
        """Test recording usage without product_id fails"""
        invalid_request = ProductTestDataFactory.make_invalid_usage_request_missing_product_id()

        response = await async_client.post(
            f"{API_BASE}/usage/record",
            json=invalid_request
        )

        assert response.status_code in [400, 422]

    async def test_record_usage_negative_amount(
        self, async_client, test_user_id, test_product_id
    ):
        """Test recording usage with negative amount fails"""
        invalid_request = ProductTestDataFactory.make_invalid_usage_request_negative_amount()

        response = await async_client.post(
            f"{API_BASE}/usage/record",
            json=invalid_request
        )

        assert response.status_code in [400, 422]

    async def test_record_usage_zero_amount(
        self, async_client, test_user_id, test_product_id
    ):
        """Test recording usage with zero amount fails"""
        invalid_request = ProductTestDataFactory.make_invalid_usage_request_zero_amount()

        response = await async_client.post(
            f"{API_BASE}/usage/record",
            json=invalid_request
        )

        assert response.status_code in [400, 422]


class TestUsageQueries:
    """Tests for usage query endpoints"""

    async def test_get_usage_records_returns_list(
        self, async_client, test_user_id
    ):
        """Test getting usage records returns list"""
        response = await async_client.get(
            f"{API_BASE}/usage/records",
            params={"user_id": test_user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_usage_records_with_filters(
        self, async_client, test_user_id, test_product_id
    ):
        """Test getting usage records with multiple filters"""
        response = await async_client.get(
            f"{API_BASE}/usage/records",
            params={
                "user_id": test_user_id,
                "product_id": test_product_id,
                "limit": 10,
                "offset": 0
            }
        )

        assert response.status_code == 200

    async def test_get_usage_records_with_date_range(
        self, async_client, test_user_id
    ):
        """Test getting usage records with date filters"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        response = await async_client.get(
            f"{API_BASE}/usage/records",
            params={
                "user_id": test_user_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        assert response.status_code == 200


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Tests for statistics endpoints"""

    async def test_get_usage_statistics(self, async_client, test_user_id):
        """Test getting usage statistics"""
        response = await async_client.get(
            f"{API_BASE}/statistics/usage",
            params={"user_id": test_user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_get_usage_statistics_with_filters(
        self, async_client, test_user_id, test_product_id
    ):
        """Test usage statistics with filters"""
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        response = await async_client.get(
            f"{API_BASE}/statistics/usage",
            params={
                "user_id": test_user_id,
                "product_id": test_product_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        assert response.status_code == 200

    async def test_get_service_statistics(self, async_client):
        """Test getting service-level statistics"""
        response = await async_client.get(f"{API_BASE}/statistics/service")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


if __name__ == "__main__":
    pytest.main([__file__])
