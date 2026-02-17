-- Account Service: Cleanup Test Data
-- This script removes test users created by seed_test_data.sql

-- Delete test users (matches seed_test_data.sql pattern: test_user_XXX)
DELETE FROM account.users
WHERE user_id IN (
    'test_user_001',
    'test_user_002',
    'test_user_003',
    'test_user_004'
);

-- Print summary
DO $$
DECLARE
    user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM account.users;
    RAISE NOTICE 'Test data cleaned up. Remaining users: %', user_count;
END $$;
