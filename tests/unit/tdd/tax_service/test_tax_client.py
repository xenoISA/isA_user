"""
Tax Client — Unit Tests

L1: Tests client initialization and method signatures.
L2: Tests HTTP behavior with mocked httpx responses.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from microservices.tax_service.clients.tax_client import TaxClient

pytestmark = [pytest.mark.unit]


class TestTaxClientInit:
    """L1: Client initialization"""

    def test_init_with_base_url(self):
        client = TaxClient(base_url="http://test:8253")
        assert client.base_url == "http://test:8253"

    def test_init_strips_trailing_slash(self):
        client = TaxClient(base_url="http://test:8253/")
        assert client.base_url == "http://test:8253"

    def test_init_fallback_to_default(self):
        client = TaxClient(base_url=None)
        assert "8253" in client.base_url or "localhost" in client.base_url


class TestTaxClientMethods:
    """L2: Client HTTP methods with mocked transport"""

    @pytest.fixture
    def client(self):
        return TaxClient(base_url="http://test:8253")

    @pytest.mark.asyncio
    async def test_calculate_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tax_amount": 5.50,
            "tax_rate": 0.055,
            "order_id": "order_1",
        }
        mock_response.raise_for_status = MagicMock()

        client.client.post = AsyncMock(return_value=mock_response)

        result = await client.calculate(
            items=[{"name": "Widget", "price": 100}],
            address={"state": "CA", "zip": "94105"},
            order_id="order_1",
        )
        assert result is not None
        assert result["tax_amount"] == 5.50

    @pytest.mark.asyncio
    async def test_calculate_returns_none_on_error(self, client):
        client.client.post = AsyncMock(side_effect=httpx.ConnectError("fail"))

        result = await client.calculate(
            items=[{"name": "Widget", "price": 100}],
            address={"state": "CA"},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_calculation_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"order_id": "order_1", "tax_amount": 5.50}
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)

        result = await client.get_calculation("order_1")
        assert result is not None
        assert result["order_id"] == "order_1"

    @pytest.mark.asyncio
    async def test_get_calculation_returns_none_on_404(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status = MagicMock(side_effect=error)

        client.client.get = AsyncMock(return_value=mock_response)

        result = await client.get_calculation("order_nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        client.client.get = AsyncMock(return_value=mock_response)

        assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        client.client.get = AsyncMock(side_effect=Exception("down"))
        assert await client.health_check() is False
