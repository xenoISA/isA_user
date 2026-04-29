"""Unit tests for migration 023_add_inference_service_surface_pricing.sql."""

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
    "023_add_inference_service_surface_pricing.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_inference_service_surfaces_are_seeded(migration_sql):
    for product_id in [
        "api",
        "codex-sub",
        "claude-sub",
        "local-gpu",
        "cloud-gpu",
        "local-ollama",
    ]:
        assert f"'{product_id}'" in migration_sql


def test_local_gpu_rows_are_rebound_to_customer_surface(migration_sql):
    assert "SET product_id = 'local-gpu'" in migration_sql
    assert '{"service_surface":"local-gpu"}' in migration_sql
    assert "COALESCE(metadata->>'backend', '') = 'local_gpu'" in migration_sql


def test_cloud_gpu_and_proxy_surface_cost_rows_exist(migration_sql):
    for cost_id in [
        "cost_codex_sub_input",
        "cost_claude_sub_output",
        "cost_cloud_gpu_modal_input",
        "cost_cloud_gpu_modal_gpu_seconds",
        "cost_local_ollama_output",
    ]:
        assert f"'{cost_id}'" in migration_sql
