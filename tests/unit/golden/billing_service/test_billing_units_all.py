"""
Golden test suite for all billing unit types (Stories #252, #253).

Validates that every ServiceType, UnitType, BillingMethod, and BillingStatus
enum value is accounted for in the billing_units_fixture and that the
billing_service can record and aggregate usage for each service type.
"""

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from microservices.billing_service.models import (
    ServiceType,
    BillingMethod,
    BillingStatus,
    BillingRecord,
    UsageAggregation,
)
from microservices.billing_service.billing_service import BillingService
from microservices.product_service.models import UnitType

# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).parent / "billing_units_fixture.json"


@pytest.fixture(scope="module")
def fixture_data():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def service_units(fixture_data):
    return fixture_data["service_units"]


@pytest.fixture(scope="module")
def service_type_map(service_units):
    """Map service_type -> fixture entry for quick lookup."""
    return {entry["service_type"]: entry for entry in service_units}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_repository(**overrides):
    repo = AsyncMock()
    repo.get_usage_aggregations = AsyncMock(return_value=[])
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


def _make_service(repository=None):
    repo = repository or _make_mock_repository()
    return BillingService(
        repository=repo,
        event_bus=None,
        product_client=None,
        wallet_client=None,
        subscription_client=None,
    )


# ===========================================================================
# Story #253: Fixture completeness — every enum value has a mapping
# ===========================================================================


@pytest.mark.unit
class TestFixtureCompleteness:
    """Validate the billing_units_fixture covers all enum values."""

    def test_all_service_types_in_fixture(self, service_type_map):
        """Every ServiceType enum value must appear in the fixture."""
        missing = []
        for st in ServiceType:
            if st.value not in service_type_map:
                missing.append(st.value)
        assert missing == [], f"ServiceType values missing from fixture: {missing}"

    def test_fixture_has_no_unknown_service_types(self, service_type_map):
        """Fixture should not contain service types that don't exist in the enum."""
        known = {st.value for st in ServiceType}
        unknown = [k for k in service_type_map if k not in known]
        assert unknown == [], f"Unknown service types in fixture: {unknown}"

    def test_all_billing_methods_in_fixture(self, fixture_data):
        fixture_methods = set(fixture_data["billing_methods"])
        enum_methods = {bm.value for bm in BillingMethod}
        assert enum_methods == fixture_methods, (
            f"Mismatch: enum={enum_methods - fixture_methods}, fixture={fixture_methods - enum_methods}"
        )

    def test_all_billing_statuses_in_fixture(self, fixture_data):
        fixture_statuses = set(fixture_data["billing_statuses"])
        enum_statuses = {bs.value for bs in BillingStatus}
        assert enum_statuses == fixture_statuses, (
            f"Mismatch: enum={enum_statuses - fixture_statuses}, fixture={fixture_statuses - enum_statuses}"
        )

    def test_fixture_unit_types_are_valid(self, service_units):
        """Every unit_type in the fixture must be a valid UnitType enum value."""
        valid = {ut.value for ut in UnitType}
        invalid = []
        for entry in service_units:
            if entry["unit_type"] not in valid:
                invalid.append((entry["service_type"], entry["unit_type"]))
        assert invalid == [], f"Invalid unit_types in fixture: {invalid}"

    def test_fixture_entries_have_required_fields(self, service_units):
        required = {"service_type", "meter_type", "unit_type", "example_usage_amount", "example_unit_price"}
        for entry in service_units:
            missing = required - set(entry.keys())
            assert missing == set(), f"{entry['service_type']} missing fields: {missing}"

    def test_fixture_has_16_service_types(self, service_units):
        assert len(service_units) == 16, f"Expected 16 service types, got {len(service_units)}"

    def test_unit_type_enum_coverage(self):
        """Document UnitType enum size for regression detection."""
        assert len(UnitType) == 20, f"UnitType enum changed: expected 20, got {len(UnitType)}"


# ===========================================================================
# Story #252: Golden tests — billing service handles every service type
# ===========================================================================


@pytest.mark.unit
class TestBillingRecordCreation:
    """Validate BillingRecord can be created for every service type."""

    @pytest.mark.parametrize("service_type", [st.value for st in ServiceType])
    def test_billing_record_accepts_service_type(self, service_type, service_type_map):
        """BillingRecord model accepts every known service type."""
        entry = service_type_map[service_type]
        record = BillingRecord(
            billing_id=f"golden-{service_type}",
            user_id="golden-user",
            usage_record_id=f"ur-golden-{service_type}",
            product_id=f"product-{service_type}",
            service_type=ServiceType(service_type),
            usage_amount=Decimal(str(entry["example_usage_amount"])),
            unit_price=Decimal(str(entry["example_unit_price"])),
            total_amount=Decimal(str(entry["example_usage_amount"])) * Decimal(str(entry["example_unit_price"])),
            billing_method=BillingMethod.CREDIT_CONSUMPTION,
        )
        assert record.service_type == ServiceType(service_type)
        assert record.usage_amount == Decimal(str(entry["example_usage_amount"]))
        assert record.total_amount > 0 or service_type == "other"


@pytest.mark.unit
class TestBillingMethodVariants:
    """Validate billing works with every billing method."""

    @pytest.mark.parametrize("method", [bm.value for bm in BillingMethod])
    def test_billing_record_accepts_method(self, method):
        record = BillingRecord(
            billing_id=f"golden-method-{method}",
            user_id="golden-user",
            usage_record_id=f"ur-golden-method-{method}",
            product_id="gpt-4o",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("100"),
            unit_price=Decimal("0.00001"),
            total_amount=Decimal("0.001"),
            billing_method=BillingMethod(method),
        )
        assert record.billing_method == BillingMethod(method)


@pytest.mark.unit
class TestBillingStatusTransitions:
    """Validate billing records can be in every status."""

    @pytest.mark.parametrize("status", [bs.value for bs in BillingStatus])
    def test_billing_record_accepts_status(self, status):
        record = BillingRecord(
            billing_id=f"golden-status-{status}",
            user_id="golden-user",
            usage_record_id=f"ur-golden-status-{status}",
            product_id="gpt-4o",
            service_type=ServiceType.MODEL_INFERENCE,
            usage_amount=Decimal("100"),
            unit_price=Decimal("0.00001"),
            total_amount=Decimal("0.001"),
            billing_method=BillingMethod.CREDIT_CONSUMPTION,
            billing_status=BillingStatus(status),
        )
        assert record.billing_status == BillingStatus(status)


@pytest.mark.unit
class TestUsageAggregationPerServiceType:
    """Validate UsageAggregation works for every service type."""

    @pytest.mark.parametrize("service_type", [st.value for st in ServiceType])
    def test_aggregation_per_service_type(self, service_type, service_type_map):
        entry = service_type_map[service_type]
        agg = UsageAggregation(
            aggregation_id=f"agg-golden-{service_type}",
            period_start=datetime(2026, 4, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 5, 1, tzinfo=timezone.utc),
            period_type="monthly",
            service_type=ServiceType(service_type),
            total_usage_count=10,
            total_usage_amount=Decimal(str(entry["example_usage_amount"] * 10)),
            total_cost=Decimal(str(round(entry["example_usage_amount"] * entry["example_unit_price"] * 10, 6))),
            service_breakdown={
                service_type: {
                    "usage_count": 10,
                    "usage_amount": entry["example_usage_amount"] * 10,
                    "total_cost": round(entry["example_usage_amount"] * entry["example_unit_price"] * 10, 6),
                }
            },
        )
        assert agg.service_type == ServiceType(service_type)
        assert agg.total_usage_count == 10


@pytest.mark.unit
class TestBillingStatusUnifiedView:
    """Validate get_user_billing_status aggregates across service types."""

    @pytest.mark.asyncio
    async def test_status_includes_multi_service_usage(self):
        """Unified status should sum usage from multiple service types."""
        repo = _make_mock_repository()
        repo.get_usage_aggregations = AsyncMock(return_value=[
            UsageAggregation(
                aggregation_id="agg-1",
                period_start=datetime(2026, 4, 1, tzinfo=timezone.utc),
                period_end=datetime(2026, 5, 1, tzinfo=timezone.utc),
                period_type="monthly",
                total_usage_count=25,
                total_usage_amount=Decimal("10000"),
                total_cost=Decimal("1.50"),
                service_breakdown={},
            )
        ])

        svc = _make_service(repository=repo)
        # Clear cache from prior tests
        BillingService._billing_status_cache.clear()

        result = await svc.get_user_billing_status("golden-user")
        assert result["current_period_usage"]["requests"] == 25
        assert result["current_period_usage"]["tokens"] == 10000
        assert result["current_period_usage"]["cost"] == 1.50


@pytest.mark.unit
class TestServiceTypeMeterMapping:
    """Validate fixture meter_type choices make semantic sense."""

    EXPECTED_METERS = {
        "model_inference": "tokens",
        "agent_execution": "tokens",
        "gpu_training": "gpu_seconds",
        "storage_minio": "storage_gb_month",
        "mcp_service": "tool_calls",
        "agent_runtime": "runtime_minutes",
    }

    @pytest.mark.parametrize("service_type,expected_meter", list(EXPECTED_METERS.items()))
    def test_known_service_meter_mapping(self, service_type, expected_meter, service_type_map):
        entry = service_type_map[service_type]
        assert entry["meter_type"] == expected_meter, (
            f"{service_type} should use meter '{expected_meter}', got '{entry['meter_type']}'"
        )
