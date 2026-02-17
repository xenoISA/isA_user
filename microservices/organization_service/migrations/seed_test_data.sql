-- Organization Service Test Data
-- Standardized test data following test_data_standard.md
-- Date: 2025-11-11

-- Insert test organizations
INSERT INTO organization.organizations (
    organization_id, name, display_name, billing_email, plan, status, credits_pool, settings, metadata, api_keys
) VALUES
    ('test_org_001', 'Test Organization Alpha', 'Test Org Alpha', 'billing-alpha@example.com', 'free', 'active', 1000.0, '{}', '{}', '[]'),
    ('test_org_002', 'Test Organization Beta', 'Test Org Beta', 'billing-beta@example.com', 'professional', 'active', 5000.0, '{}', '{}', '[]'),
    ('test_org_003', 'Test Organization Gamma', 'Test Org Gamma', 'billing-gamma@example.com', 'enterprise', 'active', 10000.0, '{}', '{}', '[]')
ON CONFLICT (organization_id) DO NOTHING;

-- Insert test organization members (using standardized user IDs)
INSERT INTO organization.organization_members (
    organization_id, user_id, role, status, permissions, is_founder
) VALUES
    ('test_org_001', 'test_user_001', 'owner', 'active', '[]', true),
    ('test_org_001', 'test_user_002', 'admin', 'active', '[]', false),
    ('test_org_001', 'test_user_003', 'member', 'active', '[]', false),
    ('test_org_002', 'test_user_002', 'owner', 'active', '[]', true),
    ('test_org_002', 'test_user_003', 'member', 'active', '[]', false),
    ('test_org_003', 'test_user_001', 'owner', 'active', '[]', true)
ON CONFLICT (organization_id, user_id) DO NOTHING;

-- Insert test family sharing resources
INSERT INTO organization.family_sharing_resources (
    sharing_id, organization_id, resource_type, resource_id, resource_name,
    created_by, share_with_all_members, default_permission, status,
    quota_settings, restrictions, metadata
) VALUES
    ('test_share_001', 'test_org_001', 'storage', 'test_storage_001', 'Family Storage',
     'test_user_001', true, 'read_write', 'active', '{}', '{}', '{}'),
    ('test_share_002', 'test_org_001', 'device', 'test_device_001', 'Family Frame',
     'test_user_001', false, 'read_only', 'active', '{}', '{}', '{}'),
    ('test_share_003', 'test_org_002', 'subscription', 'test_sub_001', 'Premium Subscription',
     'test_user_002', true, 'view_only', 'active', '{}', '{}', '{}')
ON CONFLICT (organization_id, resource_type, resource_id) DO NOTHING;

-- Insert test family sharing member permissions
INSERT INTO organization.family_sharing_member_permissions (
    permission_id, sharing_id, user_id, permission_level,
    quota_allocated, quota_used, restrictions, is_active
) VALUES
    ('test_perm_001', 'test_share_001', 'test_user_002', 'read_write', '{}', '{}', '{}', true),
    ('test_perm_002', 'test_share_001', 'test_user_003', 'read_only', '{}', '{}', '{}', true),
    ('test_perm_003', 'test_share_002', 'test_user_002', 'full_access', '{}', '{}', '{}', true)
ON CONFLICT (sharing_id, user_id) DO NOTHING;

-- Verify test data
SELECT 'Organizations:', COUNT(*) FROM organization.organizations WHERE organization_id LIKE 'test_org_%';
SELECT 'Members:', COUNT(*) FROM organization.organization_members WHERE organization_id LIKE 'test_org_%';
SELECT 'Sharing Resources:', COUNT(*) FROM organization.family_sharing_resources WHERE sharing_id LIKE 'test_share_%';
SELECT 'Member Permissions:', COUNT(*) FROM organization.family_sharing_member_permissions WHERE permission_id LIKE 'test_perm_%';
