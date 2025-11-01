-- Authorization Service: Seed Test Data
-- This script creates test permissions for development and testing

-- Insert test resource permissions (resource_config)
INSERT INTO authz.permissions (permission_type, target_type, target_id, resource_type, resource_name, resource_category, access_level, permission_source, subscription_tier_required, description, is_active, metadata, created_at, updated_at)
VALUES
    ('resource_config', 'global', NULL, 'mcp_tool', 'filesystem_read', 'file_operations', 'read_only', 'system_default', 'free', 'Read access to filesystem', TRUE, '{"max_files": 100}'::jsonb, NOW(), NOW()),
    ('resource_config', 'global', NULL, 'mcp_tool', 'filesystem_write', 'file_operations', 'read_write', 'system_default', 'pro', 'Write access to filesystem', TRUE, '{"max_files": 1000}'::jsonb, NOW(), NOW()),
    ('resource_config', 'global', NULL, 'api_endpoint', 'user_api', 'api', 'read_write', 'system_default', 'free', 'User API access', TRUE, '{"rate_limit": 100}'::jsonb, NOW(), NOW()),
    ('resource_config', 'global', NULL, 'database', 'postgres_read', 'database', 'read_only', 'system_default', 'free', 'Read-only database access', TRUE, '{}'::jsonb, NOW(), NOW()),
    ('resource_config', 'global', NULL, 'ai_model', 'gpt4', 'ai', 'read_write', 'system_default', 'enterprise', 'GPT-4 model access', TRUE, '{"max_tokens": 10000}'::jsonb, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Insert test user permissions
INSERT INTO authz.permissions (permission_type, target_type, target_id, resource_type, resource_name, access_level, permission_source, subscription_tier_required, is_active, metadata, created_at, updated_at)
VALUES
    ('user_permission', 'user', 'test-user-1', 'mcp_tool', 'filesystem_read', 'read_only', 'subscription', 'free', TRUE, '{}'::jsonb, NOW(), NOW()),
    ('user_permission', 'user', 'test-user-2', 'mcp_tool', 'filesystem_write', 'read_write', 'subscription', 'pro', TRUE, '{}'::jsonb, NOW(), NOW()),
    ('user_permission', 'user', 'test-user-3', 'ai_model', 'gpt4', 'read_write', 'subscription', 'enterprise', TRUE, '{}'::jsonb, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Insert test organization permissions
INSERT INTO authz.permissions (permission_type, target_type, target_id, resource_type, resource_name, access_level, permission_source, is_active, metadata, created_at, updated_at)
VALUES
    ('org_permission', 'organization', 'test-org-1', 'api_endpoint', 'user_api', 'admin', 'admin_grant', TRUE, '{"members": 10}'::jsonb, NOW(), NOW()),
    ('org_permission', 'organization', 'test-org-2', 'database', 'postgres_read', 'read_write', 'organization', TRUE, '{}'::jsonb, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Print summary
DO $$
DECLARE
    perm_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO perm_count FROM authz.permissions;
    RAISE NOTICE 'Test data seeded successfully. Total permissions: %', perm_count;
END $$;
