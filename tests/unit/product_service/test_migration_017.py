"""Unit tests for migration 017_add_active_model_catalog_coverage.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "017_add_active_model_catalog_coverage.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_active_model_skus_are_seeded(migration_sql):
    for product_id in [
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-5.4",
        "gpt-5-mini",
        "gpt-5-nano",
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "claude-haiku-4-5",
        "deepseek-reasoner",
        "mistralai/ministral-3b-2512",
        "nvidia/nemotron-3-nano-30b-a3b:free",
    ]:
        assert f"'{product_id}'" in migration_sql


def test_model_billing_profiles_are_backfilled(migration_sql):
    assert "WHERE product_type = 'model_inference'" in migration_sql
    assert "'primary_meter', 'tokens'" in migration_sql
    assert "Provider-backed model inference token cost" in migration_sql


def test_cost_definitions_are_seeded_for_new_models(migration_sql):
    for cost_id in [
        "cost_gpt41_input",
        "cost_gpt5_nano_output",
        "cost_claude_sonnet46_input",
        "cost_deepseek_reasoner_output",
        "cost_ministral_3b_2512_input",
    ]:
        assert f"'{cost_id}'" in migration_sql
