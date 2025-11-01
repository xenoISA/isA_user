-- Migration: Remove foreign key constraints on user_id fields
-- This allows vault service to work independently without requiring users table
-- User validation will be done via microservice-to-microservice communication

-- 1. Remove FK constraint from vault_items table
ALTER TABLE IF EXISTS dev.vault_items
DROP CONSTRAINT IF EXISTS vault_items_user_id_fk;

-- Add index on user_id for performance (if not exists)
CREATE INDEX IF NOT EXISTS idx_vault_items_user_id ON dev.vault_items(user_id);

-- Comment explaining the design decision
COMMENT ON COLUMN dev.vault_items.user_id IS 'User ID - validated via account_service microservice, not via FK constraint';

-- 2. Remove FK constraints from vault_shares table
ALTER TABLE IF EXISTS dev.vault_shares
DROP CONSTRAINT IF EXISTS vault_shares_owner_fk;

ALTER TABLE IF EXISTS dev.vault_shares
DROP CONSTRAINT IF EXISTS vault_shares_shared_with_fk;

ALTER TABLE IF EXISTS dev.vault_shares
DROP CONSTRAINT IF EXISTS vault_shares_user_fk;

-- Add indexes on user_id fields for performance
CREATE INDEX IF NOT EXISTS idx_vault_shares_owner_user_id ON dev.vault_shares(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_vault_shares_shared_with_user_id ON dev.vault_shares(shared_with_user_id);

-- Comments explaining the design decision
COMMENT ON COLUMN dev.vault_shares.owner_user_id IS 'Owner user ID - validated via account_service microservice, not via FK constraint';
COMMENT ON COLUMN dev.vault_shares.shared_with_user_id IS 'Shared with user ID - validated via account_service microservice, not via FK constraint';

-- 3. Remove FK constraint from vault_access_logs table
ALTER TABLE IF EXISTS dev.vault_access_logs
DROP CONSTRAINT IF EXISTS vault_logs_user_id_fk;

-- Add index on user_id for performance
CREATE INDEX IF NOT EXISTS idx_vault_access_logs_user_id ON dev.vault_access_logs(user_id);

-- Comment explaining the design decision
COMMENT ON COLUMN dev.vault_access_logs.user_id IS 'User ID - validated via account_service microservice, not via FK constraint';
