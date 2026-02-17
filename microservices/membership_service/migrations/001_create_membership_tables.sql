-- Membership Service Schema
-- Version: 1.0.0
-- Description: Core tables for membership service

CREATE SCHEMA IF NOT EXISTS membership;

-- Memberships table
CREATE TABLE IF NOT EXISTS membership.memberships (
    id SERIAL PRIMARY KEY,
    membership_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    organization_id VARCHAR(50),

    -- Tier
    tier_code VARCHAR(20) NOT NULL DEFAULT 'bronze',
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    -- Points
    points_balance BIGINT NOT NULL DEFAULT 0,
    tier_points BIGINT NOT NULL DEFAULT 0,
    lifetime_points BIGINT NOT NULL DEFAULT 0,
    pending_points BIGINT NOT NULL DEFAULT 0,

    -- Dates
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expiration_date TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,

    -- Auto-renewal
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metadata
    enrollment_source VARCHAR(50),
    promo_code VARCHAR(50),
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for memberships
CREATE INDEX IF NOT EXISTS idx_memberships_user_id ON membership.memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_memberships_status ON membership.memberships(status);
CREATE INDEX IF NOT EXISTS idx_memberships_tier ON membership.memberships(tier_code);
CREATE UNIQUE INDEX IF NOT EXISTS idx_memberships_user_active
    ON membership.memberships(user_id, organization_id)
    WHERE status IN ('active', 'pending');

-- Membership history table
CREATE TABLE IF NOT EXISTS membership.membership_history (
    id SERIAL PRIMARY KEY,
    history_id VARCHAR(50) UNIQUE NOT NULL,
    membership_id VARCHAR(50) NOT NULL,

    -- Action
    action VARCHAR(30) NOT NULL,
    points_change BIGINT NOT NULL DEFAULT 0,
    balance_after BIGINT,
    previous_tier VARCHAR(20),
    new_tier VARCHAR(20),

    -- Context
    source VARCHAR(50),
    reference_id VARCHAR(100),
    reward_code VARCHAR(50),
    benefit_code VARCHAR(50),
    description TEXT,
    initiated_by VARCHAR(20) NOT NULL DEFAULT 'system',
    metadata JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for history
CREATE INDEX IF NOT EXISTS idx_history_membership ON membership.membership_history(membership_id);
CREATE INDEX IF NOT EXISTS idx_history_created ON membership.membership_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_action ON membership.membership_history(action);

-- Tiers table
CREATE TABLE IF NOT EXISTS membership.tiers (
    id SERIAL PRIMARY KEY,
    tier_code VARCHAR(20) UNIQUE NOT NULL,
    tier_name VARCHAR(50) NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    qualification_threshold BIGINT NOT NULL DEFAULT 0,
    point_multiplier DECIMAL(4, 2) NOT NULL DEFAULT 1.0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed tier data
INSERT INTO membership.tiers (tier_code, tier_name, display_order, qualification_threshold, point_multiplier)
VALUES
    ('bronze', 'Bronze', 1, 0, 1.0),
    ('silver', 'Silver', 2, 5000, 1.25),
    ('gold', 'Gold', 3, 20000, 1.5),
    ('platinum', 'Platinum', 4, 50000, 2.0),
    ('diamond', 'Diamond', 5, 100000, 3.0)
ON CONFLICT (tier_code) DO NOTHING;

-- Tier benefits table
CREATE TABLE IF NOT EXISTS membership.tier_benefits (
    id SERIAL PRIMARY KEY,
    benefit_id VARCHAR(50) UNIQUE NOT NULL,
    tier_code VARCHAR(20) NOT NULL,
    benefit_code VARCHAR(50) NOT NULL,
    benefit_name VARCHAR(100) NOT NULL,
    benefit_type VARCHAR(50) NOT NULL,
    usage_limit INTEGER,
    is_unlimited BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (tier_code, benefit_code)
);

-- Index for tier benefits
CREATE INDEX IF NOT EXISTS idx_tier_benefits_tier ON membership.tier_benefits(tier_code);

-- Seed tier benefits
INSERT INTO membership.tier_benefits (benefit_id, tier_code, benefit_code, benefit_name, benefit_type, is_unlimited)
VALUES
    -- Bronze benefits
    ('bnft_bronze_support', 'bronze', 'BASIC_SUPPORT', 'Basic Support', 'service', true),

    -- Silver benefits
    ('bnft_silver_support', 'silver', 'PRIORITY_SUPPORT', 'Priority Support', 'service', true),
    ('bnft_silver_ship', 'silver', 'FREE_SHIPPING', 'Free Shipping', 'discount', false),

    -- Gold benefits
    ('bnft_gold_support', 'gold', 'PRIORITY_SUPPORT', 'Priority Support', 'service', true),
    ('bnft_gold_ship', 'gold', 'FREE_SHIPPING', 'Free Shipping', 'discount', true),
    ('bnft_gold_access', 'gold', 'EARLY_ACCESS', 'Early Access', 'access', true),

    -- Platinum benefits
    ('bnft_plat_support', 'platinum', 'VIP_SUPPORT', 'VIP Support', 'service', true),
    ('bnft_plat_ship', 'platinum', 'FREE_SHIPPING', 'Free Shipping', 'discount', true),
    ('bnft_plat_access', 'platinum', 'EARLY_ACCESS', 'Early Access', 'access', true),
    ('bnft_plat_exclusive', 'platinum', 'EXCLUSIVE_CONTENT', 'Exclusive Content', 'access', true),

    -- Diamond benefits
    ('bnft_diamond_concierge', 'diamond', 'VIP_CONCIERGE', 'VIP Concierge', 'service', true),
    ('bnft_diamond_ship', 'diamond', 'FREE_SHIPPING', 'Free Shipping', 'discount', true),
    ('bnft_diamond_access', 'diamond', 'EARLY_ACCESS', 'Early Access', 'access', true),
    ('bnft_diamond_exclusive', 'diamond', 'EXCLUSIVE_CONTENT', 'Exclusive Content', 'access', true),
    ('bnft_diamond_special', 'diamond', 'SPECIAL_OFFERS', 'Special Offers', 'discount', true)
ON CONFLICT (tier_code, benefit_code) DO NOTHING;

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION membership.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to memberships table
DROP TRIGGER IF EXISTS update_memberships_updated_at ON membership.memberships;
CREATE TRIGGER update_memberships_updated_at
    BEFORE UPDATE ON membership.memberships
    FOR EACH ROW
    EXECUTE FUNCTION membership.update_updated_at_column();
