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

    def test_admin_endpoints_reject_without_header(self, http_client):
        """All admin endpoints require X-Admin-Role: true"""
        endpoints = [
            ("POST", f"{ADMIN_BASE}/products"),
            ("PUT", f"{ADMIN_BASE}/products/test"),
            ("DELETE", f"{ADMIN_BASE}/products/test"),
            ("GET", f"{ADMIN_BASE}/cost-definitions"),
            ("GET", f"{ADMIN_BASE}/health/catalog-alignment"),
        ]
        for method, url in endpoints:
            response = http_client.request(method, url, json={})
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

    def test_create_product_returns_201(self, http_client, unique_id):
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
        assert response.status_code == 201

    def test_create_duplicate_product_returns_409(self, http_client, unique_id):
        payload = {
            "product_id": unique_id,
            "product_name": f"Test {unique_id}",
            "product_code": unique_id.upper(),
            "product_type": "other",
        }
        r1 = http_client.post(f"{ADMIN_BASE}/products", headers=ADMIN_HEADERS, json=payload)
        assert r1.status_code == 201
        r2 = http_client.post(f"{ADMIN_BASE}/products", headers=ADMIN_HEADERS, json=payload)
        assert r2.status_code == 409

    def test_update_product_returns_200(self, http_client, unique_id):
        http_client.post(f"{ADMIN_BASE}/products", headers=ADMIN_HEADERS, json={
            "product_id": unique_id,
            "product_name": f"Original {unique_id}",
            "product_code": f"CODE-{unique_id}",
            "product_type": "other",
        })
        response = http_client.put(
            f"{ADMIN_BASE}/products/{unique_id}",
            headers=ADMIN_HEADERS,
            json={"product_name": f"Updated {unique_id}"},
        )
        assert response.status_code == 200

    def test_update_nonexistent_product_returns_404(self, http_client):
        response = http_client.put(
            f"{ADMIN_BASE}/products/nonexistent_xyz",
            headers=ADMIN_HEADERS,
            json={"product_name": "Nope"},
        )
        assert response.status_code == 404

    def test_delete_product_returns_200(self, http_client, unique_id):
        http_client.post(f"{ADMIN_BASE}/products", headers=ADMIN_HEADERS, json={
            "product_id": unique_id,
            "product_name": f"ToDelete {unique_id}",
            "product_code": f"DEL-{unique_id}",
            "product_type": "other",
        })
        response = http_client.delete(
            f"{ADMIN_BASE}/products/{unique_id}",
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == unique_id

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
        # Create product first
        http_client.post(f"{ADMIN_BASE}/products", headers=ADMIN_HEADERS, json={
            "product_id": unique_id,
            "product_name": f"Priced {unique_id}",
            "product_code": f"PRC-{unique_id}",
            "product_type": "model_inference",
        })
        response = http_client.post(
            f"{ADMIN_BASE}/products/{unique_id}/pricing",
            headers=ADMIN_HEADERS,
            json={
                "pricing_id": f"pricing_{unique_id}",
                "tier_name": "base",
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
