-- =====================================================
-- Campaign Service Database Schema
-- Migration: 001_create_campaign_tables.sql
-- Description: Create all campaign service tables
-- Author: isA Vibe Orchestrator
-- Date: 2026-02-02
-- =====================================================

-- Create campaign schema
CREATE SCHEMA IF NOT EXISTS campaign;

-- =====================================================
-- 1. campaigns (Core Campaign Entity)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaigns (
    id SERIAL PRIMARY KEY,
    campaign_id VARCHAR(50) NOT NULL UNIQUE,
    organization_id VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    campaign_type VARCHAR(20) NOT NULL, -- scheduled, triggered
    status VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft, scheduled, active, running, paused, completed, cancelled

    -- Scheduling Configuration
    schedule_type VARCHAR(20), -- one_time, recurring
    scheduled_at TIMESTAMPTZ,
    cron_expression VARCHAR(100),
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Holdout Configuration
    holdout_percentage DECIMAL(5,2) DEFAULT 0,

    -- Task Service Integration
    task_id VARCHAR(50),

    -- Metadata
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Throttle Config (JSONB for flexibility)
    throttle_config JSONB DEFAULT '{}'::jsonb,

    -- A/B Test Config (JSONB for flexibility)
    ab_test_config JSONB DEFAULT '{}'::jsonb,

    -- Conversion Config (JSONB for flexibility)
    conversion_config JSONB DEFAULT '{}'::jsonb,

    -- Audit
    created_by VARCHAR(50) NOT NULL,
    updated_by VARCHAR(50),
    paused_by VARCHAR(50),
    paused_at TIMESTAMPTZ,
    cancelled_by VARCHAR(50),
    cancelled_at TIMESTAMPTZ,
    cancelled_reason TEXT,
    cloned_from_id VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT valid_status CHECK (status IN ('draft', 'scheduled', 'active', 'running', 'paused', 'completed', 'cancelled')),
    CONSTRAINT valid_campaign_type CHECK (campaign_type IN ('scheduled', 'triggered')),
    CONSTRAINT valid_schedule_type CHECK (schedule_type IS NULL OR schedule_type IN ('one_time', 'recurring')),
    CONSTRAINT valid_holdout CHECK (holdout_percentage >= 0 AND holdout_percentage <= 20)
);

CREATE INDEX IF NOT EXISTS idx_campaigns_org ON campaign.campaigns(organization_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaign.campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_type ON campaign.campaigns(campaign_type);
CREATE INDEX IF NOT EXISTS idx_campaigns_scheduled_at ON campaign.campaigns(scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_campaigns_deleted ON campaign.campaigns(deleted_at) WHERE deleted_at IS NULL;

-- =====================================================
-- 2. campaign_audiences (Audience Segments)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_audiences (
    id SERIAL PRIMARY KEY,
    audience_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id) ON DELETE CASCADE,

    -- Segment Configuration
    segment_type VARCHAR(20) NOT NULL, -- include, exclude
    segment_id VARCHAR(100), -- Reference to isA_Data segment
    segment_query JSONB, -- Inline segment query

    -- Metadata
    name VARCHAR(255),
    estimated_size INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_segment_type CHECK (segment_type IN ('include', 'exclude'))
);

CREATE INDEX IF NOT EXISTS idx_audiences_campaign ON campaign.campaign_audiences(campaign_id);

-- =====================================================
-- 3. campaign_variants (A/B Test Variants)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_variants (
    id SERIAL PRIMARY KEY,
    variant_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id) ON DELETE CASCADE,

    -- Variant Configuration
    name VARCHAR(100) NOT NULL,
    description TEXT,
    allocation_percentage DECIMAL(5,2) NOT NULL,
    is_control BOOLEAN DEFAULT FALSE, -- Control variant (no message sent)

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_allocation CHECK (allocation_percentage >= 0 AND allocation_percentage <= 100)
);

CREATE INDEX IF NOT EXISTS idx_variants_campaign ON campaign.campaign_variants(campaign_id);

-- =====================================================
-- 4. campaign_channels (Channel Content)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_channels (
    id SERIAL PRIMARY KEY,
    channel_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id) ON DELETE CASCADE,
    variant_id VARCHAR(50) REFERENCES campaign.campaign_variants(variant_id) ON DELETE SET NULL,

    -- Channel Configuration
    channel_type VARCHAR(20) NOT NULL, -- email, sms, whatsapp, in_app, webhook
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0, -- Fallback order

    -- Email Configuration
    email_subject VARCHAR(255),
    email_body_html TEXT,
    email_body_text TEXT,
    email_sender_name VARCHAR(100),
    email_sender_email VARCHAR(255),
    email_reply_to VARCHAR(255),

    -- SMS Configuration
    sms_body VARCHAR(160),

    -- WhatsApp Configuration
    whatsapp_body VARCHAR(1600),
    whatsapp_template_id VARCHAR(100),

    -- In-App Configuration
    in_app_title VARCHAR(255),
    in_app_body TEXT,
    in_app_action_url TEXT,
    in_app_icon VARCHAR(255),

    -- Webhook Configuration
    webhook_url TEXT,
    webhook_method VARCHAR(10) DEFAULT 'POST',
    webhook_headers JSONB DEFAULT '{}'::jsonb,
    webhook_payload_template TEXT,

    -- Template Reference
    template_id VARCHAR(100), -- Reference to isA_Creative template

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_channel_type CHECK (channel_type IN ('email', 'sms', 'whatsapp', 'in_app', 'webhook'))
);

CREATE INDEX IF NOT EXISTS idx_channels_campaign ON campaign.campaign_channels(campaign_id);
CREATE INDEX IF NOT EXISTS idx_channels_variant ON campaign.campaign_channels(variant_id);

-- =====================================================
-- 5. campaign_triggers (Event Triggers)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_triggers (
    id SERIAL PRIMARY KEY,
    trigger_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id) ON DELETE CASCADE,

    -- Trigger Configuration
    event_type VARCHAR(100) NOT NULL,
    conditions JSONB DEFAULT '[]'::jsonb, -- [{field, operator, value}]
    delay_minutes INTEGER DEFAULT 0,
    delay_days INTEGER DEFAULT 0,

    -- Frequency Limiting
    frequency_limit INTEGER DEFAULT 1,
    frequency_window_hours INTEGER DEFAULT 24,

    -- Quiet Hours
    quiet_hours_start INTEGER, -- Hour (0-23)
    quiet_hours_end INTEGER,   -- Hour (0-23)
    quiet_hours_timezone VARCHAR(50) DEFAULT 'user_local',

    -- State
    enabled BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_triggers_campaign ON campaign.campaign_triggers(campaign_id);
CREATE INDEX IF NOT EXISTS idx_triggers_event_type ON campaign.campaign_triggers(event_type);
CREATE INDEX IF NOT EXISTS idx_triggers_enabled ON campaign.campaign_triggers(enabled) WHERE enabled = TRUE;

-- =====================================================
-- 6. campaign_executions (Execution History)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL REFERENCES campaign.campaigns(campaign_id) ON DELETE CASCADE,

    -- Execution Configuration
    execution_type VARCHAR(20) NOT NULL, -- scheduled, triggered, manual
    trigger_event_id VARCHAR(50), -- For triggered executions

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, paused, completed, failed, cancelled

    -- Audience
    total_audience_size INTEGER DEFAULT 0,
    holdout_size INTEGER DEFAULT 0,

    -- Progress
    messages_queued INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    messages_delivered INTEGER DEFAULT 0,
    messages_failed INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_executions_campaign ON campaign.campaign_executions(campaign_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON campaign.campaign_executions(status);
CREATE INDEX IF NOT EXISTS idx_executions_started ON campaign.campaign_executions(started_at);

-- =====================================================
-- 7. campaign_messages (Individual Messages)
-- Note: Using regular table instead of partitioned for simplicity
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    execution_id VARCHAR(50) NOT NULL,
    variant_id VARCHAR(50),

    -- Recipient
    user_id VARCHAR(50) NOT NULL,
    channel_type VARCHAR(20) NOT NULL,
    recipient_address VARCHAR(255), -- email, phone, etc.

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'queued', -- queued, sent, delivered, opened, clicked, bounced, failed, unsubscribed

    -- Tracking
    notification_id VARCHAR(50), -- Reference to notification_service
    provider_message_id VARCHAR(100),

    -- Timestamps
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    bounced_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    unsubscribed_at TIMESTAMPTZ,

    -- Error Tracking
    error_message TEXT,
    bounce_type VARCHAR(20), -- hard, soft

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_messages_campaign ON campaign.campaign_messages(campaign_id);
CREATE INDEX IF NOT EXISTS idx_messages_execution ON campaign.campaign_messages(execution_id);
CREATE INDEX IF NOT EXISTS idx_messages_user ON campaign.campaign_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_status ON campaign.campaign_messages(status);
CREATE INDEX IF NOT EXISTS idx_messages_queued_at ON campaign.campaign_messages(queued_at);

-- =====================================================
-- 8. campaign_metrics (Aggregated Metrics)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_metrics (
    id SERIAL PRIMARY KEY,
    metric_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    execution_id VARCHAR(50),
    variant_id VARCHAR(50),
    channel_type VARCHAR(20),
    segment_id VARCHAR(50),

    -- Metric Type
    metric_type VARCHAR(50) NOT NULL, -- sent, delivered, opened, clicked, converted, bounced, unsubscribed

    -- Values
    count INTEGER DEFAULT 0,
    rate DECIMAL(10,6), -- Calculated rate (e.g., open_rate = opened/delivered)
    value DECIMAL(15,2), -- For conversion value

    -- Time Bucket (for time-series metrics)
    bucket_start TIMESTAMPTZ,
    bucket_end TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_campaign ON campaign.campaign_metrics(campaign_id);
CREATE INDEX IF NOT EXISTS idx_metrics_execution ON campaign.campaign_metrics(execution_id);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON campaign.campaign_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_bucket ON campaign.campaign_metrics(bucket_start, bucket_end);

-- =====================================================
-- 9. campaign_conversions (Conversion Attribution)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_conversions (
    id SERIAL PRIMARY KEY,
    conversion_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    execution_id VARCHAR(50),
    message_id VARCHAR(50),

    -- User
    user_id VARCHAR(50) NOT NULL,

    -- Conversion Details
    conversion_event_type VARCHAR(100) NOT NULL,
    conversion_event_id VARCHAR(50),
    conversion_value DECIMAL(15,2),

    -- Attribution
    attribution_model VARCHAR(20) NOT NULL,
    attribution_weight DECIMAL(5,4) DEFAULT 1.0, -- For linear attribution

    -- Timestamps
    converted_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversions_campaign ON campaign.campaign_conversions(campaign_id);
CREATE INDEX IF NOT EXISTS idx_conversions_user ON campaign.campaign_conversions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversions_converted ON campaign.campaign_conversions(converted_at);

-- =====================================================
-- 10. campaign_unsubscribes (Unsubscribe Tracking)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_unsubscribes (
    id SERIAL PRIMARY KEY,
    unsubscribe_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    message_id VARCHAR(50),

    -- User
    user_id VARCHAR(50) NOT NULL,

    -- Channel
    channel_type VARCHAR(20) NOT NULL,

    -- Details
    reason VARCHAR(255),
    source VARCHAR(50) DEFAULT 'link', -- link, reply, complaint

    -- Timestamps
    unsubscribed_at TIMESTAMPTZ DEFAULT NOW(),
    synced_to_account_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_unsubscribes_campaign ON campaign.campaign_unsubscribes(campaign_id);
CREATE INDEX IF NOT EXISTS idx_unsubscribes_user ON campaign.campaign_unsubscribes(user_id);

-- =====================================================
-- 11. campaign_trigger_history (Trigger Execution History)
-- =====================================================
CREATE TABLE IF NOT EXISTS campaign.campaign_trigger_history (
    id SERIAL PRIMARY KEY,
    history_id VARCHAR(50) NOT NULL UNIQUE,
    campaign_id VARCHAR(50) NOT NULL,
    trigger_id VARCHAR(50) NOT NULL,

    -- Event Details
    event_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(50) NOT NULL,

    -- Result
    triggered BOOLEAN NOT NULL,
    skip_reason VARCHAR(100), -- frequency_limit, quiet_hours, not_in_segment, already_triggered

    -- Execution Reference
    execution_id VARCHAR(50),

    -- Timestamps
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    scheduled_send_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_trigger_history_campaign ON campaign.campaign_trigger_history(campaign_id);
CREATE INDEX IF NOT EXISTS idx_trigger_history_user ON campaign.campaign_trigger_history(user_id);
CREATE INDEX IF NOT EXISTS idx_trigger_history_evaluated ON campaign.campaign_trigger_history(evaluated_at);

-- =====================================================
-- Grant permissions
-- =====================================================
GRANT ALL PRIVILEGES ON SCHEMA campaign TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA campaign TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA campaign TO postgres;

-- Complete
SELECT 'Campaign schema migration completed successfully' AS status;
