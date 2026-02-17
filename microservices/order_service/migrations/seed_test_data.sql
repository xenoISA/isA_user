-- Seed test data for Order Service
-- Schema: orders
-- Date: 2025-10-27

INSERT INTO orders.orders (
    order_id, user_id, order_type, status, total_amount, currency,
    discount_amount, tax_amount, final_amount, payment_status,
    items, metadata, fulfillment_status
) VALUES
    ('order_test_001', 'test_user_001', 'purchase', 'completed', 99.99, 'USD',
     0.0, 9.99, 109.98, 'completed',
     '[{"name": "Premium Subscription", "quantity": 1, "price": 99.99}]'::jsonb, '{}'::jsonb, 'delivered'),
    ('order_test_002', 'test_user_002', 'credit_purchase', 'pending', 50.00, 'USD',
     0.0, 0.0, 50.00, 'pending',
     '[{"name": "1000 Credits", "quantity": 1, "price": 50.00}]'::jsonb, '{}'::jsonb, 'pending')
ON CONFLICT (order_id) DO NOTHING;

SELECT 'Orders:', COUNT(*) FROM orders.orders;
