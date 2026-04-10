"""
Fulfillment Service — Smoke tests for shipment lifecycle.

Port: 8254 (PORT env var)
Routes: /api/v1/fulfillment/...
"""

import os
import uuid

import httpx
import pytest

pytestmark = pytest.mark.smoke

BASE_URL = os.getenv("FULFILLMENT_SERVICE_URL", "http://localhost:8254")
TIMEOUT = 15.0

INTERNAL_HEADERS = {
    "X-Internal-Call": "true",
    "X-Internal-Service": "true",
    "X-Internal-Service-Secret": "dev-internal-secret-change-in-production",
    "user-id": "smoke-test-user",
}

_state: dict = {}


class TestFulfillmentHealthSmoke:
    @pytest.mark.asyncio
    async def test_health(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{BASE_URL}/health")
            assert resp.status_code == 200


class TestShipmentCRUDSmoke:
    @pytest.mark.asyncio
    async def test_create_shipment(self):
        order_id = f"smoke-order-{uuid.uuid4().hex[:8]}"
        _state["order_id"] = order_id

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/fulfillment/shipments",
                headers=INTERNAL_HEADERS,
                json={
                    "order_id": order_id,
                    "user_id": "smoke-test-user",
                    "items": [
                        {"sku": "SMOKE-001", "quantity": 1, "name": "Smoke Test Item"}
                    ],
                    "address": {
                        "line1": "123 Smoke Test St",
                        "city": "Test City",
                        "state": "TS",
                        "postal_code": "12345",
                        "country": "US",
                    },
                },
            )
            assert resp.status_code in (200, 201), (
                f"Create shipment failed: {resp.status_code} {resp.text[:200]}"
            )
            data = resp.json()
            _state["shipment_id"] = data.get("id") or data.get("shipment_id")

    @pytest.mark.asyncio
    async def test_get_shipment(self):
        order_id = _state.get("order_id")
        if not order_id:
            pytest.skip("No shipment created")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/fulfillment/shipments/{order_id}",
                headers=INTERNAL_HEADERS,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("order_id") == order_id

    @pytest.mark.asyncio
    async def test_create_shipping_label(self):
        shipment_id = _state.get("shipment_id")
        if not shipment_id:
            pytest.skip("No shipment created")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/fulfillment/shipments/{shipment_id}/label",
                headers=INTERNAL_HEADERS,
                json={},
            )
            # 200 = label created, 400/422 = missing carrier config (expected in test)
            assert resp.status_code in (200, 201, 400, 422)
            if resp.status_code in (200, 201):
                data = resp.json()
                tracking = data.get("tracking_number")
                if tracking:
                    _state["tracking_number"] = tracking

    @pytest.mark.asyncio
    async def test_get_by_tracking(self):
        tracking = _state.get("tracking_number")
        if not tracking:
            pytest.skip("No tracking number available")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/fulfillment/tracking/{tracking}",
                headers=INTERNAL_HEADERS,
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_cancel_shipment(self):
        shipment_id = _state.get("shipment_id")
        if not shipment_id:
            pytest.skip("No shipment created")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/fulfillment/shipments/{shipment_id}/cancel",
                headers=INTERNAL_HEADERS,
                json={"reason": "Smoke test cleanup"},
            )
            assert resp.status_code in (200, 204, 400)  # 400 if already cancelled
