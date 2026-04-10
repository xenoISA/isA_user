"""Unit tests for migration 011_add_web_crawl_product.sql."""

import os

import pytest

pytestmark = pytest.mark.unit

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "microservices", "product_service", "migrations",
    "011_add_web_crawl_product.sql",
)


@pytest.fixture(scope="module")
def migration_sql():
    path = os.path.normpath(MIGRATION_PATH)
    assert os.path.exists(path), f"Migration file not found: {path}"
    with open(path) as handle:
        return handle.read()


def test_web_crawl_product_present(migration_sql):
    assert "'web_crawl'" in migration_sql
    assert "'WEB-CRAWL'" in migration_sql


def test_web_crawl_pricing_row_present(migration_sql):
    assert "'pricing_web_crawl_default'" in migration_sql


def test_web_crawl_metadata_is_canonical(migration_sql):
    assert '"service_type": "web_service"' in migration_sql
    assert '"operation_type": "crawl"' in migration_sql
    assert '"unit": "url"' in migration_sql
