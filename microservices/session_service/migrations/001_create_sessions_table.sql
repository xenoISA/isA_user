-- Session Service Migration: Create sessions table
-- Version: 001 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    conversation_data JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0.0,
    session_summary TEXT DEFAULT '',
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sessions_session_id ON dev.sessions(session_id);
CREATE INDEX idx_sessions_user_id ON dev.sessions(user_id);
CREATE INDEX idx_sessions_status ON dev.sessions(status);
CREATE INDEX idx_sessions_is_active ON dev.sessions(is_active);
CREATE INDEX idx_sessions_last_activity ON dev.sessions(last_activity);
CREATE INDEX idx_sessions_created_at ON dev.sessions(created_at);
CREATE INDEX idx_sessions_conversation_data ON dev.sessions USING GIN(conversation_data);
CREATE INDEX idx_sessions_metadata ON dev.sessions USING GIN(metadata);

-- Trigger
CREATE TRIGGER trigger_update_sessions_updated_at
    BEFORE UPDATE ON dev.sessions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.sessions TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.sessions TO authenticated;

-- Comments
COMMENT ON TABLE dev.sessions IS 'User conversation sessions with metadata and statistics';
COMMENT ON COLUMN dev.sessions.session_id IS 'Unique session identifier';
COMMENT ON COLUMN dev.sessions.user_id IS 'Associated user ID';
COMMENT ON COLUMN dev.sessions.conversation_data IS 'Session conversation data stored as JSONB';
COMMENT ON COLUMN dev.sessions.status IS 'Session status (active, ended, expired)';
COMMENT ON COLUMN dev.sessions.metadata IS 'Additional session metadata stored as JSONB';
COMMENT ON COLUMN dev.sessions.is_active IS 'Whether session is currently active';
COMMENT ON COLUMN dev.sessions.message_count IS 'Total number of messages in session';
COMMENT ON COLUMN dev.sessions.total_tokens IS 'Total tokens used in session';
COMMENT ON COLUMN dev.sessions.total_cost IS 'Total cost of session in USD';
COMMENT ON COLUMN dev.sessions.session_summary IS 'Summary of the session';
COMMENT ON COLUMN dev.sessions.last_activity IS 'Last activity timestamp';