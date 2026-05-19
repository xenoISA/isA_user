"""Create memory.semantic_memories table

Revision ID: mem_004
Revises: mem_003
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 004_create_semantic_memories_table.sql

Semantic memories — concepts/definitions and general knowledge.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_004"
down_revision: Union[str, None] = "mem_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory.semantic_memories (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            memory_type VARCHAR(50) DEFAULT 'semantic',
            content TEXT NOT NULL,
            concept_type VARCHAR(100) NOT NULL,
            definition TEXT NOT NULL,
            properties JSONB DEFAULT '{}'::jsonb,
            abstraction_level VARCHAR(50) DEFAULT 'medium' CHECK (abstraction_level IN ('low', 'medium', 'high')),
            related_concepts TEXT[] DEFAULT '{}',
            category VARCHAR(100) NOT NULL,
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

    op.execute("CREATE INDEX IF NOT EXISTS idx_semantic_memories_user_id ON memory.semantic_memories(user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_semantic_memories_concept_type ON memory.semantic_memories(concept_type)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_semantic_memories_category ON memory.semantic_memories(category)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_semantic_memories_abstraction ON memory.semantic_memories(abstraction_level)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_semantic_memories_definition "
        "ON memory.semantic_memories USING gin(to_tsvector('english', definition))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_semantic_memories_created_at ON memory.semantic_memories(created_at DESC)"
    )

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger
                 WHERE tgname = 'trigger_update_semantic_memories_updated_at'
            ) THEN
                CREATE TRIGGER trigger_update_semantic_memories_updated_at
                    BEFORE UPDATE ON memory.semantic_memories
                    FOR EACH ROW
                    EXECUTE FUNCTION memory.update_updated_at();
            END IF;
        END$$;
    """)

    op.execute(
        "COMMENT ON TABLE memory.semantic_memories IS "
        "'Semantic memories - concepts and general knowledge with definitions'"
    )
    op.execute("COMMENT ON COLUMN memory.semantic_memories.id IS 'Memory ID - also used as Qdrant point ID'")
    op.execute("COMMENT ON COLUMN memory.semantic_memories.properties IS 'Concept properties as JSON object'")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_update_semantic_memories_updated_at ON memory.semantic_memories")
    op.execute("DROP TABLE IF EXISTS memory.semantic_memories CASCADE")
