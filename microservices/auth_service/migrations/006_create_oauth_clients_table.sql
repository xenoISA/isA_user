-- OAuth clients for machine-to-machine (A2A) authentication
CREATE TABLE IF NOT EXISTS auth.oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret_hash TEXT NOT NULL,
    client_name TEXT NOT NULL,
    organization_id TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    allowed_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    token_ttl_seconds INTEGER NOT NULL DEFAULT 3600,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oauth_clients_org ON auth.oauth_clients(organization_id);
CREATE INDEX IF NOT EXISTS idx_oauth_clients_active ON auth.oauth_clients(is_active);
