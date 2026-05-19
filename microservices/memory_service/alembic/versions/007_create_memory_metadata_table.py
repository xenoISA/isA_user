"""Create memory.memory_metadata table

Revision ID: mem_007
Revises: mem_006
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 007_create_memory_metadata_table.sql

Per-(user, memory_type, memory_id) sidecar tracking usage / quality /
lifecycle. Updated by the trigger fns added in revision mem_009.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_007"
down_revision: Union[str, None] = "mem_006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory.memory_metadata (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            memory_type VARCHAR(20) NOT NULL
                CHECK (memory_type IN ('factual', 'procedural', 'episodic', 'semantic', 'working', 'session')),
            memory_id VARCHAR(255) NOT NULL,
            access_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMPTZ,
            first_accessed_at TIMESTAMPTZ DEFAULT NOW(),
            modification_count INTEGER DEFAULT 0,
            last_modified_at TIMESTAMPTZ,
            version INTEGER DEFAULT 1,
            accuracy_score FLOAT CHECK (accuracy_score >= 0 AND accuracy_score <= 1),
            relevance_score FLOAT CHECK (relevance_score >= 0 AND relevance_score <= 1),
            completeness_score FLOAT CHECK (completeness_score >= 0 AND completeness_score <= 1),
            user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
            user_feedback TEXT,
            feedback_timestamp TIMESTAMPTZ,
            system_flags JSONB DEFAULT '{}'::jsonb,
            priority_level INTEGER DEFAULT 3 CHECK (priority_level >= 1 AND priority_level <= 5),
            dependency_count INTEGER DEFAULT 0,
            reference_count INTEGER DEFAULT 0,
            lifecycle_stage VARCHAR(20) DEFAULT 'active'
                CHECK (lifecycle_stage IN ('active', 'stale', 'deprecated', 'archived')),
            auto_expire BOOLEAN DEFAULT false,
            expire_after_days INTEGER,
            reinforcement_score FLOAT DEFAULT 0.0,
            learning_curve JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, memory_type, memory_id)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_metadata_user_type ON memory.memory_metadata(user_id, memory_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metadata_memory ON memory.memory_metadata(memory_type, memory_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metadata_access ON memory.memory_metadata(access_count DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_metadata_quality "
        "ON memory.memory_metadata(accuracy_score DESC, relevance_score DESC)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_metadata_priority ON memory.memory_metadata(priority_level DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metadata_lifecycle ON memory.memory_metadata(lifecycle_stage)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_metadata_flags ON memory.memory_metadata USING gin(system_flags)")

    op.execute(
        "COMMENT ON TABLE memory.memory_metadata IS "
        "'Memory metadata for tracking usage, quality, and lifecycle of memories'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.memory_metadata.memory_id IS 'References the ID in the specific memory type table'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory.memory_metadata CASCADE")
