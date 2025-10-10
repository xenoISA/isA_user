-- Auth Service Migration: Create users table
-- Version: 001 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL UNIQUE,
    auth0_id VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    subscription_status VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_user_id ON dev.users(user_id);
CREATE INDEX idx_users_auth0_id ON dev.users(auth0_id);
CREATE INDEX idx_users_email ON dev.users(email);
CREATE INDEX idx_users_is_active ON dev.users(is_active);

-- Trigger
CREATE TRIGGER trigger_update_users_updated_at
    BEFORE UPDATE ON dev.users
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Permissions  
GRANT ALL ON dev.users TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.users TO authenticated;

-- Comments
COMMENT ON TABLE dev.users IS 'User authentication and profile information';
COMMENT ON COLUMN dev.users.user_id IS 'Unique user identifier';
COMMENT ON COLUMN dev.users.auth0_id IS 'Auth0 provider user ID';
COMMENT ON COLUMN dev.users.email IS 'User email address';
COMMENT ON COLUMN dev.users.name IS 'User display name';
COMMENT ON COLUMN dev.users.subscription_status IS 'User subscription status';
COMMENT ON COLUMN dev.users.is_active IS 'Whether user account is active';