-- Session Service Migration: Fix decimal types to float
-- Version: 004
-- Date: 2025-10-27

-- Change total_cost from DECIMAL to DOUBLE PRECISION (float8)
ALTER TABLE session.sessions ALTER COLUMN total_cost TYPE DOUBLE PRECISION;

-- Change cost_usd from DECIMAL to DOUBLE PRECISION (float8)
ALTER TABLE session.session_messages ALTER COLUMN cost_usd TYPE DOUBLE PRECISION;

-- Comments
COMMENT ON COLUMN session.sessions.total_cost IS 'Total cost in USD (float)';
COMMENT ON COLUMN session.session_messages.cost_usd IS 'Cost in USD for this message (float)';
