-- Organization Service Test Data
-- Purpose: Seed test data for organization service testing
-- Schema: organization

-- Insert test organizations
INSERT INTO organization.organizations (
    organization_id, name, display_name, billing_email, plan, status, credits_pool, settings, metadata, api_keys
) VALUES
    ('org_test_001', 'Test Organization 1', 'Test Org 1', 'billing@test1.com', 'free', 'active', 1000.0, '{}', '{}', '[]'),
    ('org_test_002', 'Test Organization 2', 'Test Org 2', 'billing@test2.com', 'professional', 'active', 5000.0, '{}', '{}', '[]'),
    ('org_test_003', 'Test Organization 3', 'Test Org 3', 'billing@test3.com', 'enterprise', 'active', 10000.0, '{}', '{}', '[]')
ON CONFLICT (organization_id) DO NOTHING;

-- Insert test organization members
INSERT INTO organization.organization_members (
    organization_id, user_id, role, status, permissions, is_founder
) VALUES
    ('org_test_001', 'user_test_001', 'owner', 'active', '[]', true),
    ('org_test_001', 'user_test_002', 'admin', 'active', '[]', false),
    ('org_test_001', 'user_test_003', 'member', 'active', '[]', false),
    ('org_test_002', 'user_test_002', 'owner', 'active', '[]', true),
    ('org_test_002', 'user_test_004', 'member', 'active', '[]', false),
    ('org_test_003', 'user_test_001', 'owner', 'active', '[]', true)
ON CONFLICT (organization_id, user_id) DO NOTHING;

-- Insert test family sharing resources
INSERT INTO organization.family_sharing_resources (
    sharing_id, organization_id, resource_type, resource_id, resource_name,
    created_by, share_with_all_members, default_permission, status,
    quota_settings, restrictions, metadata
) VALUES
    ('share_test_001', 'org_test_001', 'storage', 'storage_001', 'Family Storage',
     'user_test_001', true, 'read_write', 'active', '{}', '{}', '{}'),
    ('share_test_002', 'org_test_001', 'device', 'device_001', 'Family Frame',
     'user_test_001', false, 'read_only', 'active', '{}', '{}', '{}'),
    ('share_test_003', 'org_test_002', 'subscription', 'sub_001', 'Premium Subscription',
     'user_test_002', true, 'view_only', 'active', '{}', '{}', '{}')
ON CONFLICT (organization_id, resource_type, resource_id) DO NOTHING;

-- Insert test family sharing member permissions
INSERT INTO organization.family_sharing_member_permissions (
    permission_id, sharing_id, user_id, permission_level,
    quota_allocated, quota_used, restrictions, is_active
) VALUES
    ('perm_test_001', 'share_test_001', 'user_test_002', 'read_write', '{}', '{}', '{}', true),
    ('perm_test_002', 'share_test_001', 'user_test_003', 'read_only', '{}', '{}', '{}', true),
    ('perm_test_003', 'share_test_002', 'user_test_002', 'full_access', '{}', '{}', '{}', true)
ON CONFLICT (sharing_id, user_id) DO NOTHING;

-- Verify test data
SELECT 'Organizations:', COUNT(*) FROM organization.organizations WHERE organization_id LIKE 'org_test_%';
SELECT 'Members:', COUNT(*) FROM organization.organization_members WHERE organization_id LIKE 'org_test_%';
SELECT 'Sharing Resources:', COUNT(*) FROM organization.family_sharing_resources WHERE sharing_id LIKE 'share_test_%';
SELECT 'Member Permissions:', COUNT(*) FROM organization.family_sharing_member_permissions WHERE permission_id LIKE 'perm_test_%';
