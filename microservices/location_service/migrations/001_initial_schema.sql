-- Location Service Database Schema
-- Requires PostGIS extension

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create schema
CREATE SCHEMA IF NOT EXISTS location;

-- ==================== Locations Table ====================

CREATE TABLE IF NOT EXISTS location.locations (
    location_id UUID PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,

    -- Geographic data (PostGIS Geography type for accurate distance calculations)
    coordinates GEOGRAPHY(POINT, 4326) NOT NULL,
    altitude FLOAT,
    accuracy FLOAT NOT NULL,  -- Accuracy in meters
    heading FLOAT CHECK (heading >= 0 AND heading < 360),  -- Direction in degrees
    speed FLOAT CHECK (speed >= 0),  -- Speed in m/s

    -- Address information (from reverse geocoding)
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),

    -- Metadata
    location_method VARCHAR(20) NOT NULL,  -- gps, wifi, cellular, manual, hybrid
    battery_level FLOAT CHECK (battery_level >= 0 AND battery_level <= 100),
    source VARCHAR(50) NOT NULL,  -- device, app, manual
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    CONSTRAINT location_device_timestamp_idx UNIQUE (device_id, timestamp)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_locations_device_timestamp
    ON location.locations (device_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_locations_user_timestamp
    ON location.locations (user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_locations_coordinates
    ON location.locations USING GIST (coordinates);

CREATE INDEX IF NOT EXISTS idx_locations_timestamp
    ON location.locations (timestamp DESC);

-- ==================== Geofences Table ====================

CREATE TABLE IF NOT EXISTS location.geofences (
    geofence_id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    user_id VARCHAR(100) NOT NULL,
    organization_id VARCHAR(100),

    -- Geometry (supports circle, polygon, rectangle)
    shape_type VARCHAR(20) NOT NULL CHECK (shape_type IN ('circle', 'polygon', 'rectangle')),
    geometry GEOGRAPHY NOT NULL,

    -- Configuration
    active BOOLEAN DEFAULT TRUE,
    trigger_on_enter BOOLEAN DEFAULT TRUE,
    trigger_on_exit BOOLEAN DEFAULT TRUE,
    trigger_on_dwell BOOLEAN DEFAULT FALSE,
    dwell_time_seconds INT CHECK (dwell_time_seconds IS NULL OR dwell_time_seconds >= 60),

    -- Target devices (JSONB arrays)
    target_devices JSONB DEFAULT '[]',
    target_groups JSONB DEFAULT '[]',

    -- Time restrictions
    active_days JSONB,  -- ["monday", "tuesday", ...]
    active_hours JSONB,  -- {"start": "09:00", "end": "18:00"}

    -- Notification configuration
    notification_channels JSONB DEFAULT '[]',
    notification_template TEXT,

    -- Statistics
    total_triggers INT DEFAULT 0,
    last_triggered TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_geofences_user_active
    ON location.geofences (user_id, active);

CREATE INDEX IF NOT EXISTS idx_geofences_geometry
    ON location.geofences USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_geofences_organization
    ON location.geofences (organization_id) WHERE organization_id IS NOT NULL;

-- ==================== Location Events Table ====================

CREATE TABLE IF NOT EXISTS location.location_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,

    -- Related location
    location_id UUID,

    -- Geofence information (if applicable)
    geofence_id UUID,
    geofence_name VARCHAR(200),

    -- Movement information
    distance_from_last FLOAT,  -- meters
    time_from_last FLOAT,  -- seconds
    estimated_speed FLOAT,  -- m/s

    -- Event details
    trigger_reason TEXT,
    metadata JSONB DEFAULT '{}',

    -- Status
    timestamp TIMESTAMPTZ NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign keys
    CONSTRAINT fk_location
        FOREIGN KEY (location_id)
        REFERENCES location.locations(location_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_geofence
        FOREIGN KEY (geofence_id)
        REFERENCES location.geofences(geofence_id)
        ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_events_device_timestamp
    ON location.location_events (device_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_events_event_type
    ON location.location_events (event_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_events_geofence
    ON location.location_events (geofence_id, timestamp DESC)
    WHERE geofence_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_events_processed
    ON location.location_events (processed, timestamp)
    WHERE NOT processed;

-- ==================== Places Table ====================

CREATE TABLE IF NOT EXISTS location.places (
    place_id UUID PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('home', 'work', 'school', 'favorite', 'custom')),

    -- Location
    coordinates GEOGRAPHY(POINT, 4326) NOT NULL,
    address TEXT,
    radius FLOAT NOT NULL CHECK (radius > 0 AND radius <= 1000),  -- Recognition radius in meters

    -- Display
    icon VARCHAR(50),
    color VARCHAR(20),

    -- Statistics
    visit_count INT DEFAULT 0,
    total_time_spent INT DEFAULT 0,  -- seconds
    last_visit TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    tags JSONB DEFAULT '[]'
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_places_user_category
    ON location.places (user_id, category);

CREATE INDEX IF NOT EXISTS idx_places_coordinates
    ON location.places USING GIST (coordinates);

-- ==================== Routes Table ====================

CREATE TABLE IF NOT EXISTS location.routes (
    route_id UUID PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    name VARCHAR(200),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'cancelled')),

    -- Start and end locations
    start_location_id UUID,
    end_location_id UUID,

    -- Statistics
    total_distance FLOAT,  -- meters
    total_duration FLOAT,  -- seconds
    avg_speed FLOAT,  -- m/s
    max_speed FLOAT,  -- m/s
    waypoint_count INT DEFAULT 0,

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Foreign keys
    CONSTRAINT fk_start_location
        FOREIGN KEY (start_location_id)
        REFERENCES location.locations(location_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_end_location
        FOREIGN KEY (end_location_id)
        REFERENCES location.locations(location_id)
        ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_routes_device_started
    ON location.routes (device_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_routes_user_started
    ON location.routes (user_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_routes_status
    ON location.routes (status, started_at DESC);

-- ==================== Route Waypoints Table ====================

CREATE TABLE IF NOT EXISTS location.route_waypoints (
    route_id UUID NOT NULL,
    location_id UUID NOT NULL,
    sequence_number INT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,

    PRIMARY KEY (route_id, sequence_number),

    CONSTRAINT fk_route
        FOREIGN KEY (route_id)
        REFERENCES location.routes(route_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_waypoint_location
        FOREIGN KEY (location_id)
        REFERENCES location.locations(location_id)
        ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_waypoints_route_sequence
    ON location.route_waypoints (route_id, sequence_number);

CREATE INDEX IF NOT EXISTS idx_waypoints_route_timestamp
    ON location.route_waypoints (route_id, timestamp);

-- ==================== Device Geofence Status Table ====================
-- Tracks which geofences each device is currently inside

CREATE TABLE IF NOT EXISTS location.device_geofence_status (
    device_id VARCHAR(100) NOT NULL,
    geofence_id UUID NOT NULL,
    inside BOOLEAN NOT NULL,
    entered_at TIMESTAMPTZ,
    last_updated TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (device_id, geofence_id),

    CONSTRAINT fk_status_geofence
        FOREIGN KEY (geofence_id)
        REFERENCES location.geofences(geofence_id)
        ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_device_geofence_status
    ON location.device_geofence_status (device_id, inside);

-- ==================== Views ====================

-- View for active locations (most recent per device)
CREATE OR REPLACE VIEW location.active_locations AS
SELECT DISTINCT ON (device_id)
    location_id,
    device_id,
    user_id,
    ST_Y(coordinates::geometry) as latitude,
    ST_X(coordinates::geometry) as longitude,
    altitude,
    accuracy,
    heading,
    speed,
    location_method,
    battery_level,
    timestamp,
    created_at
FROM location.locations
ORDER BY device_id, timestamp DESC;

-- ==================== Functions ====================

-- Function to update geofence trigger count
CREATE OR REPLACE FUNCTION location.update_geofence_trigger_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.event_type IN ('geofence_enter', 'geofence_exit', 'geofence_dwell')
       AND NEW.geofence_id IS NOT NULL THEN
        UPDATE location.geofences
        SET total_triggers = total_triggers + 1,
            last_triggered = NEW.timestamp
        WHERE geofence_id = NEW.geofence_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for geofence trigger count
DROP TRIGGER IF EXISTS trigger_update_geofence_count ON location.location_events;
CREATE TRIGGER trigger_update_geofence_count
    AFTER INSERT ON location.location_events
    FOR EACH ROW
    EXECUTE FUNCTION location.update_geofence_trigger_count();

-- Function to update place visit statistics
CREATE OR REPLACE FUNCTION location.update_place_visit_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.event_type = 'place_visited' THEN
        UPDATE location.places
        SET visit_count = visit_count + 1,
            last_visit = NEW.timestamp
        WHERE place_id = (NEW.metadata->>'place_id')::UUID;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for place visit statistics
DROP TRIGGER IF EXISTS trigger_update_place_stats ON location.location_events;
CREATE TRIGGER trigger_update_place_stats
    AFTER INSERT ON location.location_events
    FOR EACH ROW
    EXECUTE FUNCTION location.update_place_visit_stats();

-- ==================== Sample Data (Optional) ====================

-- Insert sample geofence for testing (commented out)
/*
INSERT INTO location.geofences (
    geofence_id, name, user_id, shape_type, geometry,
    trigger_on_enter, trigger_on_exit, active
) VALUES (
    gen_random_uuid(),
    'Sample Home Geofence',
    'test_user',
    'circle',
    ST_Buffer(ST_MakePoint(-122.4194, 37.7749)::geography, 100),  -- 100m radius around San Francisco
    true,
    true,
    true
);
*/
