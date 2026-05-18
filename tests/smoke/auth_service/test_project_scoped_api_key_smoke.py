from unittest.mock import AsyncMock

import pytest

from microservices.auth_service.api_key_repository import ApiKeyRepository
from microservices.auth_service.api_key_service import ApiKeyService
from tests.integration.tdd.auth_service.test_project_scoped_api_keys import MemoryApiKeyDb

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


class AllowingProjectAccess:
    async def validate_project_access(self, **kwargs):
        return True


@pytest.fixture
def repository():
    repo = object.__new__(ApiKeyRepository)
    repo.organization_service_client = None
    repo.db = MemoryApiKeyDb()
    repo.schema = "auth"
    repo.organizations_table = "organizations"
    return repo


async def test_project_scoped_api_key_create_verify_list_revoke_smoke(repository):
    service = ApiKeyService(
        repository=repository,
        project_access_client=AllowingProjectAccess(),
        billing_http_client=AsyncMock(),
    )

    created = await service.create_api_key(
        organization_id="org_1",
        name="Smoke project key",
        created_by="usr_1",
        project_id="proj_1",
        scopes=["models.invoke"],
        ip_allowlist=["127.0.0.1"],
        rate_limits={"requests_per_minute": 10},
        spend_limit=5,
    )
    assert created["success"] is True

    listed = await service.list_api_keys("org_1", project_id="proj_1")
    assert listed["total"] == 1
    assert listed["api_keys"][0]["project_id"] == "proj_1"

    verified = await service.verify_api_key(
        created["api_key"], project_id="proj_1", ip_address="127.0.0.1"
    )
    assert verified["valid"] is True
    assert verified["project_id"] == "proj_1"
    assert verified["scopes"] == ["models.invoke"]

    revoked = await service.revoke_api_key(created["key_id"], "org_1")
    assert revoked["success"] is True

    verify_revoked = await service.verify_api_key(created["api_key"], project_id="proj_1")
    assert verify_revoked["valid"] is False
