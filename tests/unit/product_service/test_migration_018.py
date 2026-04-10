"""Unit tests for migration 018_add_remaining_llm_omni_skus.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "018_add_remaining_llm_omni_skus.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_remaining_llm_omni_skus_are_seeded(migration_sql):
    for product_id in [
        "gpt-oss-120b",
        "llama-3.3-70b",
        "llama-4-scout-17b-16e-instruct",
        "llama3.1-8b",
        "qwen-3-32b",
        "o4-mini",
        "o4-mini-deep-search",
        "claude-3.5-sonnet",
        "claude-3-opus",
        "deepseek-r1",
        "qwen3.5-397b-a17b",
        "glm-5.1",
        "mixtral-8x22b-instruct",
    ]:
        assert f"'{product_id}'" in migration_sql


def test_config_backed_pricing_is_marked_in_metadata(migration_sql):
    assert "isa_model_provider_config_2026_04_09" in migration_sql
    assert "'primary_meter'," in migration_sql
    assert "'tokens'" in migration_sql


def test_pricing_and_cost_ids_are_generated_from_product_ids(migration_sql):
    assert "pricing_%s_%s" in migration_sql
    assert "cost_%s_%s" in migration_sql
    assert "regexp_replace(lower(sm.product_id)" in migration_sql
