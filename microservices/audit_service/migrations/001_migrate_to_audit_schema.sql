-- Audit Service Migration: Migrate to dedicated audit schema
-- Version: 001
-- Date: 2025-10-28
-- Description: Move tables from dev/public schema to audit schema

-- Create audit schema
CREATE SCHEMA IF NOT EXISTS audit;

-- Drop existing tables/views in audit schema if they exist
DROP TABLE IF EXISTS audit.audit_events CASCADE;

-- 1. Create audit_events table (unified audit table)
CREATE TABLE audit.audit_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,

    -- Event classification
    event_type VARCHAR(50) NOT NULL,  -- user_activity, security_event, compliance_check, etc.
    event_category VARCHAR(50) NOT NULL,  -- authentication, authorization, data_access, etc.
    event_severity VARCHAR(20) DEFAULT 'info',  -- debug, info, warning, error, critical
    event_status VARCHAR(20) DEFAULT 'completed',  -- initiated, in_progress, completed, failed

    -- Context
    user_id VARCHAR(100),
    organization_id VARCHAR(100),
    session_id VARCHAR(100),
    ip_address VARCHAR(50),
    user_agent TEXT,

    -- Action details
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    resource_name VARCHAR(255),

    -- Results
    status_code INTEGER,
    error_message TEXT,
    changes_made JSONB DEFAULT '{}'::jsonb,  -- Before/after changes

    -- Security
    risk_score DOUBLE PRECISION,
    threat_indicators JSONB DEFAULT '[]'::jsonb,
    compliance_flags JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],

    -- Timestamps
    event_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

CREATE INDEX idx_audit_event_id ON audit.audit_events(event_id);
CREATE INDEX idx_audit_user_id ON audit.audit_events(user_id);
CREATE INDEX idx_audit_organization_id ON audit.audit_events(organization_id);
CREATE INDEX idx_audit_event_type ON audit.audit_events(event_type);
CREATE INDEX idx_audit_category ON audit.audit_events(event_category);
CREATE INDEX idx_audit_severity ON audit.audit_events(event_severity);
CREATE INDEX idx_audit_timestamp ON audit.audit_events(event_timestamp);
CREATE INDEX idx_audit_resource ON audit.audit_events(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit.audit_events(action);

-- Composite indexes for common queries
CREATE INDEX idx_audit_user_time ON audit.audit_events(user_id, event_timestamp);
CREATE INDEX idx_audit_org_type ON audit.audit_events(organization_id, event_type);
CREATE INDEX idx_audit_type_time ON audit.audit_events(event_type, event_timestamp);

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA audit IS 'Audit service schema - unified audit trail for all events';
COMMENT ON TABLE audit.audit_events IS 'Unified audit events table for user activities, security events, and compliance';

COMMENT ON COLUMN audit.audit_events.changes_made IS 'JSON object containing before/after values for data changes';
COMMENT ON COLUMN audit.audit_events.threat_indicators IS 'JSON array of detected security threats';
COMMENT ON COLUMN audit.audit_events.compliance_flags IS 'JSON array of compliance-related flags';
