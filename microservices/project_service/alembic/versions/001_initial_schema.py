"""Initial project service schema

Revision ID: proj_001
Revises: None
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 001_create_project_schema.sql

Creates the `project` schema with the `projects` and `project_files`
tables. Safe to apply on environments that already have these tables —
all DDL uses IF NOT EXISTS.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "proj_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS project")

    op.execute("""
        CREATE TABLE IF NOT EXISTS project.projects (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            org_id VARCHAR(255),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            custom_instructions TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS project.project_files (
            id VARCHAR(255) PRIMARY KEY,
            project_id VARCHAR(255) NOT NULL,
            filename VARCHAR(1024) NOT NULL,
            file_type VARCHAR(255),
            file_size BIGINT,
            storage_path TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_project_projects_user_id ON project.projects(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_projects_updated_at ON project.projects(updated_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_files_project_id ON project.project_files(project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_files_created_at ON project.project_files(created_at DESC)")

    op.execute(
        "COMMENT ON SCHEMA project IS "
        "'Project service schema - projects, instructions, and knowledge file associations'"
    )
    op.execute("COMMENT ON TABLE project.projects IS 'Project workspaces owned by users or organizations'")
    op.execute("COMMENT ON TABLE project.project_files IS 'Storage-backed file associations attached to projects'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project.project_files CASCADE")
    op.execute("DROP TABLE IF EXISTS project.projects CASCADE")
    op.execute("DROP SCHEMA IF EXISTS project CASCADE")
