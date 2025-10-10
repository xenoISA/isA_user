-- 设备认证凭证表
CREATE TABLE IF NOT EXISTS device_credentials (
    device_id VARCHAR(255) PRIMARY KEY,
    device_secret VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255) NOT NULL,
    device_name VARCHAR(255),
    device_type VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active', -- active, inactive, revoked
    last_authenticated_at TIMESTAMP,
    authentication_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- 索引优化
CREATE INDEX idx_device_credentials_org ON device_credentials(organization_id);
CREATE INDEX idx_device_credentials_status ON device_credentials(status);
CREATE INDEX idx_device_credentials_type ON device_credentials(device_type);

-- 设备认证日志表
CREATE TABLE IF NOT EXISTS device_auth_logs (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    auth_status VARCHAR(20) NOT NULL, -- success, failed, blocked
    ip_address VARCHAR(45),
    user_agent TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES device_credentials(device_id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_device_auth_logs_device ON device_auth_logs(device_id);
CREATE INDEX idx_device_auth_logs_created ON device_auth_logs(created_at);