-- Cleanup test data for fulfillment_service

DELETE FROM fulfillment.shipments WHERE shipment_id IN ('shp_test_01');
