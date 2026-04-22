"""Component tests for OrganizationRepository rate-limit methods (#461)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from microservices.organization_service.organization_repository import (
    OrganizationRepository,
)

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


SAMPLE = {
    "requests_per_second": 10,
    "requests_per_minute": 200,
    "requests_per_day": 10_000,
    "tokens_per_day": 1_000_000,
}


@pytest.fixture
def repo():
    """Build a repo without touching the real DB constructor logic."""
    repo = OrganizationRepository.__new__(OrganizationRepository)
    repo.schema = "organization"
    repo.organizations_table = "organizations"
    db = MagicMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=None)
    db.query_row = AsyncMock()
    db.execute = AsyncMock()
    repo.db = db
    return repo


class TestGetOrgRateLimits:
    async def test_returns_dict_when_present(self, repo):
        repo.db.query_row.return_value = {"rate_limits": SAMPLE}
        result = await repo.get_org_rate_limits("org_a")
        assert result == SAMPLE

    async def test_returns_empty_when_column_null(self, repo):
        repo.db.query_row.return_value = {"rate_limits": None}
        result = await repo.get_org_rate_limits("org_a")
        assert result == {}

    async def test_returns_none_when_org_missing(self, repo):
        repo.db.query_row.return_value = None
        result = await repo.get_org_rate_limits("missing")
        assert result is None

    async def test_parses_json_string(self, repo):
        # Some drivers return JSONB as a string instead of a dict.
        repo.db.query_row.return_value = {"rate_limits": json.dumps(SAMPLE)}
        result = await repo.get_org_rate_limits("org_a")
        assert result == SAMPLE


class TestUpdateOrgRateLimits:
    async def test_returns_payload_on_success(self, repo):
        repo.db.execute.return_value = 1
        result = await repo.update_org_rate_limits("org_a", SAMPLE)
        assert result == SAMPLE
        repo.db.execute.assert_awaited_once()

    async def test_returns_none_when_org_missing(self, repo):
        repo.db.execute.return_value = 0
        result = await repo.update_org_rate_limits("missing", SAMPLE)
        assert result is None

    async def test_returns_none_on_exception(self, repo):
        repo.db.execute.side_effect = RuntimeError("write failed")
        result = await repo.update_org_rate_limits("org_a", SAMPLE)
        assert result is None
