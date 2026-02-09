-- Seed test data for inventory_service

INSERT INTO inventory.stock_levels (sku_id, location_id, inventory_policy, on_hand, reserved, available)
VALUES
    ('sku_test_physical_01', 'loc_default', 'finite', 100, 0, 100),
    ('sku_test_digital_01', 'loc_default', 'infinite', 0, 0, 0)
ON CONFLICT DO NOTHING;
