-- Credit Service Schema and Tables
-- Creates the credit schema and all core tables for credit management

-- Create schema
CREATE SCHEMA IF NOT EXISTS credit;

-- ================================================================
-- Table: credit_accounts
-- Purpose: Credit account storage per user per type
-- ================================================================
CREATE TABLE IF NOT EXISTS credit.credit_accounts (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),
    credit_type VARCHAR(30) NOT NULL,
    balance INTEGER DEFAULT 0,
    total_allocated INTEGER DEFAULT 0,
    total_consumed INTEGER DEFAULT 0,
    total_expired INTEGER DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'CREDIT',
    expiration_policy VARCHAR(30) DEFAULT 'fixed_days',
    expiration_days INTEGER DEFAULT 90,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, credit_type)
);

-- ================================================================
-- Table: credit_transactions
-- Purpose: Immutable transaction log for all credit operations
-- ================================================================
CREATE TABLE IF NOT EXISTS credit.credit_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    reference_id VARCHAR(100),
    reference_type VARCHAR(30),
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================================================
-- Table: credit_campaigns
-- Purpose: Promotional campaign definitions for credit allocations
-- ================================================================
CREATE TABLE IF NOT EXISTS credit.credit_campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    credit_type VARCHAR(30) NOT NULL,
    credit_amount INTEGER NOT NULL,
    total_budget INTEGER NOT NULL,
    allocated_amount INTEGER DEFAULT 0,
    eligibility_rules JSONB DEFAULT '{}'::jsonb,
    allocation_rules JSONB DEFAULT '{}'::jsonb,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expiration_days INTEGER DEFAULT 90,
    max_allocations_per_user INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================================================
-- Table: credit_allocations
-- Purpose: Campaign-to-user allocation tracking for auditing
-- ================================================================
CREATE TABLE IF NOT EXISTS credit.credit_allocations (
    id SERIAL PRIMARY KEY,
    allocation_id VARCHAR(50) UNIQUE NOT NULL,
    campaign_id VARCHAR(50),
    user_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(50),
    amount INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'completed',
    expires_at TIMESTAMP WITH TIME ZONE,
    expired_amount INTEGER DEFAULT 0,
    consumed_amount INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ================================================================
-- Triggers for updated_at columns
-- ================================================================

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION credit.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to credit_accounts
DROP TRIGGER IF EXISTS update_credit_accounts_updated_at ON credit.credit_accounts;
CREATE TRIGGER update_credit_accounts_updated_at
    BEFORE UPDATE ON credit.credit_accounts
    FOR EACH ROW
    EXECUTE FUNCTION credit.update_updated_at_column();

-- Apply trigger to credit_campaigns
DROP TRIGGER IF EXISTS update_credit_campaigns_updated_at ON credit.credit_campaigns;
CREATE TRIGGER update_credit_campaigns_updated_at
    BEFORE UPDATE ON credit.credit_campaigns
    FOR EACH ROW
    EXECUTE FUNCTION credit.update_updated_at_column();

-- Apply trigger to credit_allocations
DROP TRIGGER IF EXISTS update_credit_allocations_updated_at ON credit.credit_allocations;
CREATE TRIGGER update_credit_allocations_updated_at
    BEFORE UPDATE ON credit.credit_allocations
    FOR EACH ROW
    EXECUTE FUNCTION credit.update_updated_at_column();

-- ================================================================
-- Comments
-- ================================================================
COMMENT ON SCHEMA credit IS 'Credit service schema for managing user credits, campaigns, and allocations';
COMMENT ON TABLE credit.credit_accounts IS 'Credit accounts per user per credit type';
COMMENT ON TABLE credit.credit_transactions IS 'Immutable transaction log for credit operations';
COMMENT ON TABLE credit.credit_campaigns IS 'Promotional campaign definitions';
COMMENT ON TABLE credit.credit_allocations IS 'Allocation tracking for campaigns';
