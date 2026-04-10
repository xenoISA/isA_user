"""Unit tests for migration 010_add_agent_runtime_products.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "010_add_agent_runtime_products.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_runtime_products_present(migration_sql):
    assert "'agent_runtime_dedicated'" in migration_sql
    assert "'agent_runtime_shared'" in migration_sql


def test_runtime_pricing_rows_present(migration_sql):
    assert "'pricing_agent_runtime_dedicated_default'" in migration_sql
    assert "'pricing_agent_runtime_shared_default'" in migration_sql


def test_runtime_metadata_is_canonical(migration_sql):
    assert '"service_type": "agent_runtime"' in migration_sql
    assert '"operation_type": "vm_occupancy"' in migration_sql
    assert '"runtime_class": "dedicated"' in migration_sql
    assert '"runtime_class": "shared"' in migration_sql
