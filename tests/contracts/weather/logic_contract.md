# Weather Service Logic Contract

**Business Rules and Specifications for Weather Service Testing**

All tests MUST verify these specifications. This is the SINGLE SOURCE OF TRUTH for weather service behavior.

---

## Table of Contents

1. [Business Rules](#business-rules)
2. [State Machines](#state-machines)
3. [Edge Cases](#edge-cases)
4. [Data Consistency Rules](#data-consistency-rules)
5. [Integration Contracts](#integration-contracts)
6. [Error Handling Contracts](#error-handling-contracts)
7. [Performance SLAs](#performance-slas)
8. [Caching Contracts](#caching-contracts)

---

## Business Rules

### Weather Data Retrieval Rules

### BR-WTH-001: Location Parameter Required
**Given**: Current weather or forecast request
**When**: Request is received
**Then**:
- Location parameter MUST be provided
- Empty string location → **400 Bad Request**
- Whitespace-only location → **400 Bad Request**
- Location must be valid city name

**Validation Rules**:
- `location`: Required, non-empty string
- Must not contain only whitespace
- Maximum length: 200 characters
- No format validation (provider handles lookup)

**Edge Cases**:
- Empty location → **HTTPException(400)**
- Whitespace-only location → **HTTPException(400)**
- Very long location (>200 chars) → **422 Validation Error**
- Unknown city → **404 Not Found** (from provider)

---

### BR-WTH-002: Unit System Validation
**Given**: Weather request with units parameter
**When**: Units value is validated
**Then**:
- Units MUST be "metric" or "imperial"
- Default value: "metric"
- Invalid units → **422 Validation Error**

**Validation Rules**:
- `units`: Optional, default = "metric"
- Valid values: `["metric", "imperial"]`
- Case-sensitive matching

**Temperature Ranges**:
- Metric: Celsius (-100°C to +60°C physically valid)
- Imperial: Fahrenheit (-148°F to +140°F physically valid)

**Edge Cases**:
- units = "Metric" (wrong case) → **422 Validation Error**
- units = "kelvin" → **422 Validation Error**
- units = "" → Uses default "metric"
- units not provided → Uses default "metric"

---

### BR-WTH-003: Cache-First Strategy
**Given**: Current weather request for location
**When**: Request is processed
**Then**:
1. Check Redis cache first (hot cache)
2. If Redis miss, check PostgreSQL cache (warm cache)
3. If both miss, fetch from external provider
4. Cache fresh data in both tiers
5. Return with `cached: true/false` flag

**Cache Key Format**:
- Pattern: `weather:{type}:{location}:{units}`
- Example: `weather:current:London:metric`

**Cache Priority**:
1. Redis (sub-millisecond)
2. PostgreSQL (milliseconds)
3. External API (100-500ms)

---

### BR-WTH-004: Weather Data Freshness
**Given**: Cached weather data
**When**: Cache expiration checked
**Then**:
- Current weather TTL: 15 minutes (900 seconds)
- Forecast TTL: 30 minutes (1800 seconds)
- Expired cache → Fetch fresh data
- Valid cache → Return cached with `cached: true`

**TTL Configuration**:
```
WEATHER_CACHE_TTL = 900      # Current weather
FORECAST_CACHE_TTL = 1800    # Forecast data
ALERTS_CACHE_TTL = 600       # Weather alerts
```

**Freshness Guarantee**:
- Current weather: max 15 minutes old
- Forecast: max 30 minutes old
- `observed_at` field shows actual observation time

---

### BR-WTH-005: Provider Response Transformation
**Given**: Response from external weather provider
**When**: Response is processed
**Then**:
- Transform to standard response format
- Normalize field names
- Convert units if needed (WeatherAPI wind_kph → m/s)
- Set `observed_at` to current timestamp

**Standard Response Fields**:
```python
{
    "location": str,        # Normalized city name
    "temperature": float,   # In requested units
    "feels_like": float,    # Apparent temperature
    "humidity": int,        # 0-100 percentage
    "condition": str,       # Lowercase condition
    "description": str,     # Full description
    "icon": str,           # Weather icon code
    "wind_speed": float,   # m/s or mph
    "observed_at": datetime # UTC timestamp
}
```

---

### BR-WTH-006: Event Publishing on Cache Miss
**Given**: Fresh weather data fetched from provider
**When**: Data is successfully retrieved
**Then**:
- Publish `weather.data.fetched` event
- Event includes location, temperature, condition, provider
- Event published AFTER caching, BEFORE response
- Event failure does NOT block response

**Event Payload**:
```json
{
    "location": "London",
    "temperature": 15.5,
    "condition": "cloudy",
    "units": "metric",
    "provider": "openweathermap",
    "timestamp": "2025-12-17T10:30:00Z"
}
```

---

### Forecast Rules

### BR-FCT-001: Forecast Days Range
**Given**: Weather forecast request
**When**: `days` parameter is validated
**Then**:
- Days MUST be between 1 and 16 inclusive
- Default value: 5 days
- days < 1 → **400 Bad Request**
- days > 16 → **400 Bad Request**

**Validation Rules**:
- `days`: Integer, ge=1, le=16
- Default: 5
- Free tier limit: 5 days (OpenWeatherMap)

**Edge Cases**:
- days = 0 → **400 Bad Request**
- days = -1 → **400 Bad Request**
- days = 17 → **400 Bad Request**
- days = 1 → Single day forecast
- days = 16 → Maximum forecast range

---

### BR-FCT-002: Daily Aggregation from Intervals
**Given**: 3-hour interval data from OpenWeatherMap
**When**: Forecast is processed
**Then**:
- Aggregate intervals into daily forecasts
- Calculate temp_max: highest of day
- Calculate temp_min: lowest of day
- Calculate temp_avg: arithmetic mean
- Select representative condition

**Aggregation Logic**:
```python
for each day:
    temp_max = max(interval_temps)
    temp_min = min(interval_temps)
    temp_avg = sum(interval_temps) / len(interval_temps)
    condition = first_interval_condition  # Or most frequent
```

**Data Points**:
- OpenWeatherMap: 8 intervals per day (3-hour)
- Maximum: 40 intervals (5 days × 8)

---

### BR-FCT-003: Forecast Response Structure
**Given**: Valid forecast request
**When**: Forecast is returned
**Then**:
- Return list of ForecastDay objects
- Days ordered chronologically (today first)
- Each day includes temp range and conditions
- `generated_at` shows when forecast was created

**Response Structure**:
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
            "humidity": 45
        }
    ],
    "generated_at": "2025-12-17T08:00:00Z",
    "cached": false
}
```

---

### Weather Alert Rules

### BR-ALT-001: Alert Severity Levels
**Given**: Weather alert data
**When**: Alert is stored/returned
**Then**:
- Severity MUST be one of: `info`, `warning`, `severe`, `extreme`
- Alerts ordered by severity (extreme first)
- Invalid severity → Rejected

**Severity Ordering**:
```
extreme > severe > warning > info
```

**Severity Definitions**:
- `info`: General weather information
- `warning`: Hazardous conditions possible
- `severe`: Dangerous conditions expected
- `extreme`: Life-threatening conditions

---

### BR-ALT-002: Active Alert Filtering
**Given**: Alert query for location
**When**: Alerts are retrieved
**Then**:
- Only return alerts where `end_time >= NOW()`
- Expired alerts filtered out
- Results ordered by severity DESC
- Empty array if no active alerts

**Query Logic**:
```sql
SELECT * FROM weather_alerts
WHERE location = $1 AND end_time >= NOW()
ORDER BY severity DESC
```

---

### BR-ALT-003: Alert Event Publishing
**Given**: Active alerts exist for location
**When**: Alerts endpoint called
**Then**:
- Publish `weather.alert.created` event
- Only publish if alerts array is non-empty
- Include alert count and summaries
- Event failure does NOT block response

**Event Payload**:
```json
{
    "location": "Miami",
    "alert_count": 2,
    "alerts": [
        {
            "severity": "severe",
            "alert_type": "hurricane",
            "headline": "Hurricane Warning"
        }
    ],
    "timestamp": "2025-12-17T14:00:00Z"
}
```

---

### BR-ALT-004: Alert Time Window Validation
**Given**: Weather alert data
**When**: Alert is stored
**Then**:
- `start_time` MUST be valid datetime
- `end_time` MUST be valid datetime
- `end_time` SHOULD be after `start_time`
- Alert source (authority) MUST be provided

**Required Fields**:
- location, alert_type, severity, headline, description
- start_time, end_time, source

---

### Favorite Location Rules

### BR-LOC-001: User ID Required for Locations
**Given**: Location save/list/delete request
**When**: Request is processed
**Then**:
- `user_id` MUST be provided
- Empty user_id → **400 Bad Request**
- Whitespace-only user_id → **400 Bad Request**
- User ID is authorization key

**Validation Rules**:
- `user_id`: Required, non-empty string
- Max length: 100 characters
- No format validation (auth service defines format)

---

### BR-LOC-002: Single Default Location
**Given**: User saves location with `is_default: true`
**When**: Location is saved
**Then**:
- Unset previous default for user
- Set new location as default
- Only ONE default per user at any time
- Operation is atomic (transaction)

**Implementation**:
```sql
-- First: Unset existing default
UPDATE weather_locations
SET is_default = FALSE, updated_at = NOW()
WHERE user_id = $1 AND is_default = TRUE;

-- Then: Insert new location
INSERT INTO weather_locations (...)
VALUES (..., is_default = TRUE, ...);
```

---

### BR-LOC-003: Location List Ordering
**Given**: Request for user's saved locations
**When**: Locations are retrieved
**Then**:
- Order by `is_default DESC` (default first)
- Then by `created_at DESC` (newest non-default first)
- Return with total count

**Query**:
```sql
SELECT * FROM weather_locations
WHERE user_id = $1
ORDER BY is_default DESC, created_at DESC
```

---

### BR-LOC-004: Location Deletion Authorization
**Given**: Delete location request
**When**: Deletion is processed
**Then**:
- Verify `user_id` matches location owner
- Only owner can delete their locations
- Mismatch → **404 Not Found** (not 403)
- Success → **204 No Content**

**Authorization Check**:
```sql
DELETE FROM weather_locations
WHERE id = $1 AND user_id = $2
```

If 0 rows affected → Location not found or unauthorized

---

### BR-LOC-005: Coordinates Validation
**Given**: Location save request with coordinates
**When**: Coordinates are validated
**Then**:
- Latitude: -90 to +90 (inclusive)
- Longitude: -180 to +180 (inclusive)
- Coordinates are optional
- Invalid coordinates → **422 Validation Error**

**Validation Rules**:
- `latitude`: Optional, ge=-90, le=90
- `longitude`: Optional, ge=-180, le=180
- Both or neither (no partial coordinates)

**Edge Cases**:
- latitude = -91 → **422 Validation Error**
- latitude = 91 → **422 Validation Error**
- longitude = -181 → **422 Validation Error**
- longitude = 181 → **422 Validation Error**
- latitude = -90 (South Pole) → Valid
- latitude = 90 (North Pole) → Valid
- longitude = -180 or 180 (International Date Line) → Valid

---

### BR-LOC-006: Nickname Validation
**Given**: Location save request with nickname
**When**: Nickname is processed
**Then**:
- Nickname is optional
- Max length: 100 characters
- Whitespace stripped
- Empty after strip → Stored as NULL

**Validation Rules**:
- `nickname`: Optional, max_length=100
- Whitespace trimmed
- Empty string → NULL

---

### Provider Integration Rules

### BR-PRV-001: Provider Selection
**Given**: Weather data request
**When**: Provider is selected
**Then**:
- Use provider from `WEATHER_PROVIDER` env var
- Default: "openweathermap"
- Valid providers: openweathermap, weatherapi
- Invalid provider → Log error, return None

**Provider Configuration**:
```
WEATHER_PROVIDER = "openweathermap"  # default
OPENWEATHER_API_KEY = "<key>"
WEATHERAPI_KEY = "<key>"
```

---

### BR-PRV-002: API Key Requirement
**Given**: External API call needed
**When**: Provider API called
**Then**:
- API key MUST be configured
- Missing key → Log error, return None
- Invalid key → Provider returns 401, log error
- API error does NOT crash service

**Key Check**:
```python
if not self.openweather_api_key:
    logger.error("OpenWeatherMap API key not configured")
    return None
```

---

### BR-PRV-003: Provider Timeout
**Given**: External API call
**When**: Call is made
**Then**:
- Timeout: 30 seconds
- Timeout exceeded → Log error, return None
- HTTP error → Log error, return None
- Service continues even if provider fails

**Error Handling**:
```python
try:
    response = await self.http_client.get(url, params=params)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    logger.error(f"API error: {e.response.status_code}")
    return None
except Exception as e:
    logger.error(f"Error fetching weather: {e}")
    return None
```

---

### Event Publishing Rules

### BR-EVT-001: Event on Cache Miss Only
**Given**: Weather data request
**When**: Data is fetched from external API
**Then**:
- Publish `weather.data.fetched` event
- Do NOT publish on cache hit
- Cache hit → No event published
- Prevents duplicate events

**Logic**:
```python
# Only publish when fresh data fetched
if not cached:
    await event_bus.publish_event(...)
```

---

### BR-EVT-002: Event Failure Isolation
**Given**: Event publishing
**When**: Publish fails
**Then**:
- Log error
- Do NOT raise exception
- Do NOT block API response
- Service remains operational

**Implementation**:
```python
if self.event_bus:
    try:
        await self.event_bus.publish_event(event)
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        # Continue - don't block response
```

---

### BR-EVT-003: Event Timestamp Format
**Given**: Event payload
**When**: Event is constructed
**Then**:
- Timestamp MUST be ISO 8601 format
- Timestamp MUST be UTC
- Format: `YYYY-MM-DDTHH:MM:SSZ`
- Example: `2025-12-17T10:30:00Z`

---

### Health Check Rules

### BR-HLT-001: Health Endpoint Available
**Given**: Health check request
**When**: GET /health called
**Then**:
- Return 200 OK with status
- Include service name and version
- No authentication required
- Response time < 20ms

**Response**:
```json
{
    "status": "healthy",
    "service": "weather_service",
    "version": "1.0.0"
}
```

---

### BR-HLT-002: Service Registration
**Given**: Service startup
**When**: Consul enabled
**Then**:
- Register with Consul
- Include capabilities metadata
- Configure HTTP health check
- Deregister on shutdown

---

## State Machines

### 1. Cache Entry Lifecycle State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cache Entry States                            │
│                                                                  │
│    ┌──────────────┐                                             │
│    │   MISSING    │◄───────────────────────────┐                │
│    │  (No entry)  │                            │                │
│    └──────┬───────┘                            │                │
│           │                                     │                │
│           │ fetch_and_cache()                  │ expire()       │
│           ▼                                     │                │
│    ┌──────────────┐                            │                │
│    │    VALID     │────────────────────────────┤                │
│    │ (TTL active) │                            │                │
│    └──────┬───────┘                            │                │
│           │                                     │                │
│           │ TTL elapsed                        │                │
│           ▼                                     │                │
│    ┌──────────────┐                            │                │
│    │   EXPIRED    │────────────────────────────┘                │
│    │ (TTL passed) │        invalidate()                         │
│    └──────────────┘                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**States**:
| State | Description | Behavior |
|-------|-------------|----------|
| MISSING | No cache entry exists | Fetch from provider |
| VALID | Cache entry within TTL | Return cached data |
| EXPIRED | Cache entry past TTL | Treat as miss, refresh |

**Transitions**:
| From | To | Trigger | Action |
|------|-----|---------|--------|
| MISSING | VALID | fetch_and_cache() | Store in Redis + PostgreSQL |
| VALID | EXPIRED | TTL elapsed | Mark stale |
| EXPIRED | MISSING | invalidate() | Delete from caches |
| EXPIRED | VALID | fetch_and_cache() | Refresh with new data |

**Invariants**:
1. Cache key uniquely identifies data (location + type + units)
2. Redis and PostgreSQL caches may have different entries
3. PostgreSQL serves as backup when Redis unavailable
4. TTL checked on every read

---

### 2. Weather Alert Lifecycle State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                  Weather Alert States                            │
│                                                                  │
│    ┌──────────────┐                                             │
│    │   PENDING    │                                             │
│    │ (Future)     │                                             │
│    └──────┬───────┘                                             │
│           │                                                      │
│           │ start_time reached                                  │
│           ▼                                                      │
│    ┌──────────────┐                                             │
│    │    ACTIVE    │─────────────────────────────┐               │
│    │ (In effect)  │                             │               │
│    └──────┬───────┘                             │               │
│           │                                      │               │
│           │ end_time reached                    │ manually      │
│           ▼                                      │ cancel()      │
│    ┌──────────────┐                             │               │
│    │   EXPIRED    │◄────────────────────────────┘               │
│    │ (Past)       │                                             │
│    └──────────────┘                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**States**:
| State | Description | Query Inclusion |
|-------|-------------|-----------------|
| PENDING | Alert issued but not yet effective | Not included |
| ACTIVE | Alert currently in effect | Included |
| EXPIRED | Alert past end_time | Not included |

**State Determination**:
```python
now = datetime.now(timezone.utc)
if alert.start_time > now:
    state = "PENDING"
elif alert.end_time < now:
    state = "EXPIRED"
else:
    state = "ACTIVE"
```

**Query Filter**:
```sql
WHERE end_time >= NOW()  -- Active alerts only
```

---

### 3. Location Default Status State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│              Location Default Status                             │
│                                                                  │
│         User saves location with is_default=true                │
│                        │                                         │
│                        ▼                                         │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │              Transaction Block                           │  │
│    │                                                          │  │
│    │  1. Find current default                                 │  │
│    │     ┌─────────────┐                                      │  │
│    │     │  DEFAULT    │──── unset ───►┌─────────────┐        │  │
│    │     │ (Location A)│               │ NON-DEFAULT │        │  │
│    │     └─────────────┘               │ (Location A)│        │  │
│    │                                   └─────────────┘        │  │
│    │  2. Set new default                                      │  │
│    │     ┌─────────────┐               ┌─────────────┐        │  │
│    │     │ NON-DEFAULT │──── set ────► │   DEFAULT   │        │  │
│    │     │ (Location B)│               │ (Location B)│        │  │
│    │     └─────────────┘               └─────────────┘        │  │
│    │                                                          │  │
│    └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Invariant**: Exactly 0 or 1 default location per user

**Transition Logic**:
```sql
-- Step 1: Unset existing defaults
UPDATE weather_locations
SET is_default = FALSE
WHERE user_id = $1 AND is_default = TRUE;

-- Step 2: Set new default
INSERT INTO weather_locations (..., is_default = TRUE, ...);
```

---

### 4. Provider Request State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│               External API Request States                        │
│                                                                  │
│    ┌──────────────┐                                             │
│    │  INITIATED   │                                             │
│    │              │                                             │
│    └──────┬───────┘                                             │
│           │                                                      │
│           │ send_request()                                      │
│           ▼                                                      │
│    ┌──────────────┐         timeout           ┌──────────────┐ │
│    │   PENDING    │─────────────────────────► │   TIMEOUT    │ │
│    │ (Waiting)    │                           │              │ │
│    └──────┬───────┘                           └──────────────┘ │
│           │                                                      │
│      ┌────┴────┐                                                │
│      │         │                                                 │
│   success    error                                              │
│      │         │                                                 │
│      ▼         ▼                                                 │
│ ┌──────────┐ ┌──────────┐                                       │
│ │ SUCCESS  │ │  FAILED  │                                       │
│ │          │ │          │                                       │
│ └──────────┘ └──────────┘                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**States**:
| State | Description | Next Action |
|-------|-------------|-------------|
| INITIATED | Request created | Send to provider |
| PENDING | Waiting for response | Wait up to 30s |
| SUCCESS | Valid response received | Transform and cache |
| FAILED | HTTP error received | Return None |
| TIMEOUT | 30s exceeded | Return None |

**Timeout Configuration**:
```python
self.http_client = httpx.AsyncClient(timeout=30.0)
```

---

## Edge Cases

### Input Validation Edge Cases

**EC-001: Empty Location String**
- **Input**: location = ""
- **Expected**: 400 Bad Request / ValidationError
- **Implementation**: Pydantic min_length=1

**EC-002: Whitespace-Only Location**
- **Input**: location = "   "
- **Expected**: 400 Bad Request after strip
- **Implementation**: Custom validator with strip()

**EC-003: Location with Special Characters**
- **Input**: location = "St. John's, N.L."
- **Expected**: Accepted (valid city name)
- **Note**: Provider handles resolution

**EC-004: Unicode Location Names**
- **Input**: location = "東京" (Tokyo in Japanese)
- **Expected**: Accepted (valid UTF-8)
- **Note**: Provider should handle localized names

**EC-005: Maximum Length Location**
- **Input**: location = "x" * 200
- **Expected**: Accepted (exactly at max)
- **Input**: location = "x" * 201
- **Expected**: 422 Validation Error

---

### Coordinate Edge Cases

**EC-006: Latitude at Boundaries**
- **Input**: latitude = -90 (South Pole)
- **Expected**: Accepted
- **Input**: latitude = 90 (North Pole)
- **Expected**: Accepted
- **Input**: latitude = -90.0001
- **Expected**: 422 Validation Error

**EC-007: Longitude at Boundaries**
- **Input**: longitude = -180 (International Date Line)
- **Expected**: Accepted
- **Input**: longitude = 180 (International Date Line)
- **Expected**: Accepted
- **Input**: longitude = 180.0001
- **Expected**: 422 Validation Error

**EC-008: Partial Coordinates**
- **Input**: latitude = 40.7, longitude = None
- **Expected**: Accepted (coordinates optional)
- **Note**: Service accepts partial, provider may require both

---

### Forecast Edge Cases

**EC-009: Minimum Forecast Days**
- **Input**: days = 1
- **Expected**: Single day forecast returned
- **Note**: Valid minimum

**EC-010: Maximum Forecast Days**
- **Input**: days = 16
- **Expected**: 16-day forecast returned
- **Note**: Valid maximum

**EC-011: Zero Forecast Days**
- **Input**: days = 0
- **Expected**: 400 Bad Request
- **Implementation**: Pydantic ge=1

**EC-012: Negative Forecast Days**
- **Input**: days = -1
- **Expected**: 400 Bad Request
- **Implementation**: Pydantic ge=1

---

### Cache Edge Cases

**EC-013: Redis Unavailable**
- **Condition**: Redis connection fails
- **Expected**: Fall back to PostgreSQL cache
- **Behavior**: Service continues, performance degrades

**EC-014: Both Caches Miss**
- **Condition**: Redis miss + PostgreSQL miss
- **Expected**: Fetch from external provider
- **Behavior**: Cache fresh data on success

**EC-015: Provider Unavailable with Stale Cache**
- **Condition**: Provider down, expired cache exists
- **Expected**: Serve stale cache (future enhancement)
- **Current**: Return None, 500 error

---

### Concurrency Edge Cases

**EC-016: Concurrent Default Location Changes**
- **Condition**: Two requests set default simultaneously
- **Expected**: Last write wins (database constraint)
- **Result**: Only one default location

**EC-017: Concurrent Cache Writes**
- **Condition**: Two requests cache same location
- **Expected**: Both succeed (idempotent)
- **Result**: Latest data cached

---

## Data Consistency Rules

### DC-001: Location Normalization
- Location stored as returned by provider
- No client-side normalization
- Provider resolves "NYC" → "New York"
- Cache key uses original input

### DC-002: Timestamp Consistency
- All timestamps stored in UTC
- Format: ISO 8601 with timezone
- `created_at`: Set once at creation, immutable
- `updated_at`: Updated on every modification
- `observed_at`: When weather was observed
- `generated_at`: When forecast was generated

### DC-003: Temperature Precision
- Temperatures stored as float with 1 decimal
- Example: 15.5°C, not 15.523°C
- Rounded in transformation layer

### DC-004: Cache Key Consistency
- Format: `weather:{type}:{location}:{units}`
- Location: As provided (case-sensitive)
- Units: lowercase (metric/imperial)
- Type: current, forecast

### DC-005: Humidity Range
- Always integer 0-100
- Validated in Pydantic model
- Never null (required field)

### DC-006: Soft Delete Not Used
- Locations are hard deleted
- Cache entries expire, not deleted
- Alerts remain for historical queries (future)

---

## Integration Contracts

### External Weather Provider Integration

#### OpenWeatherMap Current Weather

**Endpoint**: `https://api.openweathermap.org/data/2.5/weather`

**Request**:
```http
GET /data/2.5/weather?q={location}&appid={key}&units={units}
```

**Success Response** (200):
```json
{
    "name": "London",
    "main": {
        "temp": 15.5,
        "feels_like": 14.2,
        "humidity": 72
    },
    "weather": [
        {
            "main": "Clouds",
            "description": "overcast clouds",
            "icon": "04d"
        }
    ],
    "wind": {
        "speed": 3.6
    }
}
```

**Error Response** (404):
```json
{
    "cod": "404",
    "message": "city not found"
}
```

**Transformation**:
```python
{
    "location": data["name"],
    "temperature": data["main"]["temp"],
    "feels_like": data["main"]["feels_like"],
    "humidity": data["main"]["humidity"],
    "condition": data["weather"][0]["main"].lower(),
    "description": data["weather"][0]["description"],
    "icon": data["weather"][0]["icon"],
    "wind_speed": data.get("wind", {}).get("speed"),
    "observed_at": datetime.utcnow()
}
```

---

#### OpenWeatherMap Forecast

**Endpoint**: `https://api.openweathermap.org/data/2.5/forecast`

**Request**:
```http
GET /data/2.5/forecast?q={location}&appid={key}&units=metric&cnt={cnt}
```

**Parameters**:
- `cnt`: Number of 3-hour intervals (max 40)
- Formula: `cnt = min(days * 8, 40)`

**Success Response** (200):
```json
{
    "city": {"name": "Tokyo"},
    "list": [
        {
            "dt": 1734444000,
            "main": {"temp": 12.5},
            "weather": [{"main": "Clear"}]
        }
    ]
}
```

---

#### WeatherAPI Current Weather

**Endpoint**: `https://api.weatherapi.com/v1/current.json`

**Request**:
```http
GET /v1/current.json?key={key}&q={location}
```

**Success Response** (200):
```json
{
    "location": {"name": "London"},
    "current": {
        "temp_c": 15.5,
        "feelslike_c": 14.2,
        "humidity": 72,
        "wind_kph": 12.96,
        "condition": {
            "text": "Cloudy",
            "icon": "//cdn.weatherapi.com/..."
        }
    }
}
```

**Unit Conversion**:
```python
"wind_speed": data["current"]["wind_kph"] / 3.6  # kph → m/s
```

---

### NATS Event Publishing Contract

**Subject Pattern**: `weather.{event_type}`

**weather.data.fetched**:
```json
{
    "event_type": "weather.data.fetched",
    "source": "weather_service",
    "data": {
        "location": "string",
        "temperature": "number",
        "condition": "string",
        "units": "string",
        "provider": "string",
        "timestamp": "ISO8601"
    }
}
```

**weather.alert.created**:
```json
{
    "event_type": "weather.alert.created",
    "source": "weather_service",
    "data": {
        "location": "string",
        "alert_count": "integer",
        "alerts": [
            {
                "severity": "string",
                "alert_type": "string",
                "headline": "string"
            }
        ],
        "timestamp": "ISO8601"
    }
}
```

**Guarantees**:
- At-least-once delivery
- Failure does not block API response
- Events include timestamp for ordering

---

### PostgreSQL gRPC Integration

**Service**: `isa-postgres-grpc:50061`
**Schema**: `weather`

**Tables**:
- `weather_locations`: User saved locations
- `weather_cache`: Weather data cache
- `weather_alerts`: Weather alerts storage

**Connection Pattern**:
```python
async with self.db:
    results = await self.db.query(query, params, schema=self.schema)
```

---

## Error Handling Contracts

### HTTP Status Code Mapping

| Scenario | HTTP Status | Response Body |
|----------|-------------|---------------|
| Missing location parameter | 400 | `{"detail": "Location parameter required"}` |
| Invalid days parameter | 400 | `{"detail": "Days must be 1-16"}` |
| Location not found | 404 | `{"detail": "Weather data not found"}` |
| Location not owned | 404 | `{"detail": "Location not found"}` |
| Validation error | 422 | Pydantic validation detail |
| Provider error | 500 | `{"detail": "Internal server error"}` |
| Service unavailable | 503 | `{"detail": "Service unavailable"}` |

### Error Response Format

**Standard Error**:
```json
{
    "detail": "Error message here"
}
```

**Validation Error** (422):
```json
{
    "detail": [
        {
            "loc": ["query", "days"],
            "msg": "ensure this value is greater than or equal to 1",
            "type": "value_error.number.not_ge"
        }
    ]
}
```

### Error Logging Pattern

```python
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    logger.error(f"Error getting weather: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Performance SLAs

### Response Time Targets

| Operation | Target (p95) | Target (p99) |
|-----------|--------------|--------------|
| Cache hit (Redis) | < 20ms | < 50ms |
| Cache hit (PostgreSQL) | < 50ms | < 100ms |
| Cache miss (API call) | < 500ms | < 1000ms |
| Location list | < 100ms | < 200ms |
| Alert query | < 100ms | < 200ms |
| Health check | < 20ms | < 50ms |

### Throughput Targets

| Metric | Target |
|--------|--------|
| Requests/second | 1000 |
| Concurrent connections | 500 |
| Cache hit rate | > 80% |

### Availability Targets

| Metric | Target |
|--------|--------|
| Service uptime | 99.9% |
| Redis availability | 99.9% |
| PostgreSQL availability | 99.99% |

---

## Caching Contracts

### Cache Key Specification

**Current Weather**:
- Key: `weather:current:{location}:{units}`
- TTL: 900 seconds (15 minutes)
- Example: `weather:current:London:metric`

**Forecast**:
- Key: `weather:forecast:{location}:{days}`
- TTL: 1800 seconds (30 minutes)
- Example: `weather:forecast:Tokyo:7`

### Cache Read Contract

```python
# Priority order:
1. Redis.get(key)        # Hot cache
2. PostgreSQL.query(key) # Warm cache
3. Provider.fetch()      # Cold fetch

# Return value includes:
{
    "data": {...},
    "cached": true|false
}
```

### Cache Write Contract

```python
# Write to both tiers:
1. Redis.setex(key, ttl, data)     # Hot cache
2. PostgreSQL.upsert(key, data)    # Warm cache

# PostgreSQL upsert:
INSERT INTO weather_cache (cache_key, data, expires_at)
VALUES ($1, $2, $3)
ON CONFLICT (cache_key) DO UPDATE
SET data = EXCLUDED.data, expires_at = EXCLUDED.expires_at
```

### Cache Invalidation Contract

```python
# Clear all cache for location:
1. Redis.delete(f"weather:*:{location}:*")
2. PostgreSQL.delete(f"WHERE cache_key LIKE %{location}%")
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Weather Service Team
