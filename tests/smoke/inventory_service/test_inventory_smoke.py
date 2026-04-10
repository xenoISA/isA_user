"""
Inventory Service — Smoke tests for inventory reservation lifecycle.

Port: 8252 (PORT env var)
Routes: /api/v1/inventory/...
"""

import os
import uuid

import httpx
import pytest

pytestmark = pytest.mark.smoke

BASE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8252")
TIMEOUT = 15.0

INTERNAL_HEADERS = {
    "X-Internal-Call": "true",
    "X-Internal-Service": "true",
    "X-Internal-Service-Secret": "dev-internal-secret-change-in-production",
    "user-id": "smoke-test-user",
}

_state: dict = {}


class TestInventoryHealthSmoke:
    @pytest.mark.asyncio
    async def test_health(self):
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{BASE_URL}/health")
            assert resp.status_code == 200


class TestInventoryReservationSmoke:
    @pytest.mark.asyncio
    async def test_reserve_inventory(self):
        order_id = f"smoke-order-{uuid.uuid4().hex[:8]}"
        _state["order_id"] = order_id

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/inventory/reserve",
                headers=INTERNAL_HEADERS,
                json={
                    "order_id": order_id,
                    "user_id": "smoke-test-user",
                    "items": [
                        {"sku": "SMOKE-ITEM-001", "quantity": 1}
                    ],
                },
            )
            assert resp.status_code in (200, 201), (
                f"Reserve failed: {resp.status_code} {resp.text[:200]}"
            )
            data = resp.json()
            _state["reservation_id"] = data.get("reservation_id") or data.get("id")

    @pytest.mark.asyncio
    async def test_get_reservation(self):
        order_id = _state.get("order_id")
        if not order_id:
            pytest.skip("No reservation created")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{BASE_URL}/api/v1/inventory/reservations/{order_id}",
                headers=INTERNAL_HEADERS,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("order_id") == order_id
            assert "status" in data

    @pytest.mark.asyncio
    async def test_commit_reservation(self):
        order_id = _state.get("order_id")
        reservation_id = _state.get("reservation_id")
        if not order_id or not reservation_id:
            pytest.skip("No reservation to commit")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/inventory/commit",
                headers=INTERNAL_HEADERS,
                json={
                    "order_id": order_id,
                    "reservation_id": reservation_id,
                },
            )
            assert resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_reserve_and_release(self):
        """Test the reserve → release flow (alternative to commit)."""
        order_id = f"smoke-release-{uuid.uuid4().hex[:8]}"

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Reserve
            reserve_resp = await client.post(
                f"{BASE_URL}/api/v1/inventory/reserve",
                headers=INTERNAL_HEADERS,
                json={
                    "order_id": order_id,
                    "user_id": "smoke-test-user",
                    "items": [{"sku": "SMOKE-RELEASE-001", "quantity": 2}],
                },
            )
            if reserve_resp.status_code not in (200, 201):
                pytest.skip("Cannot create reservation for release test")

            reservation_id = reserve_resp.json().get("reservation_id") or reserve_resp.json().get("id")

            # Release
            release_resp = await client.post(
                f"{BASE_URL}/api/v1/inventory/release",
                headers=INTERNAL_HEADERS,
                json={
                    "order_id": order_id,
                    "reservation_id": reservation_id,
                    "reason": "Smoke test cleanup",
                },
            )
            assert release_resp.status_code in (200, 204)
