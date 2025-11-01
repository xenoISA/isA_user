-- Account Service Migration: Create users table
-- Version: 001
-- Date: 2025-01-24

-- Create account schema if not exists
CREATE SCHEMA IF NOT EXISTS account;

-- Create users table (user profile data)
CREATE TABLE IF NOT EXISTS account.users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255),
    name VARCHAR(255),
    subscription_status VARCHAR(50) DEFAULT 'free',
    is_active BOOLEAN DEFAULT TRUE,
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON account.users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON account.users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON account.users(subscription_status);
CREATE INDEX IF NOT EXISTS idx_users_preferences ON account.users USING GIN(preferences);

-- Comments
COMMENT ON TABLE account.users IS 'User account profiles (synchronized from auth_service via events)';
COMMENT ON COLUMN account.users.user_id IS 'Unique user identifier';
COMMENT ON COLUMN account.users.email IS 'User email address';
COMMENT ON COLUMN account.users.name IS 'User display name';
COMMENT ON COLUMN account.users.subscription_status IS 'User subscription plan (free, basic, premium, pro, enterprise, active)';
COMMENT ON COLUMN account.users.is_active IS 'Account active status';
COMMENT ON COLUMN account.users.preferences IS 'User preferences (JSONB)';
