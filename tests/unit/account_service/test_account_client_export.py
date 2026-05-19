from unittest.mock import AsyncMock

import pytest

from microservices.account_service.client import AccountServiceClient


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_export_user_data_collects_account_profile_and_claims():
    client = AccountServiceClient(base_url="http://test:8202")
    client.get_account_profile = AsyncMock(
        return_value={
            "user_id": "user-1",
            "email": "user@example.com",
            "name": "User One",
            "is_active": True,
            "preferences": {"theme": "dark", "language": "en"},
            "created_at": "2026-05-01T00:00:00",
            "updated_at": "2026-05-02T00:00:00",
        }
    )
    client.get_account_claims = AsyncMock(
        return_value={
            "user_id": "user-1",
            "name": "User One",
            "is_active": True,
            "admin_roles": ["platform_admin"],
        }
    )

    result = await client.export_user_data(
        user_id="user-1",
        organization_id="org-1",
        request_id="gdpr_req_1",
    )

    assert result["schema_version"] == "account-export-v1"
    assert result["service"] == "account_service"
    assert result["user_id"] == "user-1"
    assert result["organization_id"] == "org-1"
    assert result["gdpr_request_id"] == "gdpr_req_1"
    assert result["profile"]["email"] == "user@example.com"
    assert result["profile"]["preferences"] == {"theme": "dark", "language": "en"}
    assert result["claims"]["admin_roles"] == ["platform_admin"]
    assert result["counts"] == {
        "records": 1,
        "sections": {"profile": 1, "claims": 1, "preferences": 1},
    }
    client.get_account_profile.assert_awaited_once_with("user-1")
    client.get_account_claims.assert_awaited_once_with("user-1")
    await client.close()


async def test_export_user_data_returns_empty_export_when_account_is_missing():
    client = AccountServiceClient(base_url="http://test:8202")
    client.get_account_profile = AsyncMock(return_value=None)
    client.get_account_claims = AsyncMock(return_value=None)

    result = await client.export_user_data(
        user_id="missing-user",
        organization_id=None,
        request_id="gdpr_req_missing",
    )

    assert result["user_id"] == "missing-user"
    assert result["organization_id"] is None
    assert result["gdpr_request_id"] == "gdpr_req_missing"
    assert result["profile"] is None
    assert result["claims"] is None
    assert result["counts"] == {
        "records": 0,
        "sections": {"profile": 0, "claims": 0, "preferences": 0},
    }
    await client.close()
