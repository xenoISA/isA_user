"""
Unit tests for console billing APIs (stories #238-#243).

Covers:
  - Story #238: get_user_billing_status()
  - Story #239: /api/v1/billing/user/status endpoint
  - Story #242: group_by=agent_id aggregations
  - Story #243: agent_id filtering on records/aggregations
  - Story #240: group_by=service_type aggregations
  - Story #241: /api/v1/billing/invoices endpoint
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from microservices.billing_service.billing_service import BillingService
from microservices.billing_service.models import (
    BillingRecord,
    BillingStatus,
    BillingMethod,
    ServiceType,
    Currency,
    UsageAggregation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_repository(**overrides):
    repo = AsyncMock()
    repo.get_usage_aggregations = AsyncMock(return_value=[])
    repo.list_billing_records = AsyncMock(return_value=([], 0))
    repo.get_user_billing_records = AsyncMock(return_value=[])
    repo.get_billing_stats = AsyncMock(return_value={
        "total_billing_records": 0,
        "pending_billing_records": 0,
        "completed_billing_records": 0,
        "failed_billing_records": 0,
        "total_revenue": 0,
        "revenue_by_service": {},
        "revenue_by_method": {},
        "active_users": 0,
        "period_start": datetime(2026, 4, 1, tzinfo=timezone.utc),
        "period_end": datetime(2026, 4, 30, tzinfo=timezone.utc),
    })
    for k, v in overrides.items():
        setattr(repo, k, v)
    return repo


def _make_service(repository=None, subscription_client=None, **kw):
    repo = repository or _make_mock_repository()
    svc = BillingService(
        repository=repo,
        event_bus=None,
        product_client=None,
        wallet_client=None,
        subscription_client=subscription_client,
    )
    return svc


# ===========================================================================
# Story #238: get_user_billing_status()
# ===========================================================================


@pytest.mark.unit
class TestGetUserBillingStatus:
    """Story #238 - unified billing status view."""

    def setup_method(self):
        """Clear billing status cache between tests."""
        BillingService._billing_status_cache.clear()

    @pytest.mark.asyncio
    async def test_returns_unified_billing_status(self):
        sub_client = AsyncMock()
        sub_client.get_user_subscription = AsyncMock(return_value={
            "tier_code": "pro",
            "credits_remaining": 5000,
            "credits_limit": 10000,
            "next_billing_date": "2026-05-01T00:00:00Z",
            "payment_status": "active",
            "subscription_id": "sub_123",
        })
        sub_client.get_credit_balance = AsyncMock(return_value={
            "success": True,
            "subscription_credits_remaining": 5000,
            "subscription_id": "sub_123",
        })

        repo = _make_mock_repository()
        repo.get_usage_aggregations = AsyncMock(return_value=[
            UsageAggregation(
                aggregation_id="agg_1",
                period_start=datetime(2026, 4, 1, tzinfo=timezone.utc),
                period_end=datetime(2026, 5, 1, tzinfo=timezone.utc),
                period_type="monthly",
                total_usage_count=100,
                total_usage_amount=Decimal("5000"),
                total_cost=Decimal("25.50"),
                service_breakdown={},
            )
        ])

        svc = _make_service(repository=repo, subscription_client=sub_client)
        result = await svc.get_user_billing_status("user_123")

        assert result["subscription_tier"] == "pro"
        assert result["credits_remaining"] == 5000
        assert result["credits_limit"] == 10000
        assert result["payment_status"] == "active"
        assert result["current_period_usage"]["requests"] == 100
        assert result["current_period_usage"]["tokens"] == 5000
        assert result["current_period_usage"]["cost"] == 25.50

    @pytest.mark.asyncio
    async def test_fallback_to_free_tier_when_subscription_unavailable(self):
        sub_client = AsyncMock()
        sub_client.get_user_subscription = AsyncMock(return_value=None)
        sub_client.get_credit_balance = AsyncMock(return_value=None)

        repo = _make_mock_repository()
        repo.get_usage_aggregations = AsyncMock(return_value=[])

        svc = _make_service(repository=repo, subscription_client=sub_client)
        result = await svc.get_user_billing_status("user_123")

        assert result["subscription_tier"] == "free"
        assert result["credits_remaining"] == 0
        assert result["credits_limit"] == 0
        assert result["warning"] == "subscription_service_unavailable"

    @pytest.mark.asyncio
    async def test_caching_returns_same_result_within_ttl(self):
        sub_client = AsyncMock()
        sub_client.get_user_subscription = AsyncMock(return_value={
            "tier_code": "max",
            "credits_remaining": 9000,
            "credits_limit": 20000,
            "next_billing_date": "2026-06-01T00:00:00Z",
            "payment_status": "active",
            "subscription_id": "sub_456",
        })
        sub_client.get_credit_balance = AsyncMock(return_value={
            "success": True,
            "subscription_credits_remaining": 9000,
        })

        repo = _make_mock_repository()
        repo.get_usage_aggregations = AsyncMock(return_value=[])

        svc = _make_service(repository=repo, subscription_client=sub_client)

        r1 = await svc.get_user_billing_status("user_123")
        r2 = await svc.get_user_billing_status("user_123")

        # subscription client should be called only once due to caching
        assert sub_client.get_user_subscription.call_count == 1
        assert r1 == r2

    @pytest.mark.asyncio
    async def test_no_subscription_client_returns_free_with_warning(self):
        svc = _make_service(subscription_client=None)
        result = await svc.get_user_billing_status("user_123")

        assert result["subscription_tier"] == "free"
        assert result["warning"] == "subscription_service_unavailable"


# ===========================================================================
# Story #239: /api/v1/billing/user/status endpoint
# ===========================================================================


@pytest.mark.unit
class TestBillingStatusEndpoint:
    """Story #239 - REST endpoint for billing status."""

    @pytest.mark.asyncio
    async def test_status_endpoint_returns_200(self):
        from microservices.billing_service import main as billing_main

        mock_svc = AsyncMock()
        mock_svc.get_user_billing_status = AsyncMock(return_value={
            "subscription_tier": "pro",
            "credits_remaining": 5000,
            "credits_limit": 10000,
            "next_billing_date": "2026-05-01T00:00:00Z",
            "payment_status": "active",
            "current_period_usage": {"requests": 10, "tokens": 500, "cost": 1.5},
        })

        original = billing_main.billing_service
        billing_main.billing_service = mock_svc
        try:
            from httpx import AsyncClient, ASGITransport
            transport = ASGITransport(app=billing_main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/billing/user/status",
                    headers={"X-User-Id": "user_123"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["subscription_tier"] == "pro"
        finally:
            billing_main.billing_service = original


# ===========================================================================
# Story #242: group_by=agent_id aggregations
# ===========================================================================


@pytest.mark.unit
class TestGroupByAgentAggregations:
    """Story #242 - agent-level usage grouping."""

    @pytest.mark.asyncio
    async def test_group_by_agent_id_queries_repository(self):
        from microservices.billing_service import main as billing_main
        from microservices.billing_service.billing_repository import BillingRepository

        period_start = datetime(2026, 4, 8, 0, 0, tzinfo=timezone.utc)

        class _FakeDB:
            def __init__(self, rows):
                self.query = AsyncMock(return_value=rows)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

        repo = object.__new__(BillingRepository)
        repo.schema = "billing"
        repo.billing_records_table = "billing_records"
        repo.db = _FakeDB([
            {
                "agent_id": "agent_A",
                "total_tokens": 1500,
                "input_tokens": 1000,
                "output_tokens": 500,
                "request_count": 5,
                "total_cost_usd": 0.15,
            },
            {
                "agent_id": "agent_B",
                "total_tokens": 3000,
                "input_tokens": 2000,
                "output_tokens": 1000,
                "request_count": 10,
                "total_cost_usd": 0.30,
            },
        ])

        result = await repo.get_agent_usage_aggregations(user_id="user_123")
        assert len(result) == 2
        assert result[0]["agent_id"] == "agent_A"
        assert result[1]["agent_id"] == "agent_B"

    @pytest.mark.asyncio
    async def test_group_by_agent_id_via_endpoint(self):
        from microservices.billing_service import main as billing_main

        mock_svc = AsyncMock()
        mock_svc.repository = AsyncMock()
        mock_svc.repository.get_agent_usage_aggregations = AsyncMock(return_value=[
            {"agent_id": "agent_A", "total_tokens": 1500, "input_tokens": 1000,
             "output_tokens": 500, "request_count": 5, "total_cost_usd": 0.15},
        ])
        mock_svc.repository.get_usage_aggregations = AsyncMock(return_value=[])

        original = billing_main.billing_service
        billing_main.billing_service = mock_svc
        try:
            from httpx import AsyncClient, ASGITransport
            transport = ASGITransport(app=billing_main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/billing/usage/aggregations",
                    params={"user_id": "user_123", "group_by": "agent_id"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert "agent_aggregations" in data
        finally:
            billing_main.billing_service = original


# ===========================================================================
# Story #243: agent_id filtering
# ===========================================================================


@pytest.mark.unit
class TestAgentIdFiltering:
    """Story #243 - agent_id filtering on records and aggregations."""

    @pytest.mark.asyncio
    async def test_records_filtered_by_agent_id(self):
        from microservices.billing_service import main as billing_main

        mock_svc = AsyncMock()
        mock_svc.repository = AsyncMock()
        mock_svc.repository.get_user_billing_records = AsyncMock(return_value=[
            BillingRecord(
                billing_id="bill_1",
                user_id="user_123",
                agent_id="agent_A",
                usage_record_id="ur_1",
                product_id="gpt-4o",
                service_type=ServiceType.MODEL_INFERENCE,
                usage_amount=Decimal("100"),
                unit_price=Decimal("0.01"),
                total_amount=Decimal("1.0"),
                billing_method=BillingMethod.CREDIT_CONSUMPTION,
            )
        ])

        original = billing_main.billing_service
        billing_main.billing_service = mock_svc
        try:
            from httpx import AsyncClient, ASGITransport
            transport = ASGITransport(app=billing_main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/billing/records/user/user_123",
                    params={"agent_id": "agent_A"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["records"]) == 1
            assert data["records"][0]["agent_id"] == "agent_A"
        finally:
            billing_main.billing_service = original


# ===========================================================================
# Story #240: group_by=service_type
# ===========================================================================


@pytest.mark.unit
class TestGroupByServiceType:
    """Story #240 - service-level consumption breakdown."""

    @pytest.mark.asyncio
    async def test_group_by_service_type_queries_repository(self):
        from microservices.billing_service.billing_repository import BillingRepository

        class _FakeDB:
            def __init__(self, rows):
                self.query = AsyncMock(return_value=rows)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

        repo = object.__new__(BillingRepository)
        repo.schema = "billing"
        repo.billing_records_table = "billing_records"
        repo.db = _FakeDB([
            {
                "service_type": "model_inference",
                "request_count": 100,
                "total_tokens": 50000,
                "total_cost_usd": 5.0,
            },
            {
                "service_type": "mcp_service",
                "request_count": 20,
                "total_tokens": 1000,
                "total_cost_usd": 0.5,
            },
        ])

        result = await repo.get_service_usage_aggregations(user_id="user_123")
        assert len(result) == 2
        assert result[0]["service_type"] == "model_inference"

    @pytest.mark.asyncio
    async def test_group_by_service_type_via_endpoint(self):
        from microservices.billing_service import main as billing_main

        mock_svc = AsyncMock()
        mock_svc.repository = AsyncMock()
        mock_svc.repository.get_service_usage_aggregations = AsyncMock(return_value=[
            {"service_type": "model_inference", "request_count": 100,
             "total_tokens": 50000, "total_cost_usd": 5.0},
        ])
        mock_svc.repository.get_usage_aggregations = AsyncMock(return_value=[])

        original = billing_main.billing_service
        billing_main.billing_service = mock_svc
        try:
            from httpx import AsyncClient, ASGITransport
            transport = ASGITransport(app=billing_main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/billing/usage/aggregations",
                    params={"user_id": "user_123", "group_by": "service_type"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert "service_aggregations" in data
        finally:
            billing_main.billing_service = original


# ===========================================================================
# Story #241: invoice/billing history API
# ===========================================================================


@pytest.mark.unit
class TestInvoiceAPI:
    """Story #241 - invoice and billing history."""

    @pytest.mark.asyncio
    async def test_invoices_endpoint_returns_paginated_list(self):
        from microservices.billing_service import main as billing_main

        mock_svc = AsyncMock()
        mock_svc.repository = AsyncMock()
        mock_svc.repository.get_invoices = AsyncMock(return_value={
            "invoices": [
                {
                    "period_start": "2026-03-01T00:00:00Z",
                    "period_end": "2026-04-01T00:00:00Z",
                    "total_credits_used": 5000,
                    "total_cost_usd": 12.50,
                    "tier": "pro",
                    "payment_status": "paid",
                },
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
        })

        original = billing_main.billing_service
        billing_main.billing_service = mock_svc
        try:
            from httpx import AsyncClient, ASGITransport
            transport = ASGITransport(app=billing_main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/billing/invoices",
                    params={"user_id": "user_123"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert "invoices" in data
            assert data["total"] == 1
        finally:
            billing_main.billing_service = original

    @pytest.mark.asyncio
    async def test_invoices_with_date_filter(self):
        from microservices.billing_service import main as billing_main

        mock_svc = AsyncMock()
        mock_svc.repository = AsyncMock()
        mock_svc.repository.get_invoices = AsyncMock(return_value={
            "invoices": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
        })

        original = billing_main.billing_service
        billing_main.billing_service = mock_svc
        try:
            from httpx import AsyncClient, ASGITransport
            transport = ASGITransport(app=billing_main.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/billing/invoices",
                    params={
                        "user_id": "user_123",
                        "start_date": "2026-01-01T00:00:00Z",
                        "end_date": "2026-02-01T00:00:00Z",
                    },
                )
            assert resp.status_code == 200
        finally:
            billing_main.billing_service = original
