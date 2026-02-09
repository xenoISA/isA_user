-- Payment Service Migration: Add order reference and amount breakdown
-- Version: 002
-- Date: 2026-02-02
-- Description: Adds order_id and amount breakdown columns to payment transactions

ALTER TABLE payment.transactions
    ADD COLUMN IF NOT EXISTS order_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS subtotal_amount DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tax_amount DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS shipping_amount DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS discount_amount DOUBLE PRECISION DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payment.transactions(order_id);
