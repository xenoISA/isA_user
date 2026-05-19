"""Create memory.episodic_memories table

Revision ID: mem_002
Revises: mem_001
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 002_create_episodic_memories_table.sql

Episodic memories — personal events with temporal/spatial context.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_002"
down_revision: Union[str, None] = "mem_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memory.episodic_memories (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            memory_type VARCHAR(50) DEFAULT 'episodic',
            content TEXT NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            location TEXT,
            participants TEXT[] DEFAULT '{}',
            emotional_valence FLOAT DEFAULT 0.0 CHECK (emotional_valence >= -1 AND emotional_valence <= 1),
            vividness FLOAT DEFAULT 0.5 CHECK (vividness >= 0 AND vividness <= 1),
            episode_date TIMESTAMPTZ,
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
        "CREATE INDEX IF NOT EXISTS idx_episodic_memories_user_id ON memory.episodic_memories(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_memories_event_type ON memory.episodic_memories(event_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_memories_location "
        "ON memory.episodic_memories USING gin(to_tsvector('english', location))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_memories_episode_date ON memory.episodic_memories(episode_date DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_memories_emotional_valence "
        "ON memory.episodic_memories(emotional_valence)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_memories_participants "
        "ON memory.episodic_memories USING gin(participants)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_episodic_memories_created_at ON memory.episodic_memories(created_at DESC)"
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                 WHERE tgname = 'trigger_update_episodic_memories_updated_at'
            ) THEN
                CREATE TRIGGER trigger_update_episodic_memories_updated_at
                    BEFORE UPDATE ON memory.episodic_memories
                    FOR EACH ROW
                    EXECUTE FUNCTION memory.update_updated_at();
            END IF;
        END$$;
    """
    )

    op.execute(
        "COMMENT ON TABLE memory.episodic_memories IS "
        "'Episodic memories - personal experiences and events with temporal/spatial context'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.episodic_memories.id IS 'Memory ID - also used as Qdrant point ID'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.episodic_memories.emotional_valence IS "
        "'Emotional tone: -1 (negative) to 1 (positive)'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.episodic_memories.vividness IS 'How vivid/detailed the memory is (0-1)'"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trigger_update_episodic_memories_updated_at ON memory.episodic_memories"
    )
    op.execute("DROP TABLE IF EXISTS memory.episodic_memories CASCADE")
