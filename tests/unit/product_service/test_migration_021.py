"""Unit tests for migration 021_add_local_gpu_shared_runtime_components.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "microservices",
    "product_service",
    "migrations",
    "021_add_local_gpu_shared_runtime_components.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_local_gpu_runtime_components_are_seeded(migration_sql):
    for cost_id in [
        "cost_local_gpu_shared_gpu_seconds",
        "cost_local_gpu_vllm_gpu_seconds",
        "cost_local_gpu_shared_prefill_seconds",
        "cost_local_gpu_shared_queue_seconds",
        "cost_local_gpu_shared_cold_start_seconds",
        "cost_local_gpu_shared_kv_cache_gib_seconds",
    ]:
        assert f"'{cost_id}'" in migration_sql


def test_local_gpu_runtime_components_mark_pricing_dimensions(migration_sql):
    assert '"pricing_dimension":"gpu_seconds"' in migration_sql
    assert '"pricing_dimension":"prefill_seconds"' in migration_sql
    assert '"pricing_dimension":"kv_cache_gib_seconds"' in migration_sql
    assert '"tenancy_mode":"shared"' in migration_sql
