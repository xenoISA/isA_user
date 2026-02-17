-- Seed test data for fulfillment_service

INSERT INTO fulfillment.shipments (shipment_id, order_id, carrier, tracking_number, status)
VALUES
    ('shp_test_01', 'order_test_01', 'mock', 'trk_test_01', 'created')
ON CONFLICT DO NOTHING;
