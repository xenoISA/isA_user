-- Wallet Service Migration: Remove foreign key constraints
-- Version: 002
-- Date: 2025-09-26
-- Description: Remove foreign key constraints to follow microservices best practices

-- Remove foreign key constraints
ALTER TABLE dev.wallets 
    DROP CONSTRAINT IF EXISTS fk_wallet_user;

ALTER TABLE dev.wallet_transactions
    DROP CONSTRAINT IF EXISTS fk_transaction_user;

-- Add indexes for performance (replace foreign keys)
CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON dev.wallets(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON dev.wallet_transactions(user_id);

-- Add comment explaining the architecture decision
COMMENT ON COLUMN dev.wallets.user_id IS 'Reference to user in account service - no FK constraint per microservices pattern';
COMMENT ON COLUMN dev.wallet_transactions.user_id IS 'Reference to user in account service - no FK constraint per microservices pattern';