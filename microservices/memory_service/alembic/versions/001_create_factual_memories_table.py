"""Create memory.factual_memories table

Revision ID: mem_001
Revises: mem_000
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 001_create_factual_memories_table.sql

Factual memories — subject/predicate/object facts. No embedding column;
vectors live in Qdrant, keyed by `id`.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_001"
down_revision: Union[str, None] = "mem_000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory.factual_memories (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            memory_type VARCHAR(50) DEFAULT 'factual',
            content TEXT NOT NULL,
            fact_type VARCHAR(100) NOT NULL,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object_value TEXT NOT NULL,
            fact_context TEXT,
            source VARCHAR(255),
            verification_status VARCHAR(50) DEFAULT 'unverified',
            related_facts JSONB DEFAULT '[]'::jsonb,
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

    op.execute("CREATE INDEX IF NOT EXISTS idx_factual_memories_user_id ON memory.factual_memories(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_factual_memories_fact_type ON memory.factual_memories(fact_type)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_factual_memories_subject "
        "ON memory.factual_memories USING gin(to_tsvector('english', subject))"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_factual_memories_predicate ON memory.factual_memories(predicate)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_factual_memories_confidence ON memory.factual_memories(confidence)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_factual_memories_verification ON memory.factual_memories(verification_status)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_factual_memories_created_at ON memory.factual_memories(created_at DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_factual_memories_importance ON memory.factual_memories(importance_score DESC)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_factual_memories_unique_fact "
        "ON memory.factual_memories(user_id, subject, predicate)"
    )

    # Trigger — guard with DO block since CREATE TRIGGER has no IF NOT EXISTS.
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                 WHERE tgname = 'trigger_update_factual_memories_updated_at'
            ) THEN
                CREATE TRIGGER trigger_update_factual_memories_updated_at
                    BEFORE UPDATE ON memory.factual_memories
                    FOR EACH ROW
                    EXECUTE FUNCTION memory.update_updated_at();
            END IF;
        END$$;
    """)

    op.execute(
        "COMMENT ON TABLE memory.factual_memories IS "
        "'Factual memories - facts and declarative knowledge in subject-predicate-object format'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.factual_memories.id IS 'Memory ID - also used as Qdrant point ID for vector storage'"
    )
    op.execute(
        "COMMENT ON COLUMN memory.factual_memories.fact_type IS "
        "'Type of fact: person, place, event, preference, skill, etc.'"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_update_factual_memories_updated_at ON memory.factual_memories")
    op.execute("DROP TABLE IF EXISTS memory.factual_memories CASCADE")
