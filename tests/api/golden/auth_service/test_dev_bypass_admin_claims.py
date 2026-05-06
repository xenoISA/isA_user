"""
API tests for dev-bypass admin claim parity.

Covers: #370 — AUTH_DEV_BYPASS_ADMINS applies consistently to verify-token
and userinfo only when dev-bypass mode is enabled.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from microservices.auth_service.main import app

pytestmark = [pytest.mark.api, pytest.mark.golden, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_auth_service():
    with patch("microservices.auth_service.main.auth_microservice") as mock_ms:
        mock_service = AsyncMock()
        mock_ms.auth_service = mock_service
        yield mock_service


def _valid_result(email):
    return {
        "valid": True,
        "provider": "isa_user",
        "user_id": "usr_dev_admin",
        "email": email,
        "organization_id": "org_dev",
        "permissions": [],
        "metadata": {},
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
    }


async def test_verify_token_marks_dev_bypass_admin_when_enabled(
    client, mock_auth_service, monkeypatch
):
    monkeypatch.setenv("AUTH_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("AUTH_DEV_BYPASS_ADMINS", "admin@example.com")
    mock_auth_service.verify_token.return_value = _valid_result("admin@example.com")

    response = await client.post("/api/v1/auth/verify-token", json={"token": "jwt"})

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert data["permissions"] == ["auth.admin"]
    assert data["scopes"] == ["read", "write", "admin"]


async def test_verify_token_does_not_mark_admin_when_dev_bypass_disabled(
    client, mock_auth_service, monkeypatch
):
    monkeypatch.delenv("AUTH_DEV_BYPASS_ENABLED", raising=False)
    monkeypatch.setenv("AUTH_DEV_BYPASS_ADMINS", "admin@example.com")
    mock_auth_service.verify_token.return_value = _valid_result("admin@example.com")

    response = await client.post("/api/v1/auth/verify-token", json={"token": "jwt"})

    assert response.status_code == 200
    data = response.json()
    assert data["role"] is None
    assert data["permissions"] == []
    assert data["scopes"] is None


async def test_verify_token_keeps_non_allowlisted_dev_user_non_admin(
    client, mock_auth_service, monkeypatch
):
    monkeypatch.setenv("AUTH_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("AUTH_DEV_BYPASS_ADMINS", "admin@example.com")
    mock_auth_service.verify_token.return_value = _valid_result("user@example.com")

    response = await client.post("/api/v1/auth/verify-token", json={"token": "jwt"})

    assert response.status_code == 200
    data = response.json()
    assert data["role"] is None
    assert data["permissions"] == []
    assert data["scopes"] is None
