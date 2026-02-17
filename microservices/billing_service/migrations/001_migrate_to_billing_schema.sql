-- Billing Service Migration: Migrate to dedicated billing schema
-- Version: 001
-- Date: 2025-10-28
-- Description: Move tables from dev/public schema to billing schema

-- Create billing schema
CREATE SCHEMA IF NOT EXISTS billing;

-- Drop existing tables/views in billing schema if they exist
DROP TABLE IF EXISTS billing.billing_events CASCADE;
DROP TABLE IF EXISTS billing.billing_records CASCADE;
DROP TABLE IF EXISTS billing.usage_aggregations CASCADE;
DROP TABLE IF EXISTS billing.billing_quotas CASCADE;

-- 1. Create billing_records table
CREATE TABLE billing.billing_records (
    id SERIAL PRIMARY KEY,
    billing_id VARCHAR(100) UNIQUE NOT NULL,

    -- References (no FK constraints)
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    subscription_id VARCHAR(100),
    usage_record_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(100) NOT NULL,

    -- Service and billing info
    service_type VARCHAR(50) NOT NULL,  -- model_inference, mcp_service, etc.
    usage_amount DOUBLE PRECISION NOT NULL,
    unit_price DOUBLE PRECISION NOT NULL,
    total_amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(20) DEFAULT 'USD',  -- USD, CNY, CREDIT

    -- Billing method and status
    billing_method VARCHAR(50) NOT NULL,  -- wallet_deduction, payment_charge, etc.
    billing_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed, refunded

    -- Transaction info
    wallet_transaction_id VARCHAR(100),
    payment_transaction_id VARCHAR(100),
    failure_reason TEXT,

    -- Metadata
    billing_metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    billing_period_start TIMESTAMPTZ,
    billing_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create billing_events table
CREATE TABLE billing.billing_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,

    -- Event info
    event_type VARCHAR(50) NOT NULL,  -- usage_recorded, billing_processed, etc.
    billing_id VARCHAR(100),
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),

    -- Event data
    event_data JSONB DEFAULT '{}'::jsonb,
    service_type VARCHAR(50),
    amount DOUBLE PRECISION,

    -- Timestamps
    event_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create usage_aggregations table
CREATE TABLE billing.usage_aggregations (
    id SERIAL PRIMARY KEY,
    aggregation_id VARCHAR(100) UNIQUE NOT NULL,

    -- References
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    service_type VARCHAR(50) NOT NULL,

    -- Aggregation period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,

    -- Usage metrics
    total_usage DOUBLE PRECISION DEFAULT 0,
    total_cost DOUBLE PRECISION DEFAULT 0,
    currency VARCHAR(20) DEFAULT 'USD',

    -- Breakdown
    usage_breakdown JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create billing_quotas table
CREATE TABLE billing.billing_quotas (
    id SERIAL PRIMARY KEY,
    quota_id VARCHAR(100) UNIQUE NOT NULL,

    -- References
    user_id VARCHAR(100),
    organization_id VARCHAR(100),
    subscription_id VARCHAR(100),
    product_id VARCHAR(100),
    service_type VARCHAR(50) NOT NULL,

    -- Quota limits
    quota_limit DOUBLE PRECISION NOT NULL,
    quota_used DOUBLE PRECISION DEFAULT 0,
    quota_remaining DOUBLE PRECISION,

    -- Period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    reset_frequency VARCHAR(20),  -- daily, weekly, monthly, yearly

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

-- Billing records indexes
CREATE INDEX idx_billing_records_billing_id ON billing.billing_records(billing_id);
CREATE INDEX idx_billing_records_user_id ON billing.billing_records(user_id);
CREATE INDEX idx_billing_records_organization_id ON billing.billing_records(organization_id);
CREATE INDEX idx_billing_records_status ON billing.billing_records(billing_status);
CREATE INDEX idx_billing_records_created_at ON billing.billing_records(created_at);
CREATE INDEX idx_billing_records_period ON billing.billing_records(billing_period_start, billing_period_end);

-- Composite indexes
CREATE INDEX idx_billing_user_status ON billing.billing_records(user_id, billing_status);
CREATE INDEX idx_billing_org_period ON billing.billing_records(organization_id, billing_period_start);

-- Billing events indexes
CREATE INDEX idx_billing_events_event_id ON billing.billing_events(event_id);
CREATE INDEX idx_billing_events_user_id ON billing.billing_events(user_id);
CREATE INDEX idx_billing_events_billing_id ON billing.billing_events(billing_id);
CREATE INDEX idx_billing_events_type ON billing.billing_events(event_type);
CREATE INDEX idx_billing_events_timestamp ON billing.billing_events(event_timestamp);

-- Usage aggregations indexes
CREATE INDEX idx_usage_agg_user_id ON billing.usage_aggregations(user_id);
CREATE INDEX idx_usage_agg_org_id ON billing.usage_aggregations(organization_id);
CREATE INDEX idx_usage_agg_service ON billing.usage_aggregations(service_type);
CREATE INDEX idx_usage_agg_period ON billing.usage_aggregations(period_start, period_end);

-- Billing quotas indexes
CREATE INDEX idx_quotas_user_id ON billing.billing_quotas(user_id);
CREATE INDEX idx_quotas_org_id ON billing.billing_quotas(organization_id);
CREATE INDEX idx_quotas_service ON billing.billing_quotas(service_type);
CREATE INDEX idx_quotas_period ON billing.billing_quotas(period_start, period_end);

-- ====================
-- Update Triggers
-- ====================

-- Trigger for billing_records
CREATE TRIGGER update_billing_records_updated_at
    BEFORE UPDATE ON billing.billing_records
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Trigger for usage_aggregations
CREATE TRIGGER update_usage_aggregations_updated_at
    BEFORE UPDATE ON billing.usage_aggregations
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Trigger for billing_quotas
CREATE TRIGGER update_billing_quotas_updated_at
    BEFORE UPDATE ON billing.billing_quotas
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA billing IS 'Billing service schema - usage tracking, billing records, and quota management';
COMMENT ON TABLE billing.billing_records IS 'Billing records for user usage and charges';
COMMENT ON TABLE billing.billing_events IS 'Billing-related events for audit trail';
COMMENT ON TABLE billing.usage_aggregations IS 'Aggregated usage statistics by period';
COMMENT ON TABLE billing.billing_quotas IS 'Usage quotas and limits';

COMMENT ON COLUMN billing.billing_records.billing_metadata IS 'JSON metadata for billing record';
COMMENT ON COLUMN billing.billing_events.event_data IS 'JSON event payload';
