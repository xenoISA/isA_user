"""L3 Integration — Project org-scope migration contract."""

from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.tdd]


def test_project_schema_has_org_scope_column_and_index_migration():
    repo_root = Path(__file__).resolve().parents[3]
    initial_schema = (
        repo_root
        / "microservices"
        / "project_service"
        / "migrations"
        / "001_create_project_schema.sql"
    ).read_text()
    org_scope_migration = (
        repo_root
        / "microservices"
        / "project_service"
        / "migrations"
        / "002_add_organization_scope.sql"
    ).read_text()

    assert "org_id" in initial_schema
    assert "ADD COLUMN IF NOT EXISTS org_id" in org_scope_migration
    assert "idx_project_projects_org_id" in org_scope_migration
