"""Unit tests for migration 024_add_dedicated_local_gpu_endpoint_products.sql."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "microservices"
    / "product_service"
    / "migrations"
    / "024_add_dedicated_local_gpu_endpoint_products.sql"
)


@pytest.fixture(scope="module")
def migration_sql():
    assert MIGRATION_PATH.exists(), f"Migration file not found: {MIGRATION_PATH}"
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_dedicated_endpoint_product_is_seeded(migration_sql):
    assert "'local-gpu-dedicated-endpoint'" in migration_sql
    assert '"tenancy_mode": "dedicated"' in migration_sql
    assert '"primary_meter": "provisioned_gpu_seconds"' in migration_sql
    assert (
        '"attribution_keys": ["endpoint_id", "deployment_id", "model", "gpu_type", "gpu_count"]'
        in migration_sql
    )


def test_dedicated_endpoint_reservation_meters_are_seeded(migration_sql):
    assert "'cost_local_gpu_dedicated_provisioned_gpu_seconds'" in migration_sql
    assert "'provisioned_gpu_seconds'" in migration_sql
    assert "'cost_local_gpu_dedicated_warm_idle_seconds'" in migration_sql
    assert "'warm_idle_seconds'" in migration_sql
    assert '"requires_attribution":["endpoint_id","deployment_id"]' in migration_sql


def test_dedicated_endpoint_pricing_is_product_backed(migration_sql):
    assert "INSERT INTO product.product_pricing" in migration_sql
    assert "'pricing_local_gpu_dedicated_endpoint_default'" in migration_sql
    assert '"billing_type":"usage_based"' in migration_sql
