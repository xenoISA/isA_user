-- Event Service Migration: Create event schema and tables
-- Version: 001
-- Date: 2025-10-27
-- Description: Core tables for event management system
-- Following PostgreSQL + gRPC migration guide

-- Create schema
CREATE SCHEMA IF NOT EXISTS event;

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS event.processing_results CASCADE;
DROP TABLE IF EXISTS event.event_subscriptions CASCADE;
DROP TABLE IF EXISTS event.event_processors CASCADE;
DROP TABLE IF EXISTS event.event_projections CASCADE;
DROP TABLE IF EXISTS event.event_streams CASCADE;
DROP TABLE IF EXISTS event.events CASCADE;

-- ==================== Main Tables ====================

-- Events table
CREATE TABLE event.events (
    event_id VARCHAR(255) PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,
    event_source VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,

    -- Related IDs (no FK constraints - cross-service references)
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    organization_id VARCHAR(255),
    device_id VARCHAR(255),
    correlation_id VARCHAR(255),

    -- Data (JSONB fields with defaults)
    data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',
    properties JSONB DEFAULT '{}',

    -- Processing info
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    processed_at TIMESTAMPTZ,
    processors TEXT[],
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps (using TIMESTAMPTZ for timezone support)
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Version
    version VARCHAR(20) DEFAULT '1.0.0',
    schema_version VARCHAR(20) DEFAULT '1.0.0'
);

-- Event streams table
CREATE TABLE event.event_streams (
    stream_id VARCHAR(255) PRIMARY KEY,
    stream_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,

    events JSONB DEFAULT '[]',
    version INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(entity_type, entity_id)
);

-- Event projections table
CREATE TABLE event.event_projections (
    projection_id VARCHAR(255) PRIMARY KEY,
    projection_name VARCHAR(255) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,

    state JSONB DEFAULT '{}',
    version INTEGER DEFAULT 0,
    last_event_id VARCHAR(255),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(entity_type, entity_id, projection_name)
);

-- Event processors table
CREATE TABLE event.event_processors (
    processor_id VARCHAR(255) PRIMARY KEY,
    processor_name VARCHAR(255) NOT NULL UNIQUE,
    processor_type VARCHAR(100) NOT NULL,

    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,

    filters JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',

    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_processed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Event subscriptions table
CREATE TABLE event.event_subscriptions (
    subscription_id VARCHAR(255) PRIMARY KEY,
    subscriber_name VARCHAR(255) NOT NULL UNIQUE,
    subscriber_type VARCHAR(100) NOT NULL,

    event_types TEXT[],
    event_sources TEXT[],
    event_categories TEXT[],

    callback_url TEXT,
    webhook_secret TEXT,

    enabled BOOLEAN DEFAULT TRUE,
    retry_policy JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Processing results table (no FK constraint for event_id)
CREATE TABLE event.processing_results (
    result_id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) NOT NULL,  -- No FK constraint
    processor_name VARCHAR(255) NOT NULL,

    status VARCHAR(20) NOT NULL,
    message TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_ms INTEGER
);

-- ==================== Indexes ====================

-- Events indexes
CREATE INDEX idx_events_user_id ON event.events(user_id);
CREATE INDEX idx_events_device_id ON event.events(device_id);
CREATE INDEX idx_events_organization_id ON event.events(organization_id);
CREATE INDEX idx_events_session_id ON event.events(session_id);
CREATE INDEX idx_events_correlation_id ON event.events(correlation_id);
CREATE INDEX idx_events_type ON event.events(event_type);
CREATE INDEX idx_events_source ON event.events(event_source);
CREATE INDEX idx_events_category ON event.events(event_category);
CREATE INDEX idx_events_status ON event.events(status);
CREATE INDEX idx_events_timestamp ON event.events(timestamp DESC);
CREATE INDEX idx_events_created_at ON event.events(created_at DESC);
CREATE INDEX idx_events_data ON event.events USING GIN(data);
CREATE INDEX idx_events_metadata ON event.events USING GIN(metadata);

-- Compound indexes for common queries
CREATE INDEX idx_events_user_type ON event.events(user_id, event_type);
CREATE INDEX idx_events_user_timestamp ON event.events(user_id, timestamp DESC);
CREATE INDEX idx_events_type_status ON event.events(event_type, status);
CREATE INDEX idx_events_source_category ON event.events(event_source, event_category);

-- Event streams indexes
CREATE INDEX idx_streams_entity ON event.event_streams(entity_type, entity_id);
CREATE INDEX idx_streams_type ON event.event_streams(stream_type);

-- Event projections indexes
CREATE INDEX idx_projections_entity ON event.event_projections(entity_type, entity_id);
CREATE INDEX idx_projections_name ON event.event_projections(projection_name);

-- Processing results indexes
CREATE INDEX idx_results_event_id ON event.processing_results(event_id);
CREATE INDEX idx_results_processor ON event.processing_results(processor_name);
CREATE INDEX idx_results_processed_at ON event.processing_results(processed_at DESC);

-- ==================== Comments ====================

COMMENT ON SCHEMA event IS 'Event service schema - event management and processing';
COMMENT ON TABLE event.events IS 'Main events table for storing all system events';
COMMENT ON TABLE event.event_streams IS 'Event sourcing streams';
COMMENT ON TABLE event.event_projections IS 'Event projections for read models';
COMMENT ON TABLE event.event_processors IS 'Event processor configurations';
COMMENT ON TABLE event.event_subscriptions IS 'Event subscription configurations';
COMMENT ON TABLE event.processing_results IS 'Event processing results and audit log';
