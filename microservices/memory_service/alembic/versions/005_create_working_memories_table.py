"""Create memory.working_memories table

Revision ID: mem_005
Revises: mem_004
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 005_create_working_memories_table.sql

Working memories — task-scoped scratchpad with TTL.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_005"
down_revision: Union[str, None] = "mem_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memory.working_memories (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            memory_type VARCHAR(50) DEFAULT 'working',
            content TEXT NOT NULL,
            task_id VARCHAR(255) NOT NULL,
            task_context JSONB NOT NULL,
            ttl_seconds INTEGER DEFAULT 3600 CHECK (ttl_seconds > 0),
            priority INTEGER DEFAULT 1 CHECK (priority >= 1 AND priority <= 10),
            expires_at TIMESTAMPTZ NOT NULL,
            importance_score FLOAT DEFAULT 0.5 CHECK (importance_score >= 0 AND importance_score <= 1),
            confidence FLOAT DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
            access_count INTEGER DEFAULT 0,
            tags JSONB DEFAULT '[]'::jsonb,
            context JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            last_accessed_at TIMESTAMPTZ
        )
    """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_working_memories_user_id ON memory.working_memories(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_working_memories_task_id ON memory.working_memories(task_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_working_memories_priority ON memory.working_memories(priority DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_working_memories_expires_at ON memory.working_memories(expires_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_working_memories_user_expires ON memory.working_memories(user_id, expires_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_working_memories_created_at ON memory.working_memories(created_at DESC)"
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                 WHERE tgname = 'trigger_update_working_memories_updated_at'
            ) THEN
                CREATE TRIGGER trigger_update_working_memories_updated_at
                    BEFORE UPDATE ON memory.working_memories
                    FOR EACH ROW
                    EXECUTE FUNCTION memory.update_updated_at();
            END IF;
        END$$;
    """
    )

    op.execute(
        "COMMENT ON TABLE memory.working_memories IS 'Working memories - temporary task-related information with TTL'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.working_memories.id IS 'Memory ID - also used as Qdrant point ID'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.working_memories.expires_at IS 'Expiration timestamp for automatic cleanup'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.working_memories.priority IS 'Priority level (1-10, higher is more important)'"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trigger_update_working_memories_updated_at ON memory.working_memories"
    )
    op.execute("DROP TABLE IF EXISTS memory.working_memories CASCADE")
