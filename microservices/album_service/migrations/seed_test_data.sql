-- Album Service Test Data Seed Script
-- Creates sample data for testing album_service functionality
-- Run: docker exec staging-postgres psql -U postgres -d isa_platform -f /path/to/seed_test_data.sql
-- NOTE: Requires storage_service test data to be seeded first (for photo references)

-- Clean up existing test data (if any)
DELETE FROM album.album_sync_status WHERE user_id LIKE 'test_%';
DELETE FROM album.album_photos WHERE album_id IN (SELECT album_id FROM album.albums WHERE user_id LIKE 'test_%');
DELETE FROM album.albums WHERE user_id LIKE 'test_%';

-- Insert test albums
INSERT INTO album.albums (album_id, name, description, user_id, organization_id, cover_photo_id, photo_count, auto_sync, sync_frames, is_family_shared, sharing_resource_id, tags, metadata, created_at, updated_at, last_synced_at) VALUES
-- User 001 albums
('test_album_001', 'Summer Vacation 2024', 'Photos from our amazing summer trip to Hawaii', 'test_user_001', 'test_org_001', 'test_file_001', 3, TRUE, '["test_device_001", "test_device_002"]'::jsonb, TRUE, 'test_share_res_001', '["vacation", "summer", "2024", "hawaii"]'::jsonb, '{"location": "Hawaii", "year": 2024}'::jsonb, NOW() - INTERVAL '10 days', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day'),
('test_album_002', 'Family Moments', 'Special family gatherings and events', 'test_user_001', 'test_org_001', 'test_file_002', 2, TRUE, '["test_device_001"]'::jsonb, TRUE, 'test_share_res_002', '["family", "memories"]'::jsonb, '{"type": "family"}'::jsonb, NOW() - INTERVAL '5 days', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours'),
('test_album_003', 'Work Projects', 'Project documentation and presentations', 'test_user_001', NULL, 'test_file_003', 1, FALSE, '[]'::jsonb, FALSE, NULL, '["work", "projects"]'::jsonb, '{"category": "professional"}'::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days', NULL),

-- User 002 albums
('test_album_004', 'Birthday Party 2024', 'Memorable birthday celebration', 'test_user_002', 'test_org_001', 'test_file_004', 2, TRUE, '["test_device_003"]'::jsonb, TRUE, 'test_share_res_003', '["birthday", "party", "2024"]'::jsonb, '{"event_date": "2024-09-15"}'::jsonb, NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days', NOW() - INTERVAL '10 days'),
('test_album_005', 'Company Brand Assets', 'Logo and branding materials', 'test_user_002', 'test_org_002', 'test_file_005', 1, FALSE, '[]'::jsonb, FALSE, NULL, '["branding", "company"]'::jsonb, '{"access": "team-wide"}'::jsonb, NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days', NULL)
ON CONFLICT (album_id) DO NOTHING;

-- Insert test album photos (junction table)
INSERT INTO album.album_photos (album_id, photo_id, added_by, added_at, is_featured, display_order, ai_tags, ai_objects, ai_scenes, face_detection_results) VALUES
-- Summer Vacation album
('test_album_001', 'test_file_001', 'test_user_001', NOW() - INTERVAL '10 days', TRUE, 1, '["beach", "ocean", "sunset"]'::jsonb, '["water", "sky", "sand"]'::jsonb, '["beach", "sunset"]'::jsonb, '{"faces": 2, "people": ["Alice", "Bob"]}'::jsonb),
('test_album_001', 'test_file_002', 'test_user_001', NOW() - INTERVAL '9 days', FALSE, 2, '["food", "restaurant", "dining"]'::jsonb, '["table", "food", "drinks"]'::jsonb, '["restaurant"]'::jsonb, '{"faces": 4}'::jsonb),
('test_album_001', 'test_file_004', 'test_user_001', NOW() - INTERVAL '8 days', FALSE, 3, '["celebration", "party"]'::jsonb, '["cake", "balloons"]'::jsonb, '["party"]'::jsonb, '{"faces": 5}'::jsonb),

-- Family Moments album
('test_album_002', 'test_file_002', 'test_user_001', NOW() - INTERVAL '5 days', TRUE, 1, '["family", "dinner"]'::jsonb, '["table", "food"]'::jsonb, '["indoor", "dining"]'::jsonb, '{"faces": 4}'::jsonb),
('test_album_002', 'test_file_001', 'test_user_001', NOW() - INTERVAL '4 days', FALSE, 2, '["vacation", "beach"]'::jsonb, '["water", "sky"]'::jsonb, '["beach"]'::jsonb, '{"faces": 2}'::jsonb),

-- Work Projects album
('test_album_003', 'test_file_003', 'test_user_001', NOW() - INTERVAL '3 days', TRUE, 1, '["document", "presentation"]'::jsonb, '["text", "charts"]'::jsonb, '["office"]'::jsonb, NULL),

-- Birthday Party album
('test_album_004', 'test_file_004', 'test_user_002', NOW() - INTERVAL '15 days', TRUE, 1, '["birthday", "party", "celebration"]'::jsonb, '["cake", "balloons", "presents"]'::jsonb, '["party", "indoor"]'::jsonb, '{"faces": 8}'::jsonb),
('test_album_004', 'test_file_001', 'test_user_002', NOW() - INTERVAL '14 days', FALSE, 2, '["photo", "memories"]'::jsonb, '["people"]'::jsonb, '["outdoor"]'::jsonb, '{"faces": 2}'::jsonb),

-- Company Brand Assets album
('test_album_005', 'test_file_005', 'test_user_002', NOW() - INTERVAL '30 days', TRUE, 1, '["logo", "branding"]'::jsonb, '["logo", "text"]'::jsonb, '["graphic"]'::jsonb, NULL)
ON CONFLICT (album_id, photo_id) DO NOTHING;

-- Insert test album sync status (for smart frame synchronization)
INSERT INTO album.album_sync_status (album_id, user_id, frame_id, last_sync_timestamp, sync_version, total_photos, synced_photos, pending_photos, failed_photos, sync_status, error_message, created_at, updated_at) VALUES
('test_album_001', 'test_user_001', 'test_device_001', NOW() - INTERVAL '1 day', 3, 3, 3, 0, 0, 'completed', NULL, NOW() - INTERVAL '10 days', NOW() - INTERVAL '1 day'),
('test_album_001', 'test_user_001', 'test_device_002', NOW() - INTERVAL '2 hours', 3, 3, 2, 1, 0, 'in_progress', NULL, NOW() - INTERVAL '10 days', NOW() - INTERVAL '2 hours'),
('test_album_002', 'test_user_001', 'test_device_001', NOW() - INTERVAL '2 hours', 2, 2, 2, 0, 0, 'completed', NULL, NOW() - INTERVAL '5 days', NOW() - INTERVAL '2 hours'),
('test_album_004', 'test_user_002', 'test_device_003', NOW() - INTERVAL '10 days', 2, 2, 2, 0, 0, 'completed', NULL, NOW() - INTERVAL '15 days', NOW() - INTERVAL '10 days'),
('test_album_003', 'test_user_001', 'test_device_001', NOW() - INTERVAL '1 hour', 1, 1, 0, 0, 1, 'failed', 'Network timeout during sync', NOW() - INTERVAL '3 days', NOW() - INTERVAL '1 hour')
ON CONFLICT (album_id, frame_id) DO NOTHING;

-- Print summary
DO $$
DECLARE
    albums_count INTEGER;
    photos_count INTEGER;
    sync_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO albums_count FROM album.albums WHERE user_id LIKE 'test_%';
    SELECT COUNT(*) INTO photos_count FROM album.album_photos WHERE album_id IN (SELECT album_id FROM album.albums WHERE user_id LIKE 'test_%');
    SELECT COUNT(*) INTO sync_count FROM album.album_sync_status WHERE user_id LIKE 'test_%';

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Album Service Test Data Seeded';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Albums created: %', albums_count;
    RAISE NOTICE 'Album photos added: %', photos_count;
    RAISE NOTICE 'Sync statuses created: %', sync_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Test Albums:';
    RAISE NOTICE '  - test_album_001 (Summer Vacation 2024) - 3 photos [FAMILY SHARED]';
    RAISE NOTICE '  - test_album_002 (Family Moments) - 2 photos [FAMILY SHARED]';
    RAISE NOTICE '  - test_album_003 (Work Projects) - 1 photo [PRIVATE]';
    RAISE NOTICE '  - test_album_004 (Birthday Party 2024) - 2 photos [FAMILY SHARED]';
    RAISE NOTICE '  - test_album_005 (Company Brand Assets) - 1 photo [PRIVATE]';
    RAISE NOTICE '';
    RAISE NOTICE 'Sync Status:';
    RAISE NOTICE '  - 3 completed syncs';
    RAISE NOTICE '  - 1 in-progress sync';
    RAISE NOTICE '  - 1 failed sync';
    RAISE NOTICE '';
    RAISE NOTICE 'NOTE: Album photos reference storage_service test files';
    RAISE NOTICE '      Ensure storage test data is seeded first!';
    RAISE NOTICE '========================================';
END $$;
