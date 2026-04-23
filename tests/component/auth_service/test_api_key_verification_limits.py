"""Component tests for auth-side effective limit resolution and usage bars."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from microservices.auth_service.api_key_service import (
    ApiKeyService,
    raise_api_key_rate_limit_if_present,
)
from microservices.auth_service.rate_limit_state import RequestRateLimiter

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


def _make_service(repo, org_client=None, billing_response=None):
    billing_http_client = AsyncMock()
    response = MagicMock()
    response.json.return_value = billing_response or {"aggregations": []}
    response.raise_for_status.return_value = None
    billing_http_client.get.return_value = response
    return ApiKeyService(
        repository=repo,
        organization_service_client=org_client,
        request_rate_limiter=RequestRateLimiter(),
        billing_http_client=billing_http_client,
    )


class TestVerifyApiKeyRateLimits:
    async def test_verify_api_key_response_mapping_propagates_rate_limit_response(self):
        result = {
            "rate_limited": True,
            "status_code": 429,
            "detail": {"field": "requests_per_minute"},
            "headers": {"Retry-After": "60"},
        }

        with pytest.raises(HTTPException) as exc_info:
            raise_api_key_rate_limit_if_present(result)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail == {"field": "requests_per_minute"}
        assert exc_info.value.headers == {"Retry-After": "60"}

    async def test_org_defaults_are_enforced_when_key_has_no_override(self):
        repo = AsyncMock()
        repo.validate_api_key.return_value = {
            "valid": True,
            "organization_id": "org_a",
            "key_id": "key_1",
            "permissions": [],
        }
        repo.get_api_key_rate_limits.return_value = {}
        org_client = AsyncMock()
        org_client.get_org_rate_limits.return_value = {"requests_per_minute": 1}
        service = _make_service(repo, org_client=org_client)

        first = await service.verify_api_key("isa_first")
        second = await service.verify_api_key("isa_second")

        assert first["valid"] is True
        assert second["valid"] is False
        assert second["rate_limited"] is True
        assert second["status_code"] == 429
        assert second["detail"]["source"] == "organization"

    async def test_per_key_override_wins_over_org_default(self):
        repo = AsyncMock()
        repo.validate_api_key.return_value = {
            "valid": True,
            "organization_id": "org_a",
            "key_id": "key_1",
            "permissions": [],
        }
        repo.get_api_key_rate_limits.return_value = {"requests_per_minute": 2}
        org_client = AsyncMock()
        org_client.get_org_rate_limits.return_value = {"requests_per_minute": 1}
        service = _make_service(repo, org_client=org_client)

        first = await service.verify_api_key("isa_1")
        second = await service.verify_api_key("isa_2")
        third = await service.verify_api_key("isa_3")

        assert first["valid"] is True
        assert second["valid"] is True
        assert third["rate_limited"] is True
        assert third["detail"]["source"] == "api_key"


class TestUsageVsLimit:
    async def test_daily_usage_uses_billing_aggregations(self):
        repo = AsyncMock()
        org_client = AsyncMock()
        org_client.get_org_rate_limits.return_value = {
            "requests_per_day": 100,
            "tokens_per_day": 1000,
        }
        service = _make_service(
            repo,
            org_client=org_client,
            billing_response={
                "aggregations": [
                    {"total_usage_count": 7, "total_usage_amount": 300},
                    {"total_usage_count": 5, "total_usage_amount": 200},
                ]
            },
        )

        result = await service.get_org_usage_vs_limit("org_a")

        assert result["success"] is True
        assert result["usage"]["requests_per_day"]["used"] == 12
        assert result["usage"]["requests_per_day"]["remaining"] == 88
        assert result["usage"]["tokens_per_day"]["used"] == 500
        assert result["usage"]["tokens_per_day"]["remaining"] == 500
