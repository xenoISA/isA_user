-- Task Service Migration: Migrate to dedicated task schema
-- Version: 004
-- Date: 2025-10-27
-- Description: Move tables from dev schema to task schema and fix DECIMAL types

-- Create task schema
CREATE SCHEMA IF NOT EXISTS task;

-- Drop existing tables in task schema if they exist
DROP TABLE IF EXISTS task.task_executions CASCADE;
DROP TABLE IF EXISTS task.user_tasks CASCADE;
DROP TABLE IF EXISTS task.task_templates CASCADE;

-- 1. Create task templates table
CREATE TABLE task.task_templates (
    id SERIAL PRIMARY KEY,
    template_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL, -- productivity, monitoring, alerts, calendar, custom
    task_type VARCHAR(50) NOT NULL, -- daily_weather, daily_news, todo, reminder, etc.
    default_config JSONB DEFAULT '{}'::jsonb,
    required_fields TEXT[] DEFAULT ARRAY[]::TEXT[],
    optional_fields TEXT[] DEFAULT ARRAY[]::TEXT[],
    required_subscription_level VARCHAR(50) DEFAULT 'free', -- free, basic, pro, enterprise
    credits_per_run DOUBLE PRECISION DEFAULT 0,  -- Changed from DECIMAL
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create user tasks table
CREATE TABLE task.user_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    name VARCHAR(255) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, scheduled, running, completed, failed, cancelled, paused
    priority VARCHAR(20) DEFAULT 'medium', -- low, medium, high, urgent

    -- Configuration
    config JSONB DEFAULT '{}'::jsonb,
    schedule JSONB, -- cron expression or schedule config
    credits_per_run DOUBLE PRECISION DEFAULT 0,  -- Changed from DECIMAL

    -- Metadata
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Execution tracking
    next_run_time TIMESTAMPTZ,
    last_run_time TIMESTAMPTZ,
    last_success_time TIMESTAMPTZ,
    last_error TEXT,
    last_result JSONB,

    -- Statistics
    run_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    total_credits_consumed DOUBLE PRECISION DEFAULT 0,  -- Changed from DECIMAL

    -- Calendar/Todo specific
    due_date TIMESTAMPTZ,
    reminder_time TIMESTAMPTZ,
    is_completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- 3. Create task executions table
CREATE TABLE task.task_executions (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(255) NOT NULL UNIQUE,
    task_id VARCHAR(255) NOT NULL,  -- No FK constraint
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference

    -- Execution details
    status VARCHAR(50) NOT NULL, -- running, completed, failed, cancelled
    trigger_type VARCHAR(50) DEFAULT 'manual', -- manual, scheduler, webhook, event
    trigger_data JSONB,

    -- Results
    result JSONB,
    error_message TEXT,
    error_details JSONB,

    -- Resource usage
    credits_consumed DOUBLE PRECISION DEFAULT 0,  -- Changed from DECIMAL
    tokens_used INTEGER,
    api_calls_made INTEGER DEFAULT 0,
    duration_ms INTEGER,

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

-- Task templates indexes
CREATE INDEX idx_templates_category ON task.task_templates(category);
CREATE INDEX idx_templates_type ON task.task_templates(task_type);
CREATE INDEX idx_templates_active ON task.task_templates(is_active) WHERE is_active = true;
CREATE INDEX idx_templates_subscription ON task.task_templates(required_subscription_level);

-- User tasks indexes
CREATE INDEX idx_tasks_user_id ON task.user_tasks(user_id);
CREATE INDEX idx_tasks_status ON task.user_tasks(status);
CREATE INDEX idx_tasks_type ON task.user_tasks(task_type);
CREATE INDEX idx_tasks_priority ON task.user_tasks(priority);
CREATE INDEX idx_tasks_next_run ON task.user_tasks(next_run_time) WHERE next_run_time IS NOT NULL;
CREATE INDEX idx_tasks_due_date ON task.user_tasks(due_date) WHERE due_date IS NOT NULL;
CREATE INDEX idx_tasks_reminder ON task.user_tasks(reminder_time) WHERE reminder_time IS NOT NULL;
CREATE INDEX idx_tasks_deleted ON task.user_tasks(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_tags ON task.user_tasks USING GIN (tags);
CREATE INDEX idx_tasks_created_at ON task.user_tasks(created_at DESC);

-- Composite indexes for common queries
CREATE INDEX idx_tasks_user_status ON task.user_tasks(user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_user_type ON task.user_tasks(user_id, task_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_scheduled_pending ON task.user_tasks(status, next_run_time)
    WHERE status = 'scheduled' AND deleted_at IS NULL;

-- Task executions indexes
CREATE INDEX idx_executions_task_id ON task.task_executions(task_id);
CREATE INDEX idx_executions_user_id ON task.task_executions(user_id);
CREATE INDEX idx_executions_status ON task.task_executions(status);
CREATE INDEX idx_executions_trigger ON task.task_executions(trigger_type);
CREATE INDEX idx_executions_started ON task.task_executions(started_at DESC);
CREATE INDEX idx_executions_task_started ON task.task_executions(task_id, started_at DESC);

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA task IS 'Task service schema - task management and execution';
COMMENT ON TABLE task.task_templates IS 'Predefined task templates for quick task creation';
COMMENT ON TABLE task.user_tasks IS 'User-created tasks including todos, reminders, scheduled jobs';
COMMENT ON TABLE task.task_executions IS 'Task execution history and results';

COMMENT ON COLUMN task.user_tasks.task_id IS 'Unique task identifier';
COMMENT ON COLUMN task.user_tasks.user_id IS 'User identifier (no foreign key constraint)';
COMMENT ON COLUMN task.user_tasks.task_type IS 'Type of task: daily_weather, daily_news, todo, reminder, etc.';
COMMENT ON COLUMN task.user_tasks.status IS 'Current task status';
COMMENT ON COLUMN task.user_tasks.schedule IS 'Schedule configuration (cron expression or custom schedule)';
COMMENT ON COLUMN task.user_tasks.config IS 'Task-specific configuration';
COMMENT ON COLUMN task.user_tasks.credits_per_run IS 'Credits consumed per execution';
COMMENT ON COLUMN task.user_tasks.due_date IS 'Due date for todo tasks';
COMMENT ON COLUMN task.user_tasks.reminder_time IS 'Time to send reminder notification';

COMMENT ON COLUMN task.task_executions.execution_id IS 'Unique execution identifier';
COMMENT ON COLUMN task.task_executions.user_id IS 'User identifier (no foreign key constraint)';
COMMENT ON COLUMN task.task_executions.trigger_type IS 'How the execution was triggered';
COMMENT ON COLUMN task.task_executions.credits_consumed IS 'Credits consumed by this execution';
COMMENT ON COLUMN task.task_executions.duration_ms IS 'Execution duration in milliseconds';

-- Insert default task templates
INSERT INTO task.task_templates (template_id, name, description, category, task_type, default_config, required_fields, optional_fields, required_subscription_level, credits_per_run) VALUES
-- Free tier templates
('tpl_todo_basic', 'Basic Todo', 'Simple task with due date', 'productivity', 'todo',
 '{"priority": "medium"}'::jsonb, ARRAY['name', 'due_date'], ARRAY['description', 'tags'], 'free', 0),

('tpl_reminder_simple', 'Simple Reminder', 'One-time reminder notification', 'productivity', 'reminder',
 '{"notification_type": "in_app"}'::jsonb, ARRAY['name', 'reminder_time'], ARRAY['description'], 'free', 0.1),

('tpl_daily_weather', 'Daily Weather Report', 'Get daily weather updates', 'monitoring', 'daily_weather',
 '{"time": "08:00", "location": "auto"}'::jsonb, ARRAY['location'], ARRAY['units', 'time'], 'free', 0.5),

-- Basic tier templates
('tpl_daily_news', 'Daily News Digest', 'Curated news from selected sources', 'monitoring', 'daily_news',
 '{"categories": ["tech", "business"], "time": "09:00"}'::jsonb, ARRAY['categories'], ARRAY['sources', 'time'], 'basic', 1.0),

('tpl_calendar_event', 'Calendar Event', 'Scheduled event with reminders', 'calendar', 'calendar_event',
 '{"reminder_before": 15, "recurring": false}'::jsonb, ARRAY['name', 'start_time', 'end_time'], ARRAY['location', 'attendees', 'recurring'], 'basic', 0.2),

-- Pro tier templates
('tpl_price_tracker', 'Price Tracker', 'Track product prices and get alerts', 'monitoring', 'price_tracker',
 '{"check_interval": "daily", "alert_threshold": 10}'::jsonb, ARRAY['product_url', 'target_price'], ARRAY['check_interval', 'alert_threshold'], 'pro', 2.0),

('tpl_news_monitor', 'News Monitor', 'Monitor news for specific keywords', 'monitoring', 'news_monitor',
 '{"check_interval": "hourly", "notification": "email"}'::jsonb, ARRAY['keywords'], ARRAY['sources', 'check_interval', 'notification'], 'pro', 3.0),

('tpl_weather_alert', 'Weather Alert', 'Get alerts for severe weather', 'alerts', 'weather_alert',
 '{"severity": ["warning", "watch"], "location": "auto"}'::jsonb, ARRAY['location'], ARRAY['severity', 'notification'], 'pro', 1.5),

-- Enterprise tier templates
('tpl_custom_webhook', 'Custom Webhook', 'Execute custom webhook on schedule', 'custom', 'custom',
 '{"method": "POST", "headers": {}}'::jsonb, ARRAY['webhook_url', 'schedule'], ARRAY['method', 'headers', 'body'], 'enterprise', 5.0);
