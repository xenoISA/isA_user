-- Account Service: Seed Test Data
-- Standardized test data following test_data_standard.md
-- Date: 2025-11-11

-- Insert test users (standardized IDs)
INSERT INTO account.users (user_id, email, name, subscription_status, is_active, preferences, created_at, updated_at)
VALUES
    ('test_user_001', 'alice@example.com', 'Alice Test', 'free', TRUE, '{"theme": "light", "language": "en"}'::jsonb, NOW(), NOW()),
    ('test_user_002', 'bob@example.com', 'Bob Test', 'basic', TRUE, '{"theme": "dark", "language": "en"}'::jsonb, NOW(), NOW()),
    ('test_user_003', 'charlie@example.com', 'Charlie Test', 'pro', TRUE, '{"theme": "light", "language": "en"}'::jsonb, NOW(), NOW()),
    ('test_user_004', 'diana@example.com', 'Diana Test (Inactive)', 'free', FALSE, '{}'::jsonb, NOW(), NOW())
ON CONFLICT (user_id) DO NOTHING;

-- Print summary
DO $$
DECLARE
    user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM account.users;
    RAISE NOTICE 'Test data seeded successfully. Total users: %', user_count;
END $$;
