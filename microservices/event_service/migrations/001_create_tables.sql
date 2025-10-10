-- Event Service Database Schema
-- Version: 1.0.0
-- Description: Initial schema for unified event management system

-- Set schema to dev
SET search_path TO dev;

-- ==================== Main Tables ====================

-- Events table
CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,
    event_source VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    
    -- Related IDs
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    organization_id VARCHAR(255),
    device_id VARCHAR(255),
    correlation_id VARCHAR(255),
    
    -- Data
    data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    context JSONB,
    properties JSONB,
    
    -- Processing info
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    processed_at TIMESTAMP,
    processors TEXT[],
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Version
    version VARCHAR(20) DEFAULT '1.0.0',
    schema_version VARCHAR(20) DEFAULT '1.0.0'
);

-- Event streams table
CREATE TABLE IF NOT EXISTS event_streams (
    stream_id VARCHAR(36) PRIMARY KEY,
    stream_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    
    events JSONB DEFAULT '[]',
    version INTEGER DEFAULT 0,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(entity_type, entity_id)
);

-- Event projections table
CREATE TABLE IF NOT EXISTS event_projections (
    projection_id VARCHAR(36) PRIMARY KEY,
    projection_name VARCHAR(255) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    
    state JSONB DEFAULT '{}',
    version INTEGER DEFAULT 0,
    last_event_id VARCHAR(36),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(entity_type, entity_id, projection_name)
);

-- Event processors table
CREATE TABLE IF NOT EXISTS event_processors (
    processor_id VARCHAR(36) PRIMARY KEY,
    processor_name VARCHAR(255) NOT NULL UNIQUE,
    processor_type VARCHAR(100) NOT NULL,
    
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    
    filters JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',
    
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_processed_at TIMESTAMP,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Event subscriptions table
CREATE TABLE IF NOT EXISTS event_subscriptions (
    subscription_id VARCHAR(36) PRIMARY KEY,
    subscriber_name VARCHAR(255) NOT NULL,
    subscriber_type VARCHAR(100) NOT NULL,
    
    event_types TEXT[],
    event_sources TEXT[],
    event_categories TEXT[],
    
    callback_url TEXT,
    webhook_secret TEXT,
    
    enabled BOOLEAN DEFAULT TRUE,
    retry_policy JSONB DEFAULT '{}',
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(subscriber_name)
);

-- Processing results table
CREATE TABLE IF NOT EXISTS processing_results (
    result_id SERIAL PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL,
    processor_name VARCHAR(255) NOT NULL,
    
    status VARCHAR(20) NOT NULL,
    message TEXT,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

-- ==================== Indexes ====================

-- Events indexes
CREATE INDEX idx_events_user_id ON events(user_id);
CREATE INDEX idx_events_device_id ON events(device_id);
CREATE INDEX idx_events_organization_id ON events(organization_id);
CREATE INDEX idx_events_session_id ON events(session_id);
CREATE INDEX idx_events_correlation_id ON events(correlation_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_source ON events(event_source);
CREATE INDEX idx_events_category ON events(event_category);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_created_at ON events(created_at DESC);
CREATE INDEX idx_events_data ON events USING GIN(data);
CREATE INDEX idx_events_metadata ON events USING GIN(metadata);

-- Compound indexes
CREATE INDEX idx_events_user_type ON events(user_id, event_type);
CREATE INDEX idx_events_user_timestamp ON events(user_id, timestamp DESC);
CREATE INDEX idx_events_type_status ON events(event_type, status);
CREATE INDEX idx_events_source_category ON events(event_source, event_category);

-- Event streams indexes
CREATE INDEX idx_streams_entity ON event_streams(entity_type, entity_id);
CREATE INDEX idx_streams_type ON event_streams(stream_type);

-- Event projections indexes
CREATE INDEX idx_projections_entity ON event_projections(entity_type, entity_id);
CREATE INDEX idx_projections_name ON event_projections(projection_name);

-- Processing results indexes
CREATE INDEX idx_results_event_id ON processing_results(event_id);
CREATE INDEX idx_results_processor ON processing_results(processor_name);
CREATE INDEX idx_results_processed_at ON processing_results(processed_at DESC);

-- ==================== Functions ====================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ==================== Triggers ====================

-- Add update triggers for all tables
CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_streams_updated_at BEFORE UPDATE ON event_streams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projections_updated_at BEFORE UPDATE ON event_projections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processors_updated_at BEFORE UPDATE ON event_processors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON event_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==================== Views ====================

-- Event statistics view
CREATE OR REPLACE VIEW event_statistics AS
SELECT 
    COUNT(*) as total_events,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_events,
    COUNT(CASE WHEN status = 'processed' THEN 1 END) as processed_events,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_events,
    COUNT(CASE WHEN timestamp >= CURRENT_DATE THEN 1 END) as events_today,
    COUNT(CASE WHEN timestamp >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as events_this_week,
    COUNT(CASE WHEN timestamp >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as events_this_month
FROM events;

-- Event type statistics view
CREATE OR REPLACE VIEW event_type_stats AS
SELECT 
    event_type,
    COUNT(*) as count,
    MAX(timestamp) as last_occurrence
FROM events
GROUP BY event_type
ORDER BY count DESC;

-- User activity view
CREATE OR REPLACE VIEW user_activity AS
SELECT 
    user_id,
    COUNT(*) as event_count,
    COUNT(DISTINCT event_type) as unique_event_types,
    MIN(timestamp) as first_event,
    MAX(timestamp) as last_event
FROM events
WHERE user_id IS NOT NULL
GROUP BY user_id
ORDER BY event_count DESC;

-- ==================== Sample Data (Optional) ====================

-- Insert default event processors
INSERT INTO event_processors (processor_id, processor_name, processor_type, config)
VALUES 
    ('00000000-0000-0000-0000-000000000001', 'analytics_processor', 'analytics', '{"enabled": true}'),
    ('00000000-0000-0000-0000-000000000002', 'notification_processor', 'notification', '{"enabled": true}'),
    ('00000000-0000-0000-0000-000000000003', 'audit_processor', 'audit', '{"enabled": true}')
ON CONFLICT (processor_name) DO NOTHING;

-- ==================== Permissions ====================

-- Grant permissions to event_user (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO event_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO event_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO event_user;