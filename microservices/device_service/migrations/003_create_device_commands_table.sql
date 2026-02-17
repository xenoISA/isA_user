-- Device Service Migration: Create device commands table
-- Version: 003
-- Date: 2025-10-25

-- Create device_commands table
CREATE TABLE IF NOT EXISTS device.device_commands (
    command_id VARCHAR(255) PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,

    -- Command info
    command VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}',

    -- Execution settings
    timeout INTEGER DEFAULT 30,
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 10),
    require_ack BOOLEAN DEFAULT true,

    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    result JSONB,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    CONSTRAINT valid_command_status CHECK (status IN ('pending', 'sent', 'acknowledged', 'executed', 'failed', 'timeout'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_device_commands_device ON device.device_commands(device_id);
CREATE INDEX IF NOT EXISTS idx_device_commands_user ON device.device_commands(user_id);
CREATE INDEX IF NOT EXISTS idx_device_commands_status ON device.device_commands(status);
CREATE INDEX IF NOT EXISTS idx_device_commands_created ON device.device_commands(created_at DESC);

-- Comments
COMMENT ON TABLE device.device_commands IS 'Device command history and execution tracking';
COMMENT ON COLUMN device.device_commands.status IS 'Command status: pending, sent, acknowledged, executed, failed, timeout';
