-- Compliance Service Migration: GDPR data request workflow queue
-- Version: 002
-- Date: 2026-05-18
-- Description: Persist GDPR export/delete requests with per-service status tracking

CREATE SCHEMA IF NOT EXISTS compliance;

CREATE TABLE IF NOT EXISTS compliance.gdpr_data_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(100) UNIQUE NOT NULL,
    request_type VARCHAR(20) NOT NULL CHECK (request_type IN ('export', 'delete')),
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),
    requested_by VARCHAR(100) NOT NULL,
    approved_by VARCHAR(100),
    reason TEXT,
    artifact_uri TEXT,
    per_service_status JSONB NOT NULL DEFAULT '{}'::jsonb,
    failure_reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_gdpr_data_requests_request_id
    ON compliance.gdpr_data_requests(request_id);
CREATE INDEX IF NOT EXISTS idx_gdpr_data_requests_user_id
    ON compliance.gdpr_data_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_gdpr_data_requests_org_status
    ON compliance.gdpr_data_requests(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_gdpr_data_requests_status
    ON compliance.gdpr_data_requests(status);
CREATE INDEX IF NOT EXISTS idx_gdpr_data_requests_request_type
    ON compliance.gdpr_data_requests(request_type);
CREATE INDEX IF NOT EXISTS idx_gdpr_data_requests_created_at
    ON compliance.gdpr_data_requests(created_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'update_gdpr_data_requests_updated_at'
    ) THEN
        CREATE TRIGGER update_gdpr_data_requests_updated_at
            BEFORE UPDATE ON compliance.gdpr_data_requests
            FOR EACH ROW
            EXECUTE FUNCTION public.update_updated_at_column();
    END IF;
END $$;

COMMENT ON TABLE compliance.gdpr_data_requests IS
    'Queued GDPR export/delete requests with approval and per-service status tracking';
COMMENT ON COLUMN compliance.gdpr_data_requests.per_service_status IS
    'JSON object keyed by service name with export/delete progress and failures';
