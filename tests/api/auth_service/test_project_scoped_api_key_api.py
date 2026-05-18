from unittest.mock import AsyncMock

import httpx
import pytest

from microservices.auth_service.main import (
    app,
    get_api_key_service,
    get_current_caller,
)

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


async def _allowed_caller():
    return {
        "user_id": "usr_1",
        "organization_id": "org_1",
        "permissions": ["auth.api_keys.create"],
    }


def _client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.fixture
def api_key_service():
    return AsyncMock()


@pytest.fixture(autouse=True)
def dependency_overrides(api_key_service):
    app.dependency_overrides[get_api_key_service] = lambda: api_key_service
    app.dependency_overrides[get_current_caller] = _allowed_caller
    yield
    app.dependency_overrides.clear()


async def test_create_project_scoped_api_key_forwards_metadata_and_auth_token(
    api_key_service,
):
    api_key_service.create_api_key.return_value = {
        "success": True,
        "api_key": "isa_secret",
        "key_id": "key_1",
        "name": "CI key",
        "expires_at": None,
        "project_id": "proj_1",
        "owner_type": "service_account",
        "service_account_id": "sa_1",
        "scopes": ["models.invoke"],
        "ip_allowlist": ["10.0.0.1"],
        "rate_limits": {"requests_per_minute": 60},
        "spend_limit": 100,
    }

    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/api-keys",
            headers={"Authorization": "Bearer test-token"},
            json={
                "organization_id": "org_1",
                "name": "CI key",
                "permissions": ["read:data"],
                "project_id": "proj_1",
                "owner_type": "service_account",
                "service_account_id": "sa_1",
                "scopes": ["models.invoke"],
                "ip_allowlist": ["10.0.0.1"],
                "rate_limits": {"requests_per_minute": 60},
                "spend_limit": 100,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == "proj_1"
    assert body["owner_type"] == "service_account"
    assert body["service_account_id"] == "sa_1"
    assert body["scopes"] == ["models.invoke"]
    assert body["ip_allowlist"] == ["10.0.0.1"]
    assert body["rate_limits"] == {"requests_per_minute": 60}
    assert body["spend_limit"] == 100
    kwargs = api_key_service.create_api_key.await_args.kwargs
    assert kwargs["project_id"] == "proj_1"
    assert kwargs["auth_token"] == "Bearer test-token"


async def test_create_api_key_requires_create_key_permission(api_key_service):
    async def caller_without_create_permission():
        return {
            "user_id": "usr_1",
            "organization_id": "org_1",
            "permissions": [],
        }

    app.dependency_overrides[get_current_caller] = caller_without_create_permission

    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/api-keys",
            headers={"Authorization": "Bearer test-token"},
            json={
                "organization_id": "org_1",
                "name": "CI key",
                "project_id": "proj_1",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "API key creation permission required"
    api_key_service.create_api_key.assert_not_awaited()


async def test_list_api_keys_filters_by_project_and_hides_secret_material(
    api_key_service,
):
    api_key_service.list_api_keys.return_value = {
        "success": True,
        "api_keys": [
            {
                "key_id": "key_1",
                "name": "CI key",
                "project_id": "proj_1",
                "key_preview": "isa_...abcd",
            }
        ],
        "total": 1,
    }

    async with _client() as client:
        response = await client.get(
            "/api/v1/auth/api-keys/org_1",
            headers={"Authorization": "Bearer test-token"},
            params={"project_id": "proj_1"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["api_keys"][0]["project_id"] == "proj_1"
    assert "api_key" not in body["api_keys"][0]
    assert "key_hash" not in body["api_keys"][0]
    api_key_service.list_api_keys.assert_awaited_once_with(
        "org_1", project_id="proj_1"
    )


async def test_verify_api_key_returns_project_metadata(api_key_service):
    api_key_service.verify_api_key.return_value = {
        "valid": True,
        "key_id": "key_1",
        "organization_id": "org_1",
        "name": "CI key",
        "permissions": ["read:data"],
        "project_id": "proj_1",
        "owner_type": "service_account",
        "service_account_id": "sa_1",
        "scopes": ["models.invoke"],
        "ip_allowlist": ["10.0.0.1"],
        "rate_limits": {"requests_per_minute": 60},
        "spend_limit": 100,
        "effective_rate_limits": {"requests_per_minute": 60},
    }

    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/verify-api-key",
            json={
                "api_key": "isa_secret",
                "project_id": "proj_1",
                "ip_address": "10.0.0.1",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["project_id"] == "proj_1"
    assert body["owner_type"] == "service_account"
    assert body["service_account_id"] == "sa_1"
    assert body["scopes"] == ["models.invoke"]
    assert body["ip_allowlist"] == ["10.0.0.1"]
    assert body["rate_limits"] == {"requests_per_minute": 60}
    assert body["spend_limit"] == 100
    api_key_service.verify_api_key.assert_awaited_once_with(
        "isa_secret", project_id="proj_1", ip_address="10.0.0.1"
    )
