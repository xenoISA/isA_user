"""
Inventory Service - Component Tests (Golden)

Tests HTTP endpoints with mocked repository and event bus.
Validates request/response contracts and error handling.

Usage:
    pytest tests/component/golden/inventory_service -v
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock

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
    """Mock InventoryRepository"""
    repo = AsyncMock()
    repo.create_reservation = AsyncMock(return_value={
        "reservation_id": "res_test_001",
        "order_id": "order_001",
        "status": "active",
        "expires_at": "2026-03-02T01:00:00Z",
        "items": [{"sku_id": "SKU-1", "quantity": 2}],
        "user_id": "user_001",
    })
    repo.get_reservation = AsyncMock(return_value={
        "reservation_id": "res_test_001",
        "order_id": "order_001",
        "status": "active",
        "items": [{"sku_id": "SKU-1", "quantity": 2}],
        "user_id": "user_001",
    })
    repo.get_active_reservation_for_order = AsyncMock(return_value={
        "reservation_id": "res_test_001",
        "order_id": "order_001",
        "status": "active",
        "items": [{"sku_id": "SKU-1", "quantity": 2}],
        "user_id": "user_001",
    })
    repo.get_reservation_by_order = AsyncMock(return_value={
        "reservation_id": "res_test_001",
        "order_id": "order_001",
        "status": "active",
    })
    repo.commit_reservation = AsyncMock()
    repo.release_reservation = AsyncMock()
    return repo


@pytest.fixture
def client(mock_repository):
    """TestClient with mocked dependencies"""
    import microservices.inventory_service.main as mod

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
        assert data["service"] == "inventory_service"


class TestReserveInventory:
    """POST /api/v1/inventory/reserve"""

    def test_reserve_success(self, client, mock_repository):
        """CHAR: Valid reservation returns active status"""
        response = client.post("/api/v1/inventory/reserve", json={
            "order_id": "order_001",
            "user_id": "user_001",
            "items": [{"sku_id": "SKU-1", "quantity": 2}],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["reservation_id"] == "res_test_001"
        assert data["status"] == "active"

    def test_reserve_missing_order_id(self, client):
        """CHAR: Missing order_id returns 400"""
        response = client.post("/api/v1/inventory/reserve", json={
            "items": [{"sku_id": "SKU-1", "quantity": 1}],
        })
        assert response.status_code == 400

    def test_reserve_missing_items(self, client):
        """CHAR: Missing items returns 400"""
        response = client.post("/api/v1/inventory/reserve", json={
            "order_id": "order_001",
        })
        assert response.status_code == 400


class TestCommitInventory:
    """POST /api/v1/inventory/commit"""

    def test_commit_success(self, client):
        """CHAR: Valid commit returns committed status"""
        response = client.post("/api/v1/inventory/commit", json={
            "order_id": "order_001",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "committed"

    def test_commit_missing_order_id(self, client):
        """CHAR: Missing order_id returns 400"""
        response = client.post("/api/v1/inventory/commit", json={})
        assert response.status_code == 400

    def test_commit_not_found(self, client, mock_repository):
        """CHAR: No active reservation returns 404"""
        mock_repository.get_reservation = AsyncMock(return_value=None)
        mock_repository.get_active_reservation_for_order = AsyncMock(return_value=None)
        response = client.post("/api/v1/inventory/commit", json={
            "order_id": "nonexistent",
        })
        assert response.status_code == 404


class TestReleaseInventory:
    """POST /api/v1/inventory/release"""

    def test_release_success(self, client):
        """CHAR: Valid release returns released status"""
        response = client.post("/api/v1/inventory/release", json={
            "order_id": "order_001",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "released"

    def test_release_missing_order_id(self, client):
        """CHAR: Missing order_id returns 400"""
        response = client.post("/api/v1/inventory/release", json={})
        assert response.status_code == 400

    def test_release_no_reservation_graceful(self, client, mock_repository):
        """CHAR: No active reservation returns released with message"""
        mock_repository.get_reservation = AsyncMock(return_value=None)
        mock_repository.get_active_reservation_for_order = AsyncMock(return_value=None)
        response = client.post("/api/v1/inventory/release", json={
            "order_id": "nonexistent",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "released"


class TestGetReservation:
    """GET /api/v1/inventory/reservations/{order_id}"""

    def test_get_reservation_success(self, client):
        """CHAR: Valid order returns reservation"""
        response = client.get("/api/v1/inventory/reservations/order_001")
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "order_001"

    def test_get_reservation_not_found(self, client, mock_repository):
        """CHAR: Unknown order returns 404"""
        mock_repository.get_reservation_by_order = AsyncMock(return_value=None)
        response = client.get("/api/v1/inventory/reservations/nonexistent")
        assert response.status_code == 404
