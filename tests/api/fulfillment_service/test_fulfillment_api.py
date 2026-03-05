"""
L4 API Tests — Fulfillment Service

Tests HTTP endpoints via FastAPI TestClient.
Verifies request/response contracts, status codes, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from tests.contracts.fulfillment.data_contract import FulfillmentFactory
from microservices.fulfillment_service.main import app
import microservices.fulfillment_service.main as main_module


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_service():
    svc = AsyncMock()
    return svc


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
class TestFulfillmentHealthAPI:

    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "fulfillment_service"

    async def test_versioned_health_returns_ok(self, client):
        resp = await client.get("/api/v1/fulfillment/health")
        assert resp.status_code == 200


# ============================================================================
# POST /api/v1/fulfillment/shipments
# ============================================================================

@pytest.mark.api
class TestCreateShipmentAPI:

    async def test_create_shipment_200(self, client, mock_service):
        mock_service.create_shipment.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "status": "created",
            "tracking_number": "trk_1",
        }
        req = FulfillmentFactory.create_shipment_request()

        resp = await client.post("/api/v1/fulfillment/shipments", json=req)

        assert resp.status_code == 200
        data = resp.json()
        assert data["shipment_id"] == "shp_1"
        assert data["status"] == "created"

    async def test_create_shipment_400_missing_order_id(self, client, mock_service):
        mock_service.create_shipment.side_effect = ValueError("order_id, items, and address are required")

        resp = await client.post("/api/v1/fulfillment/shipments", json={
            "items": [{"sku_id": "a"}], "address": {"city": "SF"},
        })

        assert resp.status_code == 400

    async def test_create_shipment_400_missing_items(self, client, mock_service):
        mock_service.create_shipment.side_effect = ValueError("order_id, items, and address are required")

        resp = await client.post("/api/v1/fulfillment/shipments", json={
            "order_id": "ord_1", "address": {"city": "SF"},
        })

        assert resp.status_code == 400

    async def test_create_shipment_503_no_service(self, client):
        main_module.service = None

        resp = await client.post("/api/v1/fulfillment/shipments", json={
            "order_id": "ord_1", "items": [{"sku_id": "a"}], "address": {"city": "SF"},
        })

        assert resp.status_code == 503


# ============================================================================
# POST /api/v1/fulfillment/shipments/{id}/label
# ============================================================================

@pytest.mark.api
class TestCreateLabelAPI:

    async def test_create_label_200(self, client, mock_service):
        mock_service.create_label.return_value = {
            "shipment_id": "shp_1",
            "tracking_number": "trk_1",
            "carrier": "USPS",
            "status": "label_created",
        }

        resp = await client.post("/api/v1/fulfillment/shipments/shp_1/label")

        assert resp.status_code == 200
        assert resp.json()["carrier"] == "USPS"

    async def test_create_label_404_not_found(self, client, mock_service):
        mock_service.create_label.side_effect = LookupError("Shipment not found")

        resp = await client.post("/api/v1/fulfillment/shipments/shp_bad/label")

        assert resp.status_code == 404


# ============================================================================
# POST /api/v1/fulfillment/shipments/{id}/cancel
# ============================================================================

@pytest.mark.api
class TestCancelShipmentAPI:

    async def test_cancel_200(self, client, mock_service):
        mock_service.cancel_shipment.return_value = {
            "shipment_id": "shp_1",
            "status": "canceled",
            "refund_shipping": False,
        }

        resp = await client.post("/api/v1/fulfillment/shipments/shp_1/cancel")

        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    async def test_cancel_with_reason(self, client, mock_service):
        mock_service.cancel_shipment.return_value = {
            "shipment_id": "shp_1", "status": "canceled", "refund_shipping": False,
        }

        resp = await client.post(
            "/api/v1/fulfillment/shipments/shp_1/cancel",
            json={"reason": "customer_request"},
        )

        assert resp.status_code == 200

    async def test_cancel_404_not_found(self, client, mock_service):
        mock_service.cancel_shipment.side_effect = LookupError("Shipment not found")

        resp = await client.post("/api/v1/fulfillment/shipments/shp_bad/cancel")

        assert resp.status_code == 404


# ============================================================================
# GET /api/v1/fulfillment/shipments/{order_id}
# ============================================================================

@pytest.mark.api
class TestGetShipmentAPI:

    async def test_get_shipment_200(self, client, mock_service):
        mock_service.get_shipment_by_order.return_value = {
            "shipment_id": "shp_1", "order_id": "ord_1", "status": "created",
        }

        resp = await client.get("/api/v1/fulfillment/shipments/ord_1")

        assert resp.status_code == 200
        assert resp.json()["order_id"] == "ord_1"

    async def test_get_shipment_404(self, client, mock_service):
        mock_service.get_shipment_by_order.return_value = None

        resp = await client.get("/api/v1/fulfillment/shipments/ord_bad")

        assert resp.status_code == 404


# ============================================================================
# GET /api/v1/fulfillment/tracking/{tracking_number}
# ============================================================================

@pytest.mark.api
class TestGetTrackingAPI:

    async def test_get_tracking_200(self, client, mock_service):
        mock_service.get_shipment_by_tracking.return_value = {
            "shipment_id": "shp_1",
            "order_id": "ord_1",
            "carrier": "USPS",
            "status": "in_transit",
            "tracking_number": "trk_abc",
        }

        resp = await client.get("/api/v1/fulfillment/tracking/trk_abc")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tracking_number"] == "trk_abc"
        assert data["carrier"] == "USPS"

    async def test_get_tracking_404(self, client, mock_service):
        mock_service.get_shipment_by_tracking.return_value = None

        resp = await client.get("/api/v1/fulfillment/tracking/trk_bad")

        assert resp.status_code == 404
