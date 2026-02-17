-- Session Service Migration: Create session_messages table
-- Version: 002
-- Date: 2025-10-26

-- Create session_messages table
CREATE TABLE IF NOT EXISTS session.session_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'chat',
    message_metadata JSONB DEFAULT '{}',
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 4) DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_session_messages_session_id ON session.session_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_user_id ON session.session_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_created_at ON session.session_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_session_messages_session_created ON session.session_messages(session_id, created_at);

-- Comments
COMMENT ON TABLE session.session_messages IS 'Session conversation messages';
COMMENT ON COLUMN session.session_messages.id IS 'Unique message identifier (UUID)';
COMMENT ON COLUMN session.session_messages.session_id IS 'Session identifier';
COMMENT ON COLUMN session.session_messages.user_id IS 'User identifier';
COMMENT ON COLUMN session.session_messages.role IS 'Message role (user, assistant, system)';
COMMENT ON COLUMN session.session_messages.content IS 'Message content';
COMMENT ON COLUMN session.session_messages.message_type IS 'Message type (chat, system, tool_call, etc.)';
COMMENT ON COLUMN session.session_messages.message_metadata IS 'Additional message metadata';
COMMENT ON COLUMN session.session_messages.tokens_used IS 'Tokens used for this message';
COMMENT ON COLUMN session.session_messages.cost_usd IS 'Cost in USD for this message';
