-- Seed test data for Wallet Service
-- Standardized test data following test_data_standard.md
-- Date: 2025-11-11

-- Insert test wallets
INSERT INTO wallet.wallets (
    wallet_id, user_id, organization_id, balance, locked_balance,
    currency, wallet_type, metadata, is_active
) VALUES
    ('test_wallet_001', 'test_user_001', NULL, 1000.00, 0.00, 'USD', 'credits', '{}'::jsonb, true),
    ('test_wallet_002', 'test_user_002', NULL, 500.00, 50.00, 'USD', 'fiat', '{}'::jsonb, true),
    ('test_wallet_003', 'test_user_001', 'test_org_001', 2000.00, 0.00, 'USD', 'credits', '{"organization_wallet": true}'::jsonb, true)
ON CONFLICT (wallet_id) DO NOTHING;

-- Insert test transactions
INSERT INTO wallet.transactions (
    transaction_id, wallet_id, user_id, transaction_type, amount,
    balance_before, balance_after, currency, status, description, metadata
) VALUES
    ('test_tx_001', 'test_wallet_001', 'test_user_001', 'deposit', 1000.00,
     0.00, 1000.00, 'USD', 'completed', 'Initial wallet funding', '{"initial_funding": true}'::jsonb),
    ('test_tx_002', 'test_wallet_001', 'test_user_001', 'withdraw', 100.00,
     1000.00, 900.00, 'USD', 'completed', 'Test withdrawal', '{}'::jsonb),
    ('test_tx_003', 'test_wallet_002', 'test_user_002', 'deposit', 550.00,
     0.00, 550.00, 'USD', 'completed', 'Initial deposit', '{}'::jsonb),
    ('test_tx_004', 'test_wallet_002', 'test_user_002', 'consume', 50.00,
     550.00, 500.00, 'USD', 'completed', 'API usage', '{"api_calls": 1000}'::jsonb)
ON CONFLICT (transaction_id) DO NOTHING;

-- Verify data was inserted
SELECT 'Wallets:', COUNT(*) FROM wallet.wallets;
SELECT 'Transactions:', COUNT(*) FROM wallet.transactions;
