-- Weather Service Database Schema

-- ==========================================
-- 微服务数据库设计原则:
-- ==========================================
-- NO FOREIGN KEYS to other services' tables
-- user_id 只存储ID值，不建立FK

-- Favorite locations table
CREATE TABLE IF NOT EXISTS weather_locations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    location VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    is_default BOOLEAN DEFAULT FALSE,
    nickname VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_weather_locations_user ON weather_locations(user_id);
CREATE INDEX idx_weather_locations_default ON weather_locations(user_id, is_default);

-- Weather cache table (optional, if not using Redis)
CREATE TABLE IF NOT EXISTS weather_cache (
    id SERIAL PRIMARY KEY,
    location VARCHAR(255) NOT NULL,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    data JSONB NOT NULL,
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_weather_cache_key ON weather_cache(cache_key);
CREATE INDEX idx_weather_cache_expires ON weather_cache(expires_at);

-- Clean up expired cache entries (optional cleanup job)
CREATE OR REPLACE FUNCTION clean_expired_weather_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM weather_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Weather alerts table (for historical tracking)
CREATE TABLE IF NOT EXISTS weather_alerts (
    id SERIAL PRIMARY KEY,
    location VARCHAR(255) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    headline VARCHAR(500) NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_weather_alerts_location ON weather_alerts(location);
CREATE INDEX idx_weather_alerts_severity ON weather_alerts(severity);
CREATE INDEX idx_weather_alerts_time ON weather_alerts(start_time, end_time);

