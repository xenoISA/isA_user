-- Vault Service Database Schema
-- Version: 1.0.0
-- Description: Tables for secure credential and secret management

-- ============================================
-- Vault Items Table
-- ============================================
CREATE TABLE IF NOT EXISTS dev.vault_items (
    id SERIAL PRIMARY KEY,
    vault_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    secret_type VARCHAR(100) NOT NULL,
    provider VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    encrypted_value TEXT NOT NULL,  -- Base64 encoded encrypted data
    encryption_method VARCHAR(50) NOT NULL DEFAULT 'aes_256_gcm',
    encryption_key_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    version INTEGER DEFAULT 1,
    expires_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    rotation_enabled BOOLEAN DEFAULT false,
    rotation_days INTEGER,
    blockchain_reference VARCHAR(255),  -- Blockchain transaction hash for verification
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT vault_items_user_id_fk FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT vault_items_org_id_fk FOREIGN KEY (organization_id) REFERENCES dev.organizations(organization_id) ON DELETE CASCADE
);

-- Indexes for vault_items
CREATE INDEX IF NOT EXISTS idx_vault_items_user_id ON dev.vault_items(user_id);
CREATE INDEX IF NOT EXISTS idx_vault_items_org_id ON dev.vault_items(organization_id);
CREATE INDEX IF NOT EXISTS idx_vault_items_secret_type ON dev.vault_items(secret_type);
CREATE INDEX IF NOT EXISTS idx_vault_items_provider ON dev.vault_items(provider);
CREATE INDEX IF NOT EXISTS idx_vault_items_is_active ON dev.vault_items(is_active);
CREATE INDEX IF NOT EXISTS idx_vault_items_expires_at ON dev.vault_items(expires_at);
CREATE INDEX IF NOT EXISTS idx_vault_items_tags ON dev.vault_items USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_vault_items_blockchain_ref ON dev.vault_items(blockchain_reference);

-- ============================================
-- Vault Access Logs Table (Audit Trail)
-- ============================================
CREATE TABLE IF NOT EXISTS dev.vault_access_logs (
    id SERIAL PRIMARY KEY,
    log_id VARCHAR(255) NOT NULL UNIQUE,
    vault_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,  -- create, read, update, delete, rotate, share, etc.
    ip_address VARCHAR(45),  -- IPv6 compatible
    user_agent TEXT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT vault_logs_vault_id_fk FOREIGN KEY (vault_id) REFERENCES dev.vault_items(vault_id) ON DELETE CASCADE,
    CONSTRAINT vault_logs_user_id_fk FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
);

-- Indexes for vault_access_logs
CREATE INDEX IF NOT EXISTS idx_vault_logs_vault_id ON dev.vault_access_logs(vault_id);
CREATE INDEX IF NOT EXISTS idx_vault_logs_user_id ON dev.vault_access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_vault_logs_action ON dev.vault_access_logs(action);
CREATE INDEX IF NOT EXISTS idx_vault_logs_created_at ON dev.vault_access_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vault_logs_success ON dev.vault_access_logs(success);

-- ============================================
-- Vault Shares Table (Secret Sharing)
-- ============================================
CREATE TABLE IF NOT EXISTS dev.vault_shares (
    id SERIAL PRIMARY KEY,
    share_id VARCHAR(255) NOT NULL UNIQUE,
    vault_id VARCHAR(255) NOT NULL,
    owner_user_id VARCHAR(255) NOT NULL,
    shared_with_user_id VARCHAR(255),
    shared_with_org_id VARCHAR(255),
    permission_level VARCHAR(50) NOT NULL DEFAULT 'read',  -- read, read_write
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT vault_shares_vault_id_fk FOREIGN KEY (vault_id) REFERENCES dev.vault_items(vault_id) ON DELETE CASCADE,
    CONSTRAINT vault_shares_owner_fk FOREIGN KEY (owner_user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT vault_shares_user_fk FOREIGN KEY (shared_with_user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT vault_shares_org_fk FOREIGN KEY (shared_with_org_id) REFERENCES dev.organizations(organization_id) ON DELETE CASCADE,
    CONSTRAINT vault_shares_check CHECK (shared_with_user_id IS NOT NULL OR shared_with_org_id IS NOT NULL)
);

-- Indexes for vault_shares
CREATE INDEX IF NOT EXISTS idx_vault_shares_vault_id ON dev.vault_shares(vault_id);
CREATE INDEX IF NOT EXISTS idx_vault_shares_owner ON dev.vault_shares(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_vault_shares_user ON dev.vault_shares(shared_with_user_id);
CREATE INDEX IF NOT EXISTS idx_vault_shares_org ON dev.vault_shares(shared_with_org_id);
CREATE INDEX IF NOT EXISTS idx_vault_shares_is_active ON dev.vault_shares(is_active);
CREATE INDEX IF NOT EXISTS idx_vault_shares_expires_at ON dev.vault_shares(expires_at);

-- ============================================
-- Triggers for updated_at
-- ============================================
CREATE OR REPLACE FUNCTION dev.update_vault_items_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER vault_items_updated_at_trigger
    BEFORE UPDATE ON dev.vault_items
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_vault_items_updated_at();

-- ============================================
-- Views for Statistics
-- ============================================
CREATE OR REPLACE VIEW dev.vault_stats_view AS
SELECT
    user_id,
    COUNT(*) as total_secrets,
    COUNT(*) FILTER (WHERE is_active = true) as active_secrets,
    COUNT(*) FILTER (WHERE expires_at < CURRENT_TIMESTAMP) as expired_secrets,
    COUNT(*) FILTER (WHERE blockchain_reference IS NOT NULL) as blockchain_verified_secrets,
    SUM(access_count) as total_access_count,
    jsonb_object_agg(secret_type, type_count) as secrets_by_type
FROM (
    SELECT
        user_id,
        is_active,
        expires_at,
        blockchain_reference,
        access_count,
        secret_type,
        COUNT(*) as type_count
    FROM dev.vault_items
    GROUP BY user_id, is_active, expires_at, blockchain_reference, access_count, secret_type
) AS subquery
GROUP BY user_id;

-- ============================================
-- Comments
-- ============================================
COMMENT ON TABLE dev.vault_items IS 'Encrypted secrets and credentials storage';
COMMENT ON TABLE dev.vault_access_logs IS 'Audit trail for all vault access operations';
COMMENT ON TABLE dev.vault_shares IS 'Secret sharing permissions between users and organizations';

COMMENT ON COLUMN dev.vault_items.encrypted_value IS 'Base64 encoded AES-256-GCM encrypted secret value';
COMMENT ON COLUMN dev.vault_items.metadata IS 'Contains encryption metadata (dek_encrypted, kek_salt, nonce) and other custom fields';
COMMENT ON COLUMN dev.vault_items.blockchain_reference IS 'Transaction hash for blockchain-verified secrets';
COMMENT ON COLUMN dev.vault_items.rotation_enabled IS 'Enable automatic secret rotation reminders';

-- ============================================
-- Sample Secret Types (for reference)
-- ============================================
-- api_key, database_credential, ssh_key, ssl_certificate, oauth_token,
-- aws_credential, blockchain_key, environment_variable, custom

-- ============================================
-- Sample Providers (for reference)
-- ============================================
-- openai, anthropic, stripe, aws, azure, gcp, github, gitlab,
-- ethereum, polygon, custom

-- ============================================
-- Sample Actions (for reference)
-- ============================================
-- create, read, update, delete, rotate, share, revoke_share, export, import
