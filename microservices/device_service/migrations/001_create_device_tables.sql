-- Device Management Service Migration: Create device management tables
-- Version: 001
-- Date: 2025-01-21
-- Description: Core tables for IoT device management, authentication, and health monitoring

-- Drop existing tables if needed (be careful in production!)
DROP TABLE IF EXISTS dev.device_health_logs CASCADE;
DROP TABLE IF EXISTS dev.device_commands CASCADE;
DROP TABLE IF EXISTS dev.device_auth_tokens CASCADE;
DROP TABLE IF EXISTS dev.devices CASCADE;
DROP TABLE IF EXISTS dev.device_groups CASCADE;

-- Create device_groups table first (referenced by devices)
CREATE TABLE dev.device_groups (
    id SERIAL PRIMARY KEY,
    group_id VARCHAR(64) NOT NULL UNIQUE,
    group_name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    parent_group_id VARCHAR(64),
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    device_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    
    CONSTRAINT fk_parent_group FOREIGN KEY (parent_group_id) 
        REFERENCES dev.device_groups(group_id) ON DELETE SET NULL
);

-- Create devices table
CREATE TABLE dev.devices (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL UNIQUE,
    device_name VARCHAR(200) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    serial_number VARCHAR(100) UNIQUE NOT NULL,
    firmware_version VARCHAR(50) NOT NULL,
    hardware_version VARCHAR(50),
    mac_address VARCHAR(17),
    connectivity_type VARCHAR(50) NOT NULL,
    security_level VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    location JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    group_id VARCHAR(64),
    tags TEXT[],
    last_seen TIMESTAMPTZ,
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),
    total_commands INTEGER DEFAULT 0,
    total_telemetry_points BIGINT DEFAULT 0,
    uptime_percentage DECIMAL(5,2) DEFAULT 0.0,
    
    CONSTRAINT fk_device_group FOREIGN KEY (group_id)
        REFERENCES dev.device_groups(group_id) ON DELETE SET NULL,
    CONSTRAINT check_status CHECK (status IN ('pending', 'active', 'inactive', 'maintenance', 'error', 'decommissioned')),
    CONSTRAINT check_connectivity CHECK (connectivity_type IN ('wifi', 'ethernet', '4g', '5g', 'bluetooth', 'zigbee', 'lora', 'nb-iot', 'mqtt', 'coap')),
    CONSTRAINT check_security CHECK (security_level IN ('none', 'basic', 'standard', 'high', 'critical'))
);

-- Create device_auth_tokens table
CREATE TABLE dev.device_auth_tokens (
    id SERIAL PRIMARY KEY,
    token_id VARCHAR(64) NOT NULL UNIQUE,
    device_id VARCHAR(64) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type VARCHAR(20) DEFAULT 'Bearer',
    expires_at TIMESTAMPTZ NOT NULL,
    scope VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ,
    revoked BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT fk_auth_device FOREIGN KEY (device_id) 
        REFERENCES dev.devices(device_id) ON DELETE CASCADE
);

-- Create device_commands table
CREATE TABLE dev.device_commands (
    id SERIAL PRIMARY KEY,
    command_id VARCHAR(64) NOT NULL UNIQUE,
    device_id VARCHAR(64) NOT NULL,
    command VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 1,
    timeout INTEGER DEFAULT 30,
    require_ack BOOLEAN DEFAULT TRUE,
    sent_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,
    
    CONSTRAINT fk_command_device FOREIGN KEY (device_id) 
        REFERENCES dev.devices(device_id) ON DELETE CASCADE,
    CONSTRAINT check_command_status CHECK (status IN ('pending', 'sent', 'acknowledged', 'completed', 'failed', 'timeout', 'cancelled'))
);

-- Create device_health_logs table
CREATE TABLE dev.device_health_logs (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    health_score DECIMAL(5,2),
    cpu_usage DECIMAL(5,2),
    memory_usage DECIMAL(5,2),
    disk_usage DECIMAL(5,2),
    temperature DECIMAL(5,2),
    battery_level DECIMAL(5,2),
    signal_strength DECIMAL(6,2),
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    last_error TEXT,
    diagnostics JSONB DEFAULT '{}'::jsonb,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_health_device FOREIGN KEY (device_id) 
        REFERENCES dev.devices(device_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_devices_user_id ON dev.devices(user_id);
CREATE INDEX idx_devices_status ON dev.devices(status);
CREATE INDEX idx_devices_device_type ON dev.devices(device_type);
CREATE INDEX idx_devices_group_id ON dev.devices(group_id);
CREATE INDEX idx_devices_last_seen ON dev.devices(last_seen);
CREATE INDEX idx_devices_serial ON dev.devices(serial_number);
CREATE INDEX idx_devices_connectivity ON dev.devices(connectivity_type);

CREATE INDEX idx_device_groups_user_id ON dev.device_groups(user_id);
CREATE INDEX idx_device_groups_parent ON dev.device_groups(parent_group_id);

CREATE INDEX idx_device_auth_tokens_device_id ON dev.device_auth_tokens(device_id);
CREATE INDEX idx_device_auth_tokens_expires_at ON dev.device_auth_tokens(expires_at);
CREATE INDEX idx_device_auth_tokens_revoked ON dev.device_auth_tokens(revoked) WHERE revoked = FALSE;

CREATE INDEX idx_device_commands_device_id ON dev.device_commands(device_id);
CREATE INDEX idx_device_commands_status ON dev.device_commands(status);
CREATE INDEX idx_device_commands_created_at ON dev.device_commands(created_at DESC);

CREATE INDEX idx_device_health_logs_device_id ON dev.device_health_logs(device_id);
CREATE INDEX idx_device_health_logs_logged_at ON dev.device_health_logs(logged_at DESC);

-- Create composite indexes for common queries
CREATE INDEX idx_devices_user_status ON dev.devices(user_id, status);
CREATE INDEX idx_devices_user_type ON dev.devices(user_id, device_type);
CREATE INDEX idx_commands_device_status ON dev.device_commands(device_id, status);
CREATE INDEX idx_health_device_time ON dev.device_health_logs(device_id, logged_at DESC);

-- Create update triggers (assuming update_updated_at function exists)
CREATE OR REPLACE FUNCTION dev.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_devices_updated_at
    BEFORE UPDATE ON dev.devices
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_device_groups_updated_at
    BEFORE UPDATE ON dev.device_groups
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.devices TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.devices TO authenticated;
GRANT ALL ON SEQUENCE dev.devices_id_seq TO authenticated;

GRANT ALL ON dev.device_groups TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.device_groups TO authenticated;
GRANT ALL ON SEQUENCE dev.device_groups_id_seq TO authenticated;

GRANT ALL ON dev.device_auth_tokens TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.device_auth_tokens TO authenticated;
GRANT ALL ON SEQUENCE dev.device_auth_tokens_id_seq TO authenticated;

GRANT ALL ON dev.device_commands TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.device_commands TO authenticated;
GRANT ALL ON SEQUENCE dev.device_commands_id_seq TO authenticated;

GRANT ALL ON dev.device_health_logs TO postgres;
GRANT SELECT, INSERT ON dev.device_health_logs TO authenticated;
GRANT ALL ON SEQUENCE dev.device_health_logs_id_seq TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE dev.devices IS 'IoT device registry and management';
COMMENT ON TABLE dev.device_groups IS 'Device group organization and hierarchy';
COMMENT ON TABLE dev.device_auth_tokens IS 'Device authentication and access tokens';
COMMENT ON TABLE dev.device_commands IS 'Remote commands sent to devices';
COMMENT ON TABLE dev.device_health_logs IS 'Device health metrics and diagnostics';

COMMENT ON COLUMN dev.devices.device_id IS 'Unique device identifier';
COMMENT ON COLUMN dev.devices.device_type IS 'Type of device (sensor, actuator, gateway, etc.)';
COMMENT ON COLUMN dev.devices.connectivity_type IS 'Network connectivity type';
COMMENT ON COLUMN dev.devices.security_level IS 'Device security level classification';
COMMENT ON COLUMN dev.devices.status IS 'Current device operational status';
COMMENT ON COLUMN dev.devices.uptime_percentage IS 'Device uptime percentage (0-100)';

COMMENT ON COLUMN dev.device_commands.command IS 'Command to be executed on device';
COMMENT ON COLUMN dev.device_commands.priority IS 'Command priority (1-10, higher is more urgent)';
COMMENT ON COLUMN dev.device_commands.timeout IS 'Command timeout in seconds';

COMMENT ON COLUMN dev.device_health_logs.health_score IS 'Overall health score (0-100)';
COMMENT ON COLUMN dev.device_health_logs.signal_strength IS 'Signal strength in dBm';