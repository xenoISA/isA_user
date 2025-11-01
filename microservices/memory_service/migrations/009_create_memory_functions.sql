-- Memory Service Migration: Create utility functions
-- Version: 009
-- Date: 2025-01-24

-- ====================
-- Function: Track Memory Access
-- ====================
CREATE OR REPLACE FUNCTION memory.track_memory_access(
    p_user_id VARCHAR(255),
    p_memory_type VARCHAR(20),
    p_memory_id VARCHAR(255)
)
RETURNS VOID AS $$
BEGIN
    -- Update or insert metadata for access tracking
    INSERT INTO memory.memory_metadata (
        id,
        user_id,
        memory_type,
        memory_id,
        access_count,
        last_accessed_at,
        first_accessed_at
    )
    VALUES (
        gen_random_uuid()::text,
        p_user_id,
        p_memory_type,
        p_memory_id,
        1,
        NOW(),
        NOW()
    )
    ON CONFLICT (user_id, memory_type, memory_id)
    DO UPDATE SET
        access_count = memory.memory_metadata.access_count + 1,
        last_accessed_at = NOW(),
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ====================
-- Function: Update Memory Metadata (Trigger)
-- ====================
CREATE OR REPLACE FUNCTION memory.update_memory_metadata()
RETURNS TRIGGER AS $$
DECLARE
    memory_type_value VARCHAR(20);
BEGIN
    -- Map table name to memory_type
    CASE TG_TABLE_NAME
        WHEN 'factual_memories' THEN memory_type_value := 'factual';
        WHEN 'procedural_memories' THEN memory_type_value := 'procedural';
        WHEN 'episodic_memories' THEN memory_type_value := 'episodic';
        WHEN 'semantic_memories' THEN memory_type_value := 'semantic';
        WHEN 'working_memories' THEN memory_type_value := 'working';
        WHEN 'session_memories' THEN memory_type_value := 'session';
        ELSE memory_type_value := 'unknown';
    END CASE;

    -- Update or insert metadata
    INSERT INTO memory.memory_metadata (
        id,
        user_id,
        memory_type,
        memory_id,
        modification_count,
        last_modified_at,
        version
    )
    VALUES (
        gen_random_uuid()::text,
        NEW.user_id,
        memory_type_value,
        NEW.id,
        1,
        NOW(),
        1
    )
    ON CONFLICT (user_id, memory_type, memory_id)
    DO UPDATE SET
        modification_count = memory.memory_metadata.modification_count + 1,
        last_modified_at = NOW(),
        version = memory.memory_metadata.version + 1,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ====================
-- Attach Triggers to Memory Tables
-- ====================
CREATE TRIGGER factual_metadata_trigger
    AFTER INSERT OR UPDATE ON memory.factual_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_memory_metadata();

CREATE TRIGGER episodic_metadata_trigger
    AFTER INSERT OR UPDATE ON memory.episodic_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_memory_metadata();

CREATE TRIGGER procedural_metadata_trigger
    AFTER INSERT OR UPDATE ON memory.procedural_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_memory_metadata();

CREATE TRIGGER semantic_metadata_trigger
    AFTER INSERT OR UPDATE ON memory.semantic_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_memory_metadata();

CREATE TRIGGER working_metadata_trigger
    AFTER INSERT OR UPDATE ON memory.working_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_memory_metadata();

CREATE TRIGGER session_metadata_trigger
    AFTER INSERT OR UPDATE ON memory.session_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_memory_metadata();

-- Comments
COMMENT ON FUNCTION memory.track_memory_access IS 'Track memory access for analytics and recommendations';
COMMENT ON FUNCTION memory.update_memory_metadata IS 'Automatically update metadata when memories are created or modified';
