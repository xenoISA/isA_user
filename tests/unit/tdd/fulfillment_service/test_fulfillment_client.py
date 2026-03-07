"""
Fulfillment Client — Unit Tests

L1: Tests client initialization and method signatures.
L2: Tests HTTP behavior with mocked httpx responses.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from microservices.fulfillment_service.clients.fulfillment_client import FulfillmentClient

pytestmark = [pytest.mark.unit]


class TestFulfillmentClientInit:
    """L1: Client initialization"""

    def test_init_with_base_url(self):
        client = FulfillmentClient(base_url="http://test:8254")
        assert client.base_url == "http://test:8254"

    def test_init_strips_trailing_slash(self):
        client = FulfillmentClient(base_url="http://test:8254/")
        assert client.base_url == "http://test:8254"

    def test_init_fallback_to_default(self):
        client = FulfillmentClient(base_url=None)
        assert "8254" in client.base_url or "localhost" in client.base_url


class TestFulfillmentClientMethods:
    """L2: Client HTTP methods with mocked transport"""

    @pytest.fixture
    def client(self):
        return FulfillmentClient(base_url="http://test:8254")

    @pytest.mark.asyncio
    async def test_create_shipment_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "shipment_id": "ship_123",
            "tracking_number": "TRK001",
            "status": "created",
        }
        mock_response.raise_for_status = MagicMock()

        client.client.post = AsyncMock(return_value=mock_response)

        result = await client.create_shipment(
            order_id="order_1",
            items=[{"sku": "item_1", "quantity": 1}],
            address={"street": "123 Main St"},
        )
        assert result is not None
        assert result["shipment_id"] == "ship_123"

    @pytest.mark.asyncio
    async def test_create_shipment_returns_none_on_error(self, client):
        client.client.post = AsyncMock(side_effect=httpx.ConnectError("fail"))

        result = await client.create_shipment(
            order_id="order_1",
            items=[{"sku": "item_1"}],
            address={"street": "123 Main St"},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_shipment_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"order_id": "order_1", "status": "shipped"}
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)

        result = await client.get_shipment("order_1")
        assert result is not None
        assert result["order_id"] == "order_1"

    @pytest.mark.asyncio
    async def test_get_shipment_returns_none_on_404(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status = MagicMock(side_effect=error)

        client.client.get = AsyncMock(return_value=mock_response)

        result = await client.get_shipment("order_nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_tracking_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tracking_number": "TRK001",
            "status": "in_transit",
        }
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)

        result = await client.get_tracking("TRK001")
        assert result is not None
        assert result["tracking_number"] == "TRK001"

    @pytest.mark.asyncio
    async def test_get_tracking_returns_none_on_404(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status = MagicMock(side_effect=error)

        client.client.get = AsyncMock(return_value=mock_response)

        result = await client.get_tracking("TRK_INVALID")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_label_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"label_url": "https://labels.example.com/123"}
        mock_response.raise_for_status = MagicMock()

        client.client.post = AsyncMock(return_value=mock_response)

        result = await client.create_label("ship_123")
        assert result is not None
        assert "label_url" in result

    @pytest.mark.asyncio
    async def test_cancel_shipment_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "canceled"}
        mock_response.raise_for_status = MagicMock()

        client.client.post = AsyncMock(return_value=mock_response)

        result = await client.cancel_shipment("ship_123", reason="customer_request")
        assert result is not None
        assert result["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_shipment_returns_none_on_404(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status = MagicMock(side_effect=error)

        client.client.post = AsyncMock(return_value=mock_response)

        result = await client.cancel_shipment("ship_nonexistent")
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
