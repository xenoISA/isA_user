-- Compliance Service Migration: Migrate to dedicated compliance schema
-- Version: 001
-- Date: 2025-10-28
-- Description: Move tables from dev/public schema to compliance schema

-- Create compliance schema
CREATE SCHEMA IF NOT EXISTS compliance;

-- Drop existing tables/views in compliance schema if they exist
DROP TABLE IF EXISTS compliance.compliance_policies CASCADE;
DROP TABLE IF EXISTS compliance.compliance_checks CASCADE;

-- 1. Create compliance_checks table
CREATE TABLE compliance.compliance_checks (
    id SERIAL PRIMARY KEY,
    check_id VARCHAR(100) UNIQUE NOT NULL,
    check_type VARCHAR(50) NOT NULL,  -- content_moderation, pii_detection, etc.
    content_type VARCHAR(50) NOT NULL,  -- text, image, audio, video, etc.
    status VARCHAR(20) NOT NULL,  -- pass, fail, warning, pending, flagged, blocked
    risk_level VARCHAR(20) NOT NULL,  -- none, low, medium, high, critical

    -- References (no FK constraints for cross-service independence)
    user_id VARCHAR(100),
    organization_id VARCHAR(100),
    session_id VARCHAR(100),
    request_id VARCHAR(100),
    content_id VARCHAR(255),

    -- Content info
    content_hash VARCHAR(255),
    content_size INTEGER,

    -- Check results
    confidence_score DOUBLE PRECISION,
    violations JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    detected_issues JSONB DEFAULT '{}'::jsonb,
    moderation_categories JSONB DEFAULT '[]'::jsonb,
    detected_pii JSONB DEFAULT '[]'::jsonb,

    -- Actions
    action_taken VARCHAR(100),
    blocked_reason TEXT,
    human_review_required BOOLEAN DEFAULT FALSE,
    reviewed_by VARCHAR(100),
    review_notes TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    provider VARCHAR(100),  -- e.g., openai, azure, custom

    -- Timestamps
    checked_at TIMESTAMPTZ NOT NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create compliance_policies table
CREATE TABLE compliance.compliance_policies (
    id SERIAL PRIMARY KEY,
    policy_id VARCHAR(100) UNIQUE NOT NULL,
    organization_id VARCHAR(100) NOT NULL,

    -- Policy info
    policy_name VARCHAR(255) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,

    -- Policy configuration
    check_types TEXT[],  -- Array of check types to apply
    content_types TEXT[],  -- Array of content types to check
    rules JSONB NOT NULL,  -- Policy rules configuration
    thresholds JSONB DEFAULT '{}'::jsonb,  -- Risk thresholds

    -- Actions
    auto_block BOOLEAN DEFAULT FALSE,
    require_review BOOLEAN DEFAULT TRUE,
    notify_admin BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_by VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

-- Compliance checks indexes
CREATE INDEX idx_checks_check_id ON compliance.compliance_checks(check_id);
CREATE INDEX idx_checks_user_id ON compliance.compliance_checks(user_id);
CREATE INDEX idx_checks_organization_id ON compliance.compliance_checks(organization_id);
CREATE INDEX idx_checks_session_id ON compliance.compliance_checks(session_id);
CREATE INDEX idx_checks_status ON compliance.compliance_checks(status);
CREATE INDEX idx_checks_risk_level ON compliance.compliance_checks(risk_level);
CREATE INDEX idx_checks_check_type ON compliance.compliance_checks(check_type);
CREATE INDEX idx_checks_checked_at ON compliance.compliance_checks(checked_at);
CREATE INDEX idx_checks_human_review ON compliance.compliance_checks(human_review_required);

-- Composite indexes for common queries
CREATE INDEX idx_checks_org_status ON compliance.compliance_checks(organization_id, status);
CREATE INDEX idx_checks_user_time ON compliance.compliance_checks(user_id, checked_at);
CREATE INDEX idx_checks_status_risk ON compliance.compliance_checks(status, risk_level);

-- Compliance policies indexes
CREATE INDEX idx_policies_organization_id ON compliance.compliance_policies(organization_id);
CREATE INDEX idx_policies_enabled ON compliance.compliance_policies(enabled);

-- ====================
-- Update Triggers
-- ====================

-- Trigger for compliance_checks
CREATE TRIGGER update_compliance_checks_updated_at
    BEFORE UPDATE ON compliance.compliance_checks
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Trigger for compliance_policies
CREATE TRIGGER update_compliance_policies_updated_at
    BEFORE UPDATE ON compliance.compliance_policies
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA compliance IS 'Compliance service schema - content moderation, PII detection, policy management';
COMMENT ON TABLE compliance.compliance_checks IS 'Compliance check records for content moderation and safety';
COMMENT ON TABLE compliance.compliance_policies IS 'Organization-specific compliance policies';

COMMENT ON COLUMN compliance.compliance_checks.violations IS 'JSON array of detected violations';
COMMENT ON COLUMN compliance.compliance_checks.detected_pii IS 'JSON array of detected PII instances';
COMMENT ON COLUMN compliance.compliance_policies.rules IS 'JSON configuration of policy rules';
