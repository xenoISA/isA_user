-- Wallet Service Migration: Add credit accounts and transactions
-- Version: 002
-- Date: 2025-11-28
-- Description: Add credit_accounts and credit_transactions tables for the credit-based billing system
-- Reference: /docs/design/billing-credit-subscription-design.md

-- ====================
-- Credit Accounts Table
-- ====================
-- Stores purchased credits (never expires) and bonus credits (may have expiration)

CREATE TABLE IF NOT EXISTS wallet.credit_accounts (
    id SERIAL PRIMARY KEY,
    credit_account_id VARCHAR(100) UNIQUE NOT NULL,

    -- Owner Information (no FK constraints - cross-service reference)
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    wallet_id VARCHAR(100),                  -- Reference to wallet.wallets

    -- Credit Type
    credit_type VARCHAR(50) NOT NULL,        -- purchased, bonus, referral, promotional

    -- Balance (in credits - 1 Credit = $0.00001 USD)
    balance BIGINT NOT NULL DEFAULT 0,       -- Current balance
    total_credited BIGINT NOT NULL DEFAULT 0, -- Total credits ever added
    total_consumed BIGINT NOT NULL DEFAULT 0, -- Total credits ever consumed

    -- Expiration (for bonus/promotional credits)
    expires_at TIMESTAMPTZ,                  -- NULL = never expires (purchased credits)
    is_expired BOOLEAN DEFAULT FALSE,

    -- Purchase Information (for purchased credits)
    purchase_amount_usd DOUBLE PRECISION,    -- USD amount paid
    payment_transaction_id VARCHAR(100),     -- Reference to payment transaction

    -- Priority (lower = consumed first)
    consumption_priority INTEGER DEFAULT 100, -- Purchased = 100, Bonus = 200, Promotional = 300

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Metadata
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT credit_balance_non_negative CHECK (balance >= 0)
);

-- ====================
-- Credit Transactions Table
-- ====================
-- Audit trail for all credit operations

CREATE TABLE IF NOT EXISTS wallet.credit_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) UNIQUE NOT NULL,

    -- Account Reference
    credit_account_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),

    -- Transaction Type
    transaction_type VARCHAR(50) NOT NULL,   -- credit_purchase, credit_consume, credit_refund, credit_expire, credit_transfer, credit_bonus

    -- Amount
    credits_amount BIGINT NOT NULL,          -- Positive for additions, negative for deductions
    balance_before BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,

    -- USD Equivalent (for reference)
    usd_equivalent DOUBLE PRECISION,         -- $0.00001 * credits_amount

    -- Reference
    reference_type VARCHAR(100),             -- subscription, usage, purchase, refund, bonus, etc.
    reference_id VARCHAR(255),               -- ID of related entity

    -- Usage Details (for credit_consume)
    service_type VARCHAR(50),                -- model_inference, storage_minio, mcp_service, etc.
    usage_record_id VARCHAR(100),

    -- Source (for credit_purchase)
    payment_method VARCHAR(50),              -- credit_card, bank_transfer, etc.
    payment_transaction_id VARCHAR(100),

    -- Description
    description TEXT,

    -- Status
    status VARCHAR(50) DEFAULT 'completed',  -- pending, completed, failed, reversed

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- ====================
-- Indexes
-- ====================

-- Credit accounts indexes
CREATE INDEX IF NOT EXISTS idx_credit_accounts_id ON wallet.credit_accounts(credit_account_id);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_user ON wallet.credit_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_org ON wallet.credit_accounts(organization_id);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_wallet ON wallet.credit_accounts(wallet_id);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_type ON wallet.credit_accounts(credit_type);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_active ON wallet.credit_accounts(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_credit_accounts_expires ON wallet.credit_accounts(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_credit_accounts_priority ON wallet.credit_accounts(consumption_priority);

-- Composite indexes
CREATE INDEX IF NOT EXISTS idx_credit_accounts_user_active ON wallet.credit_accounts(user_id, is_active, consumption_priority);
CREATE INDEX IF NOT EXISTS idx_credit_accounts_user_type ON wallet.credit_accounts(user_id, credit_type);

-- Credit transactions indexes
CREATE INDEX IF NOT EXISTS idx_credit_txn_id ON wallet.credit_transactions(transaction_id);
CREATE INDEX IF NOT EXISTS idx_credit_txn_account ON wallet.credit_transactions(credit_account_id);
CREATE INDEX IF NOT EXISTS idx_credit_txn_user ON wallet.credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_txn_type ON wallet.credit_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_credit_txn_created ON wallet.credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_txn_reference ON wallet.credit_transactions(reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_credit_txn_service ON wallet.credit_transactions(service_type);

-- Composite indexes
CREATE INDEX IF NOT EXISTS idx_credit_txn_user_created ON wallet.credit_transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_txn_account_created ON wallet.credit_transactions(credit_account_id, created_at DESC);

-- ====================
-- Update Triggers
-- ====================

CREATE TRIGGER update_credit_accounts_updated_at
    BEFORE UPDATE ON wallet.credit_accounts
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ====================
-- Comments
-- ====================

COMMENT ON TABLE wallet.credit_accounts IS 'Credit accounts for purchased, bonus, and promotional credits';
COMMENT ON TABLE wallet.credit_transactions IS 'Transaction history for all credit operations';

COMMENT ON COLUMN wallet.credit_accounts.credit_type IS 'purchased = never expires, bonus/referral/promotional = may expire';
COMMENT ON COLUMN wallet.credit_accounts.consumption_priority IS 'Lower value = consumed first. Purchased=100, Bonus=200, Promotional=300';
COMMENT ON COLUMN wallet.credit_accounts.balance IS 'Balance in credits (1 Credit = $0.00001 USD)';

COMMENT ON COLUMN wallet.credit_transactions.credits_amount IS 'Amount in credits. Positive=addition, Negative=deduction';
COMMENT ON COLUMN wallet.credit_transactions.usd_equivalent IS 'USD value = credits_amount * 0.00001';
