"""Unit tests for migration 009_cleanup_legacy_test_billing_rows.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "billing_service", "migrations",
    "009_cleanup_legacy_test_billing_rows.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_cleanup_targets_only_known_test_products(migration_sql):
    assert "'test-product'" in migration_sql
    assert "'test-product-2'" in migration_sql
    assert "DELETE FROM billing.billing_records" in migration_sql


def test_cleanup_removes_related_events_and_claims(migration_sql):
    assert "DELETE FROM billing.billing_events" in migration_sql
    assert "DELETE FROM billing.event_processing_claims" in migration_sql
    assert "source_event_id" in migration_sql
