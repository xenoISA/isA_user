"""Unit tests for migration 013_add_pipeline_and_user_profile_products.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "013_add_pipeline_and_user_profile_products.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_pipeline_and_user_profile_products_present(migration_sql):
    assert "'data_pipeline_run'" in migration_sql
    assert "'data_etl_job'" in migration_sql
    assert "'data_query_execution'" in migration_sql
    assert "'data_export'" in migration_sql
    assert "'curated.account.user_profiles'" in migration_sql


def test_pipeline_metadata_uses_canonical_service_types(migration_sql):
    assert '"service_type": "data_pipeline"' in migration_sql
    assert '"operation_type": "pipeline_run"' in migration_sql
    assert '"operation_type": "etl_job"' in migration_sql
    assert '"operation_type": "query_execution"' in migration_sql
    assert '"operation_type": "data_export"' in migration_sql


def test_pipeline_and_user_profile_billing_profiles_are_abstract_services(migration_sql):
    assert '"billing_surface": "abstract_service"' in migration_sql
    assert '"component_type": "runtime"' in migration_sql
    assert '"component_type": "storage"' in migration_sql
    assert '"component_type": "network"' in migration_sql
    assert '"component_type": "external_api"' in migration_sql
