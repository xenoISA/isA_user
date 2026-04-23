from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from core.auth_dependencies import require_auth_or_internal_service


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _FakeResponse:
    def __init__(self, status_code: int, payload, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = str(payload)

    def json(self):
        return self._payload


async def test_api_key_rate_limit_surfaces_as_429():
    request = SimpleNamespace(
        url=SimpleNamespace(path="/api/v1/model/invoke"),
        client=SimpleNamespace(host="127.0.0.1"),
    )
    http_client = AsyncMock()
    http_client.post.return_value = _FakeResponse(
        429,
        {"detail": {"field": "requests_per_minute"}},
        headers={"Retry-After": "60"},
    )

    with patch("core.auth_dependencies._get_http_client", return_value=http_client):
        with pytest.raises(HTTPException) as exc_info:
            await require_auth_or_internal_service(
                request=request,
                x_internal_service=None,
                x_internal_service_secret=None,
                authorization=None,
                x_api_key="isa_live",
            )

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "60"


async def test_valid_api_key_returns_org_identity():
    request = SimpleNamespace(
        url=SimpleNamespace(path="/api/v1/model/invoke"),
        client=SimpleNamespace(host="127.0.0.1"),
    )
    http_client = AsyncMock()
    http_client.post.return_value = _FakeResponse(
        200,
        {"valid": True, "organization_id": "org_123"},
    )

    with patch("core.auth_dependencies._get_http_client", return_value=http_client):
        user_id = await require_auth_or_internal_service(
            request=request,
            x_internal_service=None,
            x_internal_service_secret=None,
            authorization=None,
            x_api_key="isa_live",
        )

    assert user_id == "org_123"
