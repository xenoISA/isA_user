"""Unit tests for migration 015_backfill_remaining_billing_profiles.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "015_backfill_remaining_billing_profiles.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_internal_components_are_marked_non_invoiceable(migration_sql):
    assert "'api_gateway'" in migration_sql
    assert "'compute_general'" in migration_sql
    assert "'nats_messaging'" in migration_sql
    assert '"billing_surface": "internal_component"' in migration_sql
    assert '"invoiceable": false' in migration_sql


def test_legacy_advanced_agent_is_deactivated(migration_sql):
    assert "'advanced_agent'" in migration_sql
    assert "Replaced by runtime-based agent billing products" in migration_sql


def test_remaining_data_products_get_generic_billing_profiles(migration_sql):
    assert "product_type = 'data_processing'" in migration_sql
    assert '"primary_meter": "data_product_requests"' in migration_sql
    assert '"component_id": "hybrid_data_vector_search"' in migration_sql
