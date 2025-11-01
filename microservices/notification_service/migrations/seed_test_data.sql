-- Seed test data for Notification Service
-- Schema: notification
-- Date: 2025-10-27

-- Insert test notification templates
INSERT INTO notification.notification_templates (
    template_id, name, description, type, subject, content, html_content,
    variables, metadata, status, version, created_by, created_at, updated_at
) VALUES
    ('tmpl_test_001', 'Welcome Email', 'Welcome new users', 'email',
     'Welcome to ISA Platform', 'Hello {{name}}, welcome to our platform!',
     '<h1>Hello {{name}}</h1><p>Welcome to our platform!</p>',
     '["name"]'::jsonb, '{}'::jsonb, 'active', 1, 'test_admin', NOW(), NOW()),
    ('tmpl_test_002', 'Order Confirmation', 'Confirm orders', 'email',
     'Order Confirmation', 'Your order {{order_id}} has been confirmed.',
     '<p>Your order {{order_id}} has been confirmed.</p>',
     '["order_id"]'::jsonb, '{}'::jsonb, 'active', 1, 'test_admin', NOW(), NOW()),
    ('tmpl_test_003', 'Push Notification', 'General push notifications', 'push',
     'New Message', 'You have a new message from {{sender}}',
     NULL, '["sender"]'::jsonb, '{}'::jsonb, 'active', 1, 'test_admin', NOW(), NOW())
ON CONFLICT (template_id) DO NOTHING;

-- Insert test notifications
INSERT INTO notification.notifications (
    notification_id, user_id, type, channel, recipient, subject, content,
    template_id, variables, metadata, priority, status, retry_count, max_retries,
    created_at, updated_at
) VALUES
    ('notif_test_001', 'test_user_001', 'email', 'primary', 'test@example.com',
     'Welcome to ISA Platform', 'Hello Test User, welcome to our platform!',
     'tmpl_test_001', '{"name": "Test User"}'::jsonb, '{}'::jsonb,
     'normal', 'sent', 0, 3, NOW(), NOW()),
    ('notif_test_002', 'test_user_002', 'email', 'primary', 'user2@example.com',
     'Order Confirmation', 'Your order ORDER-123 has been confirmed.',
     'tmpl_test_002', '{"order_id": "ORDER-123"}'::jsonb, '{}'::jsonb,
     'high', 'delivered', 0, 3, NOW(), NOW()),
    ('notif_test_003', 'test_user_001', 'push', 'all', 'device_token_123',
     'New Message', 'You have a new message from John',
     'tmpl_test_003', '{"sender": "John"}'::jsonb, '{}'::jsonb,
     'urgent', 'pending', 0, 3, NOW(), NOW())
ON CONFLICT (notification_id) DO NOTHING;

-- Insert test in-app notifications
INSERT INTO notification.in_app_notifications (
    notification_id, user_id, title, message, type, category, priority,
    action_type, action_url, action_data, icon, is_read, is_archived,
    metadata, created_at, updated_at
) VALUES
    ('inapp_test_001', 'test_user_001', 'Welcome!', 'Welcome to ISA Platform',
     'info', 'system', 'normal', 'link', '/dashboard', '{}'::jsonb,
     'welcome', FALSE, FALSE, '{}'::jsonb, NOW(), NOW()),
    ('inapp_test_002', 'test_user_002', 'Payment Received', 'Your payment has been processed',
     'success', 'payment', 'high', 'button', '/payments', '{}'::jsonb,
     'payment', FALSE, FALSE, '{}'::jsonb, NOW(), NOW()),
    ('inapp_test_003', 'test_user_001', 'Update Available', 'A new software update is available',
     'warning', 'system', 'low', 'link', '/settings/update', '{}'::jsonb,
     'update', TRUE, FALSE, '{}'::jsonb, NOW(), NOW())
ON CONFLICT (notification_id) DO NOTHING;

-- Insert test notification batches
INSERT INTO notification.notification_batches (
    batch_id, name, description, template_id, type, total_count,
    sent_count, delivered_count, failed_count, status, scheduled_at,
    metadata, created_by, created_at, updated_at
) VALUES
    ('batch_test_001', 'Welcome Campaign', 'Send welcome emails to new users',
     'tmpl_test_001', 'email', 100, 80, 75, 5, 'processing', NULL,
     '{}'::jsonb, 'test_admin', NOW(), NOW()),
    ('batch_test_002', 'Product Launch', 'Announce new product',
     'tmpl_test_003', 'push', 500, 500, 480, 20, 'completed',
     NOW() + INTERVAL '1 day', '{}'::jsonb, 'test_admin', NOW(), NOW())
ON CONFLICT (batch_id) DO NOTHING;

-- Insert test push subscriptions
INSERT INTO notification.push_subscriptions (
    subscription_id, user_id, platform, device_token, device_id, device_name,
    app_version, os_version, endpoint, p256dh, auth, topics, is_active,
    metadata, created_at, updated_at
) VALUES
    ('sub_test_001', 'test_user_001', 'ios', 'ios_token_abc123', 'device_001',
     'iPhone 14 Pro', '1.0.0', 'iOS 17.0', NULL, NULL, NULL,
     ARRAY['news', 'alerts'], TRUE, '{}'::jsonb, NOW(), NOW()),
    ('sub_test_002', 'test_user_002', 'android', 'android_token_xyz789', 'device_002',
     'Samsung Galaxy S23', '1.0.0', 'Android 14', NULL, NULL, NULL,
     ARRAY['news', 'promotions'], TRUE, '{}'::jsonb, NOW(), NOW()),
    ('sub_test_003', 'test_user_001', 'web', 'web_token_def456', NULL,
     'Chrome Browser', '1.0.0', 'macOS', 'https://push.example.com',
     'p256dh_key_example', 'auth_key_example', ARRAY['alerts'], TRUE,
     '{}'::jsonb, NOW(), NOW())
ON CONFLICT (user_id, device_token, platform) DO UPDATE SET
    device_name = EXCLUDED.device_name,
    updated_at = EXCLUDED.updated_at;

-- Verify seeded data
SELECT 'Templates:', COUNT(*) FROM notification.notification_templates;
SELECT 'Notifications:', COUNT(*) FROM notification.notifications;
SELECT 'In-App Notifications:', COUNT(*) FROM notification.in_app_notifications;
SELECT 'Batches:', COUNT(*) FROM notification.notification_batches;
SELECT 'Push Subscriptions:', COUNT(*) FROM notification.push_subscriptions;
