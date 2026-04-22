-- Organization Service Migration 004: add rate_limits JSONB column
-- Story xenoISA/isA_Console#461 — managed rate limits per org and per api-key.
-- Per-key rate limits live in auth.organizations.api_keys[].rate_limits JSONB
-- (no DDL needed there); this column holds org-level defaults.
--
-- Shape (validated at the API layer, not at DB level):
--   {
--     "requests_per_second": int | null,
--     "requests_per_minute": int | null,
--     "requests_per_day":    int | null,
--     "tokens_per_day":      int | null
--   }
-- null on any field means "no limit". The whole column is nullable so
-- existing orgs default to "no managed limits configured".

ALTER TABLE organization.organizations
    ADD COLUMN IF NOT EXISTS rate_limits JSONB DEFAULT NULL;

COMMENT ON COLUMN organization.organizations.rate_limits IS
    'Org-level rate-limit defaults (Story #461). NULL = no limits. Per-key '
    'overrides live in auth.organizations.api_keys[].rate_limits.';
