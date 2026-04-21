"""
Component tests for billing_service.get_usage_overview (Story #458).

Verifies the cross-service aggregator combines billing daily series with
agent counts, degrades gracefully when sub-services fail, and shapes the
response correctly for the console Usage page.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from microservices.billing_service.billing_service import BillingService

pytestmark = [pytest.mark.component, pytest.mark.tdd, pytest.mark.asyncio]


def _agg(period_start: datetime, count: int, amount: int, cost: float):
    """Build a minimal usage-aggregation row matching what the repo returns."""
    return SimpleNamespace(
        period_start=period_start,
        total_usage_count=count,
        total_usage_amount=amount,
        total_cost=Decimal(str(cost)),
    )


def _make_service(aggregations=None, agg_error=None, agent_count=3, agent_error=None):
    repository = AsyncMock()
    if agg_error is not None:
        repository.get_usage_aggregations.side_effect = agg_error
    else:
        repository.get_usage_aggregations.return_value = aggregations or []

    if agent_error is not None:
        agent_client = AsyncMock()
        agent_client.count_agents.side_effect = agent_error
    else:
        agent_client = AsyncMock()
        agent_client.count_agents.return_value = agent_count

    return BillingService(repository=repository, agent_client=agent_client)


class TestUsageOverview:
    async def test_combines_billing_and_agent_count(self):
        day1 = datetime(2026, 4, 19, tzinfo=timezone.utc)
        day2 = datetime(2026, 4, 20, tzinfo=timezone.utc)
        service = _make_service(
            aggregations=[
                _agg(day1, count=10, amount=1000, cost=0.50),
                _agg(day1, count=5, amount=500, cost=0.25),
                _agg(day2, count=20, amount=2000, cost=1.00),
            ],
            agent_count=4,
        )

        result = await service.get_usage_overview(user_id="u1", period_days=30)

        assert result["totals"]["requests"] == 35
        assert result["totals"]["tokens"] == 3500
        assert result["totals"]["cost"] == 1.75
        assert result["totals"]["currency"] == "USD"
        assert result["counts"]["active_agents"] == 4
        assert result["period"]["days"] == 30
        assert result["warnings"] == []
        assert len(result["daily"]) == 2
        # daily series is sorted oldest-first by date string
        assert result["daily"][0]["date"] == "2026-04-19"
        assert result["daily"][0]["requests"] == 15
        assert result["daily"][0]["tokens"] == 1500
        assert result["daily"][0]["cost"] == 0.75
        assert result["daily"][1]["date"] == "2026-04-20"

    async def test_warns_when_agent_service_returns_none(self):
        service = _make_service(aggregations=[], agent_count=None)

        result = await service.get_usage_overview(user_id="u1")

        assert result["counts"]["active_agents"] == 0
        assert "agent_service_unavailable" in result["warnings"]

    async def test_warns_when_agent_client_raises(self):
        service = _make_service(aggregations=[], agent_error=RuntimeError("boom"))

        result = await service.get_usage_overview(user_id="u1")

        assert result["counts"]["active_agents"] == 0
        assert "agent_service_unavailable" in result["warnings"]

    async def test_warns_when_billing_repo_raises_but_still_returns(self):
        service = _make_service(agg_error=RuntimeError("db down"), agent_count=2)

        result = await service.get_usage_overview(user_id="u1")

        assert result["totals"]["requests"] == 0
        assert result["totals"]["tokens"] == 0
        assert result["totals"]["cost"] == 0.0
        assert result["daily"] == []
        assert "billing_aggregations_unavailable" in result["warnings"]
        assert result["counts"]["active_agents"] == 2  # unaffected by billing error

    async def test_warns_when_no_agent_client_configured(self):
        repository = AsyncMock()
        repository.get_usage_aggregations.return_value = []
        service = BillingService(repository=repository, agent_client=None)

        result = await service.get_usage_overview(user_id="u1")

        assert "agent_service_unavailable" in result["warnings"]
        assert result["counts"]["active_agents"] == 0

    async def test_period_days_passed_through_to_repo(self):
        repository = AsyncMock()
        repository.get_usage_aggregations.return_value = []
        agent_client = AsyncMock()
        agent_client.count_agents.return_value = 0
        service = BillingService(repository=repository, agent_client=agent_client)

        before = datetime.utcnow()
        await service.get_usage_overview(user_id="u1", period_days=7, organization_id="o1")
        after = datetime.utcnow()

        repository.get_usage_aggregations.assert_awaited_once()
        kwargs = repository.get_usage_aggregations.await_args.kwargs
        assert kwargs["user_id"] == "u1"
        assert kwargs["organization_id"] == "o1"
        assert kwargs["period_type"] == "daily"
        assert kwargs["limit"] == 7
        # period_start should be ~7 days before period_end, both within the test window
        delta = kwargs["period_end"] - kwargs["period_start"]
        assert abs(delta - timedelta(days=7)) < timedelta(seconds=2)
        assert before - timedelta(seconds=2) <= kwargs["period_end"] <= after + timedelta(seconds=2)

    async def test_optional_counts_default_null(self):
        service = _make_service(aggregations=[], agent_count=0)

        result = await service.get_usage_overview(user_id="u1")

        # model_deployments and prompt_versions are reserved fields — null until wired
        assert result["counts"]["model_deployments"] is None
        assert result["counts"]["prompt_versions"] is None
