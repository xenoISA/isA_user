-- Storage Service Test Data Cleanup Script
-- Removes all test data created by seed_test_data.sql
-- Run: docker exec staging-postgres psql -U postgres -d isa_platform -f /path/to/cleanup_test_data.sql

-- Delete test data in correct order (no foreign keys, but logical order)
DELETE FROM storage.storage_intelligence_index WHERE user_id LIKE 'test_%';
DELETE FROM storage.file_shares WHERE file_id IN (SELECT file_id FROM storage.storage_files WHERE user_id LIKE 'test_%');
DELETE FROM storage.storage_files WHERE user_id LIKE 'test_%';
DELETE FROM storage.storage_quotas WHERE entity_id LIKE 'test_%';

-- Print summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Storage Service Test Data Cleaned';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'All test files, shares, quotas, and intelligence docs removed.';
    RAISE NOTICE '========================================';
END $$;
