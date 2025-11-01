-- Telemetry Service Migration: Migrate to dedicated telemetry schema
-- Version: 002
-- Date: 2025-10-27
-- Description: Move tables from dev schema to telemetry schema, fix DECIMAL types, remove foreign keys

-- Create telemetry schema
CREATE SCHEMA IF NOT EXISTS telemetry;

-- Drop existing tables in telemetry schema if they exist
DROP MATERIALIZED VIEW IF EXISTS telemetry.device_metrics_summary CASCADE;
DROP TABLE IF EXISTS telemetry.data_retention_policies CASCADE;
DROP TABLE IF EXISTS telemetry.telemetry_stats CASCADE;
DROP TABLE IF EXISTS telemetry.real_time_subscriptions CASCADE;
DROP TABLE IF EXISTS telemetry.alerts CASCADE;
DROP TABLE IF EXISTS telemetry.alert_rules CASCADE;
DROP TABLE IF EXISTS telemetry.aggregated_data CASCADE;
DROP TABLE IF EXISTS telemetry.telemetry_data CASCADE;
DROP TABLE IF EXISTS telemetry.metric_definitions CASCADE;

-- 1. Create metric_definitions table
CREATE TABLE telemetry.metric_definitions (
    id SERIAL PRIMARY KEY,
    metric_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(500),
    data_type VARCHAR(20) NOT NULL,
    metric_type VARCHAR(20) NOT NULL DEFAULT 'gauge',
    unit VARCHAR(20),
    min_value DOUBLE PRECISION,  -- Changed from DECIMAL
    max_value DOUBLE PRECISION,  -- Changed from DECIMAL
    retention_days INTEGER DEFAULT 90,
    aggregation_interval INTEGER DEFAULT 60,
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL,

    CONSTRAINT check_data_type CHECK (data_type IN ('numeric', 'string', 'boolean', 'json', 'binary', 'geolocation', 'timestamp')),
    CONSTRAINT check_metric_type CHECK (metric_type IN ('gauge', 'counter', 'histogram', 'summary')),
    CONSTRAINT check_retention_days CHECK (retention_days BETWEEN 1 AND 3650)
);

-- 2. Create telemetry_data table (main time-series table)
CREATE TABLE telemetry.telemetry_data (
    time TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(64) NOT NULL,  -- No FK constraint - cross-service reference
    metric_name VARCHAR(100) NOT NULL,
    value_numeric DOUBLE PRECISION,  -- Changed from DECIMAL
    value_string TEXT,
    value_boolean BOOLEAN,
    value_json JSONB,
    unit VARCHAR(20),
    tags JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    quality INTEGER DEFAULT 100,

    PRIMARY KEY (time, device_id, metric_name)
);

-- 3. Create aggregated_data table
CREATE TABLE telemetry.aggregated_data (
    id SERIAL PRIMARY KEY,
    time_bucket TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(64),
    metric_name VARCHAR(100) NOT NULL,
    aggregation_type VARCHAR(20) NOT NULL,
    interval_seconds INTEGER NOT NULL,

    -- Aggregated values - Changed from DECIMAL to DOUBLE PRECISION
    avg_value DOUBLE PRECISION,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    sum_value DOUBLE PRECISION,
    count_value BIGINT,
    stddev_value DOUBLE PRECISION,
    median_value DOUBLE PRECISION,
    p95_value DOUBLE PRECISION,
    p99_value DOUBLE PRECISION,

    metadata JSONB DEFAULT '{}'::jsonb,
    computed_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_aggregation_type CHECK (aggregation_type IN ('avg', 'min', 'max', 'sum', 'count', 'median', 'p95', 'p99')),
    UNIQUE(time_bucket, device_id, metric_name, aggregation_type, interval_seconds)
);

-- 4. Create alert_rules table
CREATE TABLE telemetry.alert_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(1000),
    metric_name VARCHAR(100) NOT NULL,
    condition VARCHAR(500) NOT NULL,
    threshold_value TEXT NOT NULL,
    evaluation_window INTEGER DEFAULT 300,
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
    auto_resolve_timeout INTEGER DEFAULT 3600,

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

-- 5. Create alerts table
CREATE TABLE telemetry.alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(64) NOT NULL UNIQUE,
    rule_id VARCHAR(64) NOT NULL,  -- No FK constraint
    rule_name VARCHAR(200) NOT NULL,
    device_id VARCHAR(64) NOT NULL,  -- No FK constraint - cross-service reference
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

    CONSTRAINT check_alert_status CHECK (status IN ('active', 'acknowledged', 'resolved', 'suppressed'))
);

-- 6. Create real_time_subscriptions table
CREATE TABLE telemetry.real_time_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(64) NOT NULL UNIQUE,
    user_id VARCHAR(100) NOT NULL,
    device_ids TEXT[],
    metric_names TEXT[],
    tags JSONB DEFAULT '{}'::jsonb,
    filter_condition TEXT,
    max_frequency INTEGER DEFAULT 1000,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_sent TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    active BOOLEAN DEFAULT TRUE,

    websocket_id VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 7. Create telemetry_stats table
CREATE TABLE telemetry.telemetry_stats (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(64),
    metric_name VARCHAR(100),
    period VARCHAR(20) NOT NULL,

    -- Statistics - Changed from DECIMAL to DOUBLE PRECISION
    total_points BIGINT DEFAULT 0,
    avg_value DOUBLE PRECISION,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    last_value DOUBLE PRECISION,
    last_updated TIMESTAMPTZ,

    -- Data quality
    missing_points INTEGER DEFAULT 0,
    error_points INTEGER DEFAULT 0,
    quality_score DOUBLE PRECISION DEFAULT 100.0,  -- Changed from DECIMAL

    computed_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT check_period CHECK (period IN ('hour', 'day', 'week', 'month', 'year'))
);

-- 8. Create data_retention_policies table
CREATE TABLE telemetry.data_retention_policies (
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

-- ====================
-- Indexes
-- ====================

-- Telemetry data indexes
CREATE INDEX idx_telemetry_data_device_id ON telemetry.telemetry_data(device_id, time DESC);
CREATE INDEX idx_telemetry_data_metric_name ON telemetry.telemetry_data(metric_name, time DESC);
CREATE INDEX idx_telemetry_data_device_metric ON telemetry.telemetry_data(device_id, metric_name, time DESC);
CREATE INDEX idx_telemetry_data_time ON telemetry.telemetry_data(time DESC);
CREATE INDEX idx_telemetry_data_device_time_numeric ON telemetry.telemetry_data(device_id, time DESC) WHERE value_numeric IS NOT NULL;

-- Aggregated data indexes
CREATE INDEX idx_aggregated_data_device_id ON telemetry.aggregated_data(device_id, time_bucket DESC);
CREATE INDEX idx_aggregated_data_metric_name ON telemetry.aggregated_data(metric_name, time_bucket DESC);
CREATE INDEX idx_aggregated_data_time ON telemetry.aggregated_data(time_bucket DESC);

-- Alert rules indexes
CREATE INDEX idx_alert_rules_metric_name ON telemetry.alert_rules(metric_name);
CREATE INDEX idx_alert_rules_enabled ON telemetry.alert_rules(enabled) WHERE enabled = TRUE;

-- Alerts indexes
CREATE INDEX idx_alerts_device_id ON telemetry.alerts(device_id);
CREATE INDEX idx_alerts_status ON telemetry.alerts(status);
CREATE INDEX idx_alerts_triggered_at ON telemetry.alerts(triggered_at DESC);
CREATE INDEX idx_alerts_rule_id ON telemetry.alerts(rule_id);
CREATE INDEX idx_alerts_device_status ON telemetry.alerts(device_id, status);
CREATE INDEX idx_alerts_active ON telemetry.alerts(status) WHERE status = 'active';

-- Real-time subscriptions indexes
CREATE INDEX idx_real_time_subscriptions_user_id ON telemetry.real_time_subscriptions(user_id);
CREATE INDEX idx_real_time_subscriptions_active ON telemetry.real_time_subscriptions(active) WHERE active = TRUE;

-- Telemetry stats indexes
CREATE INDEX idx_telemetry_stats_device_id ON telemetry.telemetry_stats(device_id);
CREATE INDEX idx_telemetry_stats_period ON telemetry.telemetry_stats(period);
CREATE INDEX idx_telemetry_stats_device_metric ON telemetry.telemetry_stats(device_id, metric_name, period);

-- ====================
-- Materialized View
-- ====================

CREATE MATERIALIZED VIEW telemetry.device_metrics_summary AS
SELECT
    device_id,
    metric_name,
    COUNT(*) as total_points,
    MIN(time) as first_seen,
    MAX(time) as last_seen,
    AVG(value_numeric) as avg_value,
    MIN(value_numeric) as min_value,
    MAX(value_numeric) as max_value
FROM telemetry.telemetry_data
WHERE value_numeric IS NOT NULL
GROUP BY device_id, metric_name;

CREATE INDEX idx_device_metrics_summary_device ON telemetry.device_metrics_summary(device_id);
CREATE INDEX idx_device_metrics_summary_metric ON telemetry.device_metrics_summary(metric_name);

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA telemetry IS 'Telemetry service schema - IoT device time-series data and monitoring';
COMMENT ON TABLE telemetry.metric_definitions IS 'Definition and configuration for telemetry metrics';
COMMENT ON TABLE telemetry.telemetry_data IS 'Time-series telemetry data from IoT devices';
COMMENT ON TABLE telemetry.aggregated_data IS 'Pre-computed aggregations for performance optimization';
COMMENT ON TABLE telemetry.alert_rules IS 'Alert rule definitions for monitoring';
COMMENT ON TABLE telemetry.alerts IS 'Active and historical alerts';
COMMENT ON TABLE telemetry.real_time_subscriptions IS 'WebSocket subscriptions for real-time data';
COMMENT ON TABLE telemetry.telemetry_stats IS 'Cached statistics for quick access';
COMMENT ON TABLE telemetry.data_retention_policies IS 'Data retention and archival policies';

COMMENT ON COLUMN telemetry.telemetry_data.quality IS 'Data quality score (0-100)';
COMMENT ON COLUMN telemetry.telemetry_data.time IS 'Timestamp of the measurement';
COMMENT ON COLUMN telemetry.aggregated_data.time_bucket IS 'Start of the aggregation time bucket';
COMMENT ON COLUMN telemetry.alert_rules.evaluation_window IS 'Time window for evaluating conditions (seconds)';
COMMENT ON COLUMN telemetry.alerts.auto_resolve_at IS 'Time when alert will auto-resolve if configured';
COMMENT ON COLUMN telemetry.real_time_subscriptions.max_frequency IS 'Minimum interval between updates (milliseconds)';
COMMENT ON COLUMN telemetry.telemetry_stats.quality_score IS 'Overall data quality score (0-100)';
