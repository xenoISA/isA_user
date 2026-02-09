# Weather Service - Domain Context

## Overview

The Weather Service is the **environmental intelligence layer** for the isA_user platform. It provides real-time weather data, multi-day forecasts, weather alerts, and location management capabilities by integrating with external weather API providers.

**Business Context**: Enable users and IoT devices to make weather-informed decisions through accurate, cached weather data from multiple providers. Weather Service owns the "what's the weather" of the system - ensuring every user and device has access to reliable meteorological information.

**Core Value Proposition**: Transform external weather API data into a unified, cached weather layer with intelligent caching, multi-provider fallback, user location management, and event-driven alert notifications across the platform.

---

## Business Taxonomy

### Core Entities

#### 1. Weather Data (Current Weather)
**Definition**: Real-time meteorological conditions for a specific location at the current moment.

**Business Purpose**:
- Provide current temperature, humidity, and conditions
- Enable weather-aware device automation
- Support user decision-making for activities
- Feed IoT device intelligence systems

**Key Attributes**:
- Location (city name or coordinates)
- Temperature (in Celsius or Fahrenheit)
- Feels Like Temperature (wind chill/heat index adjusted)
- Humidity (percentage 0-100)
- Condition (clear, cloudy, rain, snow, etc.)
- Description (detailed weather description)
- Icon (weather icon code for UI display)
- Wind Speed (meters per second)
- Observed At (timestamp of observation)
- Provider (data source: OpenWeatherMap, WeatherAPI)

**Weather Conditions**:
- **Clear**: No precipitation, clear skies
- **Cloudy**: Overcast or partially cloudy
- **Rain**: Active precipitation (light to heavy)
- **Snow**: Winter precipitation
- **Thunderstorm**: Severe weather with lightning
- **Mist/Fog**: Reduced visibility conditions

#### 2. Weather Forecast
**Definition**: Predicted weather conditions for upcoming days (1-16 day outlook).

**Business Purpose**:
- Enable planning for outdoor activities
- Support device scheduling decisions
- Provide trend analysis for weather patterns
- Enable proactive user notifications

**Key Attributes**:
- Location (city name or coordinates)
- Forecast Days (list of daily predictions)
- Generated At (forecast creation timestamp)
- Provider (data source)

**Forecast Day Attributes**:
- Date (forecast date)
- Temp Max (daily high temperature)
- Temp Min (daily low temperature)
- Temp Avg (average temperature)
- Condition (expected weather condition)
- Description (detailed forecast text)
- Icon (weather icon code)
- Humidity (expected humidity)
- Wind Speed (expected wind)
- Precipitation Chance (0-100%)
- Precipitation Amount (mm)

#### 3. Weather Alert
**Definition**: Severe weather warnings issued for a specific location during a time period.

**Business Purpose**:
- Protect users from hazardous conditions
- Enable emergency notifications
- Support device safety automation
- Ensure regulatory compliance for weather warnings

**Key Attributes**:
- Location (affected area)
- Alert Type (storm, flood, heat, cold, hurricane, etc.)
- Severity (info, warning, severe, extreme)
- Headline (brief alert summary)
- Description (detailed alert information)
- Start Time (alert effective time)
- End Time (alert expiration time)
- Source (issuing authority)
- Created At (when alert was received)

**Alert Severity Levels**:
- **Info**: General weather information
- **Warning**: Hazardous conditions possible
- **Severe**: Dangerous conditions expected
- **Extreme**: Life-threatening conditions

#### 4. Favorite Location
**Definition**: User-saved location for quick weather access and personalized alerts.

**Business Purpose**:
- Enable personalized weather experience
- Support multi-location monitoring
- Track user location preferences
- Enable location-based notifications

**Key Attributes**:
- User ID (owner of the saved location)
- Location (city name or place name)
- Latitude (GPS coordinate)
- Longitude (GPS coordinate)
- Is Default (primary location flag)
- Nickname (user-friendly name, e.g., "Home", "Office")
- Created At (when saved)

#### 5. Weather Cache
**Definition**: Temporary storage of weather data to reduce API calls and improve response times.

**Business Purpose**:
- Reduce external API costs and rate limits
- Improve response latency
- Ensure availability during provider outages
- Enable offline-first architecture

**Key Attributes**:
- Cache Key (unique identifier: location + data type + units)
- Data (cached weather response)
- Cached At (when cached)
- Expires At (cache expiration time)
- Location (for cache lookup)

**Cache TTL Settings**:
- Current Weather: 15 minutes (900 seconds)
- Forecast Data: 30 minutes (1800 seconds)
- Weather Alerts: 10 minutes (600 seconds)

---

## Domain Scenarios

### Scenario 1: Get Current Weather with Caching
**Actor**: User, Mobile App, IoT Device
**Trigger**: User requests current weather for a location
**Preconditions**: Weather API key configured, location valid
**Flow**:
1. Client calls `GET /api/v1/weather/current?location=London&units=metric`
2. Weather Service generates cache key: `weather:current:London:metric`
3. Service checks Redis cache for existing data
4. **Cache Hit**: Return cached data with `cached: true`
5. **Cache Miss**: Fetch from external provider (OpenWeatherMap or WeatherAPI)
6. Transform provider response to standard format
7. Cache result in Redis with 15-minute TTL
8. Also cache in PostgreSQL as backup
9. Publishes `weather.data.fetched` event to NATS
10. Return weather data with `cached: false`

**Outcome**: User receives current weather, subsequent requests served from cache
**Events**: `weather.data.fetched`
**Errors**:
- 404: Location not found by weather provider
- 500: External API error or service unavailable

### Scenario 2: Get Multi-Day Weather Forecast
**Actor**: User, Scheduling App
**Trigger**: User requests weather forecast for planning
**Preconditions**: Weather API key configured, location valid
**Flow**:
1. Client calls `GET /api/v1/weather/forecast?location=Tokyo&days=7`
2. Weather Service validates days parameter (1-16 range)
3. Generates cache key: `weather:forecast:Tokyo:7`
4. Checks cache for existing forecast
5. **Cache Hit**: Return cached forecast
6. **Cache Miss**: Fetch from external provider
7. Provider returns 3-hour interval data (OpenWeatherMap)
8. Service aggregates intervals into daily forecasts
9. Calculates daily min/max/avg temperatures
10. Caches result with 30-minute TTL
11. Returns forecast with daily predictions

**Outcome**: User receives multi-day forecast for planning
**Errors**:
- 400: Invalid days parameter (< 1 or > 16)
- 404: Location not found
- 500: Provider API error

### Scenario 3: Weather Alert Detection and Notification
**Actor**: Weather Service, Notification Service
**Trigger**: Active weather alerts exist for user's location
**Preconditions**: User has saved locations, alerts enabled
**Flow**:
1. Client calls `GET /api/v1/weather/alerts?location=Miami`
2. Weather Service queries PostgreSQL for active alerts
3. Filters alerts where `end_time >= now()`
4. Orders by severity (extreme > severe > warning > info)
5. If alerts exist, publishes `weather.alert.created` event
6. Event payload includes alert count, severity, headlines
7. Notification Service receives event
8. Notification Service sends push/email to affected users
9. Returns alert list to client

**Outcome**: Users notified of severe weather, can take protective action
**Events**: `weather.alert.created`
**Errors**:
- 500: Database query error

### Scenario 4: Save Favorite Location
**Actor**: Authenticated User
**Trigger**: User wants to save a location for quick access
**Preconditions**: User authenticated, valid location data
**Flow**:
1. Client calls `POST /api/v1/weather/locations` with user_id, location, coordinates
2. Weather Service validates request fields
3. If `is_default: true`, unsets other default locations for user
4. Inserts new location record in PostgreSQL
5. Publishes `weather.location_saved` event
6. Returns saved location with generated ID

**Outcome**: User can quickly access weather for saved locations
**Events**: `weather.location_saved`
**Errors**:
- 400: Invalid request (missing required fields)
- 500: Database insert error

### Scenario 5: Multi-Location Weather Dashboard
**Actor**: User, Dashboard App
**Trigger**: User views weather for all saved locations
**Preconditions**: User has saved locations
**Flow**:
1. Dashboard calls `GET /api/v1/weather/locations/{user_id}`
2. Weather Service queries all user locations from PostgreSQL
3. Orders by `is_default DESC, created_at DESC`
4. Returns location list with total count
5. Dashboard iterates through locations
6. For each location, calls `GET /api/v1/weather/current`
7. Weather Service serves from cache (most likely cached)
8. Dashboard displays unified weather view

**Outcome**: User sees weather for all important locations in one view
**Errors**:
- 500: Database query error

### Scenario 6: Delete Favorite Location
**Actor**: Authenticated User
**Trigger**: User removes a saved location
**Preconditions**: Location exists and belongs to user
**Flow**:
1. Client calls `DELETE /api/v1/weather/locations/{location_id}?user_id={user_id}`
2. Weather Service verifies location_id exists
3. Verifies user_id matches location owner
4. Deletes location from PostgreSQL
5. Returns 204 No Content on success

**Outcome**: Location removed, no longer appears in user's saved locations
**Errors**:
- 404: Location not found or user_id mismatch
- 500: Database delete error

### Scenario 7: Provider Fallback on Failure
**Actor**: Weather Service (Internal)
**Trigger**: Primary weather provider returns error
**Preconditions**: Multiple providers configured
**Flow**:
1. User requests current weather
2. Service attempts OpenWeatherMap API call
3. Provider returns 503 Service Unavailable
4. Service logs error and attempts WeatherAPI fallback
5. WeatherAPI returns valid data
6. Service transforms to standard format
7. Caches result (source: WeatherAPI)
8. Returns weather to user

**Outcome**: User receives weather despite primary provider outage
**Note**: Currently implemented for current weather; forecast fallback pending

### Scenario 8: Cache Invalidation for Location
**Actor**: Admin, Weather Service
**Trigger**: Need to force fresh weather data
**Preconditions**: Location has cached data
**Flow**:
1. Admin or scheduled task triggers cache clear for location
2. Weather Service calls `clear_location_cache("London")`
3. Service scans Redis for keys matching `weather:*:London:*`
4. Deletes all matching Redis keys
5. Deletes from PostgreSQL cache table where location matches
6. Next request will fetch fresh data from provider

**Outcome**: Stale cache removed, fresh data served on next request

---

## Domain Events

### Published Events

#### 1. `weather.data.fetched` (EventType.WEATHER_DATA_FETCHED)
**Trigger**: After successfully fetching current weather from external provider
**When**: On cache miss, after API call succeeds
**Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "weather.data.fetched",
  "source": "weather_service",
  "data": {
    "location": "London",
    "temperature": 15.5,
    "condition": "cloudy",
    "units": "metric",
    "provider": "openweathermap",
    "timestamp": "2025-01-15T10:30:00Z"
  },
  "correlation_id": "optional-uuid"
}
```
**Consumers**:
- **Analytics Service**: Track weather API usage and popular locations
- **Device Service**: Update device displays with latest weather
- **Memory Service**: Store weather context for user interactions

**Ordering**: Per-location ordering (same location events in sequence)
**Retry**: 3 retries, exponential backoff

#### 2. `weather.alert.created` (EventType.WEATHER_ALERT_CREATED)
**Trigger**: When active weather alerts are detected for a location
**When**: On `/api/v1/weather/alerts` request with non-empty results
**Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "weather.alert.created",
  "source": "weather_service",
  "data": {
    "location": "Miami",
    "alert_count": 2,
    "alerts": [
      {
        "severity": "severe",
        "alert_type": "hurricane",
        "headline": "Hurricane Warning in Effect"
      },
      {
        "severity": "warning",
        "alert_type": "flood",
        "headline": "Flood Watch Until Tomorrow"
      }
    ],
    "timestamp": "2025-01-15T14:00:00Z"
  }
}
```
**Consumers**:
- **Notification Service**: Send push notifications to users in affected areas
- **Device Service**: Trigger safety mode on outdoor devices
- **Calendar Service**: Flag affected calendar events

**Ordering**: Per-location ordering
**Retry**: 3 retries, immediate retry for alerts (time-sensitive)

#### 3. `weather.location_saved` (Event Model Defined)
**Trigger**: When user saves a favorite location
**When**: After successful location insert
**Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "weather.location_saved",
  "source": "weather_service",
  "data": {
    "user_id": "user_12345",
    "location_id": 42,
    "location": "New York",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "is_default": true,
    "nickname": "Home",
    "created_at": "2025-01-15T09:00:00Z"
  }
}
```
**Consumers**:
- **Notification Service**: Setup location-based weather alerts
- **Analytics Service**: Track location preferences
- **Device Service**: Configure device location awareness

**Ordering**: Per-user ordering
**Retry**: 3 retries, exponential backoff

#### 4. `weather.alert_issued` (Event Model Defined)
**Trigger**: When a new weather alert is detected for a user's saved location
**When**: Alert matches user's saved location
**Payload**:
```json
{
  "event_id": "uuid",
  "event_type": "weather.alert_issued",
  "source": "weather_service",
  "data": {
    "user_id": "user_12345",
    "location": "Miami",
    "alert_type": "hurricane",
    "severity": "high",
    "description": "Hurricane warning in effect",
    "start_time": "2025-01-16T14:00:00Z",
    "end_time": "2025-01-17T06:00:00Z",
    "issued_at": "2025-01-15T10:00:00Z"
  }
}
```
**Consumers**:
- **Notification Service**: Send personalized alert to user
- **Calendar Service**: Update calendar with weather warnings
- **Device Service**: Trigger protective device actions

**Ordering**: Per-user ordering
**Retry**: Immediate retry (time-critical alerts)

### Consumed Events

Weather Service is primarily an event publisher. It does not currently subscribe to events from other services. Future integrations may include:

- `device.location_updated` from device_service: Update device-linked weather data
- `user.preferences_updated` from account_service: Update weather preferences (units, providers)

---

## Core Concepts

### Multi-Provider Architecture
Weather Service integrates with multiple external weather API providers to ensure reliability and data quality:

1. **OpenWeatherMap** (Primary)
   - Current weather: `api.openweathermap.org/data/2.5/weather`
   - Forecast: `api.openweathermap.org/data/2.5/forecast`
   - Free tier: 60 calls/minute, 5-day forecast
   - Response transformation required

2. **WeatherAPI** (Secondary)
   - Current weather: `api.weatherapi.com/v1/current.json`
   - Forecast: `api.weatherapi.com/v1/forecast.json`
   - Free tier: 1M calls/month
   - Richer data fields

3. **VisualCrossing** (Future)
   - Reserved for historical weather data
   - Not yet implemented

Provider selection is configured via `WEATHER_PROVIDER` environment variable. Fallback logic ensures service availability.

### Intelligent Caching Strategy
Weather Service implements a two-tier caching strategy to optimize performance and reduce API costs:

**Tier 1: Redis (Hot Cache)**
- In-memory, sub-millisecond access
- TTL-based expiration
- Preferred for read-heavy workloads
- Key format: `weather:{type}:{location}:{units}`

**Tier 2: PostgreSQL (Warm Cache)**
- Persistent backup cache
- Survives Redis restarts
- Query-based expiration check
- Table: `weather.weather_cache`

**Cache TTL Guidelines**:
| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Current Weather | 15 min | Balance freshness vs. API limits |
| Forecast | 30 min | Forecasts change slowly |
| Alerts | 10 min | Time-critical, need freshness |

### Unit System Support
Weather Service supports both metric and imperial unit systems:

**Metric** (default):
- Temperature: Celsius (°C)
- Wind Speed: meters/second (m/s)
- Precipitation: millimeters (mm)

**Imperial**:
- Temperature: Fahrenheit (°F)
- Wind Speed: miles/hour (mph)
- Precipitation: inches (in)

Unit conversion happens at the API provider level when possible.

### Location Resolution
Locations can be specified in multiple formats:

1. **City Name**: "London", "New York", "Tokyo"
2. **City, Country**: "Paris, FR", "Sydney, AU"
3. **Coordinates**: "40.7128,-74.0060" (future)
4. **ZIP/Postal Code**: "10001" (future)

Location normalization ensures consistent cache keys regardless of input format.

### Separation of Concerns
**Weather Service owns**:
- Weather data fetching and caching
- Multi-provider integration
- Weather alerts storage and retrieval
- User favorite locations
- Cache management

**Weather Service does NOT own**:
- User authentication (auth_service)
- Notification delivery (notification_service)
- Device weather displays (device_service)
- Weather-based calendar events (calendar_service)
- Weather analytics (analytics_service)

---

## High-Level Business Rules

### Weather Data Rules (BR-WTH-001 to BR-WTH-010)

**BR-WTH-001: Location Required**
- All weather requests MUST include a valid location parameter
- System validates location is non-empty string
- Error returned if missing: "Location parameter is required"
- Example: `location.length >= 1`

**BR-WTH-002: Unit System Validation**
- Units parameter MUST be "metric" or "imperial"
- Default value: "metric" if not specified
- Error returned if invalid: "Invalid units, must be metric or imperial"
- Example: `units IN ("metric", "imperial")`

**BR-WTH-003: Temperature Range Validation**
- Temperature values MUST be within physical limits
- Celsius: -100°C to +60°C
- Fahrenheit: -148°F to +140°F
- Values outside range indicate provider error

**BR-WTH-004: Humidity Percentage**
- Humidity MUST be between 0 and 100 inclusive
- Validated in models: `ge=0, le=100`
- Error: "Humidity must be percentage 0-100"
- Example: `humidity >= 0 AND humidity <= 100`

**BR-WTH-005: Weather Provider Configuration**
- Service MUST have at least one valid API key configured
- Check: `OPENWEATHER_API_KEY` or `WEATHERAPI_KEY` set
- Error logged if no providers available
- Service degrades gracefully if API key missing

**BR-WTH-006: Cache Key Uniqueness**
- Cache keys MUST uniquely identify weather data
- Format: `weather:{type}:{location}:{units}`
- Example: `weather:current:London:metric`
- Related: BR-WTH-007

**BR-WTH-007: Cache Expiration**
- Cached weather data MUST expire after configured TTL
- Current weather: 15 minutes (900 seconds)
- Forecast: 30 minutes (1800 seconds)
- Alerts: 10 minutes (600 seconds)
- Environment override: `WEATHER_CACHE_TTL`, `FORECAST_CACHE_TTL`, `ALERTS_CACHE_TTL`

**BR-WTH-008: Provider Response Transformation**
- External API responses MUST be transformed to standard format
- Standard fields: location, temperature, humidity, condition, wind_speed
- Provider-specific fields normalized (e.g., WeatherAPI wind_kph → m/s)

**BR-WTH-009: Observed Timestamp Required**
- Current weather MUST include `observed_at` timestamp
- Timestamp represents when observation was taken
- Format: ISO 8601 UTC
- Example: `2025-01-15T10:30:00Z`

**BR-WTH-010: Cache Flag in Response**
- Response MUST indicate if data was served from cache
- `cached: true` for cache hits
- `cached: false` for fresh API data
- Enables client-side staleness awareness

### Forecast Rules (BR-FCT-001 to BR-FCT-010)

**BR-FCT-001: Forecast Days Range**
- Days parameter MUST be between 1 and 16 inclusive
- Validated in models: `ge=1, le=16`
- Error: "Days must be between 1 and 16"
- Example: `days >= 1 AND days <= 16`

**BR-FCT-002: OpenWeatherMap Free Tier Limit**
- Free tier supports maximum 5-day forecast
- System calculates: `cnt = min(days * 8, 40)`
- 8 data points per day (3-hour intervals)
- Extended forecasts require premium API

**BR-FCT-003: Daily Aggregation**
- Provider 3-hour data MUST be aggregated to daily forecasts
- Temp Max: highest temperature of day
- Temp Min: lowest temperature of day
- Temp Avg: arithmetic mean of day's temperatures
- Condition: most frequent condition of day

**BR-FCT-004: Forecast Day Date**
- Each forecast day MUST have valid date
- Date calculated from provider timestamp
- Ordered chronologically (today first)
- No duplicate dates in forecast array

**BR-FCT-005: Precipitation Percentage**
- Precipitation chance MUST be 0-100 percentage
- Validated: `ge=0, le=100`
- Optional field (provider-dependent)
- Example: `precipitation_chance >= 0 AND precipitation_chance <= 100`

### Alert Rules (BR-ALT-001 to BR-ALT-010)

**BR-ALT-001: Alert Severity Levels**
- Severity MUST be one of: info, warning, severe, extreme
- Defined in AlertSeverity enum
- Ordering: extreme > severe > warning > info
- Example: `severity IN ("info", "warning", "severe", "extreme")`

**BR-ALT-002: Alert Time Window**
- Active alerts MUST have `end_time >= current_time`
- Expired alerts filtered from query results
- Query: `WHERE end_time >= NOW()`
- Related: BR-ALT-003

**BR-ALT-003: Alert Ordering**
- Alert results MUST be ordered by severity DESC
- Most severe alerts appear first
- Secondary order: start_time ASC (earliest first)

**BR-ALT-004: Alert Required Fields**
- Alerts MUST include: location, alert_type, severity, headline, description
- Start time and end time required for validity window
- Source (issuing authority) required for attribution

**BR-ALT-005: Alert Type Categories**
- Alert types include: storm, flood, heat, cold, hurricane, tornado, wildfire
- Free-form string to support provider variations
- No strict validation (provider-dependent)

### Location Rules (BR-LOC-001 to BR-LOC-010)

**BR-LOC-001: User ID Required for Locations**
- Saved locations MUST be associated with a user_id
- User ID validates ownership for retrieval/deletion
- Foreign key relationship implied (not enforced)

**BR-LOC-002: Single Default Location**
- User can have only ONE default location
- Setting new default MUST unset previous default
- Query: `UPDATE SET is_default = FALSE WHERE user_id = $1`
- Related: BR-LOC-003

**BR-LOC-003: Default Location Ordering**
- Location lists ordered by `is_default DESC, created_at DESC`
- Default location always appears first
- Most recently added non-defaults appear next

**BR-LOC-004: Location Deletion Authorization**
- DELETE request MUST include user_id for authorization
- Location deleted only if user_id matches owner
- Error 404 if location not found or unauthorized

**BR-LOC-005: Coordinates Optional**
- Latitude and longitude are optional
- When provided, must be valid GPS coordinates
- Latitude: -90 to +90
- Longitude: -180 to +180

**BR-LOC-006: Location Nickname**
- Nickname is optional user-friendly name
- Examples: "Home", "Office", "Parents' House"
- Max length: 100 characters (implied)

### Event Publishing Rules (BR-EVT-001 to BR-EVT-005)

**BR-EVT-001: Event on Cache Miss**
- `weather.data.fetched` published only on cache miss
- Event NOT published when serving cached data
- Prevents duplicate event flooding

**BR-EVT-002: Alert Event on Non-Empty Results**
- `weather.alert.created` published when alerts array non-empty
- Includes all alerts in payload (max 10)
- Time-critical: immediate retry on failure

**BR-EVT-003: Event Failure Isolation**
- Event publishing failures MUST NOT block API responses
- Errors logged but response returned successfully
- Pattern: try/catch around event_bus.publish_event()

**BR-EVT-004: Event Timestamp Format**
- All events MUST include ISO 8601 UTC timestamp
- Format: `YYYY-MM-DDTHH:MM:SSZ`
- Example: `2025-01-15T10:30:00Z`

**BR-EVT-005: Event Source Attribution**
- Events MUST include `source: weather_service`
- Enables event routing and debugging
- ServiceSource.WEATHER_SERVICE enum value

### Data Consistency Rules (BR-CON-001 to BR-CON-005)

**BR-CON-001: Atomic Location Operations**
- Location insert/update/delete are atomic (PostgreSQL transaction)
- Default flag update and new location insert in single transaction

**BR-CON-002: Cache Consistency**
- Redis and PostgreSQL caches may have different expiration times
- PostgreSQL serves as backup when Redis unavailable
- No strict consistency guarantee between caches

**BR-CON-003: Provider Data Freshness**
- Cached data freshness limited by TTL settings
- Users can identify stale data via `cached: true` flag
- No mechanism for force-refresh (future enhancement)

**BR-CON-004: Idempotent Weather Fetches**
- Multiple requests for same location return same cached data
- Cache key ensures consistent response within TTL window

**BR-CON-005: Graceful Degradation**
- Service MUST remain available even if external provider fails
- Serve stale cached data if available
- Return 503 only if no data available and provider down

---

## Weather Service in the Ecosystem

### Upstream Dependencies
- **OpenWeatherMap API**: Primary weather data provider
- **WeatherAPI**: Secondary/backup weather provider
- **PostgreSQL gRPC Service**: Persistent storage (cache, alerts, locations)
- **Redis**: In-memory cache layer
- **NATS Event Bus**: Event publishing infrastructure
- **Consul**: Service discovery and health checks

### Downstream Consumers
- **Notification Service**: Weather alert notifications to users
- **Device Service**: Weather display updates for IoT devices
- **Calendar Service**: Weather-aware event planning
- **Memory Service**: Contextual weather for conversations
- **Analytics Service**: Weather usage metrics
- **Mobile Apps**: User-facing weather features

### Integration Patterns
- **Synchronous REST**: Weather data and location CRUD via FastAPI
- **Asynchronous Events**: NATS for weather alerts and data events
- **Service Discovery**: Consul for dynamic service location
- **Protocol Buffers**: PostgreSQL gRPC communication
- **HTTP External APIs**: Weather provider integration
- **Health Checks**: `/health` endpoint for monitoring

---

## Success Metrics

### Weather Quality Metrics
- **Cache Hit Rate**: % of requests served from cache (target: >80%)
- **Provider Success Rate**: % of successful API calls (target: >99%)
- **Alert Delivery Rate**: % of alerts successfully published (target: >99.5%)
- **Data Freshness**: Average age of served data (target: <15 min)

### Performance Metrics
- **Current Weather Latency**: Cache hit response time (target: <50ms)
- **Cache Miss Latency**: Full API fetch time (target: <500ms)
- **Forecast Latency**: 7-day forecast response time (target: <200ms)
- **Location Save Latency**: Database insert time (target: <100ms)

### Availability Metrics
- **Service Uptime**: Weather Service availability (target: 99.9%)
- **Provider Connectivity**: External API success rate (target: >99%)
- **Cache Availability**: Redis connection success (target: >99.9%)
- **Database Connectivity**: PostgreSQL success rate (target: >99.99%)

### Business Metrics
- **Daily Weather Requests**: Total weather API calls per day
- **Unique Locations Queried**: Distinct locations requested per day
- **Saved Locations Per User**: Average locations per user
- **Alert Delivery Success**: Users notified of severe weather

---

## Glossary

**Weather Data**: Current meteorological conditions for a location
**Forecast**: Predicted weather conditions for future days
**Weather Alert**: Severe weather warning for a geographic area
**Favorite Location**: User-saved location for weather monitoring
**Cache**: Temporary storage to reduce API calls and latency
**TTL**: Time-to-live, duration before cache expires
**Provider**: External weather API service (OpenWeatherMap, WeatherAPI)
**Metric Units**: Temperature in Celsius, wind in m/s
**Imperial Units**: Temperature in Fahrenheit, wind in mph
**Cache Key**: Unique identifier for cached weather data
**Feels Like**: Apparent temperature adjusted for wind/humidity
**Condition**: Weather state (clear, cloudy, rain, etc.)
**Severity**: Alert danger level (info to extreme)
**Default Location**: Primary location for a user
**Observed At**: Timestamp when weather was measured
**Generated At**: Timestamp when forecast was created

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Weather Service Team
