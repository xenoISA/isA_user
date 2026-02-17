-- Session Service Migration: Create session_memories table
-- Version: 003
-- Date: 2025-10-26

-- Create session_memories table
CREATE TABLE IF NOT EXISTS session.session_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    conversation_summary TEXT DEFAULT '',
    session_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_session_memories_session_id ON session.session_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_session_memories_user_id ON session.session_memories(user_id);

-- Comments
COMMENT ON TABLE session.session_memories IS 'Session memory and summaries';
COMMENT ON COLUMN session.session_memories.id IS 'Unique memory identifier (UUID)';
COMMENT ON COLUMN session.session_memories.session_id IS 'Session identifier (unique)';
COMMENT ON COLUMN session.session_memories.user_id IS 'User identifier';
COMMENT ON COLUMN session.session_memories.conversation_summary IS 'Conversation summary';
COMMENT ON COLUMN session.session_memories.session_metadata IS 'Additional memory metadata';
