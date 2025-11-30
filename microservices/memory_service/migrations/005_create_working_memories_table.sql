-- Memory Service Migration: Create working_memories table
-- Version: 005
-- Date: 2025-01-24

-- ====================
-- Working Memories Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.working_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'working',

    -- Content
    content TEXT NOT NULL,

    -- Working memory structure
    task_id VARCHAR(255) NOT NULL,
    task_context JSONB NOT NULL,

    -- Working memory specific
    ttl_seconds INTEGER DEFAULT 3600 CHECK (ttl_seconds > 0),
    priority INTEGER DEFAULT 1 CHECK (priority >= 1 AND priority <= 10),
    expires_at TIMESTAMPTZ NOT NULL,

    -- Cognitive attributes
    importance_score FLOAT DEFAULT 0.5 CHECK (importance_score >= 0 AND importance_score <= 1),
    confidence FLOAT DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    access_count INTEGER DEFAULT 0,

    -- Metadata
    tags JSONB DEFAULT '[]'::jsonb,
    context JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ
);

-- Indexes for working memories
CREATE INDEX idx_working_memories_user_id ON memory.working_memories(user_id);
CREATE INDEX idx_working_memories_task_id ON memory.working_memories(task_id);
CREATE INDEX idx_working_memories_priority ON memory.working_memories(priority DESC);
CREATE INDEX idx_working_memories_expires_at ON memory.working_memories(expires_at);
-- Note: Cannot use NOW() in index predicate as it's not IMMUTABLE
-- CREATE INDEX idx_working_memories_active ON memory.working_memories(user_id, expires_at) WHERE expires_at > NOW();
-- Instead, create a simple index on expires_at which can be used with WHERE clause in queries
CREATE INDEX idx_working_memories_user_expires ON memory.working_memories(user_id, expires_at);
CREATE INDEX idx_working_memories_created_at ON memory.working_memories(created_at DESC);

-- Trigger for updated_at
CREATE TRIGGER trigger_update_working_memories_updated_at
    BEFORE UPDATE ON memory.working_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_updated_at();

-- Comments
COMMENT ON TABLE memory.working_memories IS 'Working memories - temporary task-related information with TTL';
COMMENT ON COLUMN memory.working_memories.id IS 'Memory ID - also used as Qdrant point ID';
COMMENT ON COLUMN memory.working_memories.expires_at IS 'Expiration timestamp for automatic cleanup';
COMMENT ON COLUMN memory.working_memories.priority IS 'Priority level (1-10, higher is more important)';
