-- Auth Service Migration: Create devices tables
-- Version: 003
-- Date: 2025-01-20

-- Devices table
CREATE TABLE IF NOT EXISTS auth.devices (
    device_id VARCHAR(255) PRIMARY KEY,
    device_secret VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    device_name VARCHAR(255),
    device_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    last_authenticated_at TIMESTAMPTZ,
    authentication_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Indexes for devices
CREATE INDEX IF NOT EXISTS idx_devices_org ON auth.devices(organization_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON auth.devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_type ON auth.devices(device_type);

-- Device authentication logs
CREATE TABLE IF NOT EXISTS auth.device_logs (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    auth_status VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for device_logs
CREATE INDEX IF NOT EXISTS idx_device_logs_device ON auth.device_logs(device_id);
CREATE INDEX IF NOT EXISTS idx_device_logs_created ON auth.device_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_logs_status ON auth.device_logs(auth_status);

-- Comments
COMMENT ON TABLE auth.devices IS 'Device authentication credentials for IoT/smart frames';
COMMENT ON COLUMN auth.devices.device_id IS 'Unique device identifier';
COMMENT ON COLUMN auth.devices.device_secret IS 'Device authentication secret';
COMMENT ON COLUMN auth.devices.organization_id IS 'Organization that owns this device';
COMMENT ON COLUMN auth.devices.status IS 'Device status: active, inactive, revoked';

COMMENT ON TABLE auth.device_logs IS 'Device authentication attempt logs';
COMMENT ON COLUMN auth.device_logs.auth_status IS 'Authentication result: success, failed, blocked';
