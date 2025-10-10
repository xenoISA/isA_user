-- Audit Service Migration: Create audit_events table
-- Version: 001 
-- Date: 2025-01-20

CREATE TABLE IF NOT EXISTS dev.audit_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'success',
    action VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Subject information
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    organization_id VARCHAR(255),
    
    -- Resource information
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    resource_name VARCHAR(255),
    
    -- Technical information
    ip_address INET,
    user_agent TEXT,
    api_endpoint VARCHAR(500),
    http_method VARCHAR(10),
    
    -- Result information
    success BOOLEAN DEFAULT TRUE,
    error_code VARCHAR(50),
    error_message TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],
    
    -- Timestamps
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Compliance related
    retention_policy VARCHAR(100),
    compliance_flags TEXT[]
);

-- Indexes
CREATE INDEX idx_audit_events_event_type ON dev.audit_events(event_type);
CREATE INDEX idx_audit_events_category ON dev.audit_events(category);
CREATE INDEX idx_audit_events_severity ON dev.audit_events(severity);
CREATE INDEX idx_audit_events_user_id ON dev.audit_events(user_id);
CREATE INDEX idx_audit_events_session_id ON dev.audit_events(session_id);
CREATE INDEX idx_audit_events_organization_id ON dev.audit_events(organization_id);
CREATE INDEX idx_audit_events_resource_type ON dev.audit_events(resource_type);
CREATE INDEX idx_audit_events_resource_id ON dev.audit_events(resource_id);
CREATE INDEX idx_audit_events_ip_address ON dev.audit_events(ip_address);
CREATE INDEX idx_audit_events_success ON dev.audit_events(success);
CREATE INDEX idx_audit_events_timestamp ON dev.audit_events(timestamp);
CREATE INDEX idx_audit_events_created_at ON dev.audit_events(created_at);
CREATE INDEX idx_audit_events_metadata ON dev.audit_events USING GIN(metadata);
CREATE INDEX idx_audit_events_tags ON dev.audit_events USING GIN(tags);

-- Composite indexes for common queries
CREATE INDEX idx_audit_events_user_activity ON dev.audit_events(user_id, timestamp DESC);
CREATE INDEX idx_audit_events_security ON dev.audit_events(category, severity, timestamp DESC) WHERE category = 'security';
CREATE INDEX idx_audit_events_org_activity ON dev.audit_events(organization_id, timestamp DESC);

-- Permissions  
GRANT ALL ON dev.audit_events TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.audit_events TO authenticated;

-- Comments
COMMENT ON TABLE dev.audit_events IS 'Comprehensive audit trail for all system events';
COMMENT ON COLUMN dev.audit_events.event_type IS 'Type of event (authentication, data_access, security, etc.)';
COMMENT ON COLUMN dev.audit_events.category IS 'Event category (authentication, authorization, data, security, system)';
COMMENT ON COLUMN dev.audit_events.severity IS 'Event severity level (low, medium, high, critical)';
COMMENT ON COLUMN dev.audit_events.status IS 'Event status (success, failure, pending)';
COMMENT ON COLUMN dev.audit_events.action IS 'Specific action performed';
COMMENT ON COLUMN dev.audit_events.description IS 'Human-readable description of the event';
COMMENT ON COLUMN dev.audit_events.user_id IS 'ID of the user who performed the action';
COMMENT ON COLUMN dev.audit_events.session_id IS 'Session ID associated with the event';
COMMENT ON COLUMN dev.audit_events.organization_id IS 'Organization ID if applicable';
COMMENT ON COLUMN dev.audit_events.resource_type IS 'Type of resource affected';
COMMENT ON COLUMN dev.audit_events.resource_id IS 'ID of the specific resource';
COMMENT ON COLUMN dev.audit_events.resource_name IS 'Name of the resource';
COMMENT ON COLUMN dev.audit_events.ip_address IS 'Source IP address';
COMMENT ON COLUMN dev.audit_events.user_agent IS 'User agent string';
COMMENT ON COLUMN dev.audit_events.api_endpoint IS 'API endpoint accessed';
COMMENT ON COLUMN dev.audit_events.http_method IS 'HTTP method used';
COMMENT ON COLUMN dev.audit_events.success IS 'Whether the operation was successful';
COMMENT ON COLUMN dev.audit_events.error_code IS 'Error code if applicable';
COMMENT ON COLUMN dev.audit_events.error_message IS 'Error message if applicable';
COMMENT ON COLUMN dev.audit_events.metadata IS 'Additional event metadata stored as JSONB';
COMMENT ON COLUMN dev.audit_events.tags IS 'Array of tags for categorization';
COMMENT ON COLUMN dev.audit_events.timestamp IS 'When the event occurred';
COMMENT ON COLUMN dev.audit_events.retention_policy IS 'Data retention policy for this event';
COMMENT ON COLUMN dev.audit_events.compliance_flags IS 'Compliance-related flags';