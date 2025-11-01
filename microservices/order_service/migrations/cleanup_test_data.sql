-- Cleanup test data for Order Service
-- Schema: orders
-- Date: 2025-10-27

-- Delete test data
DELETE FROM orders.orders WHERE order_id LIKE 'order_test_%';

-- Verify cleanup
SELECT 'Orders remaining:', COUNT(*) FROM orders.orders;
