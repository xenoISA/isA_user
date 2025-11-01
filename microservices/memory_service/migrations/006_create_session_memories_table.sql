-- Memory Service Migration: Create session_memories and session_summaries tables
-- Version: 006
-- Date: 2025-01-24

-- ====================
-- Session Memories Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.session_memories (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) DEFAULT 'session',

    -- Content
    content TEXT NOT NULL,

    -- Session structure
    session_id VARCHAR(255) NOT NULL,
    interaction_sequence INTEGER NOT NULL,
    conversation_state JSONB DEFAULT '{}'::jsonb,

    -- Session memory specific
    session_type VARCHAR(50) DEFAULT 'chat',
    active BOOLEAN DEFAULT true,

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

-- Indexes for session memories
CREATE INDEX idx_session_memories_user_id ON memory.session_memories(user_id);
CREATE INDEX idx_session_memories_session_id ON memory.session_memories(session_id);
CREATE INDEX idx_session_memories_user_session ON memory.session_memories(user_id, session_id, interaction_sequence);
CREATE INDEX idx_session_memories_active ON memory.session_memories(user_id, active) WHERE active = true;
CREATE INDEX idx_session_memories_session_type ON memory.session_memories(session_type);
CREATE INDEX idx_session_memories_created_at ON memory.session_memories(created_at DESC);

-- Trigger for updated_at
CREATE TRIGGER trigger_update_session_memories_updated_at
    BEFORE UPDATE ON memory.session_memories
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_updated_at();

-- ====================
-- Session Summaries Table
-- ====================
CREATE TABLE IF NOT EXISTS memory.session_summaries (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,

    -- Summary content
    summary TEXT NOT NULL,
    key_points TEXT[] DEFAULT '{}',
    message_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for session summaries
CREATE INDEX idx_session_summaries_user_id ON memory.session_summaries(user_id);
CREATE INDEX idx_session_summaries_session_id ON memory.session_summaries(session_id);
CREATE INDEX idx_session_summaries_user_session ON memory.session_summaries(user_id, session_id);
CREATE INDEX idx_session_summaries_created_at ON memory.session_summaries(created_at DESC);

-- Comments
COMMENT ON TABLE memory.session_memories IS 'Session memories - conversation context and interaction history';
COMMENT ON TABLE memory.session_summaries IS 'Session summaries - condensed conversation summaries';
COMMENT ON COLUMN memory.session_memories.id IS 'Memory ID - also used as Qdrant point ID';
COMMENT ON COLUMN memory.session_memories.interaction_sequence IS 'Sequence number in the session for ordering';
