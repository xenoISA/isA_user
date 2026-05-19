"""Create memory.procedural_memories table

Revision ID: mem_003
Revises: mem_002
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 003_create_procedural_memories_table.sql

Procedural memories — how-to knowledge with stepwise procedures.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_003"
down_revision: Union[str, None] = "mem_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memory.procedural_memories (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            memory_type VARCHAR(50) DEFAULT 'procedural',
            content TEXT NOT NULL,
            skill_type VARCHAR(100) NOT NULL,
            steps JSONB NOT NULL,
            prerequisites TEXT[] DEFAULT '{}',
            difficulty_level VARCHAR(50) DEFAULT 'medium' CHECK (difficulty_level IN ('easy', 'medium', 'hard')),
            success_rate FLOAT DEFAULT 0.0 CHECK (success_rate >= 0 AND success_rate <= 1),
            domain VARCHAR(100) NOT NULL,
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
        "CREATE INDEX IF NOT EXISTS idx_procedural_memories_user_id ON memory.procedural_memories(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_procedural_memories_skill_type ON memory.procedural_memories(skill_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_procedural_memories_domain ON memory.procedural_memories(domain)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_procedural_memories_difficulty ON memory.procedural_memories(difficulty_level)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_procedural_memories_success_rate "
        "ON memory.procedural_memories(success_rate DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_procedural_memories_created_at ON memory.procedural_memories(created_at DESC)"
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                 WHERE tgname = 'trigger_update_procedural_memories_updated_at'
            ) THEN
                CREATE TRIGGER trigger_update_procedural_memories_updated_at
                    BEFORE UPDATE ON memory.procedural_memories
                    FOR EACH ROW
                    EXECUTE FUNCTION memory.update_updated_at();
            END IF;
        END$$;
    """
    )

    op.execute(
        "COMMENT ON TABLE memory.procedural_memories IS "
        "'Procedural memories - how-to knowledge and skills with step-by-step procedures'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.procedural_memories.id IS 'Memory ID - also used as Qdrant point ID'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.procedural_memories.steps IS "
        "'Procedure steps as JSON array with order and description'"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trigger_update_procedural_memories_updated_at ON memory.procedural_memories"
    )
    op.execute("DROP TABLE IF EXISTS memory.procedural_memories CASCADE")
