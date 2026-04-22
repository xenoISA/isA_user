"""Component tests for ApiKeyService rate-limit methods (Story xenoISA/isA_Console#461).

Mocks the repository so no DB is required. Verifies the success/failure
contract the API layer relies on.
"""

from unittest.mock import AsyncMock

import pytest

from microservices.auth_service.api_key_service import ApiKeyService

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def service(repo):
    return ApiKeyService(repository=repo)


SAMPLE = {
    "requests_per_second": 10,
    "requests_per_minute": 200,
    "requests_per_day": 10_000,
    "tokens_per_day": 1_000_000,
}


class TestGetRateLimits:
    async def test_returns_configured_when_overrides_exist(self, service, repo):
        repo.get_api_key_rate_limits.return_value = SAMPLE
        result = await service.get_rate_limits("org_a", "key_1")
        assert result == {
            "success": True,
            "rate_limits": SAMPLE,
            "source": "configured",
        }
        repo.get_api_key_rate_limits.assert_awaited_once_with("org_a", "key_1")

    async def test_returns_unset_for_empty_dict(self, service, repo):
        repo.get_api_key_rate_limits.return_value = {}
        result = await service.get_rate_limits("org_a", "key_1")
        assert result["success"] is True
        assert result["rate_limits"] == {}
        assert result["source"] == "unset"

    async def test_returns_failure_for_missing_key(self, service, repo):
        repo.get_api_key_rate_limits.return_value = None
        result = await service.get_rate_limits("org_a", "missing")
        assert result == {"success": False, "error": "API key not found"}

    async def test_propagates_repo_exception_as_failure(self, service, repo):
        repo.get_api_key_rate_limits.side_effect = RuntimeError("db down")
        result = await service.get_rate_limits("org_a", "key_1")
        assert result["success"] is False
        assert "db down" in result["error"]


class TestUpdateRateLimits:
    async def test_returns_configured_on_success(self, service, repo):
        repo.update_api_key_rate_limits.return_value = SAMPLE
        result = await service.update_rate_limits("org_a", "key_1", SAMPLE)
        assert result == {
            "success": True,
            "rate_limits": SAMPLE,
            "source": "configured",
        }
        repo.update_api_key_rate_limits.assert_awaited_once_with(
            "org_a", "key_1", SAMPLE
        )

    async def test_returns_failure_when_key_missing(self, service, repo):
        repo.update_api_key_rate_limits.return_value = None
        result = await service.update_rate_limits("org_a", "missing", SAMPLE)
        assert result == {"success": False, "error": "API key not found"}

    async def test_clearing_all_fields_is_supported(self, service, repo):
        # All-None payload (the API path forwards exclude_none=False).
        cleared = {
            "requests_per_second": None,
            "requests_per_minute": None,
            "requests_per_day": None,
            "tokens_per_day": None,
        }
        repo.update_api_key_rate_limits.return_value = cleared
        result = await service.update_rate_limits("org_a", "key_1", cleared)
        assert result["success"] is True
        assert result["rate_limits"] == cleared

    async def test_propagates_repo_exception_as_failure(self, service, repo):
        repo.update_api_key_rate_limits.side_effect = RuntimeError("write failed")
        result = await service.update_rate_limits("org_a", "key_1", SAMPLE)
        assert result["success"] is False
        assert "write failed" in result["error"]
