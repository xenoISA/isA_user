-- Vault Service Migration: Migrate to dedicated vault schema
-- Version: 004
-- Date: 2025-10-27
-- Description: Move tables from dev schema to vault schema and remove foreign keys

-- Create vault schema
CREATE SCHEMA IF NOT EXISTS vault;

-- Drop existing tables/views in vault schema if they exist
DROP VIEW IF EXISTS vault.vault_stats_view CASCADE;
DROP TABLE IF EXISTS vault.vault_shares CASCADE;
DROP TABLE IF EXISTS vault.vault_access_logs CASCADE;
DROP TABLE IF EXISTS vault.vault_items CASCADE;

-- 1. Create vault_items table
CREATE TABLE vault.vault_items (
    id SERIAL PRIMARY KEY,
    vault_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    organization_id VARCHAR(255),  -- No FK constraint - cross-service reference
    secret_type VARCHAR(100) NOT NULL,
    provider VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    encrypted_value TEXT NOT NULL,
    encryption_method VARCHAR(50) NOT NULL DEFAULT 'aes_256_gcm',
    encryption_key_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    version INTEGER DEFAULT 1,
    expires_at TIMESTAMPTZ,  -- Changed from TIMESTAMP
    last_accessed_at TIMESTAMPTZ,  -- Changed from TIMESTAMP
    access_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    rotation_enabled BOOLEAN DEFAULT false,
    rotation_days INTEGER,
    blockchain_reference VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),  -- Changed from TIMESTAMP
    updated_at TIMESTAMPTZ DEFAULT NOW()  -- Changed from TIMESTAMP
);

-- 2. Create vault_access_logs table
CREATE TABLE vault.vault_access_logs (
    id SERIAL PRIMARY KEY,
    log_id VARCHAR(255) NOT NULL UNIQUE,
    vault_id VARCHAR(255) NOT NULL,  -- No FK constraint
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()  -- Changed from TIMESTAMP
);

-- 3. Create vault_shares table
CREATE TABLE vault.vault_shares (
    id SERIAL PRIMARY KEY,
    share_id VARCHAR(255) NOT NULL UNIQUE,
    vault_id VARCHAR(255) NOT NULL,  -- No FK constraint
    owner_user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    shared_with_user_id VARCHAR(255),  -- No FK constraint - cross-service reference
    shared_with_org_id VARCHAR(255),  -- No FK constraint - cross-service reference
    permission_level VARCHAR(50) NOT NULL DEFAULT 'read',
    expires_at TIMESTAMPTZ,  -- Changed from TIMESTAMP
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),  -- Changed from TIMESTAMP

    CONSTRAINT vault_shares_check CHECK (shared_with_user_id IS NOT NULL OR shared_with_org_id IS NOT NULL)
);

-- ====================
-- Indexes
-- ====================

-- Vault items indexes
CREATE INDEX idx_vault_items_user_id ON vault.vault_items(user_id);
CREATE INDEX idx_vault_items_org_id ON vault.vault_items(organization_id);
CREATE INDEX idx_vault_items_secret_type ON vault.vault_items(secret_type);
CREATE INDEX idx_vault_items_provider ON vault.vault_items(provider);
CREATE INDEX idx_vault_items_is_active ON vault.vault_items(is_active);
CREATE INDEX idx_vault_items_expires_at ON vault.vault_items(expires_at);
CREATE INDEX idx_vault_items_tags ON vault.vault_items USING GIN(tags);
CREATE INDEX idx_vault_items_blockchain_ref ON vault.vault_items(blockchain_reference);

-- Vault access logs indexes
CREATE INDEX idx_vault_logs_vault_id ON vault.vault_access_logs(vault_id);
CREATE INDEX idx_vault_logs_user_id ON vault.vault_access_logs(user_id);
CREATE INDEX idx_vault_logs_action ON vault.vault_access_logs(action);
CREATE INDEX idx_vault_logs_created_at ON vault.vault_access_logs(created_at DESC);
CREATE INDEX idx_vault_logs_success ON vault.vault_access_logs(success);

-- Vault shares indexes
CREATE INDEX idx_vault_shares_vault_id ON vault.vault_shares(vault_id);
CREATE INDEX idx_vault_shares_owner ON vault.vault_shares(owner_user_id);
CREATE INDEX idx_vault_shares_user ON vault.vault_shares(shared_with_user_id);
CREATE INDEX idx_vault_shares_org ON vault.vault_shares(shared_with_org_id);
CREATE INDEX idx_vault_shares_is_active ON vault.vault_shares(is_active);
CREATE INDEX idx_vault_shares_expires_at ON vault.vault_shares(expires_at);

-- ====================
-- Views
-- ====================

CREATE OR REPLACE VIEW vault.vault_stats_view AS
SELECT
    user_id,
    COUNT(*) as total_secrets,
    COUNT(*) FILTER (WHERE is_active = true) as active_secrets,
    COUNT(*) FILTER (WHERE expires_at < NOW()) as expired_secrets,
    COUNT(*) FILTER (WHERE blockchain_reference IS NOT NULL) as blockchain_verified_secrets,
    SUM(access_count) as total_access_count
FROM vault.vault_items
GROUP BY user_id;

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA vault IS 'Vault service schema - encrypted secrets and credentials management';
COMMENT ON TABLE vault.vault_items IS 'Encrypted secrets and credentials storage';
COMMENT ON TABLE vault.vault_access_logs IS 'Audit trail for all vault access operations';
COMMENT ON TABLE vault.vault_shares IS 'Secret sharing permissions between users and organizations';

COMMENT ON COLUMN vault.vault_items.encrypted_value IS 'Base64 encoded AES-256-GCM encrypted secret value';
COMMENT ON COLUMN vault.vault_items.metadata IS 'Contains encryption metadata (dek_encrypted, kek_salt, nonce) and other custom fields';
COMMENT ON COLUMN vault.vault_items.blockchain_reference IS 'Transaction hash for blockchain-verified secrets';
COMMENT ON COLUMN vault.vault_items.rotation_enabled IS 'Enable automatic secret rotation reminders';
