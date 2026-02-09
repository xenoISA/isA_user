-- Auth Service Migration: Add password_hash column for email/password login
-- Version: 005
-- Date: 2025-01-30

-- Add password_hash column to users table
ALTER TABLE auth.users
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- Add email_verified column to track verification status
ALTER TABLE auth.users
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- Add last_login column for tracking
ALTER TABLE auth.users
ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ;

-- Index for login queries
CREATE INDEX IF NOT EXISTS idx_users_email_verified ON auth.users(email, email_verified);

-- Comments
COMMENT ON COLUMN auth.users.password_hash IS 'Bcrypt hashed password for email/password authentication';
COMMENT ON COLUMN auth.users.email_verified IS 'Whether email has been verified';
COMMENT ON COLUMN auth.users.last_login IS 'Last successful login timestamp';
