-- Organization Service Test Data Cleanup
-- Purpose: Remove all test data

-- Delete test data in reverse order (respecting foreign keys)
DELETE FROM organization.family_sharing_member_permissions WHERE permission_id LIKE 'perm_test_%';
DELETE FROM organization.family_sharing_resources WHERE sharing_id LIKE 'share_test_%';
DELETE FROM organization.organization_members WHERE organization_id LIKE 'org_test_%';
DELETE FROM organization.organizations WHERE organization_id LIKE 'org_test_%';

-- Verify cleanup
SELECT 'Remaining test organizations:', COUNT(*) FROM organization.organizations WHERE organization_id LIKE 'org_test_%';
SELECT 'Remaining test members:', COUNT(*) FROM organization.organization_members WHERE organization_id LIKE 'org_test_%';
SELECT 'Remaining test sharing:', COUNT(*) FROM organization.family_sharing_resources WHERE sharing_id LIKE 'share_test_%';
SELECT 'Remaining test permissions:', COUNT(*) FROM organization.family_sharing_member_permissions WHERE permission_id LIKE 'perm_test_%';
