-- Session Service Migration: Create session_messages table
-- Version: 002 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.session_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) NOT NULL UNIQUE,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'chat',
    metadata JSONB DEFAULT '{}'::jsonb,
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,4) DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES dev.sessions(session_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_session_messages_message_id ON dev.session_messages(message_id);
CREATE INDEX idx_session_messages_session_id ON dev.session_messages(session_id);
CREATE INDEX idx_session_messages_user_id ON dev.session_messages(user_id);
CREATE INDEX idx_session_messages_role ON dev.session_messages(role);
CREATE INDEX idx_session_messages_message_type ON dev.session_messages(message_type);
CREATE INDEX idx_session_messages_created_at ON dev.session_messages(created_at);
CREATE INDEX idx_session_messages_metadata ON dev.session_messages USING GIN(metadata);
CREATE INDEX idx_session_messages_tokens_used ON dev.session_messages(tokens_used);

-- Permissions  
GRANT ALL ON dev.session_messages TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.session_messages TO authenticated;

-- Comments
COMMENT ON TABLE dev.session_messages IS 'Individual messages within conversation sessions';
COMMENT ON COLUMN dev.session_messages.message_id IS 'Unique message identifier';
COMMENT ON COLUMN dev.session_messages.session_id IS 'Associated session ID';
COMMENT ON COLUMN dev.session_messages.user_id IS 'Associated user ID';
COMMENT ON COLUMN dev.session_messages.role IS 'Message role (user, assistant, system)';
COMMENT ON COLUMN dev.session_messages.content IS 'Message content';
COMMENT ON COLUMN dev.session_messages.message_type IS 'Type of message (chat, system, etc.)';
COMMENT ON COLUMN dev.session_messages.metadata IS 'Additional message metadata stored as JSONB';
COMMENT ON COLUMN dev.session_messages.tokens_used IS 'Number of tokens used for this message';
COMMENT ON COLUMN dev.session_messages.cost_usd IS 'Cost of this message in USD';