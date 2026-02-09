-- Order Service Migration: Add commerce fields for physical/digital fulfillment
-- Version: 003
-- Date: 2026-02-02
-- Description: Adds billing address, shipping amount, and subtotal to orders

ALTER TABLE orders.orders
    ADD COLUMN IF NOT EXISTS billing_address JSONB,
    ADD COLUMN IF NOT EXISTS shipping_amount DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS subtotal_amount DOUBLE PRECISION DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_orders_fulfillment_status ON orders.orders(fulfillment_status);
