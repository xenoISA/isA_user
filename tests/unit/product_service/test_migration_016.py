"""Unit tests for migration 016_add_media_model_products.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "016_add_media_model_products.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_media_and_embedding_products_are_seeded(migration_sql):
    for product_id in [
        "text-embedding-3-small",
        "text-embedding-3-large",
        "whisper-1",
        "gpt-4o-mini-transcribe",
        "gpt-4o-transcribe",
        "gpt-4o-transcribe-diarize",
        "tts-1",
        "gpt-4o-realtime-preview-2024-10-01",
        "dall-e-2",
        "dall-e-3",
        "sora-2",
        "sora-2-pro",
    ]:
        assert f"'{product_id}'" in migration_sql


def test_media_pricing_rows_cover_native_units(migration_sql):
    assert '"unit": "minute"' in migration_sql
    assert '"unit": "character"' in migration_sql
    assert '"unit": "image"' in migration_sql
    assert '"unit": "second"' in migration_sql


def test_media_cost_definitions_cover_lookup_contract(migration_sql):
    assert "'cost_gpt4o_realtime_preview_input'" in migration_sql
    assert "'cost_tts_1_input'" in migration_sql
    assert "'cost_dalle_3_input'" in migration_sql
    assert "'cost_sora_2_input'" in migration_sql
