-- Credit Service: account/allocation reconciliation view
-- Resolves xenoISA/isA_user#319
--
-- Surfaces accounts whose stored balance drifts from the remaining allocation
-- pool. The credit_service's _build_consumption_plan (BR-CON-003, BR-CON-004)
-- iterates allocations (not balance), so any drift makes /credits/consume
-- either 500 ("Failed to build consumption plan") or silently over/under-charge.
--
-- Usage:
--   SELECT * FROM credit.v_account_reconciliation;                 -- all accounts
--   SELECT * FROM credit.v_account_reconciliation WHERE drift<>0;  -- drift only
--
-- The companion helper function credit.find_account_drift() returns the same
-- drift-only rows as a set — handy for JSON-returning admin endpoints.

CREATE OR REPLACE VIEW credit.v_account_reconciliation AS
SELECT
    a.account_id,
    a.user_id,
    a.organization_id,
    a.credit_type,
    a.balance                                              AS account_balance,
    COALESCE(al.allocated_total,        0)                 AS allocated_total,
    COALESCE(al.consumed_total,         0)                 AS consumed_total,
    COALESCE(al.expired_total,          0)                 AS expired_total,
    COALESCE(al.available_remaining,    0)                 AS allocation_available,
    a.balance - COALESCE(al.available_remaining, 0)        AS drift,
    a.is_active,
    a.updated_at
FROM credit.credit_accounts a
LEFT JOIN (
    SELECT
        account_id,
        SUM(amount)                                         AS allocated_total,
        SUM(consumed_amount)                                AS consumed_total,
        SUM(expired_amount)                                 AS expired_total,
        SUM(amount - consumed_amount - expired_amount)      AS available_remaining
    FROM credit.credit_allocations
    WHERE status = 'completed'
    GROUP BY account_id
) al ON al.account_id = a.account_id;

COMMENT ON VIEW credit.v_account_reconciliation IS
    'Reports per-account drift between stored balance and remaining allocation pool. '
    'drift = account_balance - allocation_available. Any non-zero row indicates a bug '
    'or a manual DB mutation that bypassed the credit_service grant flow. See '
    'xenoISA/isA_user#319 for context.';


CREATE OR REPLACE FUNCTION credit.find_account_drift()
RETURNS TABLE (
    account_id           VARCHAR(50),
    user_id              VARCHAR(50),
    credit_type          VARCHAR(30),
    account_balance      INTEGER,
    allocation_available BIGINT,
    drift                BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        v.account_id,
        v.user_id,
        v.credit_type,
        v.account_balance,
        v.allocation_available,
        v.drift
    FROM credit.v_account_reconciliation v
    WHERE v.drift <> 0
    ORDER BY abs(v.drift) DESC, v.account_id;
$$;

COMMENT ON FUNCTION credit.find_account_drift() IS
    'Returns only the drifting accounts from v_account_reconciliation, ordered by '
    'drift magnitude (largest first). Intended for admin/ops endpoints.';
