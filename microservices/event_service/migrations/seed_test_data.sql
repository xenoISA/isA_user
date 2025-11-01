-- Seed test data for Event Service
-- Schema: event
-- Date: 2025-10-27

-- Insert test events
INSERT INTO event.events (
    event_id, event_type, event_source, event_category,
    user_id, data, metadata, status, timestamp, created_at, updated_at
) VALUES
    ('event_test_001', 'user.login', 'web', 'user',
     'test_user_001', '{"ip": "192.168.1.1"}'::jsonb, '{"browser": "Chrome"}'::jsonb,
     'processed', NOW(), NOW(), NOW()),
    ('event_test_002', 'user.logout', 'web', 'user',
     'test_user_001', '{"duration": 3600}'::jsonb, '{"browser": "Chrome"}'::jsonb,
     'processed', NOW(), NOW(), NOW()),
    ('event_test_003', 'device.connected', 'iot_device', 'device',
     'test_user_002', '{"device_type": "frame"}'::jsonb, '{"model": "v1"}'::jsonb,
     'pending', NOW(), NOW(), NOW())
ON CONFLICT (event_id) DO NOTHING;

-- Insert test subscriptions
INSERT INTO event.event_subscriptions (
    subscription_id, subscriber_name, subscriber_type,
    event_types, callback_url, enabled, retry_policy, created_at, updated_at
) VALUES
    ('sub_test_001', 'test_subscriber', 'webhook',
     ARRAY['user.login', 'user.logout'], 'https://example.com/webhook',
     TRUE, '{}'::jsonb, NOW(), NOW())
ON CONFLICT (subscriber_name) DO NOTHING;

-- Verify seeded data
SELECT 'Events:', COUNT(*) FROM event.events;
SELECT 'Subscriptions:', COUNT(*) FROM event.event_subscriptions;
