-- Migration: Extend currency column to support TOKEN and other longer currency codes
-- Date: 2024-12-03

-- Extend currency column from VARCHAR(3) to VARCHAR(10) to support TOKEN
ALTER TABLE orders.orders
ALTER COLUMN currency TYPE VARCHAR(10);

-- Update comment
COMMENT ON COLUMN orders.orders.currency IS 'Currency code: USD, EUR, TOKEN, etc.';
