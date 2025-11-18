# Location Service

AI-powered location tracking and geofencing microservice with PostGIS support.

## Features

- 📍 **Real-time Location Tracking**: Track device locations with GPS, WiFi, cellular, and hybrid methods
- 🎯 **Geofencing**: Create circular, polygon, and rectangular geofences with enter/exit/dwell triggers
- 🗺️ **Spatial Queries**: Find nearby devices, search by radius or polygon
- 📌 **Places Management**: Define and track visits to favorite places (home, work, etc.)
- 🛤️ **Route Tracking**: Record and analyze device movement routes
- 📊 **Statistics & Analytics**: Location statistics, heatmaps, and travel patterns
- 🔔 **Event-Driven**: Publishes location events via NATS for real-time notifications
- 🌍 **PostGIS Integration**: Accurate geographic calculations and spatial indexing

## Architecture

```
┌─────────────────────┐
│  Device Service     │──┐
│  (设备管理)         │  │
└─────────────────────┘  │
                         │
┌─────────────────────┐  │    ┌─────────────────────┐
│  Telemetry Service  │──┼────│  Location Service   │
│  (遥测数据)         │  │    │  (位置服务)         │
└─────────────────────┘  │    └─────────────────────┘
                         │
┌─────────────────────┐  │
│  OTA Service        │──┘
│  (固件更新)         │
└─────────────────────┘
```

## Tech Stack

- **FastAPI**: High-performance async web framework
- **PostgreSQL + PostGIS**: Spatial database for geographic data
- **TimescaleDB**: Time-series optimization (optional)
- **NATS**: Event bus for real-time notifications
- **Consul**: Service discovery and configuration
- **Redis**: Caching layer for performance

## API Endpoints

### Location Management

```
POST   /locations                        - Report device location
POST   /locations/batch                  - Batch report locations
GET    /locations/device/{device_id}     - Get latest location
GET    /locations/device/{device_id}/history - Get location history
GET    /locations/user/{user_id}         - Get user's devices locations
```

### Geofencing

```
POST   /geofences                        - Create geofence
GET    /geofences                        - List geofences
GET    /geofences/{id}                   - Get geofence details
PUT    /geofences/{id}                   - Update geofence
DELETE /geofences/{id}                   - Delete geofence
POST   /geofences/{id}/activate          - Activate geofence
POST   /geofences/{id}/deactivate        - Deactivate geofence
GET    /geofences/{id}/events            - Get trigger events
```

### Spatial Search

```
GET    /locations/nearby                 - Find nearby devices
POST   /locations/search/radius          - Search in circular area
POST   /locations/search/polygon         - Search in polygon area
GET    /locations/distance               - Calculate distance
```

### Statistics

```
GET    /stats/user/{user_id}             - User location statistics
GET    /stats/device/{device_id}         - Device location statistics
GET    /stats/geofence/{geofence_id}     - Geofence trigger statistics
```

## Quick Start

### 1. Database Setup

```bash
# Create PostgreSQL database with PostGIS
psql -U postgres -c "CREATE DATABASE isa_platform;"
psql -U postgres -d isa_platform -c "CREATE EXTENSION postgis;"

# Run migrations
psql -U postgres -d isa_platform -f migrations/001_initial_schema.sql
```

### 2. Configuration

```bash
# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export REDIS_HOST=localhost
export REDIS_PORT=6379
export NATS_URL=nats://localhost:4222
export CONSUL_HOST=localhost
export CONSUL_PORT=8500
```

### 3. Run Service

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python -m microservices.location_service.main
```

The service will start on `http://localhost:8224`

## Usage Examples

### Report Location

```python
from microservices.location_service.client import LocationServiceClient

client = LocationServiceClient()

# Report device location
result = await client.report_location(
    device_id="device_123",
    latitude=37.7749,
    longitude=-122.4194,
    accuracy=10.0,
    location_method="gps",
    battery_level=85.5
)
```

### Create Geofence

```python
# Create a circular geofence (100m radius)
result = await client.create_geofence(
    name="Home",
    shape_type="circle",
    center_lat=37.7749,
    center_lon=-122.4194,
    radius=100.0,
    trigger_on_enter=True,
    trigger_on_exit=True,
    notification_channels=["email", "push"]
)
```

### Find Nearby Devices

```python
# Find devices within 5km
devices = await client.find_nearby_devices(
    latitude=37.7749,
    longitude=-122.4194,
    radius_meters=5000,
    time_window_minutes=30
)
```

## Event Types

The service publishes the following events via NATS:

```python
# Location events
location.updated
location.batch.updated

# Geofence events
location.geofence.created
location.geofence.entered
location.geofence.exited
location.geofence.dwell

# Movement events
location.device.started_moving
location.device.stopped
location.significant_movement

# Alert events
location.low_battery
location.device.out_of_bounds
```

## Database Schema

See [migrations/001_initial_schema.sql](migrations/001_initial_schema.sql) for the complete schema.

Key tables:
- `locations`: Device location records with PostGIS geography
- `geofences`: Geofence definitions with spatial geometry
- `location_events`: Location-triggered events
- `places`: User-defined favorite places
- `routes`: Movement route tracking
- `device_geofence_status`: Current geofence status per device

## Performance Optimization

### Spatial Indexing

```sql
-- PostGIS GIST indexes for fast spatial queries
CREATE INDEX idx_locations_coordinates
    ON location.locations USING GIST (coordinates);

CREATE INDEX idx_geofences_geometry
    ON location.geofences USING GIST (geometry);
```

### Time-Series Optimization with TimescaleDB

```sql
-- Convert locations to hypertable
SELECT create_hypertable('locations', 'timestamp');

-- Create continuous aggregate for hourly stats
CREATE MATERIALIZED VIEW locations_hourly
WITH (timescaledb.continuous) AS
SELECT device_id,
       time_bucket('1 hour', timestamp) AS hour,
       COUNT(*) as location_count,
       AVG(speed) as avg_speed
FROM locations
GROUP BY device_id, hour;
```

### Caching Strategy

```
location:device:{device_id}:latest → Location (TTL: 1h)
location:nearby:{lat}:{lon}:{radius} → List[DeviceLocation] (TTL: 5min)
geofence:{geofence_id} → Geofence (TTL: 1d)
```

## Security & Privacy

- **Access Control**: Users can only access their own devices' locations
- **Location Obfuscation**: Optional location fuzzing for privacy
- **Data Retention**: Automatic cleanup of old location data
- **Audit Logging**: All location accesses are logged

## Monitoring

### Health Check

```bash
curl http://localhost:8224/health
```

### Prometheus Metrics

```python
location_updates_total
location_updates_per_second
geofence_triggers_total
geofence_check_duration_seconds
nearby_search_duration_seconds
```

## Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Load testing with Locust
locust -f tests/load/locustfile.py
```

## Roadmap

- [ ] Indoor positioning support (WiFi/Bluetooth)
- [ ] Trajectory prediction using machine learning
- [ ] Real-time tracking dashboard
- [ ] Integration with mapping services (Google Maps, OpenStreetMap)
- [ ] AR location services
- [ ] Multi-device collaborative positioning

## Documentation

- [API Documentation](docs/API.md)
- [Design Document](../../docs/location_service_design.md)
- [Database Schema](migrations/001_initial_schema.sql)

## License

ISA Platform - Internal Use

## Support

For issues and questions, contact the ISA Platform team.
