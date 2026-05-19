from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from microservices.memory_service.client import MemoryServiceClient


pytestmark = [pytest.mark.unit, pytest.mark.anyio]


async def test_export_user_data_calls_memory_export_endpoint():
    client = MemoryServiceClient(base_url="http://test:8223")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "schema_version": "memory-export-v1",
        "user_id": "user-1",
        "memories": [{"id": "mem-1"}],
        "counts": {"memories": 1},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client_instance

        result = await client.export_user_data(
            user_id="user-1",
            organization_id="org-1",
            request_id="gdpr_req_1",
        )

    assert result["service"] == "memory_service"
    assert result["organization_id"] == "org-1"
    assert result["gdpr_request_id"] == "gdpr_req_1"
    assert result["counts"]["memories"] == 1
    mock_client_instance.get.assert_awaited_once()
    call_args = mock_client_instance.get.call_args
    assert "/api/v1/memories/export" in call_args.args[0]
    assert call_args.kwargs["params"] == {"user_id": "user-1", "scope": "user"}
