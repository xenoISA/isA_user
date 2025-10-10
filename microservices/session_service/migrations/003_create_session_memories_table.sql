-- Session Service Migration: Create session_memories table
-- Version: 003 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.session_memories (
    id SERIAL PRIMARY KEY,
    memory_id VARCHAR(255) NOT NULL UNIQUE,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES dev.sessions(session_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_session_memories_memory_id ON dev.session_memories(memory_id);
CREATE INDEX idx_session_memories_session_id ON dev.session_memories(session_id);
CREATE INDEX idx_session_memories_user_id ON dev.session_memories(user_id);
CREATE INDEX idx_session_memories_memory_type ON dev.session_memories(memory_type);
CREATE INDEX idx_session_memories_created_at ON dev.session_memories(created_at);
CREATE INDEX idx_session_memories_metadata ON dev.session_memories USING GIN(metadata);

-- Trigger
CREATE TRIGGER trigger_update_session_memories_updated_at
    BEFORE UPDATE ON dev.session_memories
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.session_memories TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.session_memories TO authenticated;

-- Comments
COMMENT ON TABLE dev.session_memories IS 'Long-term memories associated with conversation sessions';
COMMENT ON COLUMN dev.session_memories.memory_id IS 'Unique memory identifier';
COMMENT ON COLUMN dev.session_memories.session_id IS 'Associated session ID';
COMMENT ON COLUMN dev.session_memories.user_id IS 'Associated user ID';
COMMENT ON COLUMN dev.session_memories.memory_type IS 'Type of memory (summary, preference, fact, etc.)';
COMMENT ON COLUMN dev.session_memories.content IS 'Memory content';
COMMENT ON COLUMN dev.session_memories.metadata IS 'Additional memory metadata stored as JSONB';