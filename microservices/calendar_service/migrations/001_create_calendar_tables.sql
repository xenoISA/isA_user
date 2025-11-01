-- Calendar Service Database Schema

-- ==========================================
-- 微服务数据库设计原则:
-- ==========================================
-- NO FOREIGN KEYS to other services' tables
-- user_id, organization_id等字段只存储ID值，不建立FK
-- 通过API调用其他服务

CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    
    -- Event details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(255),
    
    -- Time information
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    all_day BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Categorization
    category VARCHAR(50) DEFAULT 'other',
    color VARCHAR(7),  -- #RRGGBB format
    
    -- Recurrence
    recurrence_type VARCHAR(20) DEFAULT 'none',
    recurrence_end_date TIMESTAMP WITH TIME ZONE,
    recurrence_rule TEXT,  -- iCalendar RRULE format
    
    -- Reminders (JSON array of minutes)
    reminders JSONB DEFAULT '[]'::jsonb,
    
    -- External sync
    sync_provider VARCHAR(50) DEFAULT 'local',
    external_event_id VARCHAR(255),
    last_synced_at TIMESTAMP WITH TIME ZONE,
    
    -- Sharing
    is_shared BOOLEAN DEFAULT FALSE,
    shared_with TEXT[],  -- Array of user IDs
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_events_user_id ON calendar_events(user_id);
CREATE INDEX idx_events_org_id ON calendar_events(organization_id);
CREATE INDEX idx_events_start_time ON calendar_events(start_time);
CREATE INDEX idx_events_end_time ON calendar_events(end_time);
CREATE INDEX idx_events_category ON calendar_events(category);
CREATE INDEX idx_events_sync_provider ON calendar_events(sync_provider);

-- Composite indexes for common queries
CREATE INDEX idx_events_user_time_range ON calendar_events(user_id, start_time, end_time);
CREATE INDEX idx_events_user_category ON calendar_events(user_id, category);

-- External calendar sync status table
CREATE TABLE IF NOT EXISTS calendar_sync_status (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    
    -- Sync info
    last_sync_time TIMESTAMP WITH TIME ZONE,
    sync_token TEXT,  -- For incremental sync
    synced_events_count INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- active, error, disabled
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, provider)
);

CREATE INDEX idx_sync_status_user ON calendar_sync_status(user_id);

-- Update trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_calendar_events_updated_at
    BEFORE UPDATE ON calendar_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_sync_status_updated_at
    BEFORE UPDATE ON calendar_sync_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

