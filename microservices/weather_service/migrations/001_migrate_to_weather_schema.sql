-- Weather Service Migration: Migrate to dedicated weather schema
-- Version: 001
-- Date: 2025-10-28
-- Description: Move tables from dev/public schema to weather schema

-- Create weather schema
CREATE SCHEMA IF NOT EXISTS weather;

-- Drop existing tables/views in weather schema if they exist
DROP TABLE IF EXISTS weather.weather_alerts CASCADE;
DROP TABLE IF EXISTS weather.weather_cache CASCADE;
DROP TABLE IF EXISTS weather.weather_locations CASCADE;

-- 1. Create weather_locations table
CREATE TABLE weather.weather_locations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,  -- No FK constraint - cross-service reference
    location VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_default BOOLEAN DEFAULT FALSE,
    nickname VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create weather_cache table
CREATE TABLE weather.weather_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    location VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,  -- Weather data in JSON format
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create weather_alerts table
CREATE TABLE weather.weather_alerts (
    id SERIAL PRIMARY KEY,
    location VARCHAR(255) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,  -- storm, flood, heat, etc.
    severity VARCHAR(20) NOT NULL,  -- info, warning, severe, extreme
    headline VARCHAR(500) NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    source VARCHAR(100) NOT NULL,  -- Alert provider
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ====================
-- Indexes
-- ====================

-- Weather locations indexes
CREATE INDEX idx_locations_user_id ON weather.weather_locations(user_id);
CREATE INDEX idx_locations_is_default ON weather.weather_locations(user_id, is_default);

-- Weather cache indexes
CREATE INDEX idx_cache_key ON weather.weather_cache(cache_key);
CREATE INDEX idx_cache_location ON weather.weather_cache(location);
CREATE INDEX idx_cache_expires_at ON weather.weather_cache(expires_at);

-- Weather alerts indexes
CREATE INDEX idx_alerts_location ON weather.weather_alerts(location);
CREATE INDEX idx_alerts_severity ON weather.weather_alerts(severity);
CREATE INDEX idx_alerts_time_range ON weather.weather_alerts(location, end_time);

-- ====================
-- Update Triggers
-- ====================

-- Trigger for weather_locations
CREATE TRIGGER update_weather_locations_updated_at
    BEFORE UPDATE ON weather.weather_locations
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Trigger for weather_cache
CREATE TRIGGER update_weather_cache_updated_at
    BEFORE UPDATE ON weather.weather_cache
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Trigger for weather_alerts
CREATE TRIGGER update_weather_alerts_updated_at
    BEFORE UPDATE ON weather.weather_alerts
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ====================
-- Comments
-- ====================

COMMENT ON SCHEMA weather IS 'Weather service schema - weather data, locations, alerts, and caching';
COMMENT ON TABLE weather.weather_locations IS 'User favorite weather locations';
COMMENT ON TABLE weather.weather_cache IS 'Cached weather data for performance';
COMMENT ON TABLE weather.weather_alerts IS 'Weather alerts and warnings';

COMMENT ON COLUMN weather.weather_cache.data IS 'JSON weather data from external providers';
COMMENT ON COLUMN weather.weather_cache.expires_at IS 'Cache expiration time';
COMMENT ON COLUMN weather.weather_alerts.severity IS 'Alert severity: info, warning, severe, extreme';
