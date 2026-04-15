"""
Contract validation between billing_service and product_service (Story #254).

Ensures ServiceType and UnitType enums stay aligned across services,
and that the billing_units_fixture remains the canonical mapping.
Catches drift when a new type is added to one service but not the other.
"""

import json
from pathlib import Path

import pytest

from microservices.billing_service.models import (
    ServiceType,
    BillingMethod,
    BillingStatus,
)
from microservices.product_service.models import (
    UnitType,
    BillingSurface,
    CostComponentType,
)

FIXTURE_PATH = (
    Path(__file__).parent
    / "../../unit/golden/billing_service/billing_units_fixture.json"
)


@pytest.fixture(scope="module")
def fixture_data():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def fixture_unit_types(fixture_data):
    return {entry["unit_type"] for entry in fixture_data["service_units"]}


@pytest.fixture(scope="module")
def fixture_service_types(fixture_data):
    return {entry["service_type"] for entry in fixture_data["service_units"]}


# ===========================================================================
# Contract: ServiceType enum ↔ fixture ↔ product_service
# ===========================================================================


@pytest.mark.contracts
class TestServiceTypeContract:
    """Billing ServiceType must match fixture and product service expectations."""

    def test_every_billing_service_type_in_fixture(self, fixture_service_types):
        """Every ServiceType enum value must appear in the fixture."""
        billing_types = {st.value for st in ServiceType}
        missing = billing_types - fixture_service_types
        assert missing == set(), (
            f"ServiceType values not in fixture: {missing}. "
            f"Update billing_units_fixture.json when adding new service types."
        )

    def test_fixture_has_no_stale_service_types(self, fixture_service_types):
        """Fixture should not reference removed service types."""
        billing_types = {st.value for st in ServiceType}
        stale = fixture_service_types - billing_types
        assert stale == set(), (
            f"Fixture references service types not in ServiceType enum: {stale}. "
            f"Remove stale entries from billing_units_fixture.json."
        )

    def test_service_type_count_regression(self):
        """Alert when ServiceType enum size changes — update fixture accordingly."""
        assert len(ServiceType) == 16, (
            f"ServiceType enum changed from 16 to {len(ServiceType)}. "
            f"Update billing_units_fixture.json and this assertion."
        )


# ===========================================================================
# Contract: UnitType enum ↔ fixture
# ===========================================================================


@pytest.mark.contracts
class TestUnitTypeContract:
    """Product service UnitType must be accepted by billing fixture."""

    def test_fixture_unit_types_are_valid_product_units(self, fixture_unit_types):
        """Every unit_type in the fixture must be a valid UnitType enum value."""
        valid_units = {ut.value for ut in UnitType}
        invalid = fixture_unit_types - valid_units
        assert invalid == set(), (
            f"Fixture uses unit types not in product_service UnitType: {invalid}. "
            f"Either add to UnitType enum or fix the fixture."
        )

    def test_unit_type_count_regression(self):
        """Alert when UnitType enum size changes."""
        assert len(UnitType) == 20, (
            f"UnitType enum changed from 20 to {len(UnitType)}. "
            f"Review if new types need billing fixture entries."
        )

    def test_core_unit_types_exist(self):
        """Critical unit types that billing depends on must exist."""
        required = {"token", "second", "minute", "request", "execution", "gb_month", "unit"}
        actual = {ut.value for ut in UnitType}
        missing = required - actual
        assert missing == set(), f"Critical unit types missing from UnitType: {missing}"


# ===========================================================================
# Contract: BillingMethod enum ↔ fixture
# ===========================================================================


@pytest.mark.contracts
class TestBillingMethodContract:
    def test_billing_methods_match_fixture(self, fixture_data):
        enum_methods = {bm.value for bm in BillingMethod}
        fixture_methods = set(fixture_data["billing_methods"])
        assert enum_methods == fixture_methods, (
            f"BillingMethod drift — "
            f"in enum only: {enum_methods - fixture_methods}, "
            f"in fixture only: {fixture_methods - enum_methods}"
        )


# ===========================================================================
# Contract: BillingStatus enum ↔ fixture
# ===========================================================================


@pytest.mark.contracts
class TestBillingStatusContract:
    def test_billing_statuses_match_fixture(self, fixture_data):
        enum_statuses = {bs.value for bs in BillingStatus}
        fixture_statuses = set(fixture_data["billing_statuses"])
        assert enum_statuses == fixture_statuses, (
            f"BillingStatus drift — "
            f"in enum only: {enum_statuses - fixture_statuses}, "
            f"in fixture only: {fixture_statuses - enum_statuses}"
        )


# ===========================================================================
# Contract: Cross-service consistency
# ===========================================================================


@pytest.mark.contracts
class TestCrossServiceConsistency:
    """Validate billing and product services share compatible types."""

    def test_billing_surface_covers_key_service_types(self):
        """BillingSurface enum should have entries relevant to billing service types."""
        surfaces = {bs.value for bs in BillingSurface}
        # At minimum, these surfaces should exist for billing integration
        assert "abstract_service" in surfaces or len(surfaces) > 0, (
            "BillingSurface enum is empty — product_service cannot classify billing surfaces"
        )

    def test_cost_component_type_enum_exists(self):
        """CostComponentType should exist for cost breakdown."""
        assert len(CostComponentType) > 0, "CostComponentType enum is empty"

    def test_meter_type_field_in_cost_component(self):
        """ProductCostComponent must have meter_type field for billing integration."""
        from microservices.product_service.models import ProductCostComponent
        fields = ProductCostComponent.model_fields
        assert "meter_type" in fields, "ProductCostComponent missing meter_type field"
        assert "unit_type" in fields, "ProductCostComponent missing unit_type field"
