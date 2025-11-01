-- Seed test data for Payment Service
-- Schema: payment
-- Date: 2025-10-27

-- Insert test subscription plans
INSERT INTO payment.subscription_plans (
    plan_id, name, description, tier, price_usd, currency, billing_cycle,
    features, credits_included, max_users, max_storage_gb, trial_days,
    is_active, is_public
) VALUES
    ('plan_free', 'Free Plan', 'Basic free tier', 'free', 0.00, 'USD', 'monthly',
     '{"api_calls": 1000, "storage": "1GB"}'::jsonb, 1000, 1, 1, 0, true, true),
    ('plan_basic', 'Basic Plan', 'For individuals', 'basic', 9.99, 'USD', 'monthly',
     '{"api_calls": 10000, "storage": "10GB"}'::jsonb, 10000, 5, 10, 14, true, true),
    ('plan_pro', 'Pro Plan', 'For professionals', 'pro', 29.99, 'USD', 'monthly',
     '{"api_calls": 100000, "storage": "100GB"}'::jsonb, 100000, 20, 100, 14, true, true),
    ('plan_enterprise', 'Enterprise Plan', 'For organizations', 'enterprise', 99.99, 'USD', 'monthly',
     '{"api_calls": -1, "storage": "1TB"}'::jsonb, -1, 100, 1000, 30, true, true)
ON CONFLICT (plan_id) DO NOTHING;

-- Insert test payment methods
INSERT INTO payment.payment_methods (
    method_id, user_id, method_type, is_default, is_verified,
    card_brand, card_last4, card_exp_month, card_exp_year
) VALUES
    ('pm_test_001', 'test_user_001', 'card', true, true, 'Visa', '4242', 12, 2025),
    ('pm_test_002', 'test_user_002', 'card', true, true, 'Mastercard', '5555', 6, 2026)
ON CONFLICT (method_id) DO NOTHING;

-- Insert test subscriptions
INSERT INTO payment.subscriptions (
    subscription_id, user_id, plan_id, status, tier,
    current_period_start, current_period_end, billing_cycle,
    payment_method_id, metadata
) VALUES
    ('sub_test_001', 'test_user_001', 'plan_basic', 'active', 'basic',
     NOW() - INTERVAL '15 days', NOW() + INTERVAL '15 days', 'monthly',
     'pm_test_001', '{}'::jsonb),
    ('sub_test_002', 'test_user_002', 'plan_pro', 'trialing', 'pro',
     NOW() - INTERVAL '5 days', NOW() + INTERVAL '25 days', 'monthly',
     'pm_test_002', '{}'::jsonb)
ON CONFLICT (subscription_id) DO NOTHING;

-- Insert test payments
INSERT INTO payment.transactions (
    payment_id, user_id, subscription_id, amount, currency, status,
    payment_method, description, processor
) VALUES
    ('pay_test_001', 'test_user_001', 'sub_test_001', 9.99, 'USD', 'succeeded',
     'stripe', 'Monthly subscription payment', 'stripe'),
    ('pay_test_002', 'test_user_002', 'sub_test_002', 29.99, 'USD', 'succeeded',
     'stripe', 'Monthly subscription payment', 'stripe')
ON CONFLICT (payment_id) DO NOTHING;

-- Insert test invoices
INSERT INTO payment.invoices (
    invoice_id, invoice_number, user_id, subscription_id, status,
    amount_total, amount_paid, amount_due, currency,
    billing_period_start, billing_period_end,
    line_items
) VALUES
    ('inv_test_001', 'INV-001-TEST', 'test_user_001', 'sub_test_001', 'paid',
     9.99, 9.99, 0.00, 'USD',
     NOW() - INTERVAL '30 days', NOW(),
     '[{"description": "Basic Plan", "amount": 9.99}]'::jsonb),
    ('inv_test_002', 'INV-002-TEST', 'test_user_002', 'sub_test_002', 'open',
     29.99, 0.00, 29.99, 'USD',
     NOW() - INTERVAL '30 days', NOW(),
     '[{"description": "Pro Plan", "amount": 29.99}]'::jsonb)
ON CONFLICT (invoice_id) DO NOTHING;

-- Insert test refund
INSERT INTO payment.refunds (
    refund_id, payment_id, user_id, amount, currency, status,
    reason, requested_by
) VALUES
    ('ref_test_001', 'pay_test_001', 'test_user_001', 9.99, 'USD', 'succeeded',
     'customer_request', 'test_user_001')
ON CONFLICT (refund_id) DO NOTHING;

-- Verify data was inserted
SELECT 'Subscription Plans:', COUNT(*) FROM payment.subscription_plans;
SELECT 'Payment Methods:', COUNT(*) FROM payment.payment_methods;
SELECT 'Subscriptions:', COUNT(*) FROM payment.subscriptions;
SELECT 'Payments:', COUNT(*) FROM payment.transactions;
SELECT 'Invoices:', COUNT(*) FROM payment.invoices;
SELECT 'Refunds:', COUNT(*) FROM payment.refunds;
