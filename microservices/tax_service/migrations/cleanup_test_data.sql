-- Cleanup test data for tax_service

DELETE FROM tax.calculations WHERE calculation_id IN ('tax_test_01');
