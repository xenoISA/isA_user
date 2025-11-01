-- Auth Service Migration: Create users table
-- Version: 001
-- Date: 2025-01-20

-- Create auth schema if not exists
CREATE SCHEMA IF NOT EXISTS auth;

-- Create users table (minimal - auth identity only)
CREATE TABLE IF NOT EXISTS auth.users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON auth.users(is_active);

-- Comments
COMMENT ON TABLE auth.users IS 'User authentication identity (minimal)';
COMMENT ON COLUMN auth.users.user_id IS 'Unique user identifier';
COMMENT ON COLUMN auth.users.email IS 'User email address (unique)';
COMMENT ON COLUMN auth.users.name IS 'User display name';
COMMENT ON COLUMN auth.users.is_active IS 'Whether user account is active';
