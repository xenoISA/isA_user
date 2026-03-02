"""
Tax Service - Component Tests (Golden)

Tests HTTP endpoints with mocked repository, provider, and event bus.
Validates request/response contracts and error handling.

Usage:
    pytest tests/component/golden/tax_service -v
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
    """Mock TaxRepository"""
    repo = AsyncMock()
    repo.create_calculation = AsyncMock(return_value={
        "calculation_id": "calc_test_001",
        "order_id": "order_001",
        "total_tax": 7.25,
        "currency": "USD",
    })
    repo.get_calculation_by_order = AsyncMock(return_value={
        "calculation_id": "calc_test_001",
        "order_id": "order_001",
        "total_tax": 7.25,
        "currency": "USD",
        "lines": [],
    })
    return repo


@pytest.fixture
def mock_provider():
    """Mock TaxProvider"""
    prov = AsyncMock()
    prov.calculate = AsyncMock(return_value={
        "total_tax": 7.25,
        "lines": [
            {"line_item_id": "item_1", "tax_amount": 7.25, "jurisdiction": "CA", "rate": 0.0725}
        ],
    })
    return prov


@pytest.fixture
def client(mock_repository, mock_provider):
    """TestClient with mocked dependencies"""
    import microservices.tax_service.main as mod

    mod.repository = mock_repository
    mod.provider = mock_provider
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
        assert data["service"] == "tax_service"


class TestCalculateTax:
    """POST /api/v1/tax/calculate"""

    def test_calculate_tax_success(self, client):
        """CHAR: Valid payload returns tax calculation"""
        response = client.post("/api/v1/tax/calculate", json={
            "order_id": "order_001",
            "user_id": "user_001",
            "items": [{"sku_id": "SKU-1", "unit_price": 100, "quantity": 1}],
            "address": {"state": "CA", "zip": "94102"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total_tax"] == 7.25
        assert "lines" in data

    def test_calculate_tax_missing_items(self, client):
        """CHAR: Missing items returns 400"""
        response = client.post("/api/v1/tax/calculate", json={
            "address": {"state": "CA"},
        })
        assert response.status_code == 400

    def test_calculate_tax_missing_address(self, client):
        """CHAR: Missing address returns 400"""
        response = client.post("/api/v1/tax/calculate", json={
            "items": [{"sku_id": "SKU-1", "unit_price": 100}],
        })
        assert response.status_code == 400

    def test_calculate_tax_with_order_stores_calculation(self, client, mock_repository):
        """CHAR: When order_id provided, calculation is stored"""
        response = client.post("/api/v1/tax/calculate", json={
            "order_id": "order_001",
            "items": [{"sku_id": "SKU-1", "unit_price": 100, "quantity": 1}],
            "address": {"state": "CA"},
        })
        assert response.status_code == 200
        data = response.json()
        assert "calculation_id" in data
        mock_repository.create_calculation.assert_called_once()


class TestGetTaxCalculation:
    """GET /api/v1/tax/calculations/{order_id}"""

    def test_get_calculation_success(self, client):
        """CHAR: Valid order returns tax calculation"""
        response = client.get("/api/v1/tax/calculations/order_001")
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "order_001"
        assert data["total_tax"] == 7.25

    def test_get_calculation_not_found(self, client, mock_repository):
        """CHAR: Unknown order returns 404"""
        mock_repository.get_calculation_by_order = AsyncMock(return_value=None)
        response = client.get("/api/v1/tax/calculations/nonexistent")
        assert response.status_code == 404
