-- Payment Service Migration: Create payment-related tables
-- Version: 001
-- Date: 2025-01-20
-- Description: Core tables for payment processing, subscriptions, invoices, and refunds

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS dev.payment_refunds CASCADE;
DROP TABLE IF EXISTS dev.payment_invoices CASCADE;
DROP TABLE IF EXISTS dev.payment_transactions CASCADE;
DROP TABLE IF EXISTS dev.payment_subscriptions CASCADE;
DROP TABLE IF EXISTS dev.payment_subscription_plans CASCADE;
DROP TABLE IF EXISTS dev.payment_methods CASCADE;

-- 1. Create subscription plans table
CREATE TABLE dev.payment_subscription_plans (
    id SERIAL PRIMARY KEY,
    plan_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tier VARCHAR(50) NOT NULL, -- free, basic, pro, enterprise
    price_usd DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    billing_cycle VARCHAR(20) NOT NULL, -- monthly, yearly
    features JSONB DEFAULT '[]'::jsonb,
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

-- 2. Create payment methods table
CREATE TABLE dev.payment_methods (
    id SERIAL PRIMARY KEY,
    method_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- card, bank_account, paypal, crypto
    is_default BOOLEAN DEFAULT false,
    stripe_payment_method_id VARCHAR(255),
    card_last4 VARCHAR(4),
    card_brand VARCHAR(50),
    card_exp_month INTEGER,
    card_exp_year INTEGER,
    billing_details JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_payment_method_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE
);

-- 3. Create subscriptions table
CREATE TABLE dev.payment_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    plan_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- active, paused, cancelled, expired
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    cancel_at_period_end BOOLEAN DEFAULT false,
    cancelled_at TIMESTAMPTZ,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    payment_method_id VARCHAR(255),
    quantity INTEGER DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_subscription_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_subscription_plan FOREIGN KEY (plan_id) 
        REFERENCES dev.payment_subscription_plans(plan_id) ON DELETE RESTRICT,
    CONSTRAINT fk_subscription_payment_method FOREIGN KEY (payment_method_id)
        REFERENCES dev.payment_methods(method_id) ON DELETE SET NULL
);

-- 4. Create payment transactions table
CREATE TABLE dev.payment_transactions (
    id SERIAL PRIMARY KEY,
    payment_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    subscription_id VARCHAR(255),
    order_id VARCHAR(255),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL, -- pending, processing, succeeded, failed, cancelled
    payment_method VARCHAR(50), -- card, bank_transfer, paypal, crypto
    payment_method_id VARCHAR(255),
    description TEXT,
    stripe_payment_intent_id VARCHAR(255),
    stripe_charge_id VARCHAR(255),
    failure_reason TEXT,
    failure_code VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT fk_payment_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_payment_subscription FOREIGN KEY (subscription_id)
        REFERENCES dev.payment_subscriptions(subscription_id) ON DELETE SET NULL,
    CONSTRAINT fk_payment_order FOREIGN KEY (order_id)
        REFERENCES dev.orders(order_id) ON DELETE SET NULL,
    CONSTRAINT fk_payment_method_ref FOREIGN KEY (payment_method_id)
        REFERENCES dev.payment_methods(method_id) ON DELETE SET NULL
);

-- 5. Create invoices table
CREATE TABLE dev.payment_invoices (
    id SERIAL PRIMARY KEY,
    invoice_id VARCHAR(255) NOT NULL UNIQUE,
    invoice_number VARCHAR(100) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    subscription_id VARCHAR(255),
    payment_id VARCHAR(255),
    status VARCHAR(50) NOT NULL, -- draft, open, paid, void, uncollectible
    amount_due DECIMAL(10, 2) NOT NULL,
    amount_paid DECIMAL(10, 2) DEFAULT 0,
    amount_remaining DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    description TEXT,
    billing_reason VARCHAR(100), -- subscription_create, subscription_cycle, manual
    due_date DATE,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    stripe_invoice_id VARCHAR(255),
    line_items JSONB DEFAULT '[]'::jsonb,
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    paid_at TIMESTAMPTZ,
    voided_at TIMESTAMPTZ,
    
    CONSTRAINT fk_invoice_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_invoice_subscription FOREIGN KEY (subscription_id)
        REFERENCES dev.payment_subscriptions(subscription_id) ON DELETE SET NULL,
    CONSTRAINT fk_invoice_payment FOREIGN KEY (payment_id)
        REFERENCES dev.payment_transactions(payment_id) ON DELETE SET NULL
);

-- 6. Create refunds table
CREATE TABLE dev.payment_refunds (
    id SERIAL PRIMARY KEY,
    refund_id VARCHAR(255) NOT NULL UNIQUE,
    payment_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL, -- pending, processing, succeeded, failed, cancelled
    reason VARCHAR(255),
    description TEXT,
    stripe_refund_id VARCHAR(255),
    failure_reason TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    
    CONSTRAINT fk_refund_payment FOREIGN KEY (payment_id) 
        REFERENCES dev.payment_transactions(payment_id) ON DELETE CASCADE,
    CONSTRAINT fk_refund_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_payment_plans_tier ON dev.payment_subscription_plans(tier);
CREATE INDEX idx_payment_plans_active ON dev.payment_subscription_plans(is_active) WHERE is_active = true;

CREATE INDEX idx_payment_methods_user ON dev.payment_methods(user_id);
CREATE INDEX idx_payment_methods_default ON dev.payment_methods(user_id, is_default) WHERE is_default = true;

CREATE INDEX idx_subscriptions_user ON dev.payment_subscriptions(user_id);
CREATE INDEX idx_subscriptions_org ON dev.payment_subscriptions(organization_id);
CREATE INDEX idx_subscriptions_status ON dev.payment_subscriptions(status);
CREATE INDEX idx_subscriptions_period_end ON dev.payment_subscriptions(current_period_end);
CREATE INDEX idx_subscriptions_stripe ON dev.payment_subscriptions(stripe_subscription_id);

CREATE INDEX idx_payments_user ON dev.payment_transactions(user_id);
CREATE INDEX idx_payments_subscription ON dev.payment_transactions(subscription_id);
CREATE INDEX idx_payments_order ON dev.payment_transactions(order_id);
CREATE INDEX idx_payments_status ON dev.payment_transactions(status);
CREATE INDEX idx_payments_created ON dev.payment_transactions(created_at DESC);
CREATE INDEX idx_payments_stripe_intent ON dev.payment_transactions(stripe_payment_intent_id);

CREATE INDEX idx_invoices_user ON dev.payment_invoices(user_id);
CREATE INDEX idx_invoices_subscription ON dev.payment_invoices(subscription_id);
CREATE INDEX idx_invoices_status ON dev.payment_invoices(status);
CREATE INDEX idx_invoices_due_date ON dev.payment_invoices(due_date);
CREATE INDEX idx_invoices_number ON dev.payment_invoices(invoice_number);

CREATE INDEX idx_refunds_payment ON dev.payment_refunds(payment_id);
CREATE INDEX idx_refunds_user ON dev.payment_refunds(user_id);
CREATE INDEX idx_refunds_status ON dev.payment_refunds(status);

-- Create update triggers
CREATE TRIGGER trigger_update_payment_plans_updated_at
    BEFORE UPDATE ON dev.payment_subscription_plans
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_payment_methods_updated_at
    BEFORE UPDATE ON dev.payment_methods
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_subscriptions_updated_at
    BEFORE UPDATE ON dev.payment_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_payments_updated_at
    BEFORE UPDATE ON dev.payment_transactions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_invoices_updated_at
    BEFORE UPDATE ON dev.payment_invoices
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_refunds_updated_at
    BEFORE UPDATE ON dev.payment_refunds
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.payment_subscription_plans TO postgres;
GRANT SELECT ON dev.payment_subscription_plans TO authenticated;
GRANT ALL ON SEQUENCE dev.payment_subscription_plans_id_seq TO authenticated;

GRANT ALL ON dev.payment_methods TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.payment_methods TO authenticated;
GRANT ALL ON SEQUENCE dev.payment_methods_id_seq TO authenticated;

GRANT ALL ON dev.payment_subscriptions TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.payment_subscriptions TO authenticated;
GRANT ALL ON SEQUENCE dev.payment_subscriptions_id_seq TO authenticated;

GRANT ALL ON dev.payment_transactions TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.payment_transactions TO authenticated;
GRANT ALL ON SEQUENCE dev.payment_transactions_id_seq TO authenticated;

GRANT ALL ON dev.payment_invoices TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.payment_invoices TO authenticated;
GRANT ALL ON SEQUENCE dev.payment_invoices_id_seq TO authenticated;

GRANT ALL ON dev.payment_refunds TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.payment_refunds TO authenticated;
GRANT ALL ON SEQUENCE dev.payment_refunds_id_seq TO authenticated;

-- Add comments
COMMENT ON TABLE dev.payment_subscription_plans IS 'Subscription plan definitions and pricing';
COMMENT ON TABLE dev.payment_methods IS 'User payment methods for recurring billing';
COMMENT ON TABLE dev.payment_subscriptions IS 'Active and historical user subscriptions';
COMMENT ON TABLE dev.payment_transactions IS 'All payment transactions including one-time and recurring';
COMMENT ON TABLE dev.payment_invoices IS 'Invoices for subscriptions and purchases';
COMMENT ON TABLE dev.payment_refunds IS 'Payment refund records';