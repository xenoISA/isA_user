-- Subscription Service Migration: Create subscription schema and tables
-- Version: 001
-- Date: 2025-11-28
-- Description: Core tables for subscription management
-- Reference: /docs/design/billing-credit-subscription-design.md

-- Create schema
CREATE SCHEMA IF NOT EXISTS subscription;

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS subscription.subscription_history CASCADE;
DROP TABLE IF EXISTS subscription.user_subscriptions CASCADE;

-- ====================
-- User Subscriptions Table
-- ====================
-- Stores active and past subscriptions for users/organizations

CREATE TABLE subscription.user_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(100) UNIQUE NOT NULL,

    -- Owner Information (no FK constraints - cross-service reference)
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),

    -- Subscription Plan Reference
    tier_id VARCHAR(100) NOT NULL,           -- Reference to product.subscription_tiers
    tier_code VARCHAR(50) NOT NULL,          -- free, pro, max, team, enterprise

    -- Subscription Status
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, trialing, past_due, canceled, paused, expired

    -- Billing Information
    billing_cycle VARCHAR(20) NOT NULL DEFAULT 'monthly',  -- monthly, yearly
    price_paid DOUBLE PRECISION NOT NULL DEFAULT 0,        -- Price paid for this period (USD)
    currency VARCHAR(10) DEFAULT 'USD',

    -- Credit Allocation
    credits_allocated BIGINT NOT NULL DEFAULT 0,           -- Credits allocated for this period
    credits_used BIGINT NOT NULL DEFAULT 0,                -- Credits used this period
    credits_remaining BIGINT NOT NULL DEFAULT 0,           -- Remaining credits
    credits_rolled_over BIGINT DEFAULT 0,                  -- Credits rolled over from previous period

    -- Period Information
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,

    -- Trial Information
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    is_trial BOOLEAN DEFAULT FALSE,

    -- Seats (for team/enterprise)
    seats_purchased INTEGER DEFAULT 1,
    seats_used INTEGER DEFAULT 1,

    -- Cancellation
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    cancellation_reason TEXT,

    -- Payment Integration
    payment_method_id VARCHAR(255),                        -- Reference to payment method
    external_subscription_id VARCHAR(255),                 -- Stripe/external subscription ID

    -- Renewal
    auto_renew BOOLEAN DEFAULT TRUE,
    next_billing_date TIMESTAMPTZ,
    last_billing_date TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT credits_non_negative CHECK (credits_remaining >= 0),
    CONSTRAINT seats_valid CHECK (seats_purchased >= seats_used)
);

-- ====================
-- Subscription History Table
-- ====================
-- Audit trail for all subscription changes

CREATE TABLE subscription.subscription_history (
    id SERIAL PRIMARY KEY,
    history_id VARCHAR(100) UNIQUE NOT NULL,

    -- Subscription Reference
    subscription_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),

    -- Change Information
    action VARCHAR(50) NOT NULL,              -- created, upgraded, downgraded, renewed, canceled, paused, resumed, credits_allocated, credits_consumed

    -- Before/After State
    previous_tier_code VARCHAR(50),
    new_tier_code VARCHAR(50),
    previous_status VARCHAR(50),
    new_status VARCHAR(50),

    -- Credit Changes
    credits_change BIGINT DEFAULT 0,          -- Positive for additions, negative for deductions
    credits_balance_after BIGINT,             -- Balance after this change

    -- Price Information
    price_change DOUBLE PRECISION DEFAULT 0,

    -- Period
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,

    -- Details
    reason TEXT,
    initiated_by VARCHAR(100),                -- user, system, admin
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

-- User subscriptions indexes
CREATE INDEX idx_user_subs_subscription_id ON subscription.user_subscriptions(subscription_id);
CREATE INDEX idx_user_subs_user_id ON subscription.user_subscriptions(user_id);
CREATE INDEX idx_user_subs_org_id ON subscription.user_subscriptions(organization_id);
CREATE INDEX idx_user_subs_tier_id ON subscription.user_subscriptions(tier_id);
CREATE INDEX idx_user_subs_tier_code ON subscription.user_subscriptions(tier_code);
CREATE INDEX idx_user_subs_status ON subscription.user_subscriptions(status);
CREATE INDEX idx_user_subs_billing_cycle ON subscription.user_subscriptions(billing_cycle);
CREATE INDEX idx_user_subs_period ON subscription.user_subscriptions(current_period_start, current_period_end);
CREATE INDEX idx_user_subs_next_billing ON subscription.user_subscriptions(next_billing_date);
CREATE INDEX idx_user_subs_external ON subscription.user_subscriptions(external_subscription_id);

-- Composite indexes for common queries
CREATE INDEX idx_user_subs_user_status ON subscription.user_subscriptions(user_id, status);
CREATE INDEX idx_user_subs_org_status ON subscription.user_subscriptions(organization_id, status);
CREATE INDEX idx_user_subs_active ON subscription.user_subscriptions(status) WHERE status = 'active';

-- Subscription history indexes
CREATE INDEX idx_sub_history_history_id ON subscription.subscription_history(history_id);
CREATE INDEX idx_sub_history_sub_id ON subscription.subscription_history(subscription_id);
CREATE INDEX idx_sub_history_user_id ON subscription.subscription_history(user_id);
CREATE INDEX idx_sub_history_action ON subscription.subscription_history(action);
CREATE INDEX idx_sub_history_created ON subscription.subscription_history(created_at DESC);

-- ====================
-- Update Triggers
-- ====================

CREATE TRIGGER update_user_subscriptions_updated_at
    BEFORE UPDATE ON subscription.user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA subscription IS 'Subscription service schema - user subscription management and credit allocation';
COMMENT ON TABLE subscription.user_subscriptions IS 'Active and historical user subscriptions with credit tracking';
COMMENT ON TABLE subscription.subscription_history IS 'Audit trail for all subscription lifecycle events';

COMMENT ON COLUMN subscription.user_subscriptions.credits_allocated IS 'Total credits allocated for the current billing period';
COMMENT ON COLUMN subscription.user_subscriptions.credits_used IS 'Credits consumed during current period';
COMMENT ON COLUMN subscription.user_subscriptions.credits_remaining IS 'Available credits (allocated + rolled_over - used)';
COMMENT ON COLUMN subscription.user_subscriptions.credits_rolled_over IS 'Credits carried over from previous period';
