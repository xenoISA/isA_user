-- Album Service Test Data Cleanup Script
-- Removes all test data created by seed_test_data.sql
-- Run: docker exec staging-postgres psql -U postgres -d isa_platform -f /path/to/cleanup_test_data.sql

-- Delete test data in correct order (no foreign keys, but logical order)
DELETE FROM album.album_sync_status WHERE user_id LIKE 'test_%';
DELETE FROM album.album_photos WHERE album_id IN (SELECT album_id FROM album.albums WHERE user_id LIKE 'test_%');
DELETE FROM album.albums WHERE user_id LIKE 'test_%';

-- Print summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Album Service Test Data Cleaned';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'All test albums, album photos, and sync statuses removed.';
    RAISE NOTICE '========================================';
END $$;
