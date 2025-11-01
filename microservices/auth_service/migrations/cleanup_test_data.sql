-- Auth Service Test Data Cleanup Script
-- Removes all test data created by seed_test_data.sql
-- Run: docker exec staging-postgres psql -U postgres -d isa_platform -f /path/to/cleanup_test_data.sql

-- Delete test data in correct order (respecting foreign keys)
DELETE FROM auth.device_logs WHERE device_id LIKE 'test_%';
DELETE FROM auth.devices WHERE device_id LIKE 'test_%';
UPDATE auth.organizations SET api_keys = '[]'::jsonb WHERE organization_id LIKE 'test_%';
DELETE FROM auth.organizations WHERE organization_id LIKE 'test_%';
DELETE FROM auth.users WHERE user_id LIKE 'test_%';

-- Print summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Test Data Cleaned Successfully';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'All test users, organizations, and devices removed.';
    RAISE NOTICE '========================================';
END $$;
