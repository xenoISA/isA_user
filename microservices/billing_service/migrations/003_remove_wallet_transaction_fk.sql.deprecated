-- Migration: Remove wallet_transaction foreign key constraint from billing_records
-- Date: 2025-10-15
-- Purpose: Allow billing service to operate independently without database-level FK to wallet transactions

-- Remove FK constraint from billing_records for wallet_transaction_id
ALTER TABLE IF EXISTS dev.billing_records
DROP CONSTRAINT IF EXISTS fk_billing_record_wallet_transaction;

-- Remove FK constraint from billing_records for payment_transaction_id (if exists)
ALTER TABLE IF EXISTS dev.billing_records
DROP CONSTRAINT IF EXISTS fk_billing_record_payment_transaction;

-- Add indexes for performance (to replace FK indexes)
CREATE INDEX IF NOT EXISTS idx_billing_records_wallet_transaction_id
ON dev.billing_records(wallet_transaction_id);

CREATE INDEX IF NOT EXISTS idx_billing_records_payment_transaction_id
ON dev.billing_records(payment_transaction_id);

-- Add comment explaining the design decision
COMMENT ON COLUMN dev.billing_records.wallet_transaction_id IS
'References wallet_service.wallet_transactions via service client (no DB FK for microservice independence)';

COMMENT ON COLUMN dev.billing_records.payment_transaction_id IS
'References payment_service.payment_transactions via service client (no DB FK for microservice independence)';
