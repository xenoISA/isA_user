-- Credit Service: Seed Test Data
-- Aligns with the shared test users in account_service/migrations/seed_test_data.sql.
-- Resolves xenoISA/isA_user#318 — without this, every authed call to
-- /api/v1/credits/consume hits "Failed to build consumption plan" because the
-- account exists with a balance but no backing allocation rows.
--
-- Invariant enforced here:
--   accounts.balance == SUM(allocations.amount - consumed_amount - expired_amount)
--                       WHERE allocations.status = 'completed'
--
-- Idempotent: safe to re-run against a populated DB (uses ON CONFLICT DO NOTHING).

-- ----------------------------------------------------------------------------
-- 1. Credit accounts (one bonus account per active test user)
-- ----------------------------------------------------------------------------
INSERT INTO credit.credit_accounts
    (account_id, user_id, credit_type, balance,
     total_allocated, total_consumed, total_expired,
     currency, expiration_policy, expiration_days, is_active,
     metadata, created_at, updated_at)
VALUES
    ('cred_acc_test_alice',   'test_user_001', 'bonus', 100000,
     100000, 0, 0, 'CREDIT', 'never', NULL, TRUE,
     '{"seed":"test_data","owner":"alice"}'::jsonb, NOW(), NOW()),
    ('cred_acc_test_bob',     'test_user_002', 'bonus',  50000,
      50000, 0, 0, 'CREDIT', 'never', NULL, TRUE,
     '{"seed":"test_data","owner":"bob"}'::jsonb, NOW(), NOW()),
    ('cred_acc_test_charlie', 'test_user_003', 'bonus', 200000,
     200000, 0, 0, 'CREDIT', 'never', NULL, TRUE,
     '{"seed":"test_data","owner":"charlie"}'::jsonb, NOW(), NOW())
ON CONFLICT (account_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. Matching allocations — one per account, same amount, no expiry
-- ----------------------------------------------------------------------------
-- credit_service._build_consumption_plan iterates allocations (not balance)
-- to produce a FIFO plan (BR-CON-003) broken by credit-type priority
-- (BR-CON-004). A balance without a matching allocation can never be consumed.
INSERT INTO credit.credit_allocations
    (allocation_id, user_id, account_id, amount, status,
     expires_at, consumed_amount, expired_amount,
     metadata, created_at, updated_at)
VALUES
    ('alloc_test_alice_seed_001',   'test_user_001', 'cred_acc_test_alice',   100000,
     'completed', NULL, 0, 0,
     '{"seed":"test_data","issue":"xenoISA/isA_user#318"}'::jsonb, NOW(), NOW()),
    ('alloc_test_bob_seed_001',     'test_user_002', 'cred_acc_test_bob',      50000,
     'completed', NULL, 0, 0,
     '{"seed":"test_data","issue":"xenoISA/isA_user#318"}'::jsonb, NOW(), NOW()),
    ('alloc_test_charlie_seed_001', 'test_user_003', 'cred_acc_test_charlie', 200000,
     'completed', NULL, 0, 0,
     '{"seed":"test_data","issue":"xenoISA/isA_user#318"}'::jsonb, NOW(), NOW())
ON CONFLICT (allocation_id) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 3. Verify invariant and print summary
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    account_count INTEGER;
    allocation_count INTEGER;
    drift_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO account_count FROM credit.credit_accounts WHERE user_id LIKE 'test_user_%';
    SELECT COUNT(*) INTO allocation_count FROM credit.credit_allocations WHERE user_id LIKE 'test_user_%';

    -- Drift = accounts whose balance doesn't match their remaining allocation pool.
    SELECT COUNT(*) INTO drift_count
    FROM credit.credit_accounts a
    LEFT JOIN (
        SELECT account_id, SUM(amount - consumed_amount - expired_amount) AS avail
        FROM credit.credit_allocations
        WHERE status = 'completed'
        GROUP BY account_id
    ) al ON al.account_id = a.account_id
    WHERE a.user_id LIKE 'test_user_%'
      AND a.balance <> COALESCE(al.avail, 0);

    RAISE NOTICE 'Credit test data seeded. accounts=%, allocations=%, drift=%',
                 account_count, allocation_count, drift_count;

    IF drift_count > 0 THEN
        RAISE WARNING 'Account/allocation drift detected on % test accounts — investigate before running consumption tests', drift_count;
    END IF;
END $$;
