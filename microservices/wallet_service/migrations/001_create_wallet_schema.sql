-- Wallet Service Migration: Create wallet schema and tables
-- Version: 001
-- Date: 2025-10-27
-- Description: Core tables for wallet management and transaction tracking
-- Following PostgreSQL + gRPC migration guide

-- Create schema
CREATE SCHEMA IF NOT EXISTS wallet;

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS wallet.transactions CASCADE;
DROP TABLE IF EXISTS wallet.wallets CASCADE;

-- Create wallets table
CREATE TABLE wallet.wallets (
    id SERIAL PRIMARY KEY,
    wallet_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    organization_id VARCHAR(255),    -- No FK constraint
    balance DOUBLE PRECISION NOT NULL DEFAULT 0,  -- Changed from DECIMAL
    locked_balance DOUBLE PRECISION NOT NULL DEFAULT 0,  -- Changed from DECIMAL
    currency VARCHAR(10) DEFAULT 'USD',
    wallet_type VARCHAR(50) NOT NULL DEFAULT 'credits', -- credits, fiat, crypto, points
    blockchain_address VARCHAR(255),
    blockchain_network VARCHAR(50), -- ethereum, polygon, solana, etc.
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT balance_non_negative CHECK (balance >= 0),
    CONSTRAINT locked_balance_non_negative CHECK (locked_balance >= 0)
);

-- Create wallet transactions table
CREATE TABLE wallet.transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(255) NOT NULL UNIQUE,
    wallet_id VARCHAR(255) NOT NULL,  -- No FK to wallets - use application-level reference
    user_id VARCHAR(255) NOT NULL,    -- No FK constraint
    transaction_type VARCHAR(50) NOT NULL, -- deposit, withdrawal, purchase, refund, transfer, adjustment, reward
    amount DOUBLE PRECISION NOT NULL,  -- Changed from DECIMAL
    balance_before DOUBLE PRECISION NOT NULL,  -- Changed from DECIMAL
    balance_after DOUBLE PRECISION NOT NULL,   -- Changed from DECIMAL
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'completed', -- pending, processing, completed, failed, cancelled
    reference_type VARCHAR(100), -- order, payment, transfer, refund, subscription, etc.
    reference_id VARCHAR(255), -- ID of related entity
    description TEXT,
    from_wallet_id VARCHAR(255),  -- No FK constraint
    to_wallet_id VARCHAR(255),    -- No FK constraint
    blockchain_txn_hash VARCHAR(255),
    blockchain_confirmation_count INTEGER DEFAULT 0,
    fee_amount DOUBLE PRECISION DEFAULT 0,  -- Changed from DECIMAL
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    failure_reason TEXT
);

-- Create indexes for performance
CREATE INDEX idx_wallets_user_id ON wallet.wallets(user_id);
CREATE INDEX idx_wallets_organization ON wallet.wallets(organization_id);
CREATE INDEX idx_wallets_type ON wallet.wallets(wallet_type);
CREATE INDEX idx_wallets_currency ON wallet.wallets(currency);
CREATE INDEX idx_wallets_active ON wallet.wallets(is_active) WHERE is_active = true;
CREATE INDEX idx_wallets_blockchain ON wallet.wallets(blockchain_address) WHERE blockchain_address IS NOT NULL;

CREATE INDEX idx_transactions_wallet_id ON wallet.transactions(wallet_id);
CREATE INDEX idx_transactions_user_id ON wallet.transactions(user_id);
CREATE INDEX idx_transactions_type ON wallet.transactions(transaction_type);
CREATE INDEX idx_transactions_status ON wallet.transactions(status);
CREATE INDEX idx_transactions_created_at ON wallet.transactions(created_at DESC);
CREATE INDEX idx_transactions_reference ON wallet.transactions(reference_type, reference_id);
CREATE INDEX idx_transactions_from_wallet ON wallet.transactions(from_wallet_id);
CREATE INDEX idx_transactions_to_wallet ON wallet.transactions(to_wallet_id);
CREATE INDEX idx_transactions_blockchain ON wallet.transactions(blockchain_txn_hash) WHERE blockchain_txn_hash IS NOT NULL;

-- Create composite indexes for common queries
CREATE INDEX idx_wallets_user_type ON wallet.wallets(user_id, wallet_type);
CREATE INDEX idx_transactions_wallet_created ON wallet.transactions(wallet_id, created_at DESC);
CREATE INDEX idx_transactions_user_created ON wallet.transactions(user_id, created_at DESC);

-- Add comments
COMMENT ON SCHEMA wallet IS 'Wallet service schema - digital wallets and transactions';
COMMENT ON TABLE wallet.wallets IS 'User digital wallets for credits, fiat, crypto, and points';
COMMENT ON TABLE wallet.transactions IS 'Wallet transaction history and ledger';
