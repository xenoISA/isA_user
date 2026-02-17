-- Notification Service Migration: Create notification schema and tables
-- Version: 001
-- Date: 2025-10-27
-- Description: Core tables for notifications, templates, batches, and push subscriptions
-- Following PostgreSQL + gRPC migration guide

-- Create schema
CREATE SCHEMA IF NOT EXISTS notification;

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS notification.push_subscriptions CASCADE;
DROP TABLE IF EXISTS notification.notification_batches CASCADE;
DROP TABLE IF EXISTS notification.in_app_notifications CASCADE;
DROP TABLE IF EXISTS notification.notifications CASCADE;
DROP TABLE IF EXISTS notification.notification_templates CASCADE;

-- 1. Notification Templates Table
CREATE TABLE notification.notification_templates (
    id SERIAL PRIMARY KEY,
    template_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL, -- email, sms, push, in_app, webhook
    subject VARCHAR(255),
    content TEXT NOT NULL,
    html_content TEXT,
    variables JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, archived
    version INTEGER DEFAULT 1,
    created_by VARCHAR(255),  -- No FK constraint - cross-service reference
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Notifications Table
CREATE TABLE notification.notifications (
    id SERIAL PRIMARY KEY,
    notification_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    template_id VARCHAR(255),  -- No FK constraint - reference to notification_templates by business logic
    type VARCHAR(50) NOT NULL, -- email, sms, push, in_app, webhook
    channel VARCHAR(50), -- primary, secondary, all
    recipient VARCHAR(255) NOT NULL, -- email address, phone number, device token
    subject VARCHAR(255),
    content TEXT NOT NULL,
    html_content TEXT,
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    status VARCHAR(50) DEFAULT 'pending', -- pending, sent, delivered, failed, bounced
    variables JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    scheduled_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    batch_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. In-App Notifications Table
CREATE TABLE notification.in_app_notifications (
    id SERIAL PRIMARY KEY,
    notification_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info', -- info, success, warning, error, system
    category VARCHAR(100), -- account, payment, system, promotion, etc.
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    action_type VARCHAR(50), -- link, button, dismiss
    action_url TEXT,
    action_data JSONB DEFAULT '{}'::jsonb,
    icon VARCHAR(255),
    avatar_url TEXT,
    is_read BOOLEAN DEFAULT false,
    is_archived BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Notification Batches Table
CREATE TABLE notification.notification_batches (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    description TEXT,
    template_id VARCHAR(255),  -- No FK constraint - reference by business logic
    type VARCHAR(50) NOT NULL, -- email, sms, push, in_app
    total_count INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    delivered_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed, cancelled
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by VARCHAR(255),  -- No FK constraint - cross-service reference
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Push Subscriptions Table
CREATE TABLE notification.push_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,  -- No FK constraint - cross-service reference
    platform VARCHAR(50) NOT NULL, -- ios, android, web
    device_token TEXT NOT NULL,
    device_id VARCHAR(255),
    device_name VARCHAR(255),
    app_version VARCHAR(50),
    os_version VARCHAR(50),
    endpoint TEXT, -- For web push
    p256dh TEXT, -- For web push encryption
    auth TEXT, -- For web push auth
    topics TEXT[], -- Subscription topics/categories
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, device_token, platform)
);

-- ==================== Indexes ====================

-- Notification Templates indexes
CREATE INDEX idx_templates_type ON notification.notification_templates(type);
CREATE INDEX idx_templates_status ON notification.notification_templates(status);
CREATE INDEX idx_templates_created_by ON notification.notification_templates(created_by);

-- Notifications indexes
CREATE INDEX idx_notifications_user_id ON notification.notifications(user_id);
CREATE INDEX idx_notifications_template_id ON notification.notifications(template_id);
CREATE INDEX idx_notifications_type ON notification.notifications(type);
CREATE INDEX idx_notifications_status ON notification.notifications(status);
CREATE INDEX idx_notifications_priority ON notification.notifications(priority);
CREATE INDEX idx_notifications_batch_id ON notification.notifications(batch_id);
CREATE INDEX idx_notifications_created_at ON notification.notifications(created_at DESC);
CREATE INDEX idx_notifications_scheduled ON notification.notifications(scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX idx_notifications_user_status ON notification.notifications(user_id, status);

-- In-App Notifications indexes
CREATE INDEX idx_in_app_user_id ON notification.in_app_notifications(user_id);
CREATE INDEX idx_in_app_read ON notification.in_app_notifications(user_id, is_read) WHERE is_read = false;
CREATE INDEX idx_in_app_archived ON notification.in_app_notifications(is_archived) WHERE is_archived = false;
CREATE INDEX idx_in_app_category ON notification.in_app_notifications(category);
CREATE INDEX idx_in_app_expires ON notification.in_app_notifications(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_in_app_created_at ON notification.in_app_notifications(created_at DESC);
CREATE INDEX idx_in_app_user_unread ON notification.in_app_notifications(user_id, created_at DESC) WHERE is_read = false;

-- Notification Batches indexes
CREATE INDEX idx_batches_status ON notification.notification_batches(status);
CREATE INDEX idx_batches_template ON notification.notification_batches(template_id);
CREATE INDEX idx_batches_type ON notification.notification_batches(type);
CREATE INDEX idx_batches_scheduled ON notification.notification_batches(scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX idx_batches_created_by ON notification.notification_batches(created_by);

-- Push Subscriptions indexes
CREATE INDEX idx_push_user_id ON notification.push_subscriptions(user_id);
CREATE INDEX idx_push_platform ON notification.push_subscriptions(platform);
CREATE INDEX idx_push_active ON notification.push_subscriptions(is_active) WHERE is_active = true;
CREATE INDEX idx_push_device_token ON notification.push_subscriptions(device_token);
CREATE INDEX idx_push_topics ON notification.push_subscriptions USING GIN (topics);
CREATE INDEX idx_push_user_platform ON notification.push_subscriptions(user_id, platform, is_active);

-- ==================== Comments ====================

COMMENT ON SCHEMA notification IS 'Notification service schema - notification management and delivery';
COMMENT ON TABLE notification.notification_templates IS 'Reusable notification templates';
COMMENT ON TABLE notification.notifications IS 'All sent and pending notifications';
COMMENT ON TABLE notification.in_app_notifications IS 'In-app notification messages for users';
COMMENT ON TABLE notification.notification_batches IS 'Batch notification campaigns';
COMMENT ON TABLE notification.push_subscriptions IS 'Push notification device subscriptions';
