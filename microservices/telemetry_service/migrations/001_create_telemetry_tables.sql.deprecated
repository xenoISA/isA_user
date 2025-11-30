-- Telemetry Service Migration: Create telemetry and monitoring tables
-- Version: 001
-- Date: 2025-01-21
-- Description: Core tables for time-series data, metrics, alerts, and real-time subscriptions

-- Drop existing tables if needed (be careful in production!)
DROP MATERIALIZED VIEW IF EXISTS dev.device_metrics_summary CASCADE;
DROP TABLE IF EXISTS dev.data_retention_policies CASCADE;
DROP TABLE IF EXISTS dev.telemetry_stats CASCADE;
DROP TABLE IF EXISTS dev.real_time_subscriptions CASCADE;
DROP TABLE IF EXISTS dev.alerts CASCADE;
DROP TABLE IF EXISTS dev.alert_rules CASCADE;
DROP TABLE IF EXISTS dev.aggregated_data CASCADE;
DROP TABLE IF EXISTS dev.telemetry_data CASCADE;
DROP TABLE IF EXISTS dev.metric_definitions CASCADE;

-- Create metric_definitions table
CREATE TABLE dev.metric_definitions (
    id SERIAL PRIMARY KEY,
    metric_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(500),
    data_type VARCHAR(20) NOT NULL,
    metric_type VARCHAR(20) NOT NULL DEFAULT 'gauge',
    unit VARCHAR(20),
    min_value DECIMAL(20,4),
    max_value DECIMAL(20,4),
    retention_days INTEGER DEFAULT 90,
    aggregation_interval INTEGER DEFAULT 60, -- seconds
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,
    
    CONSTRAINT check_data_type CHECK (data_type IN ('numeric', 'string', 'boolean', 'json', 'binary', 'geolocation', 'timestamp')),
    CONSTRAINT check_metric_type CHECK (metric_type IN ('gauge', 'counter', 'histogram', 'summary')),
    CONSTRAINT check_retention_days CHECK (retention_days BETWEEN 1 AND 3650)
);

-- Create telemetry_data table (main time-series table)
CREATE TABLE dev.telemetry_data (
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value_numeric DECIMAL(20,4),
    value_string TEXT,
    value_boolean BOOLEAN,
    value_json JSONB,
    unit VARCHAR(20),
    tags JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    quality INTEGER DEFAULT 100,
    
    PRIMARY KEY (time, device_id, metric_name),
    CONSTRAINT fk_telemetry_device FOREIGN KEY (device_id) 
        REFERENCES dev.devices(device_id) ON DELETE CASCADE
);

-- Create aggregated_data table for pre-computed aggregations
CREATE TABLE dev.aggregated_data (
    id SERIAL PRIMARY KEY,
    time_bucket TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(64),
    metric_name VARCHAR(100) NOT NULL,
    aggregation_type VARCHAR(20) NOT NULL,
    interval_seconds INTEGER NOT NULL,
    
    -- Aggregated values
    avg_value DECIMAL(20,4),
    min_value DECIMAL(20,4),
    max_value DECIMAL(20,4),
    sum_value DECIMAL(20,4),
    count_value BIGINT,
    stddev_value DECIMAL(20,4),
    median_value DECIMAL(20,4),
    p95_value DECIMAL(20,4),
    p99_value DECIMAL(20,4),
    
    metadata JSONB DEFAULT '{}'::jsonb,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_aggregation_type CHECK (aggregation_type IN ('avg', 'min', 'max', 'sum', 'count', 'median', 'p95', 'p99')),
    UNIQUE(time_bucket, device_id, metric_name, aggregation_type, interval_seconds)
);

-- Create alert_rules table
CREATE TABLE dev.alert_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(1000),
    metric_name VARCHAR(100) NOT NULL,
    condition VARCHAR(500) NOT NULL,
    threshold_value TEXT NOT NULL,
    evaluation_window INTEGER DEFAULT 300, -- seconds
    trigger_count INTEGER DEFAULT 1,
    level VARCHAR(20) NOT NULL DEFAULT 'warning',
    
    -- Target configuration
    device_ids TEXT[],
    device_groups TEXT[],
    device_filters JSONB DEFAULT '{}'::jsonb,
    
    -- Notification configuration
    notification_channels TEXT[],
    cooldown_minutes INTEGER DEFAULT 15,
    auto_resolve BOOLEAN DEFAULT TRUE,
    auto_resolve_timeout INTEGER DEFAULT 3600, -- seconds
    
    enabled BOOLEAN DEFAULT TRUE,
    tags TEXT[],
    
    -- Statistics
    total_triggers INTEGER DEFAULT 0,
    last_triggered TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,
    
    CONSTRAINT check_alert_level CHECK (level IN ('info', 'warning', 'error', 'critical', 'emergency'))
);

-- Create alerts table
CREATE TABLE dev.alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(64) NOT NULL UNIQUE,
    rule_id VARCHAR(64) NOT NULL,
    rule_name VARCHAR(200) NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    message TEXT NOT NULL,
    current_value TEXT NOT NULL,
    threshold_value TEXT NOT NULL,
    
    -- Time tracking
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    auto_resolve_at TIMESTAMPTZ,
    
    -- Action tracking
    acknowledged_by VARCHAR(100),
    resolved_by VARCHAR(100),
    resolution_note TEXT,
    
    -- Context
    affected_devices_count INTEGER DEFAULT 1,
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT fk_alert_rule FOREIGN KEY (rule_id) 
        REFERENCES dev.alert_rules(rule_id) ON DELETE CASCADE,
    CONSTRAINT fk_alert_device FOREIGN KEY (device_id) 
        REFERENCES dev.devices(device_id) ON DELETE CASCADE,
    CONSTRAINT check_alert_status CHECK (status IN ('active', 'acknowledged', 'resolved', 'suppressed'))
);

-- Create real_time_subscriptions table
CREATE TABLE dev.real_time_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(64) NOT NULL UNIQUE,
    user_id VARCHAR(100) NOT NULL,
    device_ids TEXT[],
    metric_names TEXT[],
    tags JSONB DEFAULT '{}'::jsonb,
    filter_condition TEXT,
    max_frequency INTEGER DEFAULT 1000, -- milliseconds
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_sent TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    active BOOLEAN DEFAULT TRUE,
    
    websocket_id VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create telemetry_stats table for cached statistics
CREATE TABLE dev.telemetry_stats (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(64),
    metric_name VARCHAR(100),
    period VARCHAR(20) NOT NULL,
    
    -- Statistics
    total_points BIGINT DEFAULT 0,
    avg_value DECIMAL(20,4),
    min_value DECIMAL(20,4),
    max_value DECIMAL(20,4),
    last_value DECIMAL(20,4),
    last_updated TIMESTAMPTZ,
    
    -- Data quality
    missing_points INTEGER DEFAULT 0,
    error_points INTEGER DEFAULT 0,
    quality_score DECIMAL(5,2) DEFAULT 100.0,
    
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_period CHECK (period IN ('hour', 'day', 'week', 'month', 'year'))
);

-- Create data_retention_policies table
CREATE TABLE dev.data_retention_policies (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100),
    device_type VARCHAR(50),
    retention_days INTEGER NOT NULL,
    aggregation_policy VARCHAR(20),
    compress_after_days INTEGER,
    archive_after_days INTEGER,
    delete_after_days INTEGER,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_aggregation_policy CHECK (aggregation_policy IN ('none', 'hourly', 'daily', 'weekly', 'monthly'))
);

-- Create indexes for performance
CREATE INDEX idx_telemetry_data_device_id ON dev.telemetry_data(device_id, time DESC);
CREATE INDEX idx_telemetry_data_metric_name ON dev.telemetry_data(metric_name, time DESC);
CREATE INDEX idx_telemetry_data_device_metric ON dev.telemetry_data(device_id, metric_name, time DESC);
CREATE INDEX idx_telemetry_data_time ON dev.telemetry_data(time DESC);

CREATE INDEX idx_aggregated_data_device_id ON dev.aggregated_data(device_id, time_bucket DESC);
CREATE INDEX idx_aggregated_data_metric_name ON dev.aggregated_data(metric_name, time_bucket DESC);
CREATE INDEX idx_aggregated_data_time ON dev.aggregated_data(time_bucket DESC);

CREATE INDEX idx_alert_rules_metric_name ON dev.alert_rules(metric_name);
CREATE INDEX idx_alert_rules_enabled ON dev.alert_rules(enabled) WHERE enabled = TRUE;

CREATE INDEX idx_alerts_device_id ON dev.alerts(device_id);
CREATE INDEX idx_alerts_status ON dev.alerts(status);
CREATE INDEX idx_alerts_triggered_at ON dev.alerts(triggered_at DESC);
CREATE INDEX idx_alerts_rule_id ON dev.alerts(rule_id);

CREATE INDEX idx_real_time_subscriptions_user_id ON dev.real_time_subscriptions(user_id);
CREATE INDEX idx_real_time_subscriptions_active ON dev.real_time_subscriptions(active) WHERE active = TRUE;

CREATE INDEX idx_telemetry_stats_device_id ON dev.telemetry_stats(device_id);
CREATE INDEX idx_telemetry_stats_period ON dev.telemetry_stats(period);
CREATE INDEX idx_telemetry_stats_device_metric ON dev.telemetry_stats(device_id, metric_name, period);

-- Create composite indexes for common queries
CREATE INDEX idx_telemetry_data_device_time_numeric ON dev.telemetry_data(device_id, time DESC) WHERE value_numeric IS NOT NULL;
CREATE INDEX idx_alerts_device_status ON dev.alerts(device_id, status);
CREATE INDEX idx_alerts_active ON dev.alerts(status) WHERE status = 'active';

-- Create a materialized view for device metrics summary
CREATE MATERIALIZED VIEW dev.device_metrics_summary AS
SELECT 
    device_id,
    metric_name,
    COUNT(*) as total_points,
    MIN(time) as first_seen,
    MAX(time) as last_seen,
    AVG(value_numeric) as avg_value,
    MIN(value_numeric) as min_value,
    MAX(value_numeric) as max_value
FROM dev.telemetry_data
WHERE value_numeric IS NOT NULL
GROUP BY device_id, metric_name;

CREATE INDEX idx_device_metrics_summary_device ON dev.device_metrics_summary(device_id);
CREATE INDEX idx_device_metrics_summary_metric ON dev.device_metrics_summary(metric_name);

-- Create update triggers
CREATE TRIGGER trigger_update_metric_definitions_updated_at
    BEFORE UPDATE ON dev.metric_definitions
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_alert_rules_updated_at
    BEFORE UPDATE ON dev.alert_rules
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

CREATE TRIGGER trigger_update_data_retention_policies_updated_at
    BEFORE UPDATE ON dev.data_retention_policies
    FOR EACH ROW
    EXECUTE FUNCTION dev.update_updated_at();

-- Grant permissions
GRANT ALL ON dev.metric_definitions TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.metric_definitions TO authenticated;
GRANT ALL ON SEQUENCE dev.metric_definitions_id_seq TO authenticated;

GRANT ALL ON dev.telemetry_data TO postgres;
GRANT SELECT, INSERT ON dev.telemetry_data TO authenticated;

GRANT ALL ON dev.aggregated_data TO postgres;
GRANT SELECT, INSERT ON dev.aggregated_data TO authenticated;
GRANT ALL ON SEQUENCE dev.aggregated_data_id_seq TO authenticated;

GRANT ALL ON dev.alert_rules TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.alert_rules TO authenticated;
GRANT ALL ON SEQUENCE dev.alert_rules_id_seq TO authenticated;

GRANT ALL ON dev.alerts TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.alerts TO authenticated;
GRANT ALL ON SEQUENCE dev.alerts_id_seq TO authenticated;

GRANT ALL ON dev.real_time_subscriptions TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON dev.real_time_subscriptions TO authenticated;
GRANT ALL ON SEQUENCE dev.real_time_subscriptions_id_seq TO authenticated;

GRANT ALL ON dev.telemetry_stats TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.telemetry_stats TO authenticated;
GRANT ALL ON SEQUENCE dev.telemetry_stats_id_seq TO authenticated;

GRANT ALL ON dev.data_retention_policies TO postgres;
GRANT SELECT, INSERT, UPDATE ON dev.data_retention_policies TO authenticated;
GRANT ALL ON SEQUENCE dev.data_retention_policies_id_seq TO authenticated;

GRANT ALL ON dev.device_metrics_summary TO postgres;
GRANT SELECT ON dev.device_metrics_summary TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE dev.metric_definitions IS 'Definition and configuration for telemetry metrics';
COMMENT ON TABLE dev.telemetry_data IS 'Time-series telemetry data from IoT devices';
COMMENT ON TABLE dev.aggregated_data IS 'Pre-computed aggregations for performance optimization';
COMMENT ON TABLE dev.alert_rules IS 'Alert rule definitions for monitoring';
COMMENT ON TABLE dev.alerts IS 'Active and historical alerts';
COMMENT ON TABLE dev.real_time_subscriptions IS 'WebSocket subscriptions for real-time data';
COMMENT ON TABLE dev.telemetry_stats IS 'Cached statistics for quick access';
COMMENT ON TABLE dev.data_retention_policies IS 'Data retention and archival policies';

COMMENT ON COLUMN dev.telemetry_data.quality IS 'Data quality score (0-100)';
COMMENT ON COLUMN dev.telemetry_data.time IS 'Timestamp of the measurement';
COMMENT ON COLUMN dev.aggregated_data.time_bucket IS 'Start of the aggregation time bucket';
COMMENT ON COLUMN dev.alert_rules.evaluation_window IS 'Time window for evaluating conditions (seconds)';
COMMENT ON COLUMN dev.alerts.auto_resolve_at IS 'Time when alert will auto-resolve if configured';
COMMENT ON COLUMN dev.real_time_subscriptions.max_frequency IS 'Minimum interval between updates (milliseconds)';
COMMENT ON COLUMN dev.telemetry_stats.quality_score IS 'Overall data quality score (0-100)';