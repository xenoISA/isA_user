-- Wallet Service Migration: Create wallet and transaction tables
-- Version: 001
-- Date: 2025-01-20
-- Description: Core tables for wallet management and transaction tracking

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS dev.wallet_transactions CASCADE;
DROP TABLE IF EXISTS dev.wallets CASCADE;

-- Create wallets table
CREATE TABLE dev.wallets (
    id SERIAL PRIMARY KEY,
    wallet_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    balance DECIMAL(20, 8) NOT NULL DEFAULT 0,
    locked_balance DECIMAL(20, 8) NOT NULL DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'USD',
    wallet_type VARCHAR(50) NOT NULL DEFAULT 'credits', -- credits, fiat, crypto, points
    blockchain_address VARCHAR(255),
    blockchain_network VARCHAR(50), -- ethereum, polygon, solana, etc.
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_wallet_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT balance_non_negative CHECK (balance >= 0),
    CONSTRAINT locked_balance_non_negative CHECK (locked_balance >= 0)
);

-- Create wallet transactions table
CREATE TABLE dev.wallet_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(255) NOT NULL UNIQUE,
    wallet_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL, -- deposit, withdrawal, purchase, refund, transfer, adjustment
    amount DECIMAL(20, 8) NOT NULL,
    balance_before DECIMAL(20, 8) NOT NULL,
    balance_after DECIMAL(20, 8) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'completed', -- pending, processing, completed, failed, cancelled
    reference_type VARCHAR(100), -- order, payment, transfer, refund, etc.
    reference_id VARCHAR(255), -- ID of related entity
    description TEXT,
    from_wallet_id VARCHAR(255),
    to_wallet_id VARCHAR(255),
    blockchain_txn_hash VARCHAR(255),
    blockchain_confirmation_count INTEGER DEFAULT 0,
    fee_amount DECIMAL(20, 8) DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    
    CONSTRAINT fk_transaction_wallet FOREIGN KEY (wallet_id) 
        REFERENCES dev.wallets(wallet_id) ON DELETE CASCADE,
    CONSTRAINT fk_transaction_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_transaction_from_wallet FOREIGN KEY (from_wallet_id)
        REFERENCES dev.wallets(wallet_id) ON DELETE SET NULL,
    CONSTRAINT fk_transaction_to_wallet FOREIGN KEY (to_wallet_id)
        REFERENCES dev.wallets(wallet_id) ON DELETE SET NULL
);

-- Create indexes for performance
CREATE INDEX idx_wallets_user_id ON dev.wallets(user_id);
CREATE INDEX idx_wallets_type ON dev.wallets(wallet_type);
CREATE INDEX idx_wallets_currency ON dev.wallets(currency);
CREATE INDEX idx_wallets_active ON dev.wallets(is_active) WHERE is_active = true;
CREATE INDEX idx_wallets_blockchain ON dev.wallets(blockchain_address) WHERE blockchain_address IS NOT NULL;

CREATE INDEX idx_transactions_wallet_id ON dev.wallet_transactions(wallet_id);
CREATE INDEX idx_transactions_user_id ON dev.wallet_transactions(user_id);
CREATE INDEX idx_transactions_type ON dev.wallet_transactions(transaction_type);
CREATE INDEX idx_transactions_status ON dev.wallet_transactions(status);
CREATE INDEX idx_transactions_created_at ON dev.wallet_transactions(created_at DESC);
CREATE INDEX idx_transactions_reference ON dev.wallet_transactions(reference_type, reference_id);
CREATE INDEX idx_transactions_from_wallet ON dev.wallet_transactions(from_wallet_id);
CREATE INDEX idx_transactions_to_wallet ON dev.wallet_transactions(to_wallet_id);
CREATE INDEX idx_transactions_blockchain ON dev.wallet_transactions(blockchain_txn_hash) WHERE blockchain_txn_hash IS NOT NULL;

-- Create composite indexes for common queries
CREATE INDEX idx_wallets_user_type ON dev.wallets(user_id, wallet_type);
CREATE INDEX idx_transactions_wallet_created ON dev.wallet_transactions(wallet_id, created_at DESC);
CREATE INDEX idx_transactions_user_created ON dev.wallet_transactions(user_id, created_at DESC);

-- Create update triggers
CREATE TRIGGER trigger_update_wallets_updated_at
    BEFORE UPDATE ON dev.wallets
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_transactions_updated_at
    BEFORE UPDATE ON dev.wallet_transactions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.wallets TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.wallets TO authenticated;
GRANT ALL ON SEQUENCE dev.wallets_id_seq TO authenticated;

GRANT ALL ON dev.wallet_transactions TO postgres;
GRANT SELECT, INSERT ON dev.wallet_transactions TO authenticated;
GRANT ALL ON SEQUENCE dev.wallet_transactions_id_seq TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE dev.wallets IS 'User wallet balances for credits, fiat, crypto, and points';
COMMENT ON TABLE dev.wallet_transactions IS 'Transaction history for all wallet operations';

COMMENT ON COLUMN dev.wallets.wallet_id IS 'Unique wallet identifier';
COMMENT ON COLUMN dev.wallets.balance IS 'Available balance in wallet';
COMMENT ON COLUMN dev.wallets.locked_balance IS 'Balance locked for pending transactions';
COMMENT ON COLUMN dev.wallets.wallet_type IS 'Type of wallet: credits, fiat, crypto, points';
COMMENT ON COLUMN dev.wallets.blockchain_address IS 'Blockchain address for crypto wallets';
COMMENT ON COLUMN dev.wallets.blockchain_network IS 'Blockchain network for crypto wallets';

COMMENT ON COLUMN dev.wallet_transactions.transaction_id IS 'Unique transaction identifier';
COMMENT ON COLUMN dev.wallet_transactions.transaction_type IS 'Type of transaction';
COMMENT ON COLUMN dev.wallet_transactions.amount IS 'Transaction amount';
COMMENT ON COLUMN dev.wallet_transactions.balance_before IS 'Wallet balance before transaction';
COMMENT ON COLUMN dev.wallet_transactions.balance_after IS 'Wallet balance after transaction';
COMMENT ON COLUMN dev.wallet_transactions.reference_type IS 'Type of related entity';
COMMENT ON COLUMN dev.wallet_transactions.reference_id IS 'ID of related entity';
COMMENT ON COLUMN dev.wallet_transactions.blockchain_txn_hash IS 'Blockchain transaction hash for crypto transactions';
COMMENT ON COLUMN dev.wallet_transactions.fee_amount IS 'Transaction fee amount';