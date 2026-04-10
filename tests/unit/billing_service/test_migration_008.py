"""Unit tests for migration 008_normalize_legacy_service_types.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "billing_service", "migrations",
    "008_normalize_legacy_service_types.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_legacy_other_service_type_rows_are_targeted(migration_sql):
    assert "WHERE br.service_type = 'other'" in migration_sql
    assert "service_type_normalized_by" in migration_sql


def test_normalization_covers_primary_billing_domains(migration_sql):
    for normalized_service_type in [
        "model_inference",
        "storage_minio",
        "mcp_service",
        "agent_runtime",
        "web_service",
        "data_service",
        "data_pipeline",
        "python_repl",
    ]:
        assert f"THEN '{normalized_service_type}'" in migration_sql
