-- Billing Service Migration: cleanup legacy test-only billing rows
-- Version: 009
-- Date: 2026-04-09
-- Description: removes the known test-product artifacts that were created
--              during early billing experiments before the canonical product
--              catalog and payer model were in place. These rows do not
--              represent customer activity and should not remain in the
--              production billing ledger.

WITH target_records AS (
    SELECT billing_id
    FROM billing.billing_records
    WHERE product_id IN ('test-product', 'test-product-2')
),
target_events AS (
    SELECT id::text AS source_event_id, billing_id
    FROM billing.billing_events
    WHERE billing_id IN (SELECT billing_id FROM target_records)
)
DELETE FROM billing.event_processing_claims
WHERE source_event_id IN (SELECT source_event_id FROM target_events);

WITH target_records AS (
    SELECT billing_id
    FROM billing.billing_records
    WHERE product_id IN ('test-product', 'test-product-2')
)
DELETE FROM billing.billing_events
WHERE billing_id IN (SELECT billing_id FROM target_records);

DELETE FROM billing.billing_records
WHERE product_id IN ('test-product', 'test-product-2');
