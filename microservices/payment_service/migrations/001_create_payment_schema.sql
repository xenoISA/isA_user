-- Payment Service Migration: Create payment schema and tables
-- Version: 001
-- Date: 2025-10-27
-- Description: Core tables for payment processing, subscriptions, invoices, and refunds
-- Following PostgreSQL + gRPC migration guide

-- Create schema
CREATE SCHEMA IF NOT EXISTS payment;

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS payment.refunds CASCADE;
DROP TABLE IF EXISTS payment.invoices CASCADE;
DROP TABLE IF EXISTS payment.transactions CASCADE;
DROP TABLE IF EXISTS payment.subscriptions CASCADE;
DROP TABLE IF EXISTS payment.subscription_plans CASCADE;
DROP TABLE IF EXISTS payment.payment_methods CASCADE;

-- 1. Create subscription plans table
CREATE TABLE payment.subscription_plans (
    id SERIAL PRIMARY KEY,
    plan_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tier VARCHAR(50) NOT NULL, -- free, basic, pro, enterprise
    price_usd DOUBLE PRECISION NOT NULL,  -- Changed from DECIMAL to DOUBLE PRECISION
    currency VARCHAR(3) DEFAULT 'USD',
    billing_cycle VARCHAR(20) NOT NULL, -- monthly, quarterly, yearly, one_time
    features JSONB DEFAULT '{}'::jsonb,  -- Changed default from [] to {}
    credits_included INTEGER DEFAULT 0,
    max_users INTEGER,
    max_storage_gb INTEGER,
    trial_days INTEGER DEFAULT 0,
    stripe_price_id VARCHAR(255),
    stripe_product_id VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_public BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create payment methods table (no foreign key to users)
CREATE TABLE payment.payment_methods (
    id SERIAL PRIMARY KEY,
    method_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    method_type VARCHAR(50) NOT NULL, -- card, bank_account, paypal, crypto
    is_default BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,
    stripe_payment_method_id VARCHAR(255),
    card_last4 VARCHAR(4),
    card_brand VARCHAR(50),
    card_exp_month INTEGER,
    card_exp_year INTEGER,
    bank_name VARCHAR(255),
    bank_account_last4 VARCHAR(4),
    external_account_id VARCHAR(255),
    billing_details JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create subscriptions table
CREATE TABLE payment.subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint
    organization_id VARCHAR(255),    -- No FK constraint
    plan_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- active, trialing, past_due, canceled, incomplete
    tier VARCHAR(50) NOT NULL,
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    billing_cycle VARCHAR(20) NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT false,
    canceled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    payment_method_id VARCHAR(255),
    last_payment_date TIMESTAMPTZ,
    next_payment_date TIMESTAMPTZ,
    quantity INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_subscription_plan FOREIGN KEY (plan_id)
        REFERENCES payment.subscription_plans(plan_id) ON DELETE RESTRICT
    -- Removed FK to payment_methods - method_id may not exist when subscription is created
);

-- 4. Create payment transactions table
CREATE TABLE payment.transactions (
    id SERIAL PRIMARY KEY,
    payment_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint
    organization_id VARCHAR(255),
    subscription_id VARCHAR(255),
    invoice_id VARCHAR(255),
    amount DOUBLE PRECISION NOT NULL,  -- Changed from DECIMAL
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL, -- pending, processing, succeeded, failed, canceled, refunded, partial_refund
    payment_method VARCHAR(50), -- card, bank_account, paypal, stripe
    description TEXT,
    processor VARCHAR(50) DEFAULT 'stripe',
    processor_payment_id VARCHAR(255),
    processor_response JSONB DEFAULT '{}'::jsonb,
    failure_reason TEXT,
    failure_code VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    paid_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ

    -- Removed all FK constraints - cross-service references
);

-- 5. Create invoices table
CREATE TABLE payment.invoices (
    id SERIAL PRIMARY KEY,
    invoice_id VARCHAR(255) NOT NULL UNIQUE,
    invoice_number VARCHAR(100) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint
    organization_id VARCHAR(255),
    subscription_id VARCHAR(255),
    payment_intent_id VARCHAR(255),
    payment_method_id VARCHAR(255),
    status VARCHAR(50) NOT NULL, -- draft, open, paid, void, uncollectible
    amount_total DOUBLE PRECISION NOT NULL,  -- Changed from DECIMAL
    amount_paid DOUBLE PRECISION DEFAULT 0,
    amount_due DOUBLE PRECISION NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    description TEXT,
    billing_reason VARCHAR(100), -- subscription_create, subscription_cycle, manual
    billing_period_start TIMESTAMPTZ,
    billing_period_end TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    stripe_invoice_id VARCHAR(255),
    line_items JSONB DEFAULT '[]'::jsonb,  -- Array of line items
    tax_amount DOUBLE PRECISION DEFAULT 0,
    discount_amount DOUBLE PRECISION DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    paid_at TIMESTAMPTZ,
    voided_at TIMESTAMPTZ

    -- Removed all FK constraints
);

-- 6. Create refunds table
CREATE TABLE payment.refunds (
    id SERIAL PRIMARY KEY,
    refund_id VARCHAR(255) NOT NULL UNIQUE,
    payment_id VARCHAR(255) NOT NULL,  -- No FK constraint
    user_id VARCHAR(255) NOT NULL,      -- No FK constraint
    amount DOUBLE PRECISION NOT NULL,   -- Changed from DECIMAL
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL, -- pending, processing, succeeded, failed, canceled
    reason VARCHAR(255),
    description TEXT,
    processor VARCHAR(50) DEFAULT 'stripe',
    processor_refund_id VARCHAR(255),
    processor_response JSONB DEFAULT '{}'::jsonb,
    requested_by VARCHAR(255),
    approved_by VARCHAR(255),
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()

    -- Removed all FK constraints
);

-- Create indexes for performance
CREATE INDEX idx_payment_plans_tier ON payment.subscription_plans(tier);
CREATE INDEX idx_payment_plans_active ON payment.subscription_plans(is_active) WHERE is_active = true;

CREATE INDEX idx_payment_methods_user ON payment.payment_methods(user_id);
CREATE INDEX idx_payment_methods_default ON payment.payment_methods(user_id, is_default) WHERE is_default = true;

CREATE INDEX idx_subscriptions_user ON payment.subscriptions(user_id);
CREATE INDEX idx_subscriptions_org ON payment.subscriptions(organization_id);
CREATE INDEX idx_subscriptions_status ON payment.subscriptions(status);
CREATE INDEX idx_subscriptions_tier ON payment.subscriptions(tier);
CREATE INDEX idx_subscriptions_period_end ON payment.subscriptions(current_period_end);
CREATE INDEX idx_subscriptions_stripe ON payment.subscriptions(stripe_subscription_id);

CREATE INDEX idx_payments_user ON payment.transactions(user_id);
CREATE INDEX idx_payments_subscription ON payment.transactions(subscription_id);
CREATE INDEX idx_payments_status ON payment.transactions(status);
CREATE INDEX idx_payments_created ON payment.transactions(created_at DESC);
CREATE INDEX idx_payments_stripe_intent ON payment.transactions(processor_payment_id);
CREATE INDEX idx_payments_organization ON payment.transactions(organization_id);

CREATE INDEX idx_invoices_user ON payment.invoices(user_id);
CREATE INDEX idx_invoices_subscription ON payment.invoices(subscription_id);
CREATE INDEX idx_invoices_status ON payment.invoices(status);
CREATE INDEX idx_invoices_due_date ON payment.invoices(due_date);
CREATE INDEX idx_invoices_number ON payment.invoices(invoice_number);
CREATE INDEX idx_invoices_organization ON payment.invoices(organization_id);

CREATE INDEX idx_refunds_payment ON payment.refunds(payment_id);
CREATE INDEX idx_refunds_user ON payment.refunds(user_id);
CREATE INDEX idx_refunds_status ON payment.refunds(status);
CREATE INDEX idx_refunds_requested_at ON payment.refunds(requested_at DESC);

-- Add comments
COMMENT ON SCHEMA payment IS 'Payment service schema - subscriptions, transactions, invoices, and refunds';
COMMENT ON TABLE payment.subscription_plans IS 'Subscription plan definitions and pricing';
COMMENT ON TABLE payment.payment_methods IS 'User payment methods for recurring billing';
COMMENT ON TABLE payment.subscriptions IS 'Active and historical user subscriptions';
COMMENT ON TABLE payment.transactions IS 'All payment transactions including one-time and recurring';
COMMENT ON TABLE payment.invoices IS 'Invoices for subscriptions and purchases';
COMMENT ON TABLE payment.refunds IS 'Payment refund records';
