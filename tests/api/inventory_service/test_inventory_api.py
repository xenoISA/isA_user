"""
L4 API Tests — Inventory Service

Tests HTTP endpoints via FastAPI TestClient.
Verifies request/response contracts, status codes, and error handling.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport

from tests.contracts.inventory.data_contract import InventoryFactory
from microservices.inventory_service.main import app
import microservices.inventory_service.main as main_module


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_service():
    return AsyncMock()


@pytest.fixture
async def client(mock_service):
    main_module.service = mock_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    main_module.service = None


# ============================================================================
# Health endpoint
# ============================================================================

@pytest.mark.api
class TestInventoryHealthAPI:

    async def test_health_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "inventory_service"

    async def test_versioned_health_ok(self, client):
        resp = await client.get("/api/v1/inventory/health")
        assert resp.status_code == 200


# ============================================================================
# POST /api/v1/inventory/reserve
# ============================================================================

@pytest.mark.api
class TestReserveAPI:

    async def test_reserve_200(self, client, mock_service):
        expires = datetime.now(timezone.utc) + timedelta(minutes=30)
        mock_service.reserve_inventory.return_value = {
            "reservation_id": "res_1",
            "status": "active",
            "expires_at": expires.isoformat(),
        }
        req = InventoryFactory.reserve_request()

        resp = await client.post("/api/v1/inventory/reserve", json=req)

        assert resp.status_code == 200
        assert resp.json()["reservation_id"] == "res_1"

    async def test_reserve_400_missing_order_id(self, client, mock_service):
        mock_service.reserve_inventory.side_effect = ValueError("order_id and items are required")

        resp = await client.post("/api/v1/inventory/reserve", json={
            "items": [{"sku_id": "a"}],
        })

        assert resp.status_code == 400

    async def test_reserve_400_missing_items(self, client, mock_service):
        mock_service.reserve_inventory.side_effect = ValueError("order_id and items are required")

        resp = await client.post("/api/v1/inventory/reserve", json={
            "order_id": "ord_1",
        })

        assert resp.status_code == 400

    async def test_reserve_503_no_service(self, client):
        main_module.service = None

        resp = await client.post("/api/v1/inventory/reserve", json={
            "order_id": "ord_1", "items": [{"sku_id": "a"}],
        })

        assert resp.status_code == 503


# ============================================================================
# POST /api/v1/inventory/commit
# ============================================================================

@pytest.mark.api
class TestCommitAPI:

    async def test_commit_200(self, client, mock_service):
        mock_service.commit_reservation.return_value = {
            "order_id": "ord_1", "reservation_id": "res_1", "status": "committed",
        }

        resp = await client.post("/api/v1/inventory/commit", json={
            "order_id": "ord_1", "reservation_id": "res_1",
        })

        assert resp.status_code == 200
        assert resp.json()["status"] == "committed"

    async def test_commit_400_missing_order_id(self, client, mock_service):
        mock_service.commit_reservation.side_effect = ValueError("order_id is required")

        resp = await client.post("/api/v1/inventory/commit", json={})

        assert resp.status_code == 400

    async def test_commit_404_not_found(self, client, mock_service):
        mock_service.commit_reservation.side_effect = LookupError("No active reservation found")

        resp = await client.post("/api/v1/inventory/commit", json={
            "order_id": "ord_bad",
        })

        assert resp.status_code == 404


# ============================================================================
# POST /api/v1/inventory/release
# ============================================================================

@pytest.mark.api
class TestReleaseAPI:

    async def test_release_200(self, client, mock_service):
        mock_service.release_reservation.return_value = {
            "order_id": "ord_1", "reservation_id": "res_1", "status": "released",
        }

        resp = await client.post("/api/v1/inventory/release", json={
            "order_id": "ord_1",
        })

        assert resp.status_code == 200
        assert resp.json()["status"] == "released"

    async def test_release_with_reason(self, client, mock_service):
        mock_service.release_reservation.return_value = {
            "order_id": "ord_1", "status": "released",
        }

        resp = await client.post("/api/v1/inventory/release", json={
            "order_id": "ord_1", "reason": "order_canceled",
        })

        assert resp.status_code == 200

    async def test_release_400_missing_order_id(self, client, mock_service):
        mock_service.release_reservation.side_effect = ValueError("order_id is required")

        resp = await client.post("/api/v1/inventory/release", json={})

        assert resp.status_code == 400


# ============================================================================
# GET /api/v1/inventory/reservations/{order_id}
# ============================================================================

@pytest.mark.api
class TestGetReservationAPI:

    async def test_get_200(self, client, mock_service):
        mock_service.get_reservation.return_value = {
            "reservation_id": "res_1", "order_id": "ord_1", "status": "active",
        }

        resp = await client.get("/api/v1/inventory/reservations/ord_1")

        assert resp.status_code == 200
        assert resp.json()["reservation_id"] == "res_1"

    async def test_get_404(self, client, mock_service):
        mock_service.get_reservation.return_value = None

        resp = await client.get("/api/v1/inventory/reservations/ord_bad")

        assert resp.status_code == 404
