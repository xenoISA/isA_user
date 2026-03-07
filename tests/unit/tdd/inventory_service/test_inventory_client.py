"""
Inventory Client — Unit Tests

L1: Tests client initialization and method signatures.
L2: Tests HTTP behavior with mocked httpx responses.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from microservices.inventory_service.clients.inventory_client import InventoryClient

pytestmark = [pytest.mark.unit]


class TestInventoryClientInit:
    """L1: Client initialization"""

    def test_init_with_base_url(self):
        client = InventoryClient(base_url="http://test:8252")
        assert client.base_url == "http://test:8252"

    def test_init_strips_trailing_slash(self):
        client = InventoryClient(base_url="http://test:8252/")
        assert client.base_url == "http://test:8252"

    def test_init_fallback_to_default(self):
        client = InventoryClient(base_url=None)
        assert "8252" in client.base_url or "localhost" in client.base_url


class TestInventoryClientMethods:
    """L2: Client HTTP methods with mocked transport"""

    @pytest.fixture
    def client(self):
        return InventoryClient(base_url="http://test:8252")

    @pytest.mark.asyncio
    async def test_reserve_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"reservation_id": "res_123", "status": "reserved"}
        mock_response.raise_for_status = MagicMock()

        client.client.post = AsyncMock(return_value=mock_response)

        result = await client.reserve("order_1", [{"sku": "item_1", "quantity": 2}])
        assert result is not None
        assert result["reservation_id"] == "res_123"
        client.client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_reserve_returns_none_on_error(self, client):
        client.client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        result = await client.reserve("order_1", [{"sku": "item_1", "quantity": 2}])
        assert result is None

    @pytest.mark.asyncio
    async def test_commit_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        client.client.post = AsyncMock(return_value=mock_response)

        result = await client.commit("order_1")
        assert result is True

    @pytest.mark.asyncio
    async def test_commit_returns_false_on_error(self, client):
        client.client.post = AsyncMock(side_effect=Exception("fail"))
        result = await client.commit("order_1")
        assert result is False

    @pytest.mark.asyncio
    async def test_release_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        client.client.post = AsyncMock(return_value=mock_response)

        result = await client.release("order_1", reason="cancelled")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_availability_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"order_id": "order_1", "status": "reserved"}
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)

        result = await client.check_availability("order_1")
        assert result is not None
        assert result["order_id"] == "order_1"

    @pytest.mark.asyncio
    async def test_check_availability_returns_none_on_404(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status = MagicMock(side_effect=error)

        client.client.get = AsyncMock(return_value=mock_response)

        result = await client.check_availability("order_nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200

        client.client.get = AsyncMock(return_value=mock_response)

        result = await client.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        client.client.get = AsyncMock(side_effect=Exception("down"))
        result = await client.health_check()
        assert result is False
