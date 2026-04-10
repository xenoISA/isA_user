"""Unit tests for migration 014_add_mcp_service_alias.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "014_add_mcp_service_alias.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_mcp_service_product_present(migration_sql):
    assert "'mcp_service'" in migration_sql
    assert "'MCP-SERVICE'" in migration_sql


def test_mcp_service_pricing_row_present(migration_sql):
    assert "'pricing_mcp_service_base'" in migration_sql


def test_mcp_service_metadata_is_canonical(migration_sql):
    assert '"service_type": "mcp_service"' in migration_sql
    assert '"alias_of": "mcp_tools"' in migration_sql
    assert '"primary_meter": "tool_calls"' in migration_sql
