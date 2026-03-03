"""
Fulfillment Service - Component Tests (Golden)

Tests HTTP endpoints with mocked repository and event bus.
Validates request/response contracts and error handling.

Usage:
    pytest tests/component/golden/fulfillment_service -v
"""
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

os.environ["ENV"] = "testing"
os.environ["NATS_ENABLED"] = "false"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

import isa_common
if not hasattr(isa_common, "AsyncNATSClient"):
    isa_common.AsyncNATSClient = MagicMock
if not hasattr(isa_common, "AsyncPostgresClient"):
    isa_common.AsyncPostgresClient = MagicMock

from fastapi.testclient import TestClient

pytestmark = [pytest.mark.component, pytest.mark.golden]


@pytest.fixture
def mock_repository():
    """Mock FulfillmentRepository"""
    repo = AsyncMock()
    repo.create_shipment = AsyncMock(return_value={
        "shipment_id": "ship_test_001",
        "order_id": "order_001",
        "status": "created",
        "tracking_number": "trk_mock123",
    })
    repo.get_shipment = AsyncMock(return_value={
        "shipment_id": "ship_test_001",
        "order_id": "order_001",
        "status": "created",
        "tracking_number": None,
        "carrier": None,
        "label_url": None,
        "user_id": "user_001",
    })
    repo.get_shipment_by_order = AsyncMock(return_value={
        "shipment_id": "ship_test_001",
        "order_id": "order_001",
        "status": "created",
    })
    repo.get_shipment_by_tracking = AsyncMock(return_value={
        "shipment_id": "ship_test_001",
        "order_id": "order_001",
        "status": "in_transit",
        "carrier": "USPS",
        "tracking_number": "trk_mock123",
    })
    repo.create_label = AsyncMock()
    repo.cancel_shipment = AsyncMock()
    return repo


@pytest.fixture
def client(mock_repository):
    """TestClient with mocked dependencies"""
    import microservices.fulfillment_service.main as mod

    mod.repository = mock_repository
    mod.event_bus = None
    yield TestClient(mod.app)
    mod.repository = None


class TestHealthEndpoint:
    """Health check endpoint tests"""

    def test_health_returns_ok(self, client):
        """CHAR: /health returns status ok"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "fulfillment_service"


class TestCreateShipment:
    """POST /api/v1/fulfillment/shipments"""

    def test_create_shipment_success(self, client, mock_repository):
        """CHAR: Valid payload creates shipment"""
        response = client.post("/api/v1/fulfillment/shipments", json={
            "order_id": "order_001",
            "user_id": "user_001",
            "items": [{"sku_id": "SKU-1", "quantity": 2}],
            "address": {"city": "SF", "state": "CA", "zip": "94102"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["shipment_id"] == "ship_test_001"
        assert data["order_id"] == "order_001"
        assert data["status"] == "created"

    def test_create_shipment_missing_order_id(self, client):
        """CHAR: Missing order_id returns 400"""
        response = client.post("/api/v1/fulfillment/shipments", json={
            "items": [{"sku_id": "SKU-1"}],
            "address": {"city": "SF"},
        })
        assert response.status_code == 400

    def test_create_shipment_missing_items(self, client):
        """CHAR: Missing items returns 400"""
        response = client.post("/api/v1/fulfillment/shipments", json={
            "order_id": "order_001",
            "address": {"city": "SF"},
        })
        assert response.status_code == 400

    def test_create_shipment_missing_address(self, client):
        """CHAR: Missing address returns 400"""
        response = client.post("/api/v1/fulfillment/shipments", json={
            "order_id": "order_001",
            "items": [{"sku_id": "SKU-1"}],
        })
        assert response.status_code == 400


class TestGetShipment:
    """GET /api/v1/fulfillment/shipments/{order_id}"""

    def test_get_shipment_success(self, client):
        """CHAR: Valid order_id returns shipment"""
        response = client.get("/api/v1/fulfillment/shipments/order_001")
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "order_001"

    def test_get_shipment_not_found(self, client, mock_repository):
        """CHAR: Unknown order returns 404"""
        mock_repository.get_shipment_by_order = AsyncMock(return_value=None)
        response = client.get("/api/v1/fulfillment/shipments/nonexistent")
        assert response.status_code == 404


class TestCancelShipment:
    """POST /api/v1/fulfillment/shipments/{shipment_id}/cancel"""

    def test_cancel_shipment_success(self, client):
        """CHAR: Cancel returns canceled status"""
        response = client.post("/api/v1/fulfillment/shipments/ship_test_001/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "canceled"

    def test_cancel_not_found(self, client, mock_repository):
        """CHAR: Cancel unknown shipment returns 404"""
        mock_repository.get_shipment = AsyncMock(return_value=None)
        response = client.post("/api/v1/fulfillment/shipments/nonexistent/cancel")
        assert response.status_code == 404


class TestGetTracking:
    """GET /api/v1/fulfillment/tracking/{tracking_number}"""

    def test_tracking_success(self, client):
        """CHAR: Valid tracking number returns shipment info"""
        response = client.get("/api/v1/fulfillment/tracking/trk_mock123")
        assert response.status_code == 200
        data = response.json()
        assert data["tracking_number"] == "trk_mock123"
        assert data["carrier"] == "USPS"

    def test_tracking_not_found(self, client, mock_repository):
        """CHAR: Unknown tracking number returns 404"""
        mock_repository.get_shipment_by_tracking = AsyncMock(return_value=None)
        response = client.get("/api/v1/fulfillment/tracking/nonexistent")
        assert response.status_code == 404
