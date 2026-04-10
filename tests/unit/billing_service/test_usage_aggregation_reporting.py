from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from microservices.billing_service.billing_repository import BillingRepository


class _FakeDB:
    def __init__(self, rows):
        self.query = AsyncMock(return_value=rows)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.unit
class TestUsageAggregationReporting:
    @pytest.mark.asyncio
    async def test_aggregations_are_derived_from_billing_records_with_agent_scope(self):
        period_start = datetime(2026, 4, 8, 0, 0, tzinfo=timezone.utc)
        repo = object.__new__(BillingRepository)
        repo.schema = "billing"
        repo.billing_records_table = "billing_records"
        repo.db = _FakeDB(
            [
                {
                    "period_start": period_start,
                    "service_type": "model_inference",
                    "product_id": "gpt-4o-mini",
                    "total_usage_count": 1,
                    "total_usage_amount": 40,
                    "total_cost": 0.0100,
                },
                {
                    "period_start": period_start,
                    "service_type": "mcp_service",
                    "product_id": "tool:web_search",
                    "total_usage_count": 1,
                    "total_usage_amount": 2,
                    "total_cost": 0.0042,
                },
            ]
        )

        aggregations = await BillingRepository.get_usage_aggregations(
            repo,
            user_id="user_123",
            organization_id="org_123",
            agent_id="agent_123",
            period_type="daily",
            limit=10,
        )

        query = repo.db.query.call_args.args[0]
        params = repo.db.query.call_args.kwargs["params"]

        assert "date_trunc('day', created_at)" in query
        assert params == ["user_123", "org_123", "agent_123"]
        assert len(aggregations) == 1

        aggregation = aggregations[0]
        assert aggregation.user_id == "user_123"
        assert aggregation.organization_id == "org_123"
        assert aggregation.agent_id == "agent_123"
        assert aggregation.period_type == "daily"
        assert aggregation.total_usage_count == 2
        assert aggregation.total_usage_amount == Decimal("42")
        assert aggregation.total_cost == Decimal("0.0142")
        assert (
            aggregation.service_breakdown["model_inference"]["products"]["gpt-4o-mini"]["usage_count"]
            == 1
        )
        assert (
            aggregation.service_breakdown["mcp_service"]["products"]["tool:web_search"]["usage_amount"]
            == 2.0
        )
