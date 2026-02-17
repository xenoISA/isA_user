-- Cleanup test data for inventory_service

DELETE FROM inventory.stock_levels WHERE sku_id IN ('sku_test_physical_01', 'sku_test_digital_01');
