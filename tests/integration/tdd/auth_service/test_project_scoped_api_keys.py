from datetime import datetime, timedelta, timezone

import pytest

from microservices.auth_service.api_key_repository import ApiKeyRepository

pytestmark = [pytest.mark.integration, pytest.mark.tdd, pytest.mark.asyncio]


class MemoryApiKeyDb:
    def __init__(self):
        self.organizations = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def query_row(self, query, params=None):
        params = params or []
        organization_id = params[0] if params else None
        api_keys = self.organizations.get(organization_id)
        if api_keys is None:
            return None
        return {"organization_id": organization_id, "api_keys": api_keys}

    async def query(self, query, params=None):
        return [
            {"organization_id": organization_id, "api_keys": api_keys}
            for organization_id, api_keys in self.organizations.items()
        ]

    async def execute(self, query, params=None):
        params = params or []
        if query.strip().startswith("INSERT"):
            organization_id = params[0]
            self.organizations.setdefault(organization_id, [])
            return 1

        if query.strip().startswith("UPDATE"):
            api_keys = params[0]
            organization_id = params[-1]
            self.organizations[organization_id] = api_keys
            return 1

        return 0


@pytest.fixture
def repository():
    repo = object.__new__(ApiKeyRepository)
    repo.organization_service_client = None
    repo.db = MemoryApiKeyDb()
    repo.schema = "auth"
    repo.organizations_table = "organizations"
    return repo


async def test_project_scoped_key_lifecycle_round_trips_metadata(repository):
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    created = await repository.create_api_key(
        organization_id="org_1",
        name="Project service account",
        permissions=["read:data"],
        expires_at=expires_at,
        created_by="usr_1",
        project_id="proj_1",
        owner_type="service_account",
        service_account_id="sa_1",
        scopes=["models.invoke"],
        ip_allowlist=["10.0.0.1"],
        rate_limits={"requests_per_minute": 60},
        spend_limit=50,
    )

    assert created["api_key"].startswith("isa_")
    assert created["project_id"] == "proj_1"

    listed = await repository.get_organization_api_keys("org_1", project_id="proj_1")
    assert len(listed) == 1
    assert listed[0]["project_id"] == "proj_1"
    assert listed[0]["owner_type"] == "service_account"
    assert listed[0]["service_account_id"] == "sa_1"
    assert listed[0]["scopes"] == ["models.invoke"]
    assert listed[0]["ip_allowlist"] == ["10.0.0.1"]
    assert listed[0]["rate_limits"] == {"requests_per_minute": 60}
    assert listed[0]["spend_limit"] == 50
    assert "api_key" not in listed[0]
    assert "key_hash" not in listed[0]

    verified = await repository.validate_api_key(
        created["api_key"], project_id="proj_1", ip_address="10.0.0.1"
    )
    assert verified["valid"] is True
    assert verified["project_id"] == "proj_1"
    assert verified["owner_type"] == "service_account"
    assert verified["service_account_id"] == "sa_1"
    assert verified["scopes"] == ["models.invoke"]
    assert verified["rate_limits"] == {"requests_per_minute": 60}
    assert verified["spend_limit"] == 50

    mismatch = await repository.validate_api_key(
        created["api_key"], project_id="proj_2", ip_address="10.0.0.1"
    )
    assert mismatch == {
        "valid": False,
        "error": "API key is not scoped to project proj_2",
    }

    blocked_ip = await repository.validate_api_key(
        created["api_key"], project_id="proj_1", ip_address="10.0.0.2"
    )
    assert blocked_ip == {
        "valid": False,
        "error": "IP address is not allowed for this API key",
    }

    assert await repository.revoke_api_key("org_1", created["key_id"]) is True
    revoked = await repository.validate_api_key(created["api_key"], project_id="proj_1")
    assert revoked["valid"] is False


async def test_legacy_org_scoped_keys_remain_readable(repository):
    api_key = "isa_legacy"
    repository.db.organizations["org_1"] = [
        {
            "key_id": "key_legacy",
            "name": "Legacy key",
            "key_hash": repository._hash_api_key(api_key),
            "permissions": ["read:data"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "usr_1",
            "expires_at": None,
            "is_active": True,
            "last_used": None,
        }
    ]

    listed = await repository.get_organization_api_keys("org_1")
    assert listed[0]["owner_type"] == "organization"
    assert listed[0]["project_id"] is None
    assert listed[0]["scopes"] == ["read:data"]

    verified = await repository.validate_api_key(api_key)
    assert verified["valid"] is True
    assert verified["owner_type"] == "organization"
    assert verified["project_id"] is None
    assert verified["scopes"] == ["read:data"]
