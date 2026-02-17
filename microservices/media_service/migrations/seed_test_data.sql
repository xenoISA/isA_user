-- Media Service Test Data Seed Script
-- Creates sample data for testing media_service functionality
-- Run: docker exec staging-postgres psql -U postgres -d isa_platform -f /path/to/seed_test_data.sql
-- NOTE: Requires storage_service test data to be seeded first (for photo references)

-- Clean up existing test data (if any)
DELETE FROM media.photo_cache WHERE user_id LIKE 'test_%';
DELETE FROM media.rotation_schedules WHERE user_id LIKE 'test_%';
DELETE FROM media.playlists WHERE user_id LIKE 'test_%';
DELETE FROM media.photo_metadata WHERE file_id IN (SELECT file_id FROM storage.storage_files WHERE user_id LIKE 'test_%');
DELETE FROM media.photo_versions WHERE user_id LIKE 'test_%';

-- Insert test photo versions (AI-processed versions)
INSERT INTO media.photo_versions (version_id, photo_id, user_id, organization_id, version_name, version_type, processing_mode, file_id, cloud_url, local_path, file_size, processing_params, metadata, is_current, version_number, created_at, updated_at) VALUES
-- Versions for test_file_001 (vacation_photo.jpg)
('test_version_001', 'test_file_001', 'test_user_001', 'test_org_001', 'Original', 'original', NULL, 'test_file_001', 'https://minio.example.com/test_file_001', NULL, 2457600, '{}'::jsonb, '{"width": 1920, "height": 1080}'::jsonb, TRUE, 1, NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days'),
('test_version_002', 'test_file_001', 'test_user_001', 'test_org_001', 'AI Enhanced', 'ai_enhanced', 'enhance_quality', 'test_file_001_enhanced', 'https://minio.example.com/test_file_001_enhanced', '/cache/test_file_001_enhanced.jpg', 2800000, '{"brightness": 1.1, "contrast": 1.05, "sharpness": 1.2}'::jsonb, '{"ai_model": "enhance-v2", "processing_time": 2.3}'::jsonb, FALSE, 2, NOW() - INTERVAL '9 days', NOW() - INTERVAL '9 days'),
('test_version_003', 'test_file_001', 'test_user_001', 'test_org_001', 'Artistic Style', 'ai_styled', 'artistic_style', 'test_file_001_artistic', 'https://minio.example.com/test_file_001_artistic', NULL, 3200000, '{"style": "impressionist", "strength": 0.7}'::jsonb, '{"ai_model": "style-transfer-v1"}'::jsonb, FALSE, 3, NOW() - INTERVAL '8 days', NOW() - INTERVAL '8 days'),

-- Versions for test_file_002 (family_dinner.jpg)
('test_version_004', 'test_file_002', 'test_user_001', 'test_org_001', 'Original', 'original', NULL, 'test_file_002', 'https://minio.example.com/test_file_002', NULL, 3145728, '{}'::jsonb, '{"width": 4032, "height": 3024}'::jsonb, TRUE, 1, NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days'),
('test_version_005', 'test_file_002', 'test_user_001', 'test_org_001', 'Background Removed', 'ai_background_removed', 'background_remove', 'test_file_002_nobg', 'https://minio.example.com/test_file_002_nobg', NULL, 1800000, '{"keep_subject": "people"}'::jsonb, '{"ai_model": "bg-remove-v3", "transparency": true}'::jsonb, FALSE, 2, NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 days')
ON CONFLICT (version_id) DO NOTHING;

-- Insert test photo metadata (EXIF and AI analysis)
INSERT INTO media.photo_metadata (file_id, user_id, organization_id, camera_make, camera_model, lens_model, focal_length, aperture, shutter_speed, iso, flash_used, latitude, longitude, location_name, photo_taken_at, ai_labels, ai_objects, ai_scenes, ai_colors, face_detection, text_detection, quality_score, blur_score, brightness, contrast, full_metadata, created_at, updated_at) VALUES
-- Metadata for test_file_001
('test_file_001', 'test_user_001', 'test_org_001', 'Apple', 'iPhone 15 Pro', 'iPhone 15 Pro back camera', '24mm', 'f/1.8', '1/500', 100, FALSE, 21.3099, -157.8581, 'Waikiki Beach, Hawaii', NOW() - INTERVAL '10 days', '["beach", "ocean", "sunset", "tropical"]'::jsonb, '["water", "sky", "sand", "palm_trees"]'::jsonb, '["beach", "sunset", "outdoor"]'::jsonb, '["#FF6B35", "#004E89", "#FFD23F"]'::jsonb, '{"detected": true, "count": 2, "positions": [{"x": 100, "y": 200, "w": 150, "h": 200}]}'::jsonb, '{"detected": false}'::jsonb, 8.5, 9.2, 7.8, 8.1, '{"copyright": "Test User 001"}'::jsonb, NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days'),

-- Metadata for test_file_002
('test_file_002', 'test_user_001', 'test_org_001', 'Apple', 'iPhone 15 Pro', 'iPhone 15 Pro back camera', '24mm', 'f/1.8', '1/60', 400, TRUE, 37.7749, -122.4194, 'San Francisco, CA', NOW() - INTERVAL '5 days', '["food", "restaurant", "dining", "family"]'::jsonb, '["table", "food", "people", "dishes", "drinks"]'::jsonb, '["indoor", "restaurant", "dining"]'::jsonb, '["#8B4513", "#FFE4B5", "#CD853F"]'::jsonb, '{"detected": true, "count": 4, "positions": []}'::jsonb, '{"detected": false}'::jsonb, 7.9, 8.0, 6.5, 7.2, '{}'::jsonb, NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days'),

-- Metadata for test_file_004
('test_file_004', 'test_user_002', 'test_org_001', 'Sony', 'A7 IV', 'Sony FE 24-70mm F2.8 GM', '50mm', 'f/2.8', '1/125', 800, FALSE, 40.7128, -74.0060, 'New York, NY', NOW() - INTERVAL '15 days', '["birthday", "party", "celebration", "indoor"]'::jsonb, '["cake", "balloons", "people", "decorations"]'::jsonb, '["party", "celebration", "indoor"]'::jsonb, '["#FF69B4", "#87CEEB", "#FFD700"]'::jsonb, '{"detected": true, "count": 8, "positions": []}'::jsonb, '{"detected": true, "text": ["Happy Birthday"]}'::jsonb, 8.8, 8.5, 7.5, 8.0, '{"event": "birthday_party"}'::jsonb, NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days')
ON CONFLICT (file_id) DO NOTHING;

-- Insert test playlists
INSERT INTO media.playlists (playlist_id, name, description, user_id, organization_id, playlist_type, smart_criteria, photo_ids, shuffle, loop, transition_duration, created_at, updated_at) VALUES
('test_playlist_001', 'Best Vacation Moments', 'Top photos from vacation', 'test_user_001', 'test_org_001', 'manual', NULL, '["test_file_001", "test_file_002"]'::jsonb, FALSE, TRUE, 5, NOW() - INTERVAL '10 days', NOW() - INTERVAL '2 days'),
('test_playlist_002', 'AI Curated - Beach Photos', 'Smart playlist with beach photos', 'test_user_001', 'test_org_001', 'smart', '{"tags": ["beach", "ocean"], "min_quality": 7.5}'::jsonb, '[]'::jsonb, TRUE, TRUE, 8, NOW() - INTERVAL '8 days', NOW() - INTERVAL '8 days'),
('test_playlist_003', 'Family Events', 'All family gatherings and celebrations', 'test_user_001', 'test_org_001', 'manual', NULL, '["test_file_002", "test_file_004"]'::jsonb, FALSE, TRUE, 6, NOW() - INTERVAL '5 days', NOW() - INTERVAL '1 day'),
('test_playlist_004', 'Birthday Party Slideshow', 'Birthday celebration photos', 'test_user_002', 'test_org_002', 'manual', NULL, '["test_file_004"]'::jsonb, FALSE, FALSE, 4, NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days')
ON CONFLICT (playlist_id) DO NOTHING;

-- Insert test rotation schedules
INSERT INTO media.rotation_schedules (schedule_id, user_id, frame_id, playlist_id, schedule_type, start_time, end_time, days_of_week, rotation_interval, shuffle, is_active, created_at, updated_at) VALUES
('test_schedule_001', 'test_user_001', 'test_device_001', 'test_playlist_001', 'time_based', '08:00', '22:00', ARRAY[1,2,3,4,5], 10, FALSE, TRUE, NOW() - INTERVAL '10 days', NOW() - INTERVAL '1 day'),
('test_schedule_002', 'test_user_001', 'test_device_002', 'test_playlist_002', 'continuous', NULL, NULL, ARRAY[0,1,2,3,4,5,6], 15, TRUE, TRUE, NOW() - INTERVAL '8 days', NOW() - INTERVAL '8 days'),
('test_schedule_003', 'test_user_001', 'test_device_001', 'test_playlist_003', 'time_based', '18:00', '23:00', ARRAY[0,6], 8, FALSE, TRUE, NOW() - INTERVAL '5 days', NOW() - INTERVAL '1 day'),
('test_schedule_004', 'test_user_002', 'test_device_003', 'test_playlist_004', 'continuous', NULL, NULL, ARRAY[0,1,2,3,4,5,6], 12, FALSE, FALSE, NOW() - INTERVAL '15 days', NOW() - INTERVAL '10 days')
ON CONFLICT (schedule_id) DO NOTHING;

-- Insert test photo cache
INSERT INTO media.photo_cache (cache_id, user_id, frame_id, photo_id, version_id, cache_status, cached_url, local_path, cache_size, cache_format, cache_quality, hit_count, last_accessed_at, error_message, retry_count, created_at, updated_at, expires_at) VALUES
('test_cache_001', 'test_user_001', 'test_device_001', 'test_file_001', 'test_version_001', 'cached', 'https://minio.example.com/test_file_001', '/cache/frame001/test_file_001.jpg', 2457600, 'jpeg', 'high', 15, NOW() - INTERVAL '1 day', NULL, 0, NOW() - INTERVAL '10 days', NOW() - INTERVAL '1 day', NOW() + INTERVAL '30 days'),
('test_cache_002', 'test_user_001', 'test_device_001', 'test_file_002', 'test_version_004', 'cached', 'https://minio.example.com/test_file_002', '/cache/frame001/test_file_002.jpg', 3145728, 'jpeg', 'high', 8, NOW() - INTERVAL '2 hours', NULL, 0, NOW() - INTERVAL '5 days', NOW() - INTERVAL '2 hours', NOW() + INTERVAL '30 days'),
('test_cache_003', 'test_user_001', 'test_device_002', 'test_file_001', 'test_version_002', 'cached', 'https://minio.example.com/test_file_001_enhanced', '/cache/frame002/test_file_001_enhanced.jpg', 2800000, 'jpeg', 'high', 3, NOW() - INTERVAL '3 days', NULL, 0, NOW() - INTERVAL '9 days', NOW() - INTERVAL '3 days', NOW() + INTERVAL '30 days'),
('test_cache_004', 'test_user_002', 'test_device_003', 'test_file_004', NULL, 'downloading', NULL, NULL, NULL, 'jpeg', 'high', 0, NULL, NULL, 0, NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour', NOW() + INTERVAL '30 days'),
('test_cache_005', 'test_user_001', 'test_device_001', 'test_file_004', NULL, 'failed', NULL, NULL, NULL, 'jpeg', 'high', 0, NULL, 'Network timeout', 3, NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 hours', NOW() + INTERVAL '30 days')
ON CONFLICT (cache_id) DO NOTHING;

-- Print summary
DO $$
DECLARE
    versions_count INTEGER;
    metadata_count INTEGER;
    playlists_count INTEGER;
    schedules_count INTEGER;
    cache_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO versions_count FROM media.photo_versions WHERE user_id LIKE 'test_%';
    SELECT COUNT(*) INTO metadata_count FROM media.photo_metadata WHERE user_id LIKE 'test_%';
    SELECT COUNT(*) INTO playlists_count FROM media.playlists WHERE user_id LIKE 'test_%';
    SELECT COUNT(*) INTO schedules_count FROM media.rotation_schedules WHERE user_id LIKE 'test_%';
    SELECT COUNT(*) INTO cache_count FROM media.photo_cache WHERE user_id LIKE 'test_%';

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Media Service Test Data Seeded';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Photo versions created: %', versions_count;
    RAISE NOTICE 'Photo metadata created: %', metadata_count;
    RAISE NOTICE 'Playlists created: %', playlists_count;
    RAISE NOTICE 'Rotation schedules created: %', schedules_count;
    RAISE NOTICE 'Photo cache entries created: %', cache_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Test Photo Versions:';
    RAISE NOTICE '  - test_file_001: 3 versions (original, enhanced, artistic)';
    RAISE NOTICE '  - test_file_002: 2 versions (original, bg-removed)';
    RAISE NOTICE '';
    RAISE NOTICE 'Test Playlists:';
    RAISE NOTICE '  - test_playlist_001 (Best Vacation Moments) [MANUAL]';
    RAISE NOTICE '  - test_playlist_002 (AI Curated - Beach Photos) [SMART]';
    RAISE NOTICE '  - test_playlist_003 (Family Events) [MANUAL]';
    RAISE NOTICE '  - test_playlist_004 (Birthday Party Slideshow) [MANUAL]';
    RAISE NOTICE '';
    RAISE NOTICE 'Cache Status:';
    RAISE NOTICE '  - 3 cached photos';
    RAISE NOTICE '  - 1 downloading';
    RAISE NOTICE '  - 1 failed';
    RAISE NOTICE '';
    RAISE NOTICE 'NOTE: Media test data references storage_service test files';
    RAISE NOTICE '      Ensure storage test data is seeded first!';
    RAISE NOTICE '========================================';
END $$;
