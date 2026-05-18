from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from microservices.auth_service.api_key_service import ApiKeyService

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def project_access():
    client = AsyncMock()
    client.validate_project_access.return_value = True
    return client


@pytest.fixture
def service(repo, project_access):
    return ApiKeyService(repository=repo, project_access_client=project_access)


async def test_create_project_scoped_service_account_key_validates_and_persists_metadata(
    service, repo, project_access
):
    repo.create_api_key.return_value = {
        "api_key": "isa_secret",
        "key_id": "key_1",
        "project_id": "proj_1",
        "owner_type": "service_account",
        "service_account_id": "sa_1",
        "scopes": ["models.invoke"],
        "ip_allowlist": ["10.0.0.1"],
        "rate_limits": {"requests_per_minute": 60},
        "spend_limit": 100,
    }

    result = await service.create_api_key(
        organization_id="org_1",
        name="CI key",
        permissions=["read:data"],
        expires_days=30,
        created_by="usr_1",
        project_id="proj_1",
        owner_type="service_account",
        service_account_id="sa_1",
        scopes=["models.invoke"],
        ip_allowlist=["10.0.0.1"],
        rate_limits={"requests_per_minute": 60},
        spend_limit=100,
        auth_token="Bearer token",
    )

    assert result["success"] is True
    assert result["project_id"] == "proj_1"
    assert result["owner_type"] == "service_account"
    assert result["service_account_id"] == "sa_1"
    assert result["scopes"] == ["models.invoke"]
    assert result["ip_allowlist"] == ["10.0.0.1"]
    assert result["rate_limits"] == {"requests_per_minute": 60}
    assert result["spend_limit"] == 100
    project_access.validate_project_access.assert_awaited_once_with(
        organization_id="org_1",
        project_id="proj_1",
        user_id="usr_1",
        auth_token="Bearer token",
    )
    repo.create_api_key.assert_awaited_once()
    kwargs = repo.create_api_key.await_args.kwargs
    assert kwargs["project_id"] == "proj_1"
    assert kwargs["owner_type"] == "service_account"
    assert kwargs["service_account_id"] == "sa_1"
    assert kwargs["scopes"] == ["models.invoke"]
    assert kwargs["ip_allowlist"] == ["10.0.0.1"]
    assert kwargs["rate_limits"] == {"requests_per_minute": 60}
    assert kwargs["spend_limit"] == 100


async def test_create_project_scoped_key_rejects_project_without_access(
    service, repo, project_access
):
    project_access.validate_project_access.return_value = False

    result = await service.create_api_key(
        organization_id="org_1",
        name="CI key",
        created_by="usr_1",
        project_id="proj_forbidden",
        auth_token="Bearer token",
    )

    assert result["success"] is False
    assert "not authorized" in result["error"].lower()
    repo.create_api_key.assert_not_awaited()


async def test_create_service_account_key_requires_service_account_id(service, repo):
    result = await service.create_api_key(
        organization_id="org_1",
        name="CI key",
        owner_type="service_account",
    )

    assert result["success"] is False
    assert "service_account_id" in result["error"]
    repo.create_api_key.assert_not_awaited()


async def test_list_api_keys_passes_project_filter_and_counts_filtered_keys(
    service, repo
):
    repo.get_organization_api_keys.return_value = [
        {"key_id": "key_1", "project_id": "proj_1", "key_preview": "isa_...abcd"}
    ]

    result = await service.list_api_keys("org_1", project_id="proj_1")

    assert result == {
        "success": True,
        "api_keys": [
            {"key_id": "key_1", "project_id": "proj_1", "key_preview": "isa_...abcd"}
        ],
        "total": 1,
    }
    repo.get_organization_api_keys.assert_awaited_once_with(
        "org_1", project_id="proj_1"
    )


async def test_verify_project_scoped_key_returns_metadata_for_billing(service, repo):
    repo.validate_api_key.return_value = {
        "valid": True,
        "organization_id": "org_1",
        "key_id": "key_1",
        "name": "CI key",
        "permissions": ["read:data"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used": None,
        "project_id": "proj_1",
        "owner_type": "service_account",
        "service_account_id": "sa_1",
        "scopes": ["models.invoke"],
        "ip_allowlist": ["10.0.0.1"],
        "rate_limits": {"requests_per_minute": 60},
        "spend_limit": 100,
    }
    repo.get_api_key_rate_limits.return_value = {"requests_per_minute": 60}

    result = await service.verify_api_key(
        "isa_secret", project_id="proj_1", ip_address="10.0.0.1"
    )

    assert result["valid"] is True
    assert result["project_id"] == "proj_1"
    assert result["owner_type"] == "service_account"
    assert result["service_account_id"] == "sa_1"
    assert result["scopes"] == ["models.invoke"]
    assert result["ip_allowlist"] == ["10.0.0.1"]
    assert result["rate_limits"] == {"requests_per_minute": 60}
    assert result["spend_limit"] == 100
    repo.validate_api_key.assert_awaited_once_with(
        "isa_secret", project_id="proj_1", ip_address="10.0.0.1"
    )
