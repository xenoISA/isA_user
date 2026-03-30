-- Audit Service Migration: Add admin action audit log table
-- Version: 002
-- Date: 2026-03-28
-- Description: Add dedicated admin_audit_log table for tracking admin operations
-- Related: Issue #190 — Admin Action Audit Trail (Epic #187)

-- Create admin_audit_log table in audit schema
CREATE TABLE IF NOT EXISTS audit.admin_audit_log (
    id SERIAL PRIMARY KEY,
    audit_id VARCHAR(100) UNIQUE NOT NULL,
    admin_user_id VARCHAR(100) NOT NULL,
    admin_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    changes JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for common query patterns
CREATE INDEX idx_admin_audit_admin_user ON audit.admin_audit_log(admin_user_id);
CREATE INDEX idx_admin_audit_action ON audit.admin_audit_log(action);
CREATE INDEX idx_admin_audit_resource_type ON audit.admin_audit_log(resource_type);
CREATE INDEX idx_admin_audit_resource_id ON audit.admin_audit_log(resource_id);
CREATE INDEX idx_admin_audit_timestamp ON audit.admin_audit_log(timestamp);

-- Composite indexes for filtered queries
CREATE INDEX idx_admin_audit_admin_time ON audit.admin_audit_log(admin_user_id, timestamp);
CREATE INDEX idx_admin_audit_resource_time ON audit.admin_audit_log(resource_type, timestamp);
CREATE INDEX idx_admin_audit_action_time ON audit.admin_audit_log(action, timestamp);

-- Comments
COMMENT ON TABLE audit.admin_audit_log IS 'Admin action audit trail — tracks all admin operations on products, pricing, users, etc.';
COMMENT ON COLUMN audit.admin_audit_log.changes IS 'JSON object with before/after diff of what changed';
COMMENT ON COLUMN audit.admin_audit_log.metadata IS 'Additional context (request path, service origin, etc.)';
