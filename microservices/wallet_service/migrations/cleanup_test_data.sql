-- Cleanup test data for Wallet Service
-- Schema: wallet
-- Date: 2025-10-27

-- Delete test data in reverse order of dependencies
DELETE FROM wallet.transactions WHERE transaction_id LIKE 'tx_test_%';
DELETE FROM wallet.wallets WHERE wallet_id LIKE 'wallet_test_%';

-- Verify cleanup
SELECT 'Transactions remaining:', COUNT(*) FROM wallet.transactions;
SELECT 'Wallets remaining:', COUNT(*) FROM wallet.wallets;
