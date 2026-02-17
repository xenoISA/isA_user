-- Organization Service Test Data Cleanup
-- Purpose: Remove all test data

-- Delete test data in reverse order (respecting foreign keys)
-- Matches seed_test_data.sql pattern: test_perm_XXX, test_share_XXX, test_org_XXX
DELETE FROM organization.family_sharing_member_permissions WHERE permission_id LIKE 'test_perm_%';
DELETE FROM organization.family_sharing_resources WHERE sharing_id LIKE 'test_share_%';
DELETE FROM organization.organization_members WHERE organization_id LIKE 'test_org_%';
DELETE FROM organization.organizations WHERE organization_id LIKE 'test_org_%';

-- Verify cleanup
SELECT 'Remaining test organizations:', COUNT(*) FROM organization.organizations WHERE organization_id LIKE 'test_org_%';
SELECT 'Remaining test members:', COUNT(*) FROM organization.organization_members WHERE organization_id LIKE 'test_org_%';
SELECT 'Remaining test sharing:', COUNT(*) FROM organization.family_sharing_resources WHERE sharing_id LIKE 'test_share_%';
SELECT 'Remaining test permissions:', COUNT(*) FROM organization.family_sharing_member_permissions WHERE permission_id LIKE 'test_perm_%';
