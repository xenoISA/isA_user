-- Notification Service Migration: Create notification-related tables
-- Version: 001
-- Date: 2025-01-20
-- Description: Core tables for notification templates, notifications, and push subscriptions

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS dev.push_subscriptions CASCADE;
DROP TABLE IF EXISTS dev.notification_batches CASCADE;
DROP TABLE IF EXISTS dev.in_app_notifications CASCADE;
DROP TABLE IF EXISTS dev.notifications CASCADE;
DROP TABLE IF EXISTS dev.notification_templates CASCADE;

-- 1. Create notification templates table
CREATE TABLE dev.notification_templates (
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
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create notifications table
CREATE TABLE dev.notifications (
    id SERIAL PRIMARY KEY,
    notification_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    template_id VARCHAR(255),
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
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_notification_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_notification_template FOREIGN KEY (template_id)
        REFERENCES dev.notification_templates(template_id) ON DELETE SET NULL
);

-- 3. Create in-app notifications table
CREATE TABLE dev.in_app_notifications (
    id SERIAL PRIMARY KEY,
    notification_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info', -- info, success, warning, error, system
    category VARCHAR(100), -- account, payment, system, promotion, etc.
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    action_type VARCHAR(50), -- link, button, dismiss
    action_url TEXT,
    action_data JSONB,
    icon VARCHAR(255),
    avatar_url TEXT,
    is_read BOOLEAN DEFAULT false,
    is_archived BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_in_app_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE
);

-- 4. Create notification batches table
CREATE TABLE dev.notification_batches (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    description TEXT,
    template_id VARCHAR(255),
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
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_batch_template FOREIGN KEY (template_id)
        REFERENCES dev.notification_templates(template_id) ON DELETE SET NULL
);

-- 5. Create push subscriptions table
CREATE TABLE dev.push_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(255) NOT NULL,
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
    
    CONSTRAINT fk_push_user FOREIGN KEY (user_id) 
        REFERENCES dev.users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, device_token, platform)
);

-- Create indexes for performance
CREATE INDEX idx_templates_type ON dev.notification_templates(type);
CREATE INDEX idx_templates_status ON dev.notification_templates(status);
CREATE INDEX idx_templates_created_by ON dev.notification_templates(created_by);

CREATE INDEX idx_notifications_user_id ON dev.notifications(user_id);
CREATE INDEX idx_notifications_template_id ON dev.notifications(template_id);
CREATE INDEX idx_notifications_type ON dev.notifications(type);
CREATE INDEX idx_notifications_status ON dev.notifications(status);
CREATE INDEX idx_notifications_priority ON dev.notifications(priority);
CREATE INDEX idx_notifications_batch_id ON dev.notifications(batch_id);
CREATE INDEX idx_notifications_created_at ON dev.notifications(created_at DESC);
CREATE INDEX idx_notifications_scheduled ON dev.notifications(scheduled_at) WHERE scheduled_at IS NOT NULL;

CREATE INDEX idx_in_app_user_id ON dev.in_app_notifications(user_id);
CREATE INDEX idx_in_app_read ON dev.in_app_notifications(user_id, is_read) WHERE is_read = false;
CREATE INDEX idx_in_app_archived ON dev.in_app_notifications(is_archived) WHERE is_archived = false;
CREATE INDEX idx_in_app_category ON dev.in_app_notifications(category);
CREATE INDEX idx_in_app_expires ON dev.in_app_notifications(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_in_app_created_at ON dev.in_app_notifications(created_at DESC);

CREATE INDEX idx_batches_status ON dev.notification_batches(status);
CREATE INDEX idx_batches_template ON dev.notification_batches(template_id);
CREATE INDEX idx_batches_type ON dev.notification_batches(type);
CREATE INDEX idx_batches_scheduled ON dev.notification_batches(scheduled_at) WHERE scheduled_at IS NOT NULL;

CREATE INDEX idx_push_user_id ON dev.push_subscriptions(user_id);
CREATE INDEX idx_push_platform ON dev.push_subscriptions(platform);
CREATE INDEX idx_push_active ON dev.push_subscriptions(is_active) WHERE is_active = true;
CREATE INDEX idx_push_device_token ON dev.push_subscriptions(device_token);
CREATE INDEX idx_push_topics ON dev.push_subscriptions USING GIN (topics);

-- Create update triggers
CREATE TRIGGER trigger_update_templates_updated_at
    BEFORE UPDATE ON dev.notification_templates
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_notifications_updated_at
    BEFORE UPDATE ON dev.notifications
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_in_app_updated_at
    BEFORE UPDATE ON dev.in_app_notifications
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_batches_updated_at
    BEFORE UPDATE ON dev.notification_batches
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_push_updated_at
    BEFORE UPDATE ON dev.push_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.notification_templates TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.notification_templates TO authenticated;
GRANT ALL ON SEQUENCE dev.notification_templates_id_seq TO authenticated;

GRANT ALL ON dev.notifications TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.notifications TO authenticated;
GRANT ALL ON SEQUENCE dev.notifications_id_seq TO authenticated;

GRANT ALL ON dev.in_app_notifications TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.in_app_notifications TO authenticated;
GRANT ALL ON SEQUENCE dev.in_app_notifications_id_seq TO authenticated;

GRANT ALL ON dev.notification_batches TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.notification_batches TO authenticated;
GRANT ALL ON SEQUENCE dev.notification_batches_id_seq TO authenticated;

GRANT ALL ON dev.push_subscriptions TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.push_subscriptions TO authenticated;
GRANT ALL ON SEQUENCE dev.push_subscriptions_id_seq TO authenticated;

-- Add comments
COMMENT ON TABLE dev.notification_templates IS 'Reusable notification templates';
COMMENT ON TABLE dev.notifications IS 'All sent and pending notifications';
COMMENT ON TABLE dev.in_app_notifications IS 'In-app notification messages for users';
COMMENT ON TABLE dev.notification_batches IS 'Batch notification campaigns';
COMMENT ON TABLE dev.push_subscriptions IS 'Push notification device subscriptions';