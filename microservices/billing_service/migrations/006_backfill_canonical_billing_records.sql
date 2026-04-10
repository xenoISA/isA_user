-- Billing Service Migration: repair canonical payer fields on legacy records
-- Version: 006
-- Date: 2026-04-09
-- Description: backfills actor/payer attribution on rows written after the
--              schema migration but before the canonical write path fix.

UPDATE billing.billing_records
SET actor_user_id = COALESCE(actor_user_id, user_id),
    billing_account_type = COALESCE(
        billing_account_type,
        CASE
            WHEN organization_id IS NOT NULL AND organization_id <> '' THEN 'organization'
            ELSE 'user'
        END
    ),
    billing_account_id = COALESCE(
        billing_account_id,
        CASE
            WHEN organization_id IS NOT NULL AND organization_id <> '' THEN organization_id
            ELSE user_id
        END
    ),
    billing_metadata = COALESCE(billing_metadata, '{}'::jsonb) || jsonb_build_object(
        'canonical_payer_backfill',
        '006_backfill_canonical_billing_records'
    ),
    updated_at = NOW()
WHERE actor_user_id IS NULL
   OR billing_account_type IS NULL
   OR billing_account_id IS NULL;
