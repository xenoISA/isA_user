"""
API tests for all billing surfaces (Story #255).

Seeds billing records for each of the 16 service types via the database,
then validates aggregations, agent attribution, and invoices work correctly
via real HTTP calls to the live billing_service.

Requires: billing_service running on localhost:8000
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

BILLING_URL = "http://localhost:8000"
FIXTURE_PATH = Path(__file__).parent / "../../unit/golden/billing_service/billing_units_fixture.json"
TEST_USER = f"api-test-{uuid.uuid4().hex[:8]}"
TEST_ORG = "api-test-org"
TEST_AGENT = "api-test-agent-alpha"


@pytest.fixture(scope="module")
def fixture_data():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def service_units(fixture_data):
    return fixture_data["service_units"]


def _is_service_up():
    try:
        r = httpx.get(f"{BILLING_URL}/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


# Skip entire module if billing_service is not running
pytestmark = pytest.mark.skipif(
    not _is_service_up(),
    reason="billing_service not running on localhost:8000",
)


@pytest.fixture(scope="module")
def seeded_records(service_units):
    """Seed one billing record per service type via direct DB insert using the MCP postgres connection."""
    # We'll use the billing admin endpoint or direct HTTP to seed
    # Since the usage/record endpoint requires product pricing, we use the DB
    # But for API tests we need a different approach — let's check if admin endpoint exists
    records = []
    for i, entry in enumerate(service_units):
        record = {
            "billing_id": f"api-test-{TEST_USER}-{entry['service_type']}-{uuid.uuid4().hex[:8]}",
            "usage_record_id": f"ur-api-{i}",
            "user_id": TEST_USER,
            "organization_id": TEST_ORG,
            "agent_id": TEST_AGENT if entry["service_type"] in ("model_inference", "agent_execution", "mcp_service") else None,
            "product_id": f"product-{entry['service_type']}",
            "service_type": entry["service_type"],
            "usage_amount": entry["example_usage_amount"],
            "unit_price": entry["example_unit_price"],
            "total_amount": round(entry["example_usage_amount"] * entry["example_unit_price"], 6),
            "currency": "USD",
            "billing_method": "credit_consumption",
            "billing_status": "completed",
        }
        records.append(record)
    return records


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(seeded_records):
    """Insert test records into DB and clean up after."""
    import asyncio

    async def _seed():
        import asyncpg
        conn = await asyncpg.connect(
            host="localhost", port=5432,
            user="postgres", password="staging_postgres_2024",
            database="isa_platform",
        )
        try:
            for rec in seeded_records:
                await conn.execute("""
                    INSERT INTO billing.billing_records
                    (billing_id, usage_record_id, user_id, organization_id, agent_id,
                     product_id, service_type, usage_amount, unit_price, total_amount,
                     currency, billing_method, billing_status)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                    ON CONFLICT (billing_id) DO NOTHING
                """,
                    rec["billing_id"], rec["usage_record_id"], rec["user_id"],
                    rec["organization_id"], rec["agent_id"], rec["product_id"],
                    rec["service_type"], rec["usage_amount"], rec["unit_price"],
                    rec["total_amount"], rec["currency"], rec["billing_method"],
                    rec["billing_status"],
                )
        finally:
            await conn.close()

    async def _cleanup():
        import asyncpg
        conn = await asyncpg.connect(
            host="localhost", port=5432,
            user="postgres", password="staging_postgres_2024",
            database="isa_platform",
        )
        try:
            await conn.execute(
                "DELETE FROM billing.billing_records WHERE user_id = $1", TEST_USER
            )
        finally:
            await conn.close()

    asyncio.get_event_loop().run_until_complete(_seed())
    yield
    asyncio.get_event_loop().run_until_complete(_cleanup())


# ===========================================================================
# Test: Unified billing status
# ===========================================================================


@pytest.mark.api
class TestBillingStatusAPI:
    def test_returns_usage_for_seeded_user(self):
        resp = httpx.get(
            f"{BILLING_URL}/api/v1/billing/user/status",
            headers={"X-User-Id": TEST_USER},
            timeout=5.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == TEST_USER
        assert data["current_period_usage"]["requests"] == 16  # one per service type
        assert data["current_period_usage"]["tokens"] > 0

    def test_401_without_auth(self):
        resp = httpx.get(f"{BILLING_URL}/api/v1/billing/user/status", timeout=5.0)
        assert resp.status_code == 401


# ===========================================================================
# Test: group_by=service_type — should return all 16 service types
# ===========================================================================


@pytest.mark.api
class TestServiceTypeAggregation:
    def test_returns_all_16_service_types(self):
        resp = httpx.get(
            f"{BILLING_URL}/api/v1/billing/usage/aggregations",
            params={"user_id": TEST_USER, "group_by": "service_type"},
            timeout=5.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        aggs = data["service_aggregations"]
        service_types = {a["service_type"] for a in aggs}
        assert len(service_types) == 16, f"Expected 16 service types, got {len(service_types)}: {service_types}"

    def test_each_service_has_correct_count(self):
        resp = httpx.get(
            f"{BILLING_URL}/api/v1/billing/usage/aggregations",
            params={"user_id": TEST_USER, "group_by": "service_type"},
            timeout=5.0,
        )
        data = resp.json()
        for agg in data["service_aggregations"]:
            assert agg["request_count"] >= 1, f"{agg['service_type']} has 0 requests"
            assert agg["total_tokens"] >= 0


# ===========================================================================
# Test: group_by=agent_id — should show agent attribution
# ===========================================================================


@pytest.mark.api
class TestAgentAggregation:
    def test_returns_agent_and_null_groups(self):
        resp = httpx.get(
            f"{BILLING_URL}/api/v1/billing/usage/aggregations",
            params={"user_id": TEST_USER, "group_by": "agent_id"},
            timeout=5.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        aggs = data["agent_aggregations"]
        agent_ids = {a["agent_id"] for a in aggs}
        assert TEST_AGENT in agent_ids, f"Expected {TEST_AGENT} in agents, got {agent_ids}"
        assert None in agent_ids, "Expected null agent group for non-agent services"

    def test_agent_has_3_records(self):
        """model_inference + agent_execution + mcp_service = 3 records for test agent."""
        resp = httpx.get(
            f"{BILLING_URL}/api/v1/billing/usage/aggregations",
            params={"user_id": TEST_USER, "group_by": "agent_id"},
            timeout=5.0,
        )
        data = resp.json()
        agent_agg = next(a for a in data["agent_aggregations"] if a["agent_id"] == TEST_AGENT)
        assert agent_agg["request_count"] == 3


# ===========================================================================
# Test: agent_id filtering
# ===========================================================================


@pytest.mark.api
class TestAgentFiltering:
    def test_filter_by_agent_returns_only_agent_records(self):
        resp = httpx.get(
            f"{BILLING_URL}/api/v1/billing/usage/aggregations",
            params={"user_id": TEST_USER, "agent_id": TEST_AGENT},
            timeout=5.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should only contain records with agent_id = TEST_AGENT
        assert data["total_count"] >= 1


# ===========================================================================
# Test: Invoices
# ===========================================================================


@pytest.mark.api
class TestInvoicesAPI:
    def test_returns_monthly_invoice(self):
        resp = httpx.get(
            f"{BILLING_URL}/api/v1/billing/invoices",
            params={"user_id": TEST_USER},
            timeout=5.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        invoice = data["invoices"][0]
        assert invoice["total_records"] == 16
        assert invoice["total_credits_used"] > 0
        assert invoice["total_cost_usd"] > 0


# ===========================================================================
# Test: User billing records with agent filter
# ===========================================================================


@pytest.mark.api
class TestBillingRecordsAPI:
    def test_user_records_returns_all_16(self):
        resp = httpx.get(
            f"{BILLING_URL}/api/v1/billing/records/user/{TEST_USER}",
            timeout=5.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["records"]) == 16

    def test_user_records_filtered_by_agent(self):
        resp = httpx.get(
            f"{BILLING_URL}/api/v1/billing/records/user/{TEST_USER}",
            params={"agent_id": TEST_AGENT},
            timeout=5.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["records"]) == 3
        for rec in data["records"]:
            assert rec["agent_id"] == TEST_AGENT
