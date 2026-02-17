-- Storage Service Test Data Seed Script
-- Creates sample data for testing storage_service functionality
-- Run: docker exec staging-postgres psql -U postgres -d isa_platform -f /path/to/seed_test_data.sql

-- Clean up existing test data (if any)
DELETE FROM storage.storage_intelligence_index WHERE user_id LIKE 'test_%';
DELETE FROM storage.file_shares WHERE file_id IN (SELECT file_id FROM storage.storage_files WHERE user_id LIKE 'test_%');
DELETE FROM storage.storage_files WHERE user_id LIKE 'test_%';
DELETE FROM storage.storage_quotas WHERE entity_id LIKE 'test_%';

-- Insert test quotas
INSERT INTO storage.storage_quotas (quota_type, entity_id, total_quota_bytes, used_bytes, file_count, max_file_size, max_file_count, is_active, created_at, updated_at) VALUES
('user', 'test_user_001', 10737418240, 2147483648, 15, 104857600, 10000, TRUE, NOW(), NOW()),  -- 10GB total, 2GB used
('user', 'test_user_002', 10737418240, 5368709120, 42, 104857600, 10000, TRUE, NOW(), NOW()),  -- 10GB total, 5GB used
('user', 'test_user_003', 10737418240, 0, 0, 104857600, 10000, TRUE, NOW(), NOW()),            -- Empty user
('organization', 'test_org_001', 53687091200, 10737418240, 125, 524288000, 50000, TRUE, NOW(), NOW()),  -- 50GB total, 10GB used
('organization', 'test_org_002', 53687091200, 5368709120, 63, 524288000, 50000, TRUE, NOW(), NOW())     -- 50GB total, 5GB used
ON CONFLICT (quota_type, entity_id) DO NOTHING;

-- Insert test storage files
INSERT INTO storage.storage_files (file_id, user_id, organization_id, file_name, file_path, file_size, content_type, file_extension, storage_provider, bucket_name, object_name, status, access_level, checksum, metadata, tags, uploaded_at, updated_at) VALUES
-- User 001 files
('test_file_001', 'test_user_001', 'test_org_001', 'vacation_photo.jpg', '/photos/2024/vacation_photo.jpg', 2457600, 'image/jpeg', 'jpg', 'minio', 'isa-storage', 'test_user_001/vacation_photo.jpg', 'active', 'private', 'abc123', '{"width": 1920, "height": 1080, "camera": "iPhone 15"}'::jsonb, ARRAY['vacation', 'beach', '2024'], NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days'),
('test_file_002', 'test_user_001', 'test_org_001', 'family_dinner.jpg', '/photos/2024/family_dinner.jpg', 3145728, 'image/jpeg', 'jpg', 'minio', 'isa-storage', 'test_user_001/family_dinner.jpg', 'active', 'shared', 'def456', '{"width": 4032, "height": 3024}'::jsonb, ARRAY['family', 'food'], NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days'),
('test_file_003', 'test_user_001', NULL, 'presentation.pdf', '/documents/presentation.pdf', 5242880, 'application/pdf', 'pdf', 'minio', 'isa-storage', 'test_user_001/presentation.pdf', 'active', 'private', 'ghi789', '{"pages": 24}'::jsonb, ARRAY['work', 'presentation'], NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),

-- User 002 files
('test_file_004', 'test_user_002', 'test_org_001', 'birthday_video.mp4', '/videos/birthday_2024.mp4', 52428800, 'video/mp4', 'mp4', 'minio', 'isa-storage', 'test_user_002/birthday_video.mp4', 'active', 'shared', 'jkl012', '{"duration": 125, "resolution": "1080p"}'::jsonb, ARRAY['birthday', 'family', '2024'], NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days'),
('test_file_005', 'test_user_002', 'test_org_002', 'company_logo.png', '/images/company_logo.png', 524288, 'image/png', 'png', 'minio', 'isa-storage', 'test_user_002/company_logo.png', 'active', 'public', 'mno345', '{"width": 512, "height": 512, "transparent": true}'::jsonb, ARRAY['logo', 'branding'], NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days'),
('test_file_006', 'test_user_002', NULL, 'deleted_file.txt', '/temp/deleted_file.txt', 1024, 'text/plain', 'txt', 'minio', 'isa-storage', 'test_user_002/deleted_file.txt', 'deleted', 'private', 'pqr678', '{}'::jsonb, ARRAY['temp'], NOW() - INTERVAL '7 days', NOW() - INTERVAL '2 days')
ON CONFLICT (file_id) DO NOTHING;

-- Insert test file shares
INSERT INTO storage.file_shares (share_id, file_id, shared_by, shared_with, access_token, permissions, expires_at, is_active, created_at, accessed_at) VALUES
('test_share_001', 'test_file_002', 'test_user_001', 'test_user_002', 'token_abc123', ARRAY['read', 'download'], NOW() + INTERVAL '30 days', TRUE, NOW() - INTERVAL '5 days', NOW() - INTERVAL '1 day'),
('test_share_002', 'test_file_002', 'test_user_001', NULL, 'token_def456', ARRAY['read'], NOW() + INTERVAL '60 days', TRUE, NOW() - INTERVAL '5 days', NULL),
('test_share_003', 'test_file_004', 'test_user_002', 'test_user_001', 'token_ghi789', ARRAY['read', 'download'], NOW() + INTERVAL '14 days', TRUE, NOW() - INTERVAL '10 days', NOW() - INTERVAL '3 days'),
('test_share_004', 'test_file_001', 'test_user_001', 'test_user_003', 'token_jkl012', ARRAY['read'], NOW() - INTERVAL '5 days', FALSE, NOW() - INTERVAL '15 days', NULL)  -- Expired share
ON CONFLICT (share_id) DO NOTHING;

-- Insert test intelligence index (for RAG/AI features)
INSERT INTO storage.storage_intelligence_index (doc_id, file_id, user_id, organization_id, title, content_preview, status, chunking_strategy, chunk_count, metadata, tags, search_count, last_accessed_at, indexed_at, updated_at) VALUES
('test_doc_001', 'test_file_003', 'test_user_001', 'test_org_001', 'Q4 Sales Presentation', 'This presentation covers our Q4 sales performance...', 'indexed', 'semantic', 24, '{"language": "en", "doc_type": "presentation"}'::jsonb, ARRAY['sales', 'q4', 'presentation'], 5, NOW() - INTERVAL '1 day', NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 day'),
('test_doc_002', 'test_file_005', 'test_user_002', 'test_org_002', 'Company Branding Guidelines', 'Brand colors, logo usage, typography guidelines...', 'indexed', 'fixed', 8, '{"language": "en", "doc_type": "image"}'::jsonb, ARRAY['branding', 'design', 'guidelines'], 12, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '30 days', NOW() - INTERVAL '2 hours')
ON CONFLICT (doc_id) DO NOTHING;

-- Print summary
DO $$
DECLARE
    files_count INTEGER;
    shares_count INTEGER;
    quotas_count INTEGER;
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO files_count FROM storage.storage_files WHERE user_id LIKE 'test_%';
    SELECT COUNT(*) INTO shares_count FROM storage.file_shares WHERE shared_by LIKE 'test_%';
    SELECT COUNT(*) INTO quotas_count FROM storage.storage_quotas WHERE entity_id LIKE 'test_%';
    SELECT COUNT(*) INTO index_count FROM storage.storage_intelligence_index WHERE user_id LIKE 'test_%';

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Storage Service Test Data Seeded';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Storage files created: %', files_count;
    RAISE NOTICE 'File shares created: %', shares_count;
    RAISE NOTICE 'Storage quotas created: %', quotas_count;
    RAISE NOTICE 'Intelligence docs indexed: %', index_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Test Files:';
    RAISE NOTICE '  - test_file_001 (vacation_photo.jpg) - User 001';
    RAISE NOTICE '  - test_file_002 (family_dinner.jpg) - User 001 [SHARED]';
    RAISE NOTICE '  - test_file_003 (presentation.pdf) - User 001 [INDEXED]';
    RAISE NOTICE '  - test_file_004 (birthday_video.mp4) - User 002';
    RAISE NOTICE '  - test_file_005 (company_logo.png) - User 002 [PUBLIC]';
    RAISE NOTICE '  - test_file_006 (deleted_file.txt) - User 002 [DELETED]';
    RAISE NOTICE '';
    RAISE NOTICE 'Test Quotas:';
    RAISE NOTICE '  - test_user_001: 2GB/10GB used';
    RAISE NOTICE '  - test_user_002: 5GB/10GB used';
    RAISE NOTICE '  - test_org_001: 10GB/50GB used';
    RAISE NOTICE '  - test_org_002: 5GB/50GB used';
    RAISE NOTICE '========================================';
END $$;
