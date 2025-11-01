-- Cleanup test data for Payment Service
-- Schema: payment
-- Date: 2025-10-27

-- Delete test data in reverse order of dependencies
DELETE FROM payment.refunds WHERE refund_id LIKE 'ref_test_%';
DELETE FROM payment.invoices WHERE invoice_id LIKE 'inv_test_%';
DELETE FROM payment.transactions WHERE payment_id LIKE 'pay_test_%';
DELETE FROM payment.subscriptions WHERE subscription_id LIKE 'sub_test_%';
DELETE FROM payment.payment_methods WHERE method_id LIKE 'pm_test_%';
DELETE FROM payment.subscription_plans WHERE plan_id LIKE 'plan_%';

-- Verify cleanup
SELECT 'Refunds remaining:', COUNT(*) FROM payment.refunds;
SELECT 'Invoices remaining:', COUNT(*) FROM payment.invoices;
SELECT 'Payments remaining:', COUNT(*) FROM payment.transactions;
SELECT 'Subscriptions remaining:', COUNT(*) FROM payment.subscriptions;
SELECT 'Payment Methods remaining:', COUNT(*) FROM payment.payment_methods;
SELECT 'Plans remaining:', COUNT(*) FROM payment.subscription_plans;
