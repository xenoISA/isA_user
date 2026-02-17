-- Migration: Create device_pairing_tokens table
-- Description: Store temporary pairing tokens for device-user pairing
-- Date: 2025-11-11

CREATE TABLE IF NOT EXISTS auth.device_pairing_tokens (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    pairing_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    user_id VARCHAR(255)
);

-- Create indexes separately
CREATE INDEX IF NOT EXISTS idx_pairing_token ON auth.device_pairing_tokens(pairing_token);
CREATE INDEX IF NOT EXISTS idx_device_id ON auth.device_pairing_tokens(device_id);
CREATE INDEX IF NOT EXISTS idx_expires_at ON auth.device_pairing_tokens(expires_at);

-- Add comments
COMMENT ON TABLE auth.device_pairing_tokens IS 'Temporary pairing tokens for device-user pairing';
COMMENT ON COLUMN auth.device_pairing_tokens.device_id IS 'Device ID requesting pairing';
COMMENT ON COLUMN auth.device_pairing_tokens.pairing_token IS 'Unique temporary pairing token (5 minutes validity)';
COMMENT ON COLUMN auth.device_pairing_tokens.expires_at IS 'Token expiration time';
COMMENT ON COLUMN auth.device_pairing_tokens.used IS 'Whether token has been used';
COMMENT ON COLUMN auth.device_pairing_tokens.used_at IS 'When token was used';
COMMENT ON COLUMN auth.device_pairing_tokens.user_id IS 'User ID who used the token';
