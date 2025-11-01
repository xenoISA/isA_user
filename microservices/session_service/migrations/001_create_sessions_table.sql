-- Session Service Migration: Create sessions table
-- Version: 001
-- Date: 2025-10-26

-- Create session schema if not exists
CREATE SCHEMA IF NOT EXISTS session;

-- Create sessions table
CREATE TABLE IF NOT EXISTS session.sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    conversation_data JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 4) DEFAULT 0.0,
    session_summary TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON session.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON session.sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON session.sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON session.sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_sessions_user_active ON session.sessions(user_id, is_active);

-- Comments
COMMENT ON TABLE session.sessions IS 'User conversation sessions';
COMMENT ON COLUMN session.sessions.session_id IS 'Unique session identifier';
COMMENT ON COLUMN session.sessions.user_id IS 'User identifier';
COMMENT ON COLUMN session.sessions.conversation_data IS 'Conversation context data';
COMMENT ON COLUMN session.sessions.status IS 'Session status (active, ended, expired)';
COMMENT ON COLUMN session.sessions.metadata IS 'Additional session metadata';
COMMENT ON COLUMN session.sessions.is_active IS 'Whether session is active';
COMMENT ON COLUMN session.sessions.message_count IS 'Total number of messages in session';
COMMENT ON COLUMN session.sessions.total_tokens IS 'Total tokens used in session';
COMMENT ON COLUMN session.sessions.total_cost IS 'Total cost in USD';
COMMENT ON COLUMN session.sessions.session_summary IS 'Session summary';
COMMENT ON COLUMN session.sessions.last_activity IS 'Last activity timestamp';
