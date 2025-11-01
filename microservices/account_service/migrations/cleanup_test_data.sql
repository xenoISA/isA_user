-- Account Service: Cleanup Test Data
-- This script removes test users created by seed_test_data.sql

-- Delete test users
DELETE FROM account.users
WHERE user_id IN (
    'test-user-1',
    'test-user-2',
    'test-user-3',
    'test-user-4',
    'test-user-5',
    'inactive-user-1'
);

-- Print summary
DO $$
DECLARE
    user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM account.users;
    RAISE NOTICE 'Test data cleaned up. Remaining users: %', user_count;
END $$;
