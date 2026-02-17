# Weather Service - Product Requirements Document (PRD)

## Product Overview

**Product Name**: Weather Service
**Version**: 1.0.0
**Status**: Production
**Port**: 8241
**Owner**: Platform Services Team
**Last Updated**: 2025-12-17

### Vision
Establish the most reliable, efficient environmental intelligence layer for the isA_user platform with real-time weather data, intelligent caching, multi-provider resilience, and personalized location management.

### Mission
Provide a production-grade weather service that delivers accurate meteorological data from multiple providers, serves cached responses in milliseconds, and enables users to monitor weather conditions for their important locations.

### Target Users
- **End Users**: Weather information consumers, travelers, planners
- **IoT Devices**: Smart home devices needing weather context
- **Internal Services**: Calendar, Notification, Device, Memory services
- **Mobile Apps**: User-facing weather features and widgets

### Key Differentiators
1. **Multi-Provider Architecture**: OpenWeatherMap, WeatherAPI fallback for reliability
2. **Two-Tier Caching**: Redis + PostgreSQL for sub-50ms cached responses
3. **Intelligent Cache TTL**: Data-type specific expiration (15min current, 30min forecast)
4. **Location Personalization**: Save unlimited favorite locations per user
5. **Event-Driven Alerts**: Real-time severe weather notifications via NATS

---

## Product Goals

### Primary Goals
1. **Sub-50ms Cached Reads**: Weather data from cache in <50ms (p95)
2. **High Cache Hit Rate**: >80% requests served from cache
3. **Multi-Provider Resilience**: 99.9% availability with provider fallback
4. **Alert Delivery**: Weather alerts published within 10 seconds
5. **Location Management**: Support unlimited saved locations per user

### Secondary Goals
1. **API Cost Efficiency**: Minimize external API calls through caching
2. **Multi-Unit Support**: Metric and imperial unit systems
3. **Forecast Flexibility**: 1-16 day forecast range support
4. **Location-Based Alerts**: User-specific weather notifications
5. **Device Integration**: Weather context for IoT automation

---

## Epics and User Stories

### Epic 1: Current Weather Retrieval

**Objective**: Enable real-time weather data access with intelligent caching.

#### E1-US1: Get Current Weather by Location
**As a** Mobile App User
**I want to** see current weather for any location
**So that** I can plan my activities based on weather conditions

**Acceptance Criteria**:
- AC1: GET /api/v1/weather/current accepts location and units parameters
- AC2: Returns temperature, humidity, condition, wind speed, description
- AC3: Supports metric (Celsius, m/s) and imperial (Fahrenheit, mph) units
- AC4: Response time <50ms for cached data
- AC5: Response time <500ms for fresh API calls
- AC6: Returns `cached: true/false` flag in response
- AC7: Location accepts city name format (e.g., "London", "New York")

**API Reference**: `GET /api/v1/weather/current?location=London&units=metric`

**Example Request**:
```bash
curl "http://localhost:8241/api/v1/weather/current?location=London&units=metric"
```

**Example Response**:
```json
{
  "location": "London",
  "temperature": 15.5,
  "feels_like": 14.2,
  "humidity": 72,
  "condition": "cloudy",
  "description": "overcast clouds",
  "icon": "04d",
  "wind_speed": 3.6,
  "observed_at": "2025-12-17T10:30:00Z",
  "cached": false
}
```

#### E1-US2: Weather Data Caching
**As a** System Administrator
**I want to** weather data cached appropriately
**So that** we minimize API costs and improve response times

**Acceptance Criteria**:
- AC1: Current weather cached for 15 minutes (900 seconds)
- AC2: Redis used as primary cache (hot cache)
- AC3: PostgreSQL used as backup cache (warm cache)
- AC4: Cache key format: `weather:current:{location}:{units}`
- AC5: TTL configurable via environment variables
- AC6: Cache miss triggers fresh API call

#### E1-US3: Multi-Provider Fallback
**As a** Service
**I want to** fall back to secondary provider on primary failure
**So that** weather data remains available during provider outages

**Acceptance Criteria**:
- AC1: Primary provider: OpenWeatherMap
- AC2: Secondary provider: WeatherAPI
- AC3: Provider selection via WEATHER_PROVIDER env variable
- AC4: API errors logged with provider name
- AC5: Fallback transparent to client

---

### Epic 2: Weather Forecasting

**Objective**: Provide multi-day weather predictions for planning.

#### E2-US1: Get Multi-Day Forecast
**As a** User Planning Activities
**I want to** see weather forecast for upcoming days
**So that** I can plan outdoor activities in advance

**Acceptance Criteria**:
- AC1: GET /api/v1/weather/forecast accepts location and days parameters
- AC2: Days parameter: 1-16 (default: 5)
- AC3: Returns daily forecasts with high/low/average temperatures
- AC4: Includes condition, description, humidity, wind for each day
- AC5: Response time <200ms for cached data
- AC6: Forecast cached for 30 minutes

**API Reference**: `GET /api/v1/weather/forecast?location=Tokyo&days=7`

**Example Response**:
```json
{
  "location": "Tokyo",
  "forecast": [
    {
      "date": "2025-12-17T00:00:00Z",
      "temp_max": 12.5,
      "temp_min": 6.2,
      "temp_avg": 9.4,
      "condition": "clear",
      "description": "clear sky",
      "icon": "01d",
      "humidity": 45,
      "wind_speed": 2.1,
      "precipitation_chance": null,
      "precipitation_amount": null
    }
  ],
  "generated_at": "2025-12-17T08:00:00Z",
  "cached": true
}
```

#### E2-US2: Daily Temperature Aggregation
**As a** System
**I want to** aggregate 3-hour data into daily forecasts
**So that** users see simplified daily predictions

**Acceptance Criteria**:
- AC1: OpenWeatherMap 3-hour data aggregated to daily
- AC2: Temp Max: highest temperature of day
- AC3: Temp Min: lowest temperature of day
- AC4: Temp Avg: arithmetic mean of day's temperatures
- AC5: Condition: most representative condition of day
- AC6: 8 data points per day (24 hours / 3 hours)

#### E2-US3: Forecast Range Validation
**As a** System
**I want to** validate forecast days parameter
**So that** invalid requests are rejected with clear errors

**Acceptance Criteria**:
- AC1: Days must be between 1 and 16 inclusive
- AC2: Return 400 Bad Request if days < 1 or > 16
- AC3: Free tier limited to 5-day forecast
- AC4: Clear error message in response

---

### Epic 3: Weather Alerts

**Objective**: Deliver severe weather warnings to protect users.

#### E3-US1: Get Weather Alerts for Location
**As a** User in Weather-Affected Area
**I want to** see active weather alerts for my location
**So that** I can take protective action during severe weather

**Acceptance Criteria**:
- AC1: GET /api/v1/weather/alerts accepts location parameter
- AC2: Returns active alerts (end_time >= now)
- AC3: Alerts ordered by severity (extreme first)
- AC4: Includes alert type, severity, headline, description
- AC5: Includes start_time, end_time for alert validity
- AC6: Returns empty array if no active alerts

**API Reference**: `GET /api/v1/weather/alerts?location=Miami`

**Example Response**:
```json
{
  "alerts": [
    {
      "id": 123,
      "location": "Miami",
      "alert_type": "hurricane",
      "severity": "severe",
      "headline": "Hurricane Warning in Effect",
      "description": "A hurricane warning means hurricane conditions are expected...",
      "start_time": "2025-12-17T14:00:00Z",
      "end_time": "2025-12-18T06:00:00Z",
      "source": "NWS"
    }
  ],
  "location": "Miami",
  "checked_at": "2025-12-17T10:30:00Z"
}
```

#### E3-US2: Alert Event Publishing
**As a** Notification Service
**I want to** receive weather alert events
**So that** I can notify users in affected areas

**Acceptance Criteria**:
- AC1: weather.alert.created event published when alerts exist
- AC2: Event includes location, alert count, alert summaries
- AC3: Published to NATS event bus
- AC4: Event publishing failures don't block API response
- AC5: Time-critical: immediate retry on failure

#### E3-US3: Alert Severity Classification
**As a** System
**I want to** classify alerts by severity
**So that** users understand urgency levels

**Acceptance Criteria**:
- AC1: Severity levels: info, warning, severe, extreme
- AC2: Ordering: extreme > severe > warning > info
- AC3: Severity stored as enum in database
- AC4: Clear severity descriptions in API documentation

---

### Epic 4: Favorite Locations Management

**Objective**: Enable users to save and manage weather locations.

#### E4-US1: Save Favorite Location
**As an** Authenticated User
**I want to** save a location for quick weather access
**So that** I don't have to search for the same location repeatedly

**Acceptance Criteria**:
- AC1: POST /api/v1/weather/locations accepts user_id, location, coordinates
- AC2: Coordinates (latitude, longitude) optional
- AC3: Nickname optional (e.g., "Home", "Office")
- AC4: is_default flag to mark primary location
- AC5: Only one default location per user
- AC6: Returns saved location with generated ID
- AC7: Publishes weather.location_saved event

**API Reference**: `POST /api/v1/weather/locations`

**Example Request**:
```json
{
  "user_id": "usr_abc123",
  "location": "New York",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "is_default": true,
  "nickname": "Home"
}
```

**Example Response**:
```json
{
  "id": 42,
  "user_id": "usr_abc123",
  "location": "New York",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "is_default": true,
  "nickname": "Home",
  "created_at": "2025-12-17T10:00:00Z"
}
```

#### E4-US2: Get User's Saved Locations
**As an** Authenticated User
**I want to** see all my saved weather locations
**So that** I can quickly check weather for places I care about

**Acceptance Criteria**:
- AC1: GET /api/v1/weather/locations/{user_id} returns user's locations
- AC2: Results ordered by is_default DESC, created_at DESC
- AC3: Default location appears first
- AC4: Returns location list with total count
- AC5: Response time <100ms

**API Reference**: `GET /api/v1/weather/locations/{user_id}`

**Example Response**:
```json
{
  "locations": [
    {
      "id": 42,
      "user_id": "usr_abc123",
      "location": "New York",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "is_default": true,
      "nickname": "Home",
      "created_at": "2025-12-17T10:00:00Z"
    },
    {
      "id": 43,
      "user_id": "usr_abc123",
      "location": "San Francisco",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "is_default": false,
      "nickname": "Office",
      "created_at": "2025-12-17T10:05:00Z"
    }
  ],
  "total": 2
}
```

#### E4-US3: Delete Saved Location
**As an** Authenticated User
**I want to** remove a saved location
**So that** my location list stays organized

**Acceptance Criteria**:
- AC1: DELETE /api/v1/weather/locations/{location_id} removes location
- AC2: user_id query parameter required for authorization
- AC3: Only owner can delete their locations
- AC4: Returns 204 No Content on success
- AC5: Returns 404 if location not found or unauthorized

**API Reference**: `DELETE /api/v1/weather/locations/{location_id}?user_id={user_id}`

#### E4-US4: Default Location Management
**As an** Authenticated User
**I want to** set one location as my default
**So that** the app shows my primary location's weather first

**Acceptance Criteria**:
- AC1: is_default flag marks primary location
- AC2: Setting new default unsets previous default
- AC3: Only one default per user enforced
- AC4: Atomic operation (transaction)

---

### Epic 5: Event-Driven Integration

**Objective**: Publish events for weather data consumption across platform.

#### E5-US1: Publish Weather Data Fetched Event
**As a** Weather Service
**I want to** publish events when fresh weather data is fetched
**So that** other services can react to weather updates

**Acceptance Criteria**:
- AC1: weather.data.fetched published on cache miss only
- AC2: Event includes location, temperature, condition, provider
- AC3: Published to NATS event bus
- AC4: Event failures logged but don't block response
- AC5: Consumers: Analytics, Device, Memory services

#### E5-US2: Publish Weather Alert Event
**As a** Weather Service
**I want to** publish alert events for severe weather
**So that** users receive timely notifications

**Acceptance Criteria**:
- AC1: weather.alert.created published when alerts array non-empty
- AC2: Event includes alert count, severity, headlines
- AC3: Time-critical: immediate retry on failure
- AC4: Consumers: Notification, Device, Calendar services

#### E5-US3: Publish Location Saved Event
**As a** Weather Service
**I want to** publish events when users save locations
**So that** other services can set up location-based features

**Acceptance Criteria**:
- AC1: weather.location_saved published on location creation
- AC2: Event includes user_id, location, coordinates, is_default
- AC3: Consumers: Notification, Analytics, Device services

---

### Epic 6: Health and Monitoring

**Objective**: Ensure service health visibility and operational stability.

#### E6-US1: Health Check Endpoint
**As a** Operations Team
**I want to** check weather service health
**So that** I can monitor service availability

**Acceptance Criteria**:
- AC1: GET /health returns service status
- AC2: Includes service name and version
- AC3: Response time <20ms
- AC4: Returns 200 OK when healthy

**API Reference**: `GET /health`

**Example Response**:
```json
{
  "status": "healthy",
  "service": "weather_service",
  "version": "1.0.0"
}
```

#### E6-US2: Consul Service Registration
**As a** Service Discovery System
**I want to** weather service registered with Consul
**So that** other services can discover it

**Acceptance Criteria**:
- AC1: Service registered on startup
- AC2: Health check configured (HTTP /health)
- AC3: Service metadata includes capabilities
- AC4: Deregistered on graceful shutdown

---

## API Surface Documentation

### Base URL
- **Development**: `http://localhost:8241`
- **Staging**: `https://staging-weather.isa.ai`
- **Production**: `https://weather.isa.ai`

### API Version
All endpoints prefixed with `/api/v1/`

### Authentication
- **Weather Data**: No authentication required (public endpoints)
- **Location Management**: JWT authentication required
- **Header**: `Authorization: Bearer <token>`

---

### Core Endpoints Summary

| Method | Endpoint | Purpose | Auth | Response Time |
|--------|----------|---------|------|---------------|
| GET | `/health` | Health check | No | <20ms |
| GET | `/api/v1/weather/current` | Get current weather | No | <50ms cached |
| GET | `/api/v1/weather/forecast` | Get forecast | No | <200ms |
| GET | `/api/v1/weather/alerts` | Get weather alerts | No | <100ms |
| POST | `/api/v1/weather/locations` | Save location | Yes | <100ms |
| GET | `/api/v1/weather/locations/{user_id}` | Get user locations | Yes | <100ms |
| DELETE | `/api/v1/weather/locations/{location_id}` | Delete location | Yes | <100ms |

---

### Endpoint: Get Current Weather
- **Method**: `GET`
- **Path**: `/api/v1/weather/current`
- **Description**: Get current weather conditions for a location
- **Authentication**: Not required

**Query Parameters**:
| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| location | string | - | Yes | Location name (e.g., "London", "New York") |
| units | string | metric | No | Unit system: metric or imperial |

**Response** (200 OK):
```json
{
  "location": "string",
  "temperature": "number",
  "feels_like": "number (nullable)",
  "humidity": "integer (0-100)",
  "condition": "string",
  "description": "string (nullable)",
  "icon": "string (nullable)",
  "wind_speed": "number (nullable)",
  "observed_at": "ISO8601 datetime",
  "cached": "boolean"
}
```

**Error Responses**:
| Status | Description |
|--------|-------------|
| 400 | Missing location parameter |
| 404 | Location not found by provider |
| 500 | Provider API error or internal error |

**Example**:
```bash
curl "http://localhost:8241/api/v1/weather/current?location=London&units=metric"
```

---

### Endpoint: Get Weather Forecast
- **Method**: `GET`
- **Path**: `/api/v1/weather/forecast`
- **Description**: Get multi-day weather forecast
- **Authentication**: Not required

**Query Parameters**:
| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| location | string | - | Yes | Location name |
| days | integer | 5 | No | Forecast days (1-16) |
| units | string | metric | No | Unit system |

**Response** (200 OK):
```json
{
  "location": "string",
  "forecast": [
    {
      "date": "ISO8601 datetime",
      "temp_max": "number",
      "temp_min": "number",
      "temp_avg": "number (nullable)",
      "condition": "string",
      "description": "string (nullable)",
      "icon": "string (nullable)",
      "humidity": "integer (nullable)",
      "wind_speed": "number (nullable)",
      "precipitation_chance": "integer (nullable, 0-100)",
      "precipitation_amount": "number (nullable)"
    }
  ],
  "generated_at": "ISO8601 datetime",
  "cached": "boolean"
}
```

**Error Responses**:
| Status | Description |
|--------|-------------|
| 400 | Invalid days parameter (< 1 or > 16) |
| 404 | Location not found |
| 500 | Provider API error |

**Example**:
```bash
curl "http://localhost:8241/api/v1/weather/forecast?location=Tokyo&days=7"
```

---

### Endpoint: Get Weather Alerts
- **Method**: `GET`
- **Path**: `/api/v1/weather/alerts`
- **Description**: Get active weather alerts for a location
- **Authentication**: Not required

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| location | string | Yes | Location name |

**Response** (200 OK):
```json
{
  "alerts": [
    {
      "id": "integer (nullable)",
      "location": "string",
      "alert_type": "string",
      "severity": "enum: info, warning, severe, extreme",
      "headline": "string",
      "description": "string",
      "start_time": "ISO8601 datetime",
      "end_time": "ISO8601 datetime",
      "source": "string",
      "created_at": "ISO8601 datetime (nullable)"
    }
  ],
  "location": "string",
  "checked_at": "ISO8601 datetime"
}
```

**Example**:
```bash
curl "http://localhost:8241/api/v1/weather/alerts?location=Miami"
```

---

### Endpoint: Save Favorite Location
- **Method**: `POST`
- **Path**: `/api/v1/weather/locations`
- **Description**: Save a favorite weather location
- **Authentication**: Required (JWT)

**Request Body**:
```json
{
  "user_id": "string (required)",
  "location": "string (required)",
  "latitude": "number (optional)",
  "longitude": "number (optional)",
  "is_default": "boolean (optional, default: false)",
  "nickname": "string (optional)"
}
```

**Response** (201 Created):
```json
{
  "id": "integer",
  "user_id": "string",
  "location": "string",
  "latitude": "number (nullable)",
  "longitude": "number (nullable)",
  "is_default": "boolean",
  "nickname": "string (nullable)",
  "created_at": "ISO8601 datetime"
}
```

**Error Responses**:
| Status | Description |
|--------|-------------|
| 400 | Invalid request body |
| 401 | Unauthorized |
| 500 | Database error |

**Example**:
```bash
curl -X POST "http://localhost:8241/api/v1/weather/locations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "usr_123", "location": "New York", "is_default": true}'
```

---

### Endpoint: Get User Locations
- **Method**: `GET`
- **Path**: `/api/v1/weather/locations/{user_id}`
- **Description**: Get all saved locations for a user
- **Authentication**: Required (JWT)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | string | User identifier |

**Response** (200 OK):
```json
{
  "locations": [
    {
      "id": "integer",
      "user_id": "string",
      "location": "string",
      "latitude": "number (nullable)",
      "longitude": "number (nullable)",
      "is_default": "boolean",
      "nickname": "string (nullable)",
      "created_at": "ISO8601 datetime"
    }
  ],
  "total": "integer"
}
```

**Example**:
```bash
curl "http://localhost:8241/api/v1/weather/locations/usr_123" \
  -H "Authorization: Bearer $TOKEN"
```

---

### Endpoint: Delete Location
- **Method**: `DELETE`
- **Path**: `/api/v1/weather/locations/{location_id}`
- **Description**: Delete a saved location
- **Authentication**: Required (JWT)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| location_id | integer | Location ID |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User ID for authorization |

**Response** (204 No Content): Empty body

**Error Responses**:
| Status | Description |
|--------|-------------|
| 401 | Unauthorized |
| 404 | Location not found or user mismatch |
| 500 | Database error |

**Example**:
```bash
curl -X DELETE "http://localhost:8241/api/v1/weather/locations/42?user_id=usr_123" \
  -H "Authorization: Bearer $TOKEN"
```

---

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: Location saved
- `204 No Content`: Location deleted
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Missing or invalid token
- `404 Not Found`: Location not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Provider unavailable

---

## Functional Requirements

### Core Functionality

**FR-001: Current Weather Retrieval**
- System SHALL retrieve current weather for any valid location name
- System SHALL support metric and imperial unit systems
- System SHALL return standardized weather data format
- System SHALL indicate cache status in response

**FR-002: Weather Data Caching**
- System SHALL cache current weather for 15 minutes
- System SHALL cache forecast data for 30 minutes
- System SHALL use Redis as primary cache
- System SHALL use PostgreSQL as backup cache

**FR-003: Weather Forecasting**
- System SHALL provide 1-16 day weather forecasts
- System SHALL aggregate 3-hour data into daily forecasts
- System SHALL calculate daily min/max/avg temperatures

**FR-004: Weather Alerts**
- System SHALL query active weather alerts from database
- System SHALL filter expired alerts (end_time < now)
- System SHALL order alerts by severity

**FR-005: Location Management**
- System SHALL allow saving favorite locations
- System SHALL enforce single default location per user
- System SHALL support location deletion with authorization

### Validation

**FR-006: Input Validation**
- System SHALL validate location is non-empty
- System SHALL validate units is metric or imperial
- System SHALL validate days is between 1 and 16
- System SHALL validate coordinates are valid GPS values

**FR-007: Error Handling**
- System SHALL return 400 for invalid parameters
- System SHALL return 404 for unknown locations
- System SHALL return 500 for provider errors
- System SHALL log all errors with context

### Events

**FR-008: Event Publishing**
- System SHALL publish weather.data.fetched on cache miss
- System SHALL publish weather.alert.created when alerts exist
- System SHALL publish weather.location_saved on location creation
- System SHALL ensure event failures don't block responses

### Multi-Provider

**FR-009: Provider Integration**
- System SHALL integrate with OpenWeatherMap API
- System SHALL integrate with WeatherAPI (secondary)
- System SHALL transform provider responses to standard format
- System SHALL configure provider via environment variable

**FR-010: Provider Fallback**
- System SHALL attempt secondary provider on primary failure
- System SHALL log provider errors with details
- System SHALL serve stale cache if all providers fail

---

## Non-Functional Requirements

### Performance

**NFR-001: Response Time**
- Cache hit response time SHALL be <50ms (p95)
- Cache miss response time SHALL be <500ms (p95)
- Forecast response time SHALL be <200ms (p95)
- Location operations SHALL complete in <100ms (p95)

**NFR-002: Throughput**
- System SHALL handle 1000 requests/second
- System SHALL support concurrent cache access
- System SHALL scale horizontally

### Reliability

**NFR-003: Availability**
- System SHALL maintain 99.9% uptime
- System SHALL gracefully handle provider failures
- System SHALL serve stale cache during outages

**NFR-004: Cache Durability**
- Cache data SHALL be persisted in PostgreSQL backup
- Redis restart SHALL not cause data loss
- Cache TTL SHALL be enforced consistently

### Caching

**NFR-005: Cache Efficiency**
- Cache hit rate SHALL exceed 80%
- Cache keys SHALL be unique per location/unit combination
- Cache invalidation SHALL be location-specific

**NFR-006: Cache Storage**
- Redis SHALL store hot cache data
- PostgreSQL SHALL store warm cache backup
- Cache expiration SHALL be enforced at both tiers

### Security

**NFR-007: Authentication**
- Weather data endpoints SHALL be public (no auth)
- Location management endpoints SHALL require JWT
- Authorization SHALL verify user ownership

**NFR-008: API Key Security**
- Provider API keys SHALL be stored in environment variables
- API keys SHALL NOT be exposed in logs or responses
- API keys SHALL be configurable per environment

### Observability

**NFR-009: Logging**
- All requests SHALL be logged with correlation ID
- Provider API calls SHALL be logged with response times
- Cache hits/misses SHALL be logged for metrics
- Errors SHALL include full context

**NFR-010: Health Monitoring**
- Service SHALL expose /health endpoint
- Health check SHALL verify Redis connectivity
- Health check SHALL verify PostgreSQL connectivity

### Integration

**NFR-011: External APIs**
- Provider timeouts SHALL be 30 seconds
- HTTP client SHALL be async (httpx)
- Response transformation SHALL handle provider variations

**NFR-012: Service Discovery**
- Service SHALL register with Consul on startup
- Service SHALL deregister on shutdown
- Service metadata SHALL include capabilities

---

## Dependencies

### External Services

1. **OpenWeatherMap API**: Primary weather data
   - URL: `api.openweathermap.org`
   - Auth: API key via `OPENWEATHER_API_KEY`
   - Rate Limit: 60 calls/minute (free tier)

2. **WeatherAPI**: Secondary weather data
   - URL: `api.weatherapi.com`
   - Auth: API key via `WEATHERAPI_KEY`
   - Rate Limit: 1M calls/month (free tier)

3. **PostgreSQL gRPC Service**: Data storage
   - Host: `isa-postgres-grpc:50061`
   - Schema: `weather`
   - Tables: weather_locations, weather_cache, weather_alerts

4. **Redis**: In-memory cache
   - URL: `redis://localhost:6379`
   - Configurable via `REDIS_URL`

5. **NATS Event Bus**: Event publishing
   - Host: `isa-nats:4222`
   - Subjects: weather.data.fetched, weather.alert.created, weather.location_saved

6. **Consul**: Service discovery
   - Host: `localhost:8500`
   - Service: `weather_service`

### Internal Dependencies
- **core.config_manager**: Configuration management
- **core.logger**: Structured logging
- **core.nats_client**: Event bus client
- **isa_common.consul_client**: Service registration
- **isa_common.AsyncPostgresClient**: Database client

---

## Success Criteria

### Phase 1: Core Weather (Complete)
- [x] Current weather retrieval working
- [x] Multi-provider integration (OpenWeatherMap, WeatherAPI)
- [x] Redis + PostgreSQL caching implemented
- [x] Weather forecast functional
- [x] Health check endpoint

### Phase 2: Alerts & Locations (Complete)
- [x] Weather alerts retrieval working
- [x] Favorite locations CRUD functional
- [x] Event publishing active
- [x] Consul registration working

### Phase 3: Production Hardening (Current)
- [ ] Comprehensive test coverage (Component, Integration, API, Smoke)
- [ ] Performance benchmarks met (<50ms cache hits)
- [ ] Cache hit rate >80%
- [ ] Monitoring and alerting setup

### Phase 4: Enhancement (Future)
- [ ] VisualCrossing integration (historical data)
- [ ] Coordinate-based location lookup
- [ ] Weather widgets API
- [ ] Webhook subscriptions for weather updates
- [ ] Multi-language weather descriptions

---

## Out of Scope

The following are explicitly NOT included in this release:

1. **Historical Weather Data**: VisualCrossing integration pending
2. **Weather Maps**: Map tiles and visualization
3. **Air Quality**: AQI data from providers
4. **Pollen/Allergy**: Health-related weather data
5. **Marine Weather**: Ocean/sea conditions
6. **Aviation Weather**: METAR/TAF data
7. **Custom Alert Rules**: User-defined alert thresholds
8. **Weather Webhooks**: Push notifications to external URLs
9. **Weather Widgets**: Embeddable weather components
10. **Multi-Language**: Localized weather descriptions

---

## Appendix: Request/Response Examples

### 1. Get Current Weather

**Request**:
```bash
curl "http://localhost:8241/api/v1/weather/current?location=London&units=metric"
```

**Response** (Cache Miss - 200 OK):
```json
{
  "location": "London",
  "temperature": 15.5,
  "feels_like": 14.2,
  "humidity": 72,
  "condition": "cloudy",
  "description": "overcast clouds",
  "icon": "04d",
  "wind_speed": 3.6,
  "observed_at": "2025-12-17T10:30:00Z",
  "cached": false
}
```

**Response** (Cache Hit - 200 OK):
```json
{
  "location": "London",
  "temperature": 15.5,
  "feels_like": 14.2,
  "humidity": 72,
  "condition": "cloudy",
  "description": "overcast clouds",
  "icon": "04d",
  "wind_speed": 3.6,
  "observed_at": "2025-12-17T10:30:00Z",
  "cached": true
}
```

### 2. Get Weather Forecast

**Request**:
```bash
curl "http://localhost:8241/api/v1/weather/forecast?location=Tokyo&days=3"
```

**Response** (200 OK):
```json
{
  "location": "Tokyo",
  "forecast": [
    {
      "date": "2025-12-17T00:00:00Z",
      "temp_max": 12.5,
      "temp_min": 6.2,
      "temp_avg": 9.4,
      "condition": "clear",
      "description": "clear sky",
      "icon": "01d",
      "humidity": 45,
      "wind_speed": 2.1,
      "precipitation_chance": null,
      "precipitation_amount": null
    },
    {
      "date": "2025-12-18T00:00:00Z",
      "temp_max": 14.0,
      "temp_min": 7.5,
      "temp_avg": 10.8,
      "condition": "cloudy",
      "description": "scattered clouds",
      "icon": "03d",
      "humidity": 52,
      "wind_speed": 3.2,
      "precipitation_chance": null,
      "precipitation_amount": null
    },
    {
      "date": "2025-12-19T00:00:00Z",
      "temp_max": 11.0,
      "temp_min": 5.0,
      "temp_avg": 8.0,
      "condition": "rain",
      "description": "light rain",
      "icon": "10d",
      "humidity": 78,
      "wind_speed": 4.5,
      "precipitation_chance": null,
      "precipitation_amount": null
    }
  ],
  "generated_at": "2025-12-17T08:00:00Z",
  "cached": false
}
```

### 3. Get Weather Alerts

**Request**:
```bash
curl "http://localhost:8241/api/v1/weather/alerts?location=Miami"
```

**Response** (200 OK - With Alerts):
```json
{
  "alerts": [
    {
      "id": 1,
      "location": "Miami",
      "alert_type": "hurricane",
      "severity": "severe",
      "headline": "Hurricane Warning in Effect",
      "description": "A hurricane warning means hurricane conditions are expected within 36 hours.",
      "start_time": "2025-12-17T14:00:00Z",
      "end_time": "2025-12-18T06:00:00Z",
      "source": "NWS",
      "created_at": "2025-12-17T08:00:00Z"
    }
  ],
  "location": "Miami",
  "checked_at": "2025-12-17T10:30:00Z"
}
```

**Response** (200 OK - No Alerts):
```json
{
  "alerts": [],
  "location": "London",
  "checked_at": "2025-12-17T10:30:00Z"
}
```

### 4. Save Favorite Location

**Request**:
```bash
curl -X POST "http://localhost:8241/api/v1/weather/locations" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_abc123",
    "location": "San Francisco",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "is_default": false,
    "nickname": "Work"
  }'
```

**Response** (201 Created):
```json
{
  "id": 43,
  "user_id": "usr_abc123",
  "location": "San Francisco",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "is_default": false,
  "nickname": "Work",
  "created_at": "2025-12-17T10:35:00Z"
}
```

### 5. Get User Locations

**Request**:
```bash
curl "http://localhost:8241/api/v1/weather/locations/usr_abc123" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response** (200 OK):
```json
{
  "locations": [
    {
      "id": 42,
      "user_id": "usr_abc123",
      "location": "New York",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "is_default": true,
      "nickname": "Home",
      "created_at": "2025-12-17T10:00:00Z"
    },
    {
      "id": 43,
      "user_id": "usr_abc123",
      "location": "San Francisco",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "is_default": false,
      "nickname": "Work",
      "created_at": "2025-12-17T10:35:00Z"
    }
  ],
  "total": 2
}
```

### 6. Delete Location

**Request**:
```bash
curl -X DELETE "http://localhost:8241/api/v1/weather/locations/43?user_id=usr_abc123" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response** (204 No Content): Empty body

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Weather Service Product Team
**Related Documents**:
- Domain Context: docs/domain/weather_service.md
- Design Doc: docs/design/weather_service.md (next)
- Data Contract: tests/contracts/weather/data_contract.py (next)
- Logic Contract: tests/contracts/weather/logic_contract.md (next)
