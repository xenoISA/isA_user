-- Location Service Database Schema (Simplified MVP)
-- 专注于核心功能：记录位置、查询位置、用于推荐

-- Create schema
CREATE SCHEMA IF NOT EXISTS location;

-- ==================== Locations Table ====================
-- 存储用户/设备的位置记录

CREATE TABLE IF NOT EXISTS location.locations (
    location_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,

    -- 地理坐标（简单的经纬度，不需要PostGIS）
    latitude DECIMAL(10, 8) NOT NULL,  -- -90 to 90
    longitude DECIMAL(11, 8) NOT NULL,  -- -180 to 180
    accuracy FLOAT,  -- 精度（米）

    -- 地址信息（用于推荐系统）
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    address TEXT,

    -- 元数据
    location_method VARCHAR(20),  -- gps, wifi, cellular, manual
    source VARCHAR(50) DEFAULT 'device',  -- device, app, manual
    metadata JSONB DEFAULT '{}',

    -- 时间戳
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- 确保同一设备同一时间只有一条记录
    CONSTRAINT unique_device_timestamp UNIQUE (device_id, timestamp)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_locations_device_timestamp
    ON location.locations (device_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_locations_user_timestamp
    ON location.locations (user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_locations_timestamp
    ON location.locations (timestamp DESC);

-- 地理位置索引（用于查找附近的位置）
CREATE INDEX IF NOT EXISTS idx_locations_lat_lon
    ON location.locations (latitude, longitude);

-- ==================== Places Table (可选) ====================
-- 用户标记的常用地点（家、公司等）

CREATE TABLE IF NOT EXISTS location.places (
    place_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('home', 'work', 'favorite', 'other')),

    -- 位置
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    address TEXT,

    -- 元数据
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_places_user
    ON location.places (user_id);

-- ==================== Views ====================

-- 获取每个设备的最新位置
CREATE OR REPLACE VIEW location.latest_locations AS
SELECT DISTINCT ON (device_id)
    location_id,
    device_id,
    user_id,
    latitude,
    longitude,
    accuracy,
    city,
    state,
    country,
    address,
    timestamp
FROM location.locations
ORDER BY device_id, timestamp DESC;

-- ==================== Helper Functions ====================

-- 计算两点之间的距离（Haversine公式，单位：米）
CREATE OR REPLACE FUNCTION location.calculate_distance(
    lat1 DECIMAL,
    lon1 DECIMAL,
    lat2 DECIMAL,
    lon2 DECIMAL
)
RETURNS FLOAT AS $$
DECLARE
    earth_radius FLOAT := 6371000; -- 地球半径（米）
    dlat FLOAT;
    dlon FLOAT;
    a FLOAT;
    c FLOAT;
BEGIN
    dlat := radians(lat2 - lat1);
    dlon := radians(lon2 - lon1);

    a := sin(dlat/2) * sin(dlat/2) +
         cos(radians(lat1)) * cos(radians(lat2)) *
         sin(dlon/2) * sin(dlon/2);

    c := 2 * atan2(sqrt(a), sqrt(1-a));

    RETURN earth_radius * c;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ==================== Sample Usage ====================
/*
-- 插入位置记录
INSERT INTO location.locations (device_id, user_id, latitude, longitude, city, country, timestamp)
VALUES ('device_123', 'user_456', 37.7749, -122.4194, 'San Francisco', 'USA', NOW());

-- 获取设备最新位置
SELECT * FROM location.latest_locations WHERE device_id = 'device_123';

-- 获取用户最近10条位置记录
SELECT * FROM location.locations
WHERE user_id = 'user_456'
ORDER BY timestamp DESC
LIMIT 10;

-- 计算两个位置之间的距离
SELECT location.calculate_distance(37.7749, -122.4194, 37.7849, -122.4094) as distance_meters;

-- 查找某个位置附近的设备（简单方式，适合小数据量）
SELECT DISTINCT ON (device_id)
    device_id,
    latitude,
    longitude,
    location.calculate_distance(37.7749, -122.4194, latitude, longitude) as distance
FROM location.locations
WHERE timestamp >= NOW() - INTERVAL '1 hour'
HAVING location.calculate_distance(37.7749, -122.4194, latitude, longitude) < 1000
ORDER BY device_id, timestamp DESC;
*/
