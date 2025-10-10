-- Account Service Migration: Extend users table with account-specific fields
-- Version: 001 
-- Date: 2025-01-20

-- Add account-specific columns to the existing users table
ALTER TABLE dev.users 
ADD COLUMN IF NOT EXISTS credits_remaining DECIMAL(10,2) DEFAULT 1000.0,
ADD COLUMN IF NOT EXISTS credits_total DECIMAL(10,2) DEFAULT 1000.0,
ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;

-- Indexes for account-specific fields
CREATE INDEX IF NOT EXISTS idx_users_credits_remaining ON dev.users(credits_remaining);
CREATE INDEX IF NOT EXISTS idx_users_credits_total ON dev.users(credits_total);
CREATE INDEX IF NOT EXISTS idx_users_preferences ON dev.users USING GIN(preferences);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON dev.users(subscription_status);

-- Comments for new columns
COMMENT ON COLUMN dev.users.credits_remaining IS 'Current available credits for the user';
COMMENT ON COLUMN dev.users.credits_total IS 'Total credits allocated to the user';
COMMENT ON COLUMN dev.users.preferences IS 'User preferences stored as JSONB';