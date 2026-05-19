"""Create memory.session_memories + memory.session_summaries tables

Revision ID: mem_006
Revises: mem_005
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 006_create_session_memories_table.sql

Conversation context and interaction history, plus condensed session
summaries written by the summary service.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_006"
down_revision: Union[str, None] = "mem_005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory.session_memories (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            memory_type VARCHAR(50) DEFAULT 'session',
            content TEXT NOT NULL,
            session_id VARCHAR(255) NOT NULL,
            interaction_sequence INTEGER NOT NULL,
            conversation_state JSONB DEFAULT '{}'::jsonb,
            session_type VARCHAR(50) DEFAULT 'chat',
            active BOOLEAN DEFAULT true,
            importance_score FLOAT DEFAULT 0.5 CHECK (importance_score >= 0 AND importance_score <= 1),
            confidence FLOAT DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
            access_count INTEGER DEFAULT 0,
            tags JSONB DEFAULT '[]'::jsonb,
            context JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            last_accessed_at TIMESTAMPTZ
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_session_memories_user_id ON memory.session_memories(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_session_memories_session_id ON memory.session_memories(session_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_memories_user_session "
        "ON memory.session_memories(user_id, session_id, interaction_sequence)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_memories_active "
        "ON memory.session_memories(user_id, active) WHERE active = true"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_session_memories_session_type ON memory.session_memories(session_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_session_memories_created_at ON memory.session_memories(created_at DESC)")

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                 WHERE tgname = 'trigger_update_session_memories_updated_at'
            ) THEN
                CREATE TRIGGER trigger_update_session_memories_updated_at
                    BEFORE UPDATE ON memory.session_memories
                    FOR EACH ROW
                    EXECUTE FUNCTION memory.update_updated_at();
            END IF;
        END$$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS memory.session_summaries (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            session_id VARCHAR(255) NOT NULL,
            summary TEXT NOT NULL,
            key_points TEXT[] DEFAULT '{}',
            message_count INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_session_summaries_user_id ON memory.session_summaries(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_session_summaries_session_id ON memory.session_summaries(session_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_summaries_user_session ON memory.session_summaries(user_id, session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_summaries_created_at ON memory.session_summaries(created_at DESC)"
    )

    op.execute(
        "COMMENT ON TABLE memory.session_memories IS 'Session memories - conversation context and interaction history'"
    )
    op.execute("COMMENT ON TABLE memory.session_summaries IS 'Session summaries - condensed conversation summaries'")
    op.execute("COMMENT ON COLUMN memory.session_memories.id IS 'Memory ID - also used as Qdrant point ID'")
    op.execute(
        "COMMENT ON COLUMN memory.session_memories.interaction_sequence IS "
        "'Sequence number in the session for ordering'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory.session_summaries CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_session_memories_updated_at ON memory.session_memories")
    op.execute("DROP TABLE IF EXISTS memory.session_memories CASCADE")
