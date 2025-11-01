-- Auth Service Test Data Seed Script
-- Creates sample data for testing auth_service functionality
-- Run: docker exec staging-postgres psql -U postgres -d isa_platform -f /path/to/seed_test_data.sql

-- Clean up existing test data (if any)
DELETE FROM auth.device_logs WHERE device_id LIKE 'test_%';
DELETE FROM auth.devices WHERE device_id LIKE 'test_%';
UPDATE auth.organizations SET api_keys = '[]'::jsonb WHERE organization_id LIKE 'test_%';
DELETE FROM auth.organizations WHERE organization_id LIKE 'test_%';
DELETE FROM auth.users WHERE user_id LIKE 'test_%';

-- Insert test users
INSERT INTO auth.users (user_id, email, name, is_active, created_at, updated_at) VALUES
('test_user_001', 'alice@testorg.com', 'Alice Test', TRUE, NOW(), NOW()),
('test_user_002', 'bob@testorg.com', 'Bob Test', TRUE, NOW(), NOW()),
('test_user_003', 'charlie@testorg.com', 'Charlie Test', TRUE, NOW(), NOW()),
('test_user_004', 'inactive@testorg.com', 'Inactive User', FALSE, NOW(), NOW())
ON CONFLICT (user_id) DO NOTHING;

-- Insert test organizations
INSERT INTO auth.organizations (organization_id, name, api_keys, created_at, updated_at) VALUES
('test_org_001', 'Test Organization Alpha', '[]'::jsonb, NOW(), NOW()),
('test_org_002', 'Test Organization Beta', '[]'::jsonb, NOW(), NOW()),
('test_org_003', 'Test Organization Gamma', '[]'::jsonb, NOW(), NOW())
ON CONFLICT (organization_id) DO NOTHING;

-- Insert test devices
INSERT INTO auth.devices (device_id, device_secret, organization_id, device_name, device_type, status, authentication_count, metadata, created_at, updated_at, expires_at) VALUES
('test_device_001', 'secret_device_001_abc123', 'test_org_001', 'Smart Frame Living Room', 'smart_frame', 'active', 0, '{"model": "SF-2024", "firmware": "1.0.0", "location": "Living Room"}'::jsonb, NOW(), NOW(), NOW() + INTERVAL '365 days'),
('test_device_002', 'secret_device_002_def456', 'test_org_001', 'Smart Frame Bedroom', 'smart_frame', 'active', 0, '{"model": "SF-2024-Pro", "firmware": "1.1.0", "location": "Bedroom"}'::jsonb, NOW(), NOW(), NOW() + INTERVAL '365 days'),
('test_device_003', 'secret_device_003_ghi789', 'test_org_002', 'Mobile Device iPhone', 'mobile', 'active', 0, '{"model": "iPhone 15", "os": "iOS 17"}'::jsonb, NOW(), NOW(), NOW() + INTERVAL '180 days'),
('test_device_004', 'secret_device_004_jkl012', 'test_org_002', 'IoT Sensor Kitchen', 'iot_sensor', 'active', 0, '{"model": "Sensor-X1", "location": "Kitchen"}'::jsonb, NOW(), NOW(), NOW() + INTERVAL '730 days'),
('test_device_005', 'secret_device_005_mno345', 'test_org_001', 'Revoked Device', 'smart_frame', 'revoked', 0, '{"model": "SF-2023", "firmware": "0.9.0"}'::jsonb, NOW(), NOW(), NOW() + INTERVAL '365 days')
ON CONFLICT (device_id) DO NOTHING;

-- Print summary
DO $$
DECLARE
    user_count INTEGER;
    org_count INTEGER;
    device_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM auth.users WHERE user_id LIKE 'test_%';
    SELECT COUNT(*) INTO org_count FROM auth.organizations WHERE organization_id LIKE 'test_%';
    SELECT COUNT(*) INTO device_count FROM auth.devices WHERE device_id LIKE 'test_%';

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Test Data Seeded Successfully';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Users created: %', user_count;
    RAISE NOTICE 'Organizations created: %', org_count;
    RAISE NOTICE 'Devices created: %', device_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Test Users:';
    RAISE NOTICE '  - test_user_001 (alice@testorg.com)';
    RAISE NOTICE '  - test_user_002 (bob@testorg.com)';
    RAISE NOTICE '  - test_user_003 (charlie@testorg.com)';
    RAISE NOTICE '  - test_user_004 (inactive@testorg.com) [INACTIVE]';
    RAISE NOTICE '';
    RAISE NOTICE 'Test Organizations:';
    RAISE NOTICE '  - test_org_001 (Test Organization Alpha)';
    RAISE NOTICE '  - test_org_002 (Test Organization Beta)';
    RAISE NOTICE '  - test_org_003 (Test Organization Gamma)';
    RAISE NOTICE '';
    RAISE NOTICE 'Test Devices:';
    RAISE NOTICE '  - test_device_001 (org: test_org_001) [ACTIVE]';
    RAISE NOTICE '  - test_device_002 (org: test_org_001) [ACTIVE]';
    RAISE NOTICE '  - test_device_003 (org: test_org_002) [ACTIVE]';
    RAISE NOTICE '  - test_device_004 (org: test_org_002) [ACTIVE]';
    RAISE NOTICE '  - test_device_005 (org: test_org_001) [REVOKED]';
    RAISE NOTICE '';
    RAISE NOTICE 'Run tests with: test_org_001 or test_org_002';
    RAISE NOTICE '========================================';
END $$;
