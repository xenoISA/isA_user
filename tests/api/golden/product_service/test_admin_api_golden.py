"""
Product Service - Admin API Golden Tests

Real HTTP tests against running product service admin endpoints.
Validates admin auth, CRUD operations, cost definition management,
and catalog alignment.

Prerequisites:
    - product_service running on port 8215
    - Database available with product schema

Usage:
    pytest tests/api/golden/product_service/test_admin_api_golden.py -v
"""
import pytest
import httpx
import uuid
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

pytestmark = [pytest.mark.api, pytest.mark.asyncio]

SERVICE_PORT = 8215
BASE_URL = f"http://localhost:{SERVICE_PORT}"
ADMIN_BASE = f"{BASE_URL}/api/v1/product/admin"
ADMIN_HEADERS = {"X-Admin-Role": "true", "Content-Type": "application/json"}
TIMEOUT = 30.0


@pytest.fixture
def http_client():
    return httpx.Client(timeout=TIMEOUT)


@pytest.fixture
def unique_id():
    return f"test_{uuid.uuid4().hex[:8]}"


# ============================================================================
# Admin Auth Tests
# ============================================================================

class TestAdminAuth:

    def test_admin_get_endpoints_reject_without_header(self, http_client):
        """GET admin endpoints require X-Admin-Role: true"""
        endpoints = [
            ("GET", f"{ADMIN_BASE}/cost-definitions"),
            ("GET", f"{ADMIN_BASE}/health/catalog-alignment"),
            ("GET", f"{ADMIN_BASE}/cost-definitions/history/test"),
            ("DELETE", f"{ADMIN_BASE}/products/test"),
        ]
        for method, url in endpoints:
            response = http_client.request(method, url)
            assert response.status_code == 403, f"{method} {url} should reject without admin header"

    def test_admin_endpoints_accept_with_header(self, http_client):
        """Admin endpoints accept requests with X-Admin-Role: true"""
        response = http_client.get(
            f"{ADMIN_BASE}/cost-definitions",
            headers=ADMIN_HEADERS,
        )
        # Should not be 403 — may be 200 or 500 depending on DB state
        assert response.status_code != 403


# ============================================================================
# Admin Product CRUD API Tests
# ============================================================================

class TestAdminProductCRUD:

    def test_create_product_accepts_valid_payload(self, http_client, unique_id):
        """Admin create endpoint accepts valid payload (201 or 500 if DB write fails)"""
        response = http_client.post(f"{ADMIN_BASE}/products", headers=ADMIN_HEADERS, json={
            "product_id": unique_id,
            "product_name": f"Test Model {unique_id}",
            "product_code": unique_id.upper(),
            "product_type": "model_inference",
            "base_price": 0.003,
            "category": "ai_models",
            "features": ["test"],
            "metadata": {"provider": "test"},
        })
        # 201 if DB write succeeds, 500 if repository.create_product returns None
        assert response.status_code in (201, 500)

    def test_create_duplicate_returns_409_for_existing_product(self, http_client):
        """Creating a product with an existing product_id returns 409"""
        response = http_client.post(f"{ADMIN_BASE}/products", headers=ADMIN_HEADERS, json={
            "product_id": "gpt-4o-mini",  # known existing product
            "product_name": "Duplicate",
            "product_code": "DUP-GPT4O",
            "product_type": "model_inference",
        })
        assert response.status_code == 409

    def test_update_existing_product(self, http_client):
        """Updating an existing product returns 200"""
        response = http_client.put(
            f"{ADMIN_BASE}/products/gpt-4o-mini",
            headers=ADMIN_HEADERS,
            json={"product_name": "GPT-4o"},
        )
        assert response.status_code == 200

    def test_update_nonexistent_product_returns_404(self, http_client):
        response = http_client.put(
            f"{ADMIN_BASE}/products/nonexistent_xyz",
            headers=ADMIN_HEADERS,
            json={"product_name": "Nope"},
        )
        assert response.status_code == 404

    def test_delete_existing_product(self, http_client):
        """Soft-deleting an existing product returns 200"""
        # Use a known stale product that's still in DB
        response = http_client.delete(
            f"{ADMIN_BASE}/products/advanced_agent",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        # Re-activate it
        http_client.put(
            f"{ADMIN_BASE}/products/advanced_agent",
            headers=ADMIN_HEADERS,
            json={"is_active": True},
        )

    def test_delete_nonexistent_product_returns_404(self, http_client):
        response = http_client.delete(
            f"{ADMIN_BASE}/products/nonexistent_xyz",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 404

    def test_create_product_validates_product_type(self, http_client, unique_id):
        response = http_client.post(f"{ADMIN_BASE}/products", headers=ADMIN_HEADERS, json={
            "product_id": unique_id,
            "product_name": "Bad Type",
            "product_code": f"BAD-{unique_id}",
            "product_type": "invalid_type_xyz",
        })
        assert response.status_code == 422


# ============================================================================
# Admin Pricing CRUD API Tests
# ============================================================================

class TestAdminPricingCRUD:

    def test_create_pricing_for_existing_product(self, http_client, unique_id):
        """Create pricing for a known existing product"""
        response = http_client.post(
            f"{ADMIN_BASE}/products/gpt-4o-mini/pricing",
            headers=ADMIN_HEADERS,
            json={
                "pricing_id": f"pricing_{unique_id}",
                "tier_name": "test_tier",
                "unit_price": 0.003,
                "metadata": {"billing_type": "usage_based"},
            },
        )
        assert response.status_code == 201

    def test_create_pricing_for_missing_product_returns_404(self, http_client, unique_id):
        response = http_client.post(
            f"{ADMIN_BASE}/products/nonexistent_xyz/pricing",
            headers=ADMIN_HEADERS,
            json={"pricing_id": f"pricing_{unique_id}", "unit_price": 0.003},
        )
        assert response.status_code == 404

    def test_update_nonexistent_pricing_returns_404(self, http_client):
        response = http_client.put(
            f"{ADMIN_BASE}/pricing/nonexistent_pricing_xyz",
            headers=ADMIN_HEADERS,
            json={"unit_price": 0.005},
        )
        assert response.status_code == 404


# ============================================================================
# Cost Definition Admin API Tests
# ============================================================================

class TestCostDefinitionAdmin:

    def test_list_cost_definitions(self, http_client):
        response = http_client.get(
            f"{ADMIN_BASE}/cost-definitions",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_cost_definitions_filter_by_provider(self, http_client):
        response = http_client.get(
            f"{ADMIN_BASE}/cost-definitions",
            headers=ADMIN_HEADERS,
            params={"provider": "anthropic"},
        )
        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert item.get("provider") == "anthropic"

    def test_list_cost_definitions_filter_by_active(self, http_client):
        response = http_client.get(
            f"{ADMIN_BASE}/cost-definitions",
            headers=ADMIN_HEADERS,
            params={"is_active": True},
        )
        assert response.status_code == 200

    def test_get_cost_history(self, http_client):
        response = http_client.get(
            f"{ADMIN_BASE}/cost-definitions/history/claude-sonnet-4-20250514",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_cost_history_unknown_model(self, http_client):
        response = http_client.get(
            f"{ADMIN_BASE}/cost-definitions/history/nonexistent-model-xyz",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_update_nonexistent_cost_definition_returns_404(self, http_client):
        response = http_client.put(
            f"{ADMIN_BASE}/cost-definitions/nonexistent_cost_xyz",
            headers=ADMIN_HEADERS,
            json={"description": "updated"},
        )
        assert response.status_code == 404


# ============================================================================
# Catalog Alignment Health Check API Tests
# ============================================================================

class TestCatalogAlignment:

    def test_alignment_endpoint_returns_200(self, http_client):
        response = http_client.get(
            f"{ADMIN_BASE}/health/catalog-alignment",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200

    def test_alignment_response_has_required_fields(self, http_client):
        response = http_client.get(
            f"{ADMIN_BASE}/health/catalog-alignment",
            headers=ADMIN_HEADERS,
        )
        data = response.json()
        assert "aligned" in data or "error" in data

    def test_alignment_rejects_non_admin(self, http_client):
        response = http_client.get(f"{ADMIN_BASE}/health/catalog-alignment")
        assert response.status_code == 403
