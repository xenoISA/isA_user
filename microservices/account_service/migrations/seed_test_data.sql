-- Account Service: Seed Test Data
-- This script creates test users for development and testing

-- Insert test users
INSERT INTO account.users (user_id, email, name, subscription_status, is_active, preferences, created_at, updated_at)
VALUES
    ('test-user-1', 'test1@example.com', 'Test User One', 'free', TRUE, '{"theme": "light", "language": "en"}'::jsonb, NOW(), NOW()),
    ('test-user-2', 'test2@example.com', 'Test User Two', 'basic', TRUE, '{"theme": "dark", "language": "en"}'::jsonb, NOW(), NOW()),
    ('test-user-3', 'test3@example.com', 'Test User Three', 'premium', TRUE, '{"theme": "light", "language": "es"}'::jsonb, NOW(), NOW()),
    ('test-user-4', 'test4@example.com', 'Test User Four', 'pro', TRUE, '{"theme": "dark", "language": "fr"}'::jsonb, NOW(), NOW()),
    ('test-user-5', 'test5@example.com', 'Test User Five', 'enterprise', TRUE, '{"theme": "light", "language": "de"}'::jsonb, NOW(), NOW()),
    ('inactive-user-1', 'inactive1@example.com', 'Inactive User One', 'free', FALSE, '{}'::jsonb, NOW(), NOW())
ON CONFLICT (user_id) DO NOTHING;

-- Print summary
DO $$
DECLARE
    user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM account.users;
    RAISE NOTICE 'Test data seeded successfully. Total users: %', user_count;
END $$;
