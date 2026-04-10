"""Unit tests for migration 012_backfill_billing_profiles.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "012_backfill_billing_profiles.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_billing_profile_backfill_targets_core_products(migration_sql):
    assert "'gpt-4o'" in migration_sql
    assert "'agent_runtime_dedicated'" in migration_sql
    assert "'web_automation'" in migration_sql
    assert "'python_repl_execution'" in migration_sql
    assert "'digital_rag_response'" in migration_sql
    assert "'minio_storage'" in migration_sql


def test_billing_profile_metadata_includes_component_types(migration_sql):
    assert '"billing_surface": "abstract_service"' in migration_sql
    assert '"component_type": "token_compute"' in migration_sql
    assert '"component_type": "runtime"' in migration_sql
    assert '"component_type": "storage"' in migration_sql
    assert '"component_type": "network"' in migration_sql
    assert '"component_type": "external_api"' in migration_sql


def test_external_api_components_are_treated_as_bundled_costs(migration_sql):
    assert '"component_id": "web_access_stack"' in migration_sql
    assert '"customer_visible": false' in migration_sql
    assert "browser, proxy, phone, captcha, or search providers" in migration_sql
