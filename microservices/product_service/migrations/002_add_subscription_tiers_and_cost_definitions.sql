-- Product Service Migration: Add subscription tiers and cost definitions
-- Version: 002
-- Date: 2025-11-28
-- Description: Add subscription_tiers and cost_definitions tables for the credit-based billing system
-- Reference: /docs/design/billing-credit-subscription-design.md

-- ====================
-- Subscription Tiers Table
-- ====================
-- Defines the available subscription plans: Free, Pro, Max, Team, Enterprise

CREATE TABLE IF NOT EXISTS product.subscription_tiers (
    id SERIAL PRIMARY KEY,
    tier_id VARCHAR(100) UNIQUE NOT NULL,

    -- Tier Information
    tier_name VARCHAR(100) NOT NULL,           -- Free, Pro, Max, Team, Enterprise
    tier_code VARCHAR(50) UNIQUE NOT NULL,     -- free, pro, max, team, enterprise
    description TEXT,

    -- Pricing (in USD)
    monthly_price_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
    yearly_price_usd DOUBLE PRECISION,         -- Usually 20% discount

    -- Credits (1 Credit = $0.00001 USD, 100,000 Credits = $1)
    monthly_credits BIGINT NOT NULL DEFAULT 0,  -- Credits included per month
    credit_rollover BOOLEAN DEFAULT FALSE,      -- Whether unused credits roll over
    max_rollover_credits BIGINT,                -- Maximum credits that can roll over

    -- Target Audience
    target_audience VARCHAR(50) NOT NULL,       -- individual, team, enterprise
    min_seats INTEGER DEFAULT 1,
    max_seats INTEGER,                          -- NULL = unlimited
    per_seat_price_usd DOUBLE PRECISION,        -- For team/enterprise tiers

    -- Features (JSON array)
    features JSONB DEFAULT '[]'::jsonb,

    -- Usage Limits (JSON object)
    -- Example: {"model_inference": {"daily_limit": 1000}, "storage_gb": 10}
    usage_limits JSONB DEFAULT '{}'::jsonb,

    -- Priority and Support
    support_level VARCHAR(50) DEFAULT 'community', -- community, email, priority, dedicated
    priority_queue BOOLEAN DEFAULT FALSE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT TRUE,             -- Whether shown in public pricing page
    display_order INTEGER DEFAULT 0,

    -- Trial
    trial_days INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Cost Definitions Table
-- ====================
-- Defines the cost (in credits) for each service/product usage
-- Cost already includes 30% margin

CREATE TABLE IF NOT EXISTS product.cost_definitions (
    id SERIAL PRIMARY KEY,
    cost_id VARCHAR(100) UNIQUE NOT NULL,

    -- Product/Service Reference
    product_id VARCHAR(100),                    -- Reference to products table (optional)

    -- Cost Identification
    service_type VARCHAR(50) NOT NULL,          -- model_inference, storage_minio, mcp_service, etc.
    provider VARCHAR(100),                      -- anthropic, openai, google, internal, etc.
    model_name VARCHAR(100),                    -- claude-sonnet-4-20250514, gpt-4o, etc.
    operation_type VARCHAR(50),                 -- input, output, request, storage_gb_month, etc.

    -- Cost Configuration (in Credits - 1 Credit = $0.00001 USD)
    -- All costs should include 30% margin
    cost_per_unit BIGINT NOT NULL,              -- Credits per unit
    unit_type VARCHAR(50) NOT NULL,             -- token, request, gb_month, minute, etc.
    unit_size INTEGER DEFAULT 1,                -- e.g., 1000 for "per 1K tokens"

    -- Original Cost (before margin, for reference)
    original_cost_usd DOUBLE PRECISION,         -- Original USD cost per unit
    margin_percentage DOUBLE PRECISION DEFAULT 30.0, -- Margin applied

    -- Effective Date Range
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    effective_until TIMESTAMPTZ,                -- NULL = no expiration

    -- Free Tier
    free_tier_limit BIGINT DEFAULT 0,           -- Free usage amount per period
    free_tier_period VARCHAR(20) DEFAULT 'monthly', -- daily, monthly, yearly

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Metadata
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

-- Subscription tiers indexes
CREATE INDEX IF NOT EXISTS idx_subscription_tiers_tier_id ON product.subscription_tiers(tier_id);
CREATE INDEX IF NOT EXISTS idx_subscription_tiers_tier_code ON product.subscription_tiers(tier_code);
CREATE INDEX IF NOT EXISTS idx_subscription_tiers_active ON product.subscription_tiers(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_subscription_tiers_audience ON product.subscription_tiers(target_audience);
CREATE INDEX IF NOT EXISTS idx_subscription_tiers_display ON product.subscription_tiers(display_order);

-- Cost definitions indexes
CREATE INDEX IF NOT EXISTS idx_cost_definitions_cost_id ON product.cost_definitions(cost_id);
CREATE INDEX IF NOT EXISTS idx_cost_definitions_product ON product.cost_definitions(product_id);
CREATE INDEX IF NOT EXISTS idx_cost_definitions_service ON product.cost_definitions(service_type);
CREATE INDEX IF NOT EXISTS idx_cost_definitions_provider ON product.cost_definitions(provider);
CREATE INDEX IF NOT EXISTS idx_cost_definitions_model ON product.cost_definitions(model_name);
CREATE INDEX IF NOT EXISTS idx_cost_definitions_active ON product.cost_definitions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_cost_definitions_effective ON product.cost_definitions(effective_from, effective_until);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_cost_lookup ON product.cost_definitions(service_type, provider, model_name, operation_type) WHERE is_active = TRUE;

-- ====================
-- Update Triggers
-- ====================

CREATE TRIGGER update_subscription_tiers_updated_at
    BEFORE UPDATE ON product.subscription_tiers
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_cost_definitions_updated_at
    BEFORE UPDATE ON product.cost_definitions
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ====================
-- Comments
-- ====================

COMMENT ON TABLE product.subscription_tiers IS 'Subscription plans with credit allocations and features';
COMMENT ON TABLE product.cost_definitions IS 'Cost per usage unit for each service (in credits, with 30% margin)';

COMMENT ON COLUMN product.subscription_tiers.monthly_credits IS 'Credits included monthly. 1 Credit = $0.00001 USD (100,000 Credits = $1)';
COMMENT ON COLUMN product.subscription_tiers.features IS 'JSON array of feature flags/descriptions';
COMMENT ON COLUMN product.subscription_tiers.usage_limits IS 'JSON object defining daily/monthly limits per service';

COMMENT ON COLUMN product.cost_definitions.cost_per_unit IS 'Cost in credits (1 Credit = $0.00001 USD)';
COMMENT ON COLUMN product.cost_definitions.unit_size IS 'Number of units per charge (e.g., 1000 for per 1K tokens)';
COMMENT ON COLUMN product.cost_definitions.margin_percentage IS 'Margin added to original cost (default 30%)';
