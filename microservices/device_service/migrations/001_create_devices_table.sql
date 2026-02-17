-- Device Service Migration: Create devices table
-- Version: 001
-- Date: 2025-10-25

-- Create device schema if not exists
CREATE SCHEMA IF NOT EXISTS device;

-- Create devices table
CREATE TABLE IF NOT EXISTS device.devices (
    device_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- Basic device info
    device_name VARCHAR(200) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    serial_number VARCHAR(100) NOT NULL UNIQUE,

    -- Hardware info
    firmware_version VARCHAR(50) NOT NULL,
    hardware_version VARCHAR(50),
    mac_address VARCHAR(17),

    -- Connectivity
    connectivity_type VARCHAR(50) NOT NULL,
    security_level VARCHAR(20) DEFAULT 'standard',

    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    last_seen TIMESTAMPTZ,

    -- Location and grouping
    location JSONB,
    group_id VARCHAR(255),
    tags TEXT[] DEFAULT '{}',

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Statistics
    total_commands INTEGER DEFAULT 0,
    total_telemetry_points INTEGER DEFAULT 0,
    uptime_percentage DECIMAL(5,2) DEFAULT 0.00,

    -- Timestamps
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_authenticated_at TIMESTAMPTZ,
    decommissioned_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('pending', 'active', 'inactive', 'maintenance', 'error', 'decommissioned')),
    CONSTRAINT valid_security_level CHECK (security_level IN ('none', 'basic', 'standard', 'high', 'critical'))
);

-- Indexes for devices table
CREATE INDEX IF NOT EXISTS idx_devices_user_id ON device.devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_org_id ON device.devices(organization_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON device.devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_type ON device.devices(device_type);
CREATE INDEX IF NOT EXISTS idx_devices_group ON device.devices(group_id);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON device.devices(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_devices_serial ON device.devices(serial_number);
CREATE INDEX IF NOT EXISTS idx_devices_tags ON device.devices USING GIN(tags);

-- Comments
COMMENT ON TABLE device.devices IS 'Device registration and management';
COMMENT ON COLUMN device.devices.device_id IS 'Unique device identifier';
COMMENT ON COLUMN device.devices.user_id IS 'User who owns this device';
COMMENT ON COLUMN device.devices.status IS 'Device status: pending, active, inactive, maintenance, error, decommissioned';
