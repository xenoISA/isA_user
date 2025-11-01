-- Cleanup test data for Notification Service
-- Schema: notification
-- Date: 2025-10-27

-- Delete test push subscriptions
DELETE FROM notification.push_subscriptions
WHERE subscription_id LIKE 'sub_test_%';

-- Delete test notification batches
DELETE FROM notification.notification_batches
WHERE batch_id LIKE 'batch_test_%';

-- Delete test in-app notifications
DELETE FROM notification.in_app_notifications
WHERE notification_id LIKE 'inapp_test_%';

-- Delete test notifications
DELETE FROM notification.notifications
WHERE notification_id LIKE 'notif_test_%';

-- Delete test notification templates
DELETE FROM notification.notification_templates
WHERE template_id LIKE 'tmpl_test_%';

-- Verify cleanup
SELECT 'Templates remaining:', COUNT(*) FROM notification.notification_templates;
SELECT 'Notifications remaining:', COUNT(*) FROM notification.notifications;
SELECT 'In-App Notifications remaining:', COUNT(*) FROM notification.in_app_notifications;
SELECT 'Batches remaining:', COUNT(*) FROM notification.notification_batches;
SELECT 'Push Subscriptions remaining:', COUNT(*) FROM notification.push_subscriptions;
