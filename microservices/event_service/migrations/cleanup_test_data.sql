-- Cleanup test data for Event Service
-- Schema: event
-- Date: 2025-10-27

-- Delete test data
DELETE FROM event.processing_results WHERE event_id LIKE 'event_test_%';
DELETE FROM event.events WHERE event_id LIKE 'event_test_%';
DELETE FROM event.event_subscriptions WHERE subscription_id LIKE 'sub_test_%';

-- Verify cleanup
SELECT 'Events remaining:', COUNT(*) FROM event.events;
SELECT 'Subscriptions remaining:', COUNT(*) FROM event.event_subscriptions;
