-- Media Service Test Data Cleanup Script
-- Removes all test data created by seed_test_data.sql
-- Run: docker exec staging-postgres psql -U postgres -d isa_platform -f /path/to/cleanup_test_data.sql

-- Delete test data in correct order (no foreign keys, but logical order)
DELETE FROM media.photo_cache WHERE user_id LIKE 'test_%';
DELETE FROM media.rotation_schedules WHERE user_id LIKE 'test_%';
DELETE FROM media.playlists WHERE user_id LIKE 'test_%';
DELETE FROM media.photo_metadata WHERE file_id IN (SELECT file_id FROM storage.storage_files WHERE user_id LIKE 'test_%');
DELETE FROM media.photo_versions WHERE user_id LIKE 'test_%';

-- Print summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Media Service Test Data Cleaned';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'All test photo versions, metadata, playlists, schedules, and cache removed.';
    RAISE NOTICE '========================================';
END $$;
