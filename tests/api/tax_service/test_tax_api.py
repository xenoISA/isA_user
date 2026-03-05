"""
L4 API Tests — Tax Service

Tests HTTP endpoints via FastAPI TestClient.
Verifies request/response contracts, status codes, and error handling.
"""

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

from tests.contracts.tax.data_contract import TaxFactory
from microservices.tax_service.main import app
import microservices.tax_service.main as main_module


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
class TestTaxHealthAPI:

    async def test_health_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "tax_service"

    async def test_versioned_health_ok(self, client):
        resp = await client.get("/api/v1/tax/health")
        assert resp.status_code == 200


# ============================================================================
# POST /api/v1/tax/calculate
# ============================================================================

@pytest.mark.api
class TestCalculateTaxAPI:

    async def test_calculate_200(self, client, mock_service):
        mock_service.calculate_tax.return_value = {
            "currency": "USD",
            "total_tax": 8.75,
            "lines": [{"line_item_id": "li_1", "tax_amount": 8.75}],
        }
        req = TaxFactory.calculate_request()

        resp = await client.post("/api/v1/tax/calculate", json=req)

        assert resp.status_code == 200
        assert resp.json()["total_tax"] == 8.75

    async def test_calculate_with_order_id(self, client, mock_service):
        order_id = TaxFactory.order_id()
        mock_service.calculate_tax.return_value = {
            "currency": "USD",
            "total_tax": 5.0,
            "calculation_id": "calc_1",
            "order_id": order_id,
        }
        req = TaxFactory.calculate_request(order_id=order_id)

        resp = await client.post("/api/v1/tax/calculate", json=req)

        assert resp.status_code == 200
        assert resp.json()["order_id"] == order_id

    async def test_calculate_400_missing_items(self, client, mock_service):
        mock_service.calculate_tax.side_effect = ValueError("items and address are required")

        resp = await client.post("/api/v1/tax/calculate", json={
            "address": {"state": "CA"},
        })

        assert resp.status_code == 400

    async def test_calculate_400_missing_address(self, client, mock_service):
        mock_service.calculate_tax.side_effect = ValueError("items and address are required")

        resp = await client.post("/api/v1/tax/calculate", json={
            "items": [{"sku_id": "a"}],
        })

        assert resp.status_code == 400

    async def test_calculate_503_no_service(self, client):
        main_module.service = None

        resp = await client.post("/api/v1/tax/calculate", json={
            "items": [{"sku_id": "a"}], "address": {"state": "CA"},
        })

        assert resp.status_code == 503

    async def test_calculate_passes_currency(self, client, mock_service):
        mock_service.calculate_tax.return_value = {"currency": "EUR", "total_tax": 0}

        resp = await client.post("/api/v1/tax/calculate", json={
            "items": [{"sku_id": "a", "unit_price": 10}],
            "address": {"state": "CA"},
            "currency": "EUR",
        })

        assert resp.status_code == 200

    async def test_calculate_passes_user_id(self, client, mock_service):
        mock_service.calculate_tax.return_value = {"currency": "USD", "total_tax": 0}

        await client.post("/api/v1/tax/calculate", json={
            "items": [{"sku_id": "a"}],
            "address": {"state": "CA"},
            "user_id": "usr_custom",
        })

        call_kwargs = mock_service.calculate_tax.call_args.kwargs
        assert call_kwargs["user_id"] == "usr_custom"


# ============================================================================
# GET /api/v1/tax/calculations/{order_id}
# ============================================================================

@pytest.mark.api
class TestGetTaxCalculationAPI:

    async def test_get_200(self, client, mock_service):
        mock_service.get_calculation.return_value = {
            "calculation_id": "calc_1",
            "order_id": "ord_1",
            "total_tax": 8.75,
        }

        resp = await client.get("/api/v1/tax/calculations/ord_1")

        assert resp.status_code == 200
        assert resp.json()["calculation_id"] == "calc_1"

    async def test_get_404(self, client, mock_service):
        mock_service.get_calculation.return_value = None

        resp = await client.get("/api/v1/tax/calculations/ord_bad")

        assert resp.status_code == 404
