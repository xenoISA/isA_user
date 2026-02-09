-- Credit Service Indexes
-- Performance indexes for credit tables

-- ================================================================
-- credit_accounts indexes
-- ================================================================

-- Index on user_id for looking up all accounts for a user
CREATE INDEX IF NOT EXISTS idx_credit_accounts_user_id
    ON credit.credit_accounts(user_id);

-- Index on credit_type for filtering by type
CREATE INDEX IF NOT EXISTS idx_credit_accounts_type
    ON credit.credit_accounts(credit_type);

-- Composite index on user_id and credit_type for efficient account lookup
CREATE INDEX IF NOT EXISTS idx_credit_accounts_user_type
    ON credit.credit_accounts(user_id, credit_type);

-- Partial index on active accounts for filtering
CREATE INDEX IF NOT EXISTS idx_credit_accounts_active
    ON credit.credit_accounts(is_active)
    WHERE is_active = TRUE;

-- Index on organization_id for organization-level queries
CREATE INDEX IF NOT EXISTS idx_credit_accounts_organization_id
    ON credit.credit_accounts(organization_id)
    WHERE organization_id IS NOT NULL;

-- ================================================================
-- credit_transactions indexes
-- ================================================================

-- Index on account_id for transaction history queries
CREATE INDEX IF NOT EXISTS idx_credit_transactions_account_id
    ON credit.credit_transactions(account_id);

-- Index on user_id for user transaction history
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id
    ON credit.credit_transactions(user_id);

-- Index on transaction_type for filtering by operation type
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type
    ON credit.credit_transactions(transaction_type);

-- Index on created_at for chronological queries (descending for recent-first)
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at
    ON credit.credit_transactions(created_at DESC);

-- Partial index on expires_at for expiration queries
CREATE INDEX IF NOT EXISTS idx_credit_transactions_expires_at
    ON credit.credit_transactions(expires_at)
    WHERE expires_at IS NOT NULL;

-- Composite index for user + transaction type queries
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_type
    ON credit.credit_transactions(user_id, transaction_type);

-- Index on reference_id for looking up related transactions
CREATE INDEX IF NOT EXISTS idx_credit_transactions_reference
    ON credit.credit_transactions(reference_id, reference_type)
    WHERE reference_id IS NOT NULL;

-- ================================================================
-- credit_campaigns indexes
-- ================================================================

-- Index on is_active for filtering active campaigns
CREATE INDEX IF NOT EXISTS idx_credit_campaigns_active
    ON credit.credit_campaigns(is_active);

-- Composite index on start_date and end_date for date range queries
CREATE INDEX IF NOT EXISTS idx_credit_campaigns_dates
    ON credit.credit_campaigns(start_date, end_date);

-- Index on credit_type for filtering campaigns by type
CREATE INDEX IF NOT EXISTS idx_credit_campaigns_type
    ON credit.credit_campaigns(credit_type);

-- Index on created_by for admin/creator queries
CREATE INDEX IF NOT EXISTS idx_credit_campaigns_created_by
    ON credit.credit_campaigns(created_by)
    WHERE created_by IS NOT NULL;

-- Partial index for active campaigns within date range
CREATE INDEX IF NOT EXISTS idx_credit_campaigns_active_current
    ON credit.credit_campaigns(start_date, end_date, is_active)
    WHERE is_active = TRUE;

-- ================================================================
-- credit_allocations indexes
-- ================================================================

-- Index on user_id for user allocation history
CREATE INDEX IF NOT EXISTS idx_credit_allocations_user_id
    ON credit.credit_allocations(user_id);

-- Index on campaign_id for campaign allocation tracking
CREATE INDEX IF NOT EXISTS idx_credit_allocations_campaign
    ON credit.credit_allocations(campaign_id)
    WHERE campaign_id IS NOT NULL;

-- Index on expires_at for expiration processing
CREATE INDEX IF NOT EXISTS idx_credit_allocations_expires_at
    ON credit.credit_allocations(expires_at)
    WHERE expires_at IS NOT NULL;

-- Composite index on user_id and campaign_id for per-user campaign limits
CREATE INDEX IF NOT EXISTS idx_credit_allocations_user_campaign
    ON credit.credit_allocations(user_id, campaign_id);

-- Index on account_id for account-level allocation queries
CREATE INDEX IF NOT EXISTS idx_credit_allocations_account_id
    ON credit.credit_allocations(account_id);

-- Index on status for filtering by allocation status
CREATE INDEX IF NOT EXISTS idx_credit_allocations_status
    ON credit.credit_allocations(status);

-- Index on transaction_id for linking to transactions
CREATE INDEX IF NOT EXISTS idx_credit_allocations_transaction_id
    ON credit.credit_allocations(transaction_id)
    WHERE transaction_id IS NOT NULL;

-- Composite index for expiring allocations queries (for FIFO consumption)
CREATE INDEX IF NOT EXISTS idx_credit_allocations_user_expires
    ON credit.credit_allocations(user_id, expires_at, status)
    WHERE expires_at IS NOT NULL AND status = 'completed';

-- ================================================================
-- Comments
-- ================================================================
COMMENT ON INDEX credit.idx_credit_accounts_user_id IS 'Lookup accounts by user';
COMMENT ON INDEX credit.idx_credit_accounts_user_type IS 'Unique account lookup by user and type';
COMMENT ON INDEX credit.idx_credit_transactions_user_id IS 'User transaction history';
COMMENT ON INDEX credit.idx_credit_transactions_expires_at IS 'Expiration processing';
COMMENT ON INDEX credit.idx_credit_campaigns_dates IS 'Active campaign date range queries';
COMMENT ON INDEX credit.idx_credit_allocations_user_campaign IS 'Per-user campaign allocation limits';
COMMENT ON INDEX credit.idx_credit_allocations_user_expires IS 'FIFO consumption order';
