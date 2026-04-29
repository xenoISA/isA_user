"""Unit tests for migration 019_add_local_gpu_inference_skus.sql."""

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
    "019_add_local_gpu_inference_skus.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_local_gpu_skus_target_product_schema(migration_sql):
    assert "INSERT INTO product.cost_definitions" in migration_sql
    assert "'cost_local_gpu_vllm_input'" in migration_sql
    assert "'cost_local_gpu_onnx_output'" in migration_sql
