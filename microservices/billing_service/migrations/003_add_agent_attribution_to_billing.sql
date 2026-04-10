-- Billing Service Migration: first-class agent attribution
-- Version: 003
-- Date: 2026-04-08
-- Description: Add agent_id columns and indexes for billing records and events

ALTER TABLE billing.billing_records
    ADD COLUMN IF NOT EXISTS agent_id VARCHAR(100);

ALTER TABLE billing.billing_events
    ADD COLUMN IF NOT EXISTS agent_id VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_billing_records_agent_id
    ON billing.billing_records(agent_id);

CREATE INDEX IF NOT EXISTS idx_billing_events_agent_id
    ON billing.billing_events(agent_id);

CREATE INDEX IF NOT EXISTS idx_billing_records_scope_created_at
    ON billing.billing_records(user_id, organization_id, agent_id, created_at DESC);

COMMENT ON COLUMN billing.billing_records.agent_id IS 'Agent identifier for first-class billing attribution';
COMMENT ON COLUMN billing.billing_events.agent_id IS 'Agent identifier for first-class billing attribution';
