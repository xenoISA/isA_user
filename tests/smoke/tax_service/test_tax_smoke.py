"""
Tax Service — Smoke tests for tax calculation.

Port: 8253 (PORT env var)
Routes: /api/v1/tax/...
"""

import uuid

import httpx
import pytest

from tests.smoke.conftest import resolve_base_url, resolve_service_url

pytestmark = pytest.mark.smoke

BASE_URL = resolve_base_url("tax_service", "TAX_SERVICE_URL")
HEALTH_URL = resolve_service_url("tax_service", "/health", "TAX_SERVICE_URL")
TIMEOUT = 15.0

INTERNAL_HEADERS = {
    "X-Internal-Call": "true",
    "X-Internal-Service": "true",
    "X-Internal-Service-Secret": "dev-internal-secret-change-in-production",
    "user-id": "smoke-test-user",
}

_state: dict = {}


class TestTaxHealthSmoke:
    @pytest.mark.asyncio
    async def test_health(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(HEALTH_URL)
            assert resp.status_code == 200


class TestTaxCalculationSmoke:
    @pytest.mark.asyncio
    async def test_calculate_tax(self):
        order_id = f"smoke-tax-{uuid.uuid4().hex[:8]}"
        _state["order_id"] = order_id

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/tax/calculate",
                headers=INTERNAL_HEADERS,
                json={
                    "order_id": order_id,
                    "user_id": "smoke-test-user",
                    "currency": "USD",
                    "items": [
                        {
                            "sku": "SMOKE-TAX-001",
                            "quantity": 1,
                            "unit_price": 99.99,
                            "name": "Smoke Test Item",
                        }
                    ],
                    "address": {
                        "state": "CA",
                        "postal_code": "94105",
                        "country": "US",
                    },
                },
            )
            assert resp.status_code in (
                200,
                201,
            ), f"Tax calc failed: {resp.status_code} {resp.text[:200]}"
            data = resp.json()
            # Should return tax amount and breakdown
            assert "total_tax" in data or "tax_amount" in data or "amount" in data

    @pytest.mark.asyncio
    async def test_calculate_tax_stateless(self):
        """Tax calculation without order_id (preview mode)."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/tax/calculate",
                headers=INTERNAL_HEADERS,
                json={
                    "user_id": "smoke-test-user",
                    "currency": "USD",
                    "items": [
                        {"sku": "PREVIEW-001", "quantity": 2, "unit_price": 49.99}
                    ],
                    "address": {
                        "state": "NY",
                        "postal_code": "10001",
                        "country": "US",
                    },
                },
            )
            assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_get_tax_calculation(self):
        order_id = _state.get("order_id")
        if not order_id:
            pytest.skip("No tax calculation created")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/tax/calculations/{order_id}",
                headers=INTERNAL_HEADERS,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("order_id") == order_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_calculation(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/tax/calculations/nonexistent-order",
                headers=INTERNAL_HEADERS,
            )
            assert resp.status_code == 404
