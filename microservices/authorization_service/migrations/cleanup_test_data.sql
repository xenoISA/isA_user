-- Authorization Service: Cleanup Test Data
-- This script removes test permissions created by seed_test_data.sql

-- Delete test permissions (matches seed_test_data.sql pattern: test_user_XXX, test_org_XXX)
DELETE FROM authz.permissions
WHERE
    (target_type = 'user' AND target_id IN ('test_user_001', 'test_user_002', 'test_user_003'))
    OR (target_type = 'organization' AND target_id IN ('test_org_001', 'test_org_002'))
    OR (permission_type = 'resource_config' AND resource_name IN ('filesystem_read', 'filesystem_write', 'user_api', 'postgres_read', 'gpt4'));

-- Print summary
DO $$
DECLARE
    perm_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO perm_count FROM authz.permissions;
    RAISE NOTICE 'Test data cleaned up. Remaining permissions: %', perm_count;
END $$;
