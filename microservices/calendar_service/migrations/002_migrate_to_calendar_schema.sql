-- Calendar Service Migration: Migrate to dedicated calendar schema
-- Version: 002
-- Date: 2025-10-27
-- Description: Move tables from dev/public schema to calendar schema

-- Create calendar schema
CREATE SCHEMA IF NOT EXISTS calendar;

-- Drop existing tables/views in calendar schema if they exist
DROP TABLE IF EXISTS calendar.calendar_sync_status CASCADE;
DROP TABLE IF EXISTS calendar.calendar_events CASCADE;

-- 1. Create calendar_events table
CREATE TABLE calendar.calendar_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,  -- No FK constraint - cross-service reference
    organization_id VARCHAR(100),  -- No FK constraint - cross-service reference

    -- Event details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(255),

    -- Time information
    start_time TIMESTAMPTZ NOT NULL,  -- Changed from TIMESTAMP WITH TIME ZONE
    end_time TIMESTAMPTZ NOT NULL,
    all_day BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Categorization
    category VARCHAR(50) DEFAULT 'other',
    color VARCHAR(7),  -- #RRGGBB format

    -- Recurrence
    recurrence_type VARCHAR(20) DEFAULT 'none',
    recurrence_end_date TIMESTAMPTZ,
    recurrence_rule TEXT,  -- iCalendar RRULE format

    -- Reminders (JSON array of minutes)
    reminders JSONB DEFAULT '[]'::jsonb,

    -- External sync
    sync_provider VARCHAR(50) DEFAULT 'local',
    external_event_id VARCHAR(255),
    last_synced_at TIMESTAMPTZ,

    -- Sharing
    is_shared BOOLEAN DEFAULT FALSE,
    shared_with TEXT[],  -- Array of user IDs

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create calendar_sync_status table
CREATE TABLE calendar.calendar_sync_status (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,  -- No FK constraint - cross-service reference
    provider VARCHAR(50) NOT NULL,

    -- Sync info
    last_sync_time TIMESTAMPTZ,
    sync_token TEXT,  -- For incremental sync
    synced_events_count INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- active, error, disabled
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, provider)
);

-- ====================
-- Indexes
-- ====================

-- Calendar events indexes
CREATE INDEX idx_events_user_id ON calendar.calendar_events(user_id);
CREATE INDEX idx_events_org_id ON calendar.calendar_events(organization_id);
CREATE INDEX idx_events_start_time ON calendar.calendar_events(start_time);
CREATE INDEX idx_events_end_time ON calendar.calendar_events(end_time);
CREATE INDEX idx_events_category ON calendar.calendar_events(category);
CREATE INDEX idx_events_sync_provider ON calendar.calendar_events(sync_provider);

-- Composite indexes for common queries
CREATE INDEX idx_events_user_time_range ON calendar.calendar_events(user_id, start_time, end_time);
CREATE INDEX idx_events_user_category ON calendar.calendar_events(user_id, category);

-- Sync status indexes
CREATE INDEX idx_sync_status_user ON calendar.calendar_sync_status(user_id);
CREATE INDEX idx_sync_status_provider ON calendar.calendar_sync_status(provider);

-- ====================
-- Update Triggers
-- ====================

-- Trigger for calendar_events
CREATE TRIGGER update_calendar_events_updated_at
    BEFORE UPDATE ON calendar.calendar_events
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Trigger for calendar_sync_status
CREATE TRIGGER update_calendar_sync_status_updated_at
    BEFORE UPDATE ON calendar.calendar_sync_status
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA calendar IS 'Calendar service schema - event management and external calendar sync';
COMMENT ON TABLE calendar.calendar_events IS 'Calendar events with recurrence and sharing support';
COMMENT ON TABLE calendar.calendar_sync_status IS 'External calendar provider sync status';

COMMENT ON COLUMN calendar.calendar_events.recurrence_rule IS 'iCalendar RRULE format for recurring events';
COMMENT ON COLUMN calendar.calendar_events.reminders IS 'JSON array of reminder times in minutes before event';
COMMENT ON COLUMN calendar.calendar_events.shared_with IS 'Array of user IDs who can view this event';
