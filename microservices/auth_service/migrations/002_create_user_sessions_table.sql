-- Auth Service Migration: Create user_sessions table
-- Version: 002 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.user_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMPTZ,
    invalidated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_user_sessions_session_id ON dev.user_sessions(session_id);
CREATE INDEX idx_user_sessions_user_id ON dev.user_sessions(user_id);
CREATE INDEX idx_user_sessions_is_active ON dev.user_sessions(is_active);
CREATE INDEX idx_user_sessions_expires_at ON dev.user_sessions(expires_at);
CREATE INDEX idx_user_sessions_last_activity ON dev.user_sessions(last_activity);

-- Trigger
CREATE TRIGGER trigger_update_user_sessions_updated_at
    BEFORE UPDATE ON dev.user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.user_sessions TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.user_sessions TO authenticated;

-- Comments
COMMENT ON TABLE dev.user_sessions IS 'User authentication sessions';
COMMENT ON COLUMN dev.user_sessions.session_id IS 'Unique session identifier';
COMMENT ON COLUMN dev.user_sessions.user_id IS 'Associated user ID';
COMMENT ON COLUMN dev.user_sessions.expires_at IS 'Session expiration timestamp';
COMMENT ON COLUMN dev.user_sessions.is_active IS 'Whether session is active';
COMMENT ON COLUMN dev.user_sessions.last_activity IS 'Last session activity timestamp';
COMMENT ON COLUMN dev.user_sessions.invalidated_at IS 'Session invalidation timestamp';