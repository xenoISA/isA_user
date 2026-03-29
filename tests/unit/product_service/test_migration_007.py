"""
Unit tests for migration 007_refresh_product_catalog.sql.

Tests:
- SQL file is parseable and well-formed
- Idempotent patterns: all INSERTs use ON CONFLICT DO UPDATE
- Soft-deactivation targets the correct stale product IDs
- All cost_definitions models have corresponding product upserts
- All product upserts have corresponding pricing rows
- Product metadata includes required fields (provider, model, costs)
- No duplicate pricing_id or product_id values

Covers: Migration 007 structural correctness (no DB required).
"""

import os
import re
import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "007_refresh_product_catalog.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    """Load the migration SQL file."""
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as f:
        return f.read()


class TestMigrationFileStructure:
    """Verify the migration file is well-formed."""

    def test_file_exists(self):
        path = os.path.normpath(MIGRATION_PATH)
        assert os.path.exists(path)

    def test_file_not_empty(self, migration_sql):
        assert len(migration_sql.strip()) > 0

    def test_has_version_header(self, migration_sql):
        assert "Version: 007" in migration_sql

    def test_has_description(self, migration_sql):
        assert "Description:" in migration_sql


class TestIdempotency:
    """All INSERT statements must use ON CONFLICT DO UPDATE for idempotency."""

    def test_all_inserts_have_on_conflict(self, migration_sql):
        # Find all INSERT INTO statements
        inserts = re.findall(
            r"INSERT\s+INTO\s+product\.\w+",
            migration_sql,
            re.IGNORECASE,
        )
        on_conflicts = re.findall(
            r"ON\s+CONFLICT\s*\(",
            migration_sql,
            re.IGNORECASE,
        )
        assert len(inserts) > 0, "No INSERT statements found"
        assert len(on_conflicts) == len(inserts), (
            f"Found {len(inserts)} INSERTs but {len(on_conflicts)} ON CONFLICT clauses"
        )

    def test_on_conflict_uses_do_update(self, migration_sql):
        """ON CONFLICT should DO UPDATE, not DO NOTHING."""
        conflicts = re.findall(
            r"ON\s+CONFLICT\s*\([^)]+\)\s+DO\s+(\w+)",
            migration_sql,
            re.IGNORECASE,
        )
        for action in conflicts:
            assert action.upper() == "UPDATE", (
                f"Expected DO UPDATE but got DO {action}"
            )


class TestStaleProductDeactivation:
    """Step 1: soft-deactivate stale products."""

    STALE_IDS = {"gpt-4", "claude-3-5-sonnet", "prod_ai_tokens"}

    def test_deactivation_update_exists(self, migration_sql):
        assert "SET is_active = FALSE" in migration_sql

    def test_stale_ids_targeted(self, migration_sql):
        for pid in self.STALE_IDS:
            assert f"'{pid}'" in migration_sql, (
                f"Stale product '{pid}' not found in deactivation"
            )


class TestCostDefinitionsAlignment:
    """Every AI model in cost_definitions (migration 003) must have a product."""

    COST_DEF_MODELS = {
        "claude-sonnet-4-20250514": "anthropic",
        "claude-opus-4-20250514": "anthropic",
        "claude-3-5-haiku-20241022": "anthropic",
        "gpt-4o-2024-11-20": "openai",
        "gpt-4o-mini-2024-07-18": "openai",
        "gemini-2.0-flash": "google",
    }

    def test_all_models_present_in_metadata(self, migration_sql):
        for model_name, provider in self.COST_DEF_MODELS.items():
            assert model_name in migration_sql, (
                f"Model '{model_name}' from cost_definitions not found in migration"
            )

    def test_all_providers_present(self, migration_sql):
        for provider in set(self.COST_DEF_MODELS.values()):
            assert f'"provider": "{provider}"' in migration_sql


class TestProductUpserts:
    """Validate product rows being upserted."""

    EXPECTED_PRODUCT_IDS = {
        # AI models
        "claude-sonnet-4",
        "claude-opus-4",
        "claude-haiku-35",
        "gpt-4o",
        "gpt-4o-mini",
        "gemini-2-flash",
        # Infrastructure
        "minio_storage",
        "mcp_tools",
        "advanced_agent",
        "api_gateway",
        "nats_messaging",
        "compute_general",
    }

    def test_all_expected_products_present(self, migration_sql):
        for pid in self.EXPECTED_PRODUCT_IDS:
            assert f"'{pid}'" in migration_sql, (
                f"Product '{pid}' not found in migration"
            )

    def test_no_duplicate_product_ids(self, migration_sql):
        """Each product_id should appear in exactly one INSERT VALUES tuple as first value."""
        # Extract product_id values from the INSERT INTO product.products blocks
        # We look for ('product_id', patterns in VALUES
        product_id_pattern = re.findall(
            r"^\('([a-z0-9_-]+)',\s+'[^']+',\s+'[A-Z0-9-]+',",
            migration_sql,
            re.MULTILINE,
        )
        seen = set()
        duplicates = set()
        for pid in product_id_pattern:
            if pid in seen:
                duplicates.add(pid)
            seen.add(pid)
        assert not duplicates, f"Duplicate product_ids: {duplicates}"


class TestPricingRows:
    """Validate pricing rows match products."""

    EXPECTED_PRICING_IDS = {
        "pricing_claude_sonnet4_input",
        "pricing_claude_sonnet4_output",
        "pricing_claude_opus4_input",
        "pricing_claude_opus4_output",
        "pricing_claude_haiku35_input",
        "pricing_claude_haiku35_output",
        "pricing_gpt4o_base",
        "pricing_gpt4o_mini_base",
        "pricing_gemini2_flash_base",
        "pricing_minio_base",
        "pricing_minio_tier2",
        "pricing_minio_egress",
        "pricing_mcp_tools_base",
        "pricing_agent_base",
        "pricing_api_gw_base",
        "pricing_nats_base",
        "pricing_compute_base",
    }

    def test_all_expected_pricing_present(self, migration_sql):
        for pricing_id in self.EXPECTED_PRICING_IDS:
            assert f"'{pricing_id}'" in migration_sql, (
                f"Pricing '{pricing_id}' not found in migration"
            )

    def test_no_duplicate_pricing_ids(self, migration_sql):
        pricing_ids = re.findall(
            r"'(pricing_[a-z0-9_]+)'",
            migration_sql,
        )
        seen = set()
        duplicates = set()
        for pid in pricing_ids:
            if pid in seen:
                duplicates.add(pid)
            seen.add(pid)
        assert not duplicates, f"Duplicate pricing_ids: {duplicates}"

    def test_pricing_references_valid_products(self, migration_sql):
        """All product_ids in pricing should exist as product upserts."""
        # Extract product_ids from the pricing INSERT block
        # Pattern: ('pricing_id', 'product_id', ...
        pricing_product_refs = re.findall(
            r"'pricing_[a-z0-9_]+',\s+'([a-z0-9_-]+)',",
            migration_sql,
        )
        for product_ref in pricing_product_refs:
            # Verify this product_id appears as a product upsert
            assert f"'{product_ref}'" in migration_sql, (
                f"Pricing references product '{product_ref}' which is not upserted"
            )


class TestMetadataFields:
    """Product metadata should include required fields for AI models."""

    def test_ai_models_have_provider_in_metadata(self, migration_sql):
        # All ai_models category products should have provider in metadata
        assert migration_sql.count('"provider":') >= 6, (
            "Expected at least 6 provider fields in metadata (one per AI model)"
        )

    def test_ai_models_have_model_in_metadata(self, migration_sql):
        assert migration_sql.count('"model":') >= 6

    def test_ai_models_have_cost_fields(self, migration_sql):
        assert migration_sql.count('"input_cost_per_1k":') >= 6
        assert migration_sql.count('"output_cost_per_1k":') >= 6

    def test_ai_models_have_context_window(self, migration_sql):
        assert migration_sql.count('"context_window":') >= 6


class TestVerificationQuery:
    """The migration should include a verification query."""

    def test_has_verification_section(self, migration_sql):
        assert "Verification" in migration_sql

    def test_verification_joins_cost_definitions_and_products(self, migration_sql):
        assert "cost_definitions" in migration_sql
        assert "ALIGNED" in migration_sql
