"""Create memory tracking + metadata trigger functions

Revision ID: mem_009
Revises: mem_008
Create Date: 2026-05-19

Wraps existing SQL migration:
  - 009_create_memory_functions.sql

Adds:
  - memory.track_memory_access(...) — explicit access counter (called
    from repositories on read paths).
  - memory.update_memory_metadata() — AFTER-INSERT/UPDATE trigger
    function that maintains memory.memory_metadata row counts and
    version stamps automatically for the six memory type tables.

Both are CREATE OR REPLACE so re-application is a no-op.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "mem_009"
down_revision: Union[str, None] = "mem_008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_MEMORY_TABLES = (
    "factual_memories",
    "episodic_memories",
    "procedural_memories",
    "semantic_memories",
    "working_memories",
    "session_memories",
)


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION memory.track_memory_access(
            p_user_id VARCHAR(255),
            p_memory_type VARCHAR(20),
            p_memory_id VARCHAR(255)
        )
        RETURNS VOID AS $$
        BEGIN
            INSERT INTO memory.memory_metadata (
                id, user_id, memory_type, memory_id,
                access_count, last_accessed_at, first_accessed_at
            )
            VALUES (
                gen_random_uuid()::text, p_user_id, p_memory_type, p_memory_id,
                1, NOW(), NOW()
            )
            ON CONFLICT (user_id, memory_type, memory_id)
            DO UPDATE SET
                access_count = memory.memory_metadata.access_count + 1,
                last_accessed_at = NOW(),
                updated_at = NOW();
        END;
        $$ LANGUAGE plpgsql
    """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION memory.update_memory_metadata()
        RETURNS TRIGGER AS $$
        DECLARE
            memory_type_value VARCHAR(20);
        BEGIN
            CASE TG_TABLE_NAME
                WHEN 'factual_memories' THEN memory_type_value := 'factual';
                WHEN 'procedural_memories' THEN memory_type_value := 'procedural';
                WHEN 'episodic_memories' THEN memory_type_value := 'episodic';
                WHEN 'semantic_memories' THEN memory_type_value := 'semantic';
                WHEN 'working_memories' THEN memory_type_value := 'working';
                WHEN 'session_memories' THEN memory_type_value := 'session';
                ELSE memory_type_value := 'unknown';
            END CASE;

            INSERT INTO memory.memory_metadata (
                id, user_id, memory_type, memory_id,
                modification_count, last_modified_at, version
            )
            VALUES (
                gen_random_uuid()::text, NEW.user_id, memory_type_value, NEW.id,
                1, NOW(), 1
            )
            ON CONFLICT (user_id, memory_type, memory_id)
            DO UPDATE SET
                modification_count = memory.memory_metadata.modification_count + 1,
                last_modified_at = NOW(),
                version = memory.memory_metadata.version + 1,
                updated_at = NOW();

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """
    )

    # Attach the metadata trigger to every memory table. Guard each one
    # because CREATE TRIGGER has no IF NOT EXISTS.
    for table in _MEMORY_TABLES:
        prefix = table.replace("_memories", "")
        trigger_name = f"{prefix}_metadata_trigger"
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger
                     WHERE tgname = '{trigger_name}'
                ) THEN
                    CREATE TRIGGER {trigger_name}
                        AFTER INSERT OR UPDATE ON memory.{table}
                        FOR EACH ROW
                        EXECUTE FUNCTION memory.update_memory_metadata();
                END IF;
            END$$;
        """
        )

    op.execute(
        "COMMENT ON FUNCTION memory.track_memory_access IS 'Track memory access for analytics and recommendations'"
    )
    op.execute(
        "COMMENT ON FUNCTION memory.update_memory_metadata IS "
        "'Automatically update metadata when memories are created or modified'"
    )


def downgrade() -> None:
    for table in _MEMORY_TABLES:
        prefix = table.replace("_memories", "")
        op.execute(
            f"DROP TRIGGER IF EXISTS {prefix}_metadata_trigger ON memory.{table}"
        )
    op.execute("DROP FUNCTION IF EXISTS memory.update_memory_metadata()")
    op.execute(
        "DROP FUNCTION IF EXISTS memory.track_memory_access(VARCHAR, VARCHAR, VARCHAR)"
    )
