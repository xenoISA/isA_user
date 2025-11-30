-- Cleanup test data for Wallet Service
-- Schema: wallet
-- Date: 2025-10-27

-- Delete test data in reverse order of dependencies
-- Matches seed_test_data.sql pattern: test_tx_XXX, test_wallet_XXX
DELETE FROM wallet.transactions WHERE transaction_id LIKE 'test_tx_%';
DELETE FROM wallet.wallets WHERE wallet_id LIKE 'test_wallet_%';

-- Verify cleanup
SELECT 'Transactions remaining:', COUNT(*) FROM wallet.transactions;
SELECT 'Wallets remaining:', COUNT(*) FROM wallet.wallets;
