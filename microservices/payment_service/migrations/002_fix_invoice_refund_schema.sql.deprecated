-- Payment Service Migration: Fix invoice and refund table schemas
-- Version: 002
-- Date: 2025-01-20
-- Description: Add missing columns and fix schema mismatches for invoices and refunds

-- ========================================
-- Fix payment_invoices table
-- ========================================

-- Add missing columns to payment_invoices
ALTER TABLE dev.payment_invoices
    ADD COLUMN IF NOT EXISTS organization_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS amount_total DECIMAL(10, 2);

-- Update existing data: copy amount_due to amount_total if amount_total is null
UPDATE dev.payment_invoices
SET amount_total = amount_due
WHERE amount_total IS NULL;

-- Rename columns to match repository expectations
ALTER TABLE dev.payment_invoices
    RENAME COLUMN period_start TO billing_period_start;

ALTER TABLE dev.payment_invoices
    RENAME COLUMN period_end TO billing_period_end;

-- Add payment_method_id and payment_intent_id if missing
ALTER TABLE dev.payment_invoices
    ADD COLUMN IF NOT EXISTS payment_method_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS payment_intent_id VARCHAR(255);

-- ========================================
-- Fix payment_refunds table
-- ========================================

-- Add missing columns to payment_refunds
ALTER TABLE dev.payment_refunds
    ADD COLUMN IF NOT EXISTS processor VARCHAR(50) DEFAULT 'stripe',
    ADD COLUMN IF NOT EXISTS processor_refund_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS processor_response JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS requested_by VARCHAR(255),
    ADD COLUMN IF NOT EXISTS approved_by VARCHAR(255),
    ADD COLUMN IF NOT EXISTS requested_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Update existing refunds: set requested_at to created_at if null
UPDATE dev.payment_refunds
SET requested_at = created_at
WHERE requested_at IS NULL;

-- Rename stripe_refund_id to processor_refund_id for consistency
-- First, copy data if processor_refund_id doesn't exist
UPDATE dev.payment_refunds
SET processor_refund_id = stripe_refund_id
WHERE processor_refund_id IS NULL AND stripe_refund_id IS NOT NULL;

-- ========================================
-- Fix payment_transactions table
-- ========================================

-- Add missing columns to payment_transactions
ALTER TABLE dev.payment_transactions
    ADD COLUMN IF NOT EXISTS organization_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS processor VARCHAR(50) DEFAULT 'stripe',
    ADD COLUMN IF NOT EXISTS processor_payment_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS processor_response JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ;

-- Copy stripe_payment_intent_id to processor_payment_id
UPDATE dev.payment_transactions
SET processor_payment_id = stripe_payment_intent_id
WHERE processor_payment_id IS NULL AND stripe_payment_intent_id IS NOT NULL;

-- ========================================
-- Fix payment_subscriptions table
-- ========================================

-- Add missing columns for better tracking
ALTER TABLE dev.payment_subscriptions
    ADD COLUMN IF NOT EXISTS tier VARCHAR(50) DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS billing_cycle VARCHAR(20) DEFAULT 'monthly',
    ADD COLUMN IF NOT EXISTS last_payment_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS next_payment_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;

-- Update tier based on plan_id
UPDATE dev.payment_subscriptions
SET tier = CASE
    WHEN plan_id LIKE '%enterprise%' THEN 'enterprise'
    WHEN plan_id LIKE '%pro%' THEN 'pro'
    WHEN plan_id LIKE '%basic%' THEN 'basic'
    ELSE 'free'
END
WHERE tier = 'free';

-- ========================================
-- Add indexes for new columns
-- ========================================

CREATE INDEX IF NOT EXISTS idx_invoices_organization ON dev.payment_invoices(organization_id);
CREATE INDEX IF NOT EXISTS idx_invoices_payment_intent ON dev.payment_invoices(payment_intent_id);

CREATE INDEX IF NOT EXISTS idx_refunds_processor ON dev.payment_refunds(processor);
CREATE INDEX IF NOT EXISTS idx_refunds_requested_at ON dev.payment_refunds(requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_payments_organization ON dev.payment_transactions(organization_id);
CREATE INDEX IF NOT EXISTS idx_payments_processor ON dev.payment_transactions(processor);

CREATE INDEX IF NOT EXISTS idx_subscriptions_tier ON dev.payment_subscriptions(tier);
CREATE INDEX IF NOT EXISTS idx_subscriptions_billing_cycle ON dev.payment_subscriptions(billing_cycle);

-- ========================================
-- Update comments
-- ========================================

COMMENT ON COLUMN dev.payment_invoices.amount_total IS 'Total invoice amount before any adjustments';
COMMENT ON COLUMN dev.payment_invoices.organization_id IS 'Organization owning this invoice (if applicable)';
COMMENT ON COLUMN dev.payment_refunds.processor IS 'Payment processor handling the refund (stripe, paypal, etc)';
COMMENT ON COLUMN dev.payment_refunds.requested_by IS 'User ID who requested the refund';
COMMENT ON COLUMN dev.payment_refunds.approved_by IS 'Admin/User ID who approved the refund';
