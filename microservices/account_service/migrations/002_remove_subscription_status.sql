-- Account Service Migration: Remove subscription_status field
-- Version: 002
-- Date: 2025-11-28
-- Description: Remove subscription_status from account.users table
--              Subscription data is now managed by subscription_service
-- Reference: /docs/design/billing-credit-subscription-design.md

-- Step 1: Drop the index on subscription_status
DROP INDEX IF EXISTS account.idx_users_subscription_status;

-- Step 2: Remove the subscription_status column
ALTER TABLE account.users DROP COLUMN IF EXISTS subscription_status;

-- Step 3: Update table comment
COMMENT ON TABLE account.users IS 'User account profiles - identity anchor only. Subscription data managed by subscription_service.';

-- Note: This migration removes subscription_status because:
-- 1. subscription_service is the source of truth for all subscription data
-- 2. Keeping subscription_status here creates data duplication and consistency risks
-- 3. Services needing subscription info should query subscription_service directly
