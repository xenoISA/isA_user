"""Create memory.memory_associations table

Revision ID: mem_008
Revises: mem_007
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 008_create_memory_associations_table.sql

Source ↔ target relationship mapping between memories of any type.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_008"
down_revision: Union[str, None] = "mem_007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory.memory_associations (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            source_memory_type VARCHAR(20) NOT NULL
                CHECK (source_memory_type IN ('factual', 'procedural', 'episodic', 'semantic', 'working')),
            source_memory_id VARCHAR(255) NOT NULL,
            target_memory_type VARCHAR(20) NOT NULL
                CHECK (target_memory_type IN ('factual', 'procedural', 'episodic', 'semantic', 'working')),
            target_memory_id VARCHAR(255) NOT NULL,
            association_type VARCHAR(50) NOT NULL,
            strength FLOAT DEFAULT 0.5 CHECK (strength >= 0 AND strength <= 1),
            context TEXT,
            auto_discovered BOOLEAN DEFAULT false,
            confirmation_count INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, source_memory_type, source_memory_id,
                   target_memory_type, target_memory_id, association_type)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_associations_user ON memory.memory_associations(user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_associations_source "
        "ON memory.memory_associations(source_memory_type, source_memory_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_associations_target "
        "ON memory.memory_associations(target_memory_type, target_memory_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_associations_strength ON memory.memory_associations(strength DESC)")

    op.execute(
        "COMMENT ON TABLE memory.memory_associations IS 'Associations between memories for relationship mapping'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.memory_associations.association_type IS "
        "'Type of association: related, caused_by, prerequisite_for, etc.'"
    )
    op.execute("COMMENT ON COLUMN memory.memory_associations.strength IS 'Association strength (0-1)'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory.memory_associations CASCADE")
