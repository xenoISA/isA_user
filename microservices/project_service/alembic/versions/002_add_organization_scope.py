"""Add organization scope to project.projects

Revision ID: proj_002
Revises: proj_001
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 002_add_organization_scope.sql

Adds the org_id column (nullable) and a supporting index so projects
can be scoped to an organization. Safe to apply on environments where
this column already exists.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "proj_002"
down_revision: Union[str, None] = "proj_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE project.projects ADD COLUMN IF NOT EXISTS org_id VARCHAR(255)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_projects_org_id ON project.projects(org_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS project.idx_project_projects_org_id")
    op.execute("ALTER TABLE project.projects DROP COLUMN IF EXISTS org_id")
