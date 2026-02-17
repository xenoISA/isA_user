-- Device Service Migration: Create device groups table
-- Version: 002
-- Date: 2025-10-25

-- Create device_groups table
CREATE TABLE IF NOT EXISTS device.device_groups (
    group_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- Group info
    group_name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    parent_group_id VARCHAR(255),

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    -- Statistics
    device_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_device_groups_user ON device.device_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_device_groups_org ON device.device_groups(organization_id);
CREATE INDEX IF NOT EXISTS idx_device_groups_parent ON device.device_groups(parent_group_id);

-- Comments
COMMENT ON TABLE device.device_groups IS 'Device groups for organizing devices';
COMMENT ON COLUMN device.device_groups.parent_group_id IS 'Parent group ID for hierarchical organization';
