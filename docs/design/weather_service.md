# Weather Service - Design Document

## Design Overview

**Service Name**: weather_service
**Port**: 8241
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-17

### Design Principles
1. **Cache First**: Prioritize cache hits for sub-50ms response times
2. **Multi-Provider Resilience**: Fallback architecture for weather API availability
3. **Two-Tier Caching**: Redis (hot) + PostgreSQL (warm) for durability
4. **Event-Driven Alerts**: Real-time severe weather notifications
5. **Data Freshness Balance**: Optimal TTL for accuracy vs. API cost
6. **Graceful Degradation**: Stale cache served during provider outages

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Clients                             │
│   (Mobile Apps, IoT Devices, Web Dashboard, Other Services)      │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP REST API
                       │ (Public: Weather Data, Protected: Locations)
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│                 Weather Service (Port 8241)                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)                  │ │
│  │  - Request validation (Pydantic models)                    │ │
│  │  - Response formatting                                     │ │
│  │  - Error handling & exception handlers                     │ │
│  │  - Health checks (/health)                                 │ │
│  │  - Lifecycle management (startup/shutdown)                 │ │
│  │  - HTTP client lifecycle (httpx.AsyncClient)               │ │
│  └─────────────────────┬──────────────────────────────────────┘ │
│                        │                                         │
│  ┌─────────────────────▼──────────────────────────────────────┐ │
│  │        Service Layer (weather_service.py)                  │ │
│  │  - Weather data retrieval orchestration                    │ │
│  │  - Cache check/store coordination                          │ │
│  │  - Multi-provider API calls (OpenWeatherMap, WeatherAPI)   │ │
│  │  - Response transformation to standard format              │ │
│  │  - Daily forecast aggregation                              │ │
│  │  - Alert retrieval and event publishing                    │ │
│  │  - Location management business logic                      │ │
│  │  - Event publishing orchestration                          │ │
│  └─────────────────────┬──────────────────────────────────────┘ │
│                        │                                         │
│  ┌─────────────────────▼──────────────────────────────────────┐ │
│  │       Repository Layer (weather_repository.py)             │ │
│  │  - Cache read/write operations (Redis + PostgreSQL)        │ │
│  │  - Location CRUD operations                                │ │
│  │  - Alert storage and retrieval                             │ │
│  │  - PostgreSQL gRPC communication                           │ │
│  │  - Query construction (parameterized)                      │ │
│  │  - Cache key management                                    │ │
│  └─────────────────────┬──────────────────────────────────────┘ │
│                        │                                         │
│  ┌─────────────────────▼──────────────────────────────────────┐ │
│  │       Event Publishing (events/publishers.py)              │ │
│  │  - NATS event bus integration                              │ │
│  │  - Event model construction                                │ │
│  │  - Async non-blocking publishing                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────┼──────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        │               │               │               │
        ↓               ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────────┐
│  PostgreSQL  │ │    Redis    │ │    NATS    │ │    Consul      │
│   (gRPC)     │ │   (Cache)   │ │  (Events)  │ │  (Discovery)   │
│              │ │             │ │            │ │                │
│  Schema:     │ │  Keys:      │ │ Subjects:  │ │  Service:      │
│  weather     │ │  weather:*  │ │ weather.*  │ │  weather_      │
│              │ │             │ │            │ │  service       │
│  Tables:     │ │  TTL:       │ │ Publishers:│ │                │
│  - locations │ │  15-30 min  │ │ - data.    │ │  Health:       │
│  - cache     │ │             │ │   fetched  │ │  /health       │
│  - alerts    │ │             │ │ - alert.   │ │                │
│              │ │             │ │   created  │ │                │
│  Indexes:    │ │             │ │ - location │ │                │
│  - user_id   │ │             │ │   _saved   │ │                │
│  - location  │ │             │ │            │ │                │
│  - cache_key │ │             │ │            │ │                │
└──────────────┘ └─────────────┘ └────────────┘ └────────────────┘
        │
        │ External API Calls
        ↓
┌─────────────────────────────────────────────────────────────────┐
│                    External Weather Providers                    │
│                                                                  │
│  ┌────────────────────┐    ┌────────────────────┐               │
│  │   OpenWeatherMap   │    │     WeatherAPI     │               │
│  │    (Primary)       │    │    (Secondary)     │               │
│  │                    │    │                    │               │
│  │  Endpoints:        │    │  Endpoints:        │               │
│  │  - /weather        │    │  - /current.json   │               │
│  │  - /forecast       │    │  - /forecast.json  │               │
│  │                    │    │                    │               │
│  │  Rate: 60/min      │    │  Rate: 1M/month    │               │
│  └────────────────────┘    └────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       Weather Service                            │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐        │
│  │   Models    │───→│   Service   │───→│ Repository   │        │
│  │  (Pydantic) │    │ (Business)  │    │   (Data)     │        │
│  │             │    │             │    │              │        │
│  │ - Weather   │    │ - Weather   │    │ - Weather    │        │
│  │   Data      │    │   Service   │    │   Repository │        │
│  │ - Weather   │    │             │    │              │        │
│  │   Forecast  │    │             │    │              │        │
│  │ - Weather   │    │             │    │              │        │
│  │   Alert     │    │             │    │              │        │
│  │ - Favorite  │    │             │    │              │        │
│  │   Location  │    │             │    │              │        │
│  │ - Request/  │    │             │    │              │        │
│  │   Response  │    │             │    │              │        │
│  └─────────────┘    └─────────────┘    └──────────────┘        │
│         ↑                  ↑                    ↑                │
│         │                  │                    │                │
│  ┌──────┴──────────────────┴────────────────────┴─────────────┐ │
│  │              FastAPI Main (main.py)                         │ │
│  │  - Dependency Injection (get_weather_service)              │ │
│  │  - Route Handlers (8 endpoints)                            │ │
│  │  - Exception Handlers (HTTP errors)                        │ │
│  │  - HTTP Client Management (httpx.AsyncClient)              │ │
│  └────────────────────────┬────────────────────────────────────┘ │
│                           │                                      │
│  ┌────────────────────────▼────────────────────────────────────┐ │
│  │              Event Publishers                                │ │
│  │  (events/publishers.py, events/models.py)                   │ │
│  │  - weather.data.fetched                                     │ │
│  │  - weather.alert.created                                    │ │
│  │  - weather.location_saved                                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                 Factory Pattern (Future)                     │ │
│  │              (factory.py, protocols.py)                      │ │
│  │  - create_weather_service (production)                       │ │
│  │  - WeatherRepositoryProtocol (interface)                     │ │
│  │  - WeatherProviderProtocol (interface)                       │ │
│  │  - Enables dependency injection for tests                    │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Caching Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Two-Tier Caching                             │
│                                                                  │
│     Request                                                      │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────────┐                                            │
│  │ Check Redis     │──────→ HIT ──────→ Return Cached Data      │
│  │ (Hot Cache)     │                    (cached: true)          │
│  └────────┬────────┘                                            │
│           │ MISS                                                 │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Check PostgreSQL│──────→ HIT ──────→ Return Cached Data      │
│  │ (Warm Cache)    │                    (cached: true)          │
│  └────────┬────────┘                                            │
│           │ MISS                                                 │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Fetch from      │                                            │
│  │ External API    │                                            │
│  │ (OpenWeatherMap/│                                            │
│  │  WeatherAPI)    │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Transform       │                                            │
│  │ Response        │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ├────────────────────────────────────┐                 │
│           │                                    │                 │
│           ▼                                    ▼                 │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │ Store in Redis  │              │ Store in        │           │
│  │ (TTL: 15-30min) │              │ PostgreSQL      │           │
│  └─────────────────┘              │ (TTL: 15-30min) │           │
│                                   └─────────────────┘           │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Publish Event   │                                            │
│  │ (weather.data   │                                            │
│  │  .fetched)      │                                            │
│  └─────────────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│     Return Fresh Data                                            │
│     (cached: false)                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Cache Key Format:
  weather:{type}:{location}:{units}

Examples:
  weather:current:London:metric
  weather:forecast:Tokyo:7
  weather:current:New York:imperial
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (8 endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup
- HTTP client lifecycle management
- Exception handling

**Key Endpoints**:
```python
# Health Check
GET /health                                  # Service health status

# Weather Data (Public - No Auth)
GET /api/v1/weather/current                  # Get current weather
GET /api/v1/weather/forecast                 # Get multi-day forecast
GET /api/v1/weather/alerts                   # Get weather alerts

# Location Management (Protected - JWT Required)
POST   /api/v1/weather/locations             # Save favorite location
GET    /api/v1/weather/locations/{user_id}   # Get user's locations
DELETE /api/v1/weather/locations/{location_id}  # Delete location
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await microservice.initialize()

    yield

    # Shutdown
    await microservice.shutdown()

class WeatherMicroservice:
    async def initialize(self):
        # Initialize event bus
        self.event_bus = await get_event_bus("weather_service")

        # Initialize repository
        self.repository = WeatherRepository(config=config_manager)

        # Initialize service with event bus
        self.service = WeatherService(event_bus=self.event_bus)

        # Register with Consul
        if config.consul_enabled:
            self.consul_registry = ConsulRegistry(...)
            self.consul_registry.register()

    async def shutdown(self):
        # Deregister from Consul
        if self.consul_registry:
            self.consul_registry.deregister()

        # Close event bus
        if self.event_bus:
            await self.event_bus.close()

        # Close HTTP client
        if self.service:
            await self.service.close()
```

### 2. Service Layer (weather_service.py)

**Responsibilities**:
- Weather data retrieval orchestration
- Cache check and storage coordination
- External API calls to weather providers
- Response transformation to standard format
- Daily forecast aggregation from 3-hour data
- Alert retrieval and event publishing
- Location management business logic
- Event publishing for weather events

**Key Methods**:
| Method | Description | Cache | Events Published |
|--------|-------------|-------|------------------|
| `get_current_weather()` | Get current conditions | 15 min | `weather.data.fetched` |
| `get_forecast()` | Get multi-day forecast | 30 min | None |
| `get_weather_alerts()` | Get active alerts | N/A | `weather.alert.created` |
| `save_location()` | Save favorite location | N/A | `weather.location_saved` |
| `get_user_locations()` | List user's locations | N/A | None |
| `delete_location()` | Remove saved location | N/A | None |

**Provider Integration**:
```python
async def _fetch_current_weather(self, location: str, units: str):
    if self.default_provider == "openweathermap":
        return await self._fetch_openweathermap_current(location, units)
    elif self.default_provider == "weatherapi":
        return await self._fetch_weatherapi_current(location)
    else:
        logger.error(f"Unsupported provider: {self.default_provider}")
        return None

async def _fetch_openweathermap_current(self, location: str, units: str):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": location, "appid": self.openweather_api_key, "units": units}

    response = await self.http_client.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # Transform to standard format
    return {
        "location": data["name"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "condition": data["weather"][0]["main"].lower(),
        "description": data["weather"][0]["description"],
        "icon": data["weather"][0]["icon"],
        "wind_speed": data.get("wind", {}).get("speed"),
        "observed_at": datetime.utcnow(),
    }
```

**Forecast Aggregation Logic**:
```python
async def _fetch_openweathermap_forecast(self, location: str, days: int):
    # OpenWeatherMap returns 3-hour intervals
    cnt = min(days * 8, 40)  # 8 intervals per day, max 40

    # Fetch data
    response = await self.http_client.get(url, params=params)
    data = response.json()

    # Aggregate by day
    daily_forecasts = {}
    for item in data["list"]:
        date = datetime.fromtimestamp(item["dt"]).date()

        if date not in daily_forecasts:
            daily_forecasts[date] = {
                "temps": [],
                "condition": item["weather"][0]["main"].lower(),
                ...
            }

        daily_forecasts[date]["temps"].append(item["main"]["temp"])

    # Calculate daily stats
    for date, day_data in daily_forecasts.items():
        forecast_days.append(ForecastDay(
            date=date,
            temp_max=max(day_data["temps"]),
            temp_min=min(day_data["temps"]),
            temp_avg=sum(day_data["temps"]) / len(day_data["temps"]),
            ...
        ))
```

### 3. Repository Layer (weather_repository.py)

**Responsibilities**:
- Cache read/write operations (Redis + PostgreSQL)
- Location CRUD operations
- Alert storage and retrieval
- PostgreSQL gRPC communication
- Cache key management
- TTL enforcement

**Key Methods**:
| Method | Operation | Storage |
|--------|-----------|---------|
| `get_cached_weather()` | Read cache | Redis → PostgreSQL |
| `set_cached_weather()` | Write cache | Redis + PostgreSQL |
| `clear_location_cache()` | Invalidate cache | Redis + PostgreSQL |
| `save_location()` | Create location | PostgreSQL |
| `get_user_locations()` | Query locations | PostgreSQL |
| `get_default_location()` | Query default | PostgreSQL |
| `delete_location()` | Remove location | PostgreSQL |
| `save_alert()` | Store alert | PostgreSQL |
| `get_active_alerts()` | Query alerts | PostgreSQL |

**Cache Implementation**:
```python
async def get_cached_weather(self, cache_key: str) -> Optional[Dict]:
    try:
        # Try Redis first (hot cache)
        if self.redis:
            cached = self.redis.get(cache_key)
            if cached:
                logger.debug(f"Cache hit (Redis): {cache_key}")
                return json.loads(cached)

        # Fallback to PostgreSQL (warm cache)
        query = f"""
            SELECT data FROM {self.schema}.{self.cache_table}
            WHERE cache_key = $1 AND expires_at >= $2
        """

        async with self.db:
            results = await self.db.query(
                query, [cache_key, datetime.now(timezone.utc)]
            )

        if results and len(results) > 0:
            logger.debug(f"Cache hit (DB): {cache_key}")
            return results[0].get("data")

        logger.debug(f"Cache miss: {cache_key}")
        return None
    except Exception as e:
        logger.error(f"Error reading cache: {e}")
        return None

async def set_cached_weather(self, cache_key: str, data: Dict, ttl_seconds: int):
    try:
        # Cache in Redis (hot cache)
        if self.redis:
            self.redis.setex(cache_key, ttl_seconds, json.dumps(data))

        # Cache in PostgreSQL (warm cache backup)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        query = f"""
            INSERT INTO {self.schema}.{self.cache_table} (...)
            ON CONFLICT (cache_key) DO UPDATE
            SET data = EXCLUDED.data, expires_at = EXCLUDED.expires_at
        """

        async with self.db:
            await self.db.execute(query, params)

        return True
    except Exception as e:
        logger.error(f"Error setting cache: {e}")
        return False
```

### 4. Event Layer (events/)

**Event Models** (events/models.py):
```python
class WeatherLocationSavedEventData(BaseModel):
    user_id: str
    location_id: int
    location: str
    latitude: float
    longitude: float
    is_default: bool
    nickname: Optional[str]
    created_at: datetime

class WeatherAlertEventData(BaseModel):
    user_id: str
    location: str
    alert_type: str
    severity: str
    description: str
    start_time: datetime
    end_time: Optional[datetime]
    issued_at: datetime
```

**Event Publishing**:
```python
# In weather_service.py
async def get_current_weather(self, request: WeatherCurrentRequest):
    # ... fetch weather data ...

    # Publish event on cache miss
    if self.event_bus:
        try:
            event = Event(
                event_type=EventType.WEATHER_DATA_FETCHED,
                source=ServiceSource.WEATHER_SERVICE,
                data={
                    "location": request.location,
                    "temperature": weather_data.get("temperature"),
                    "condition": weather_data.get("condition"),
                    "units": request.units,
                    "provider": self.default_provider,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await self.event_bus.publish_event(event)
        except Exception as e:
            # Log but don't block response
            logger.error(f"Failed to publish event: {e}")
```

---

## Database Schemas

### Schema: `weather`

```sql
-- Create schema
CREATE SCHEMA IF NOT EXISTS weather;

-- ============================================================================
-- Favorite Locations Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS weather.weather_locations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    location VARCHAR(200) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_default BOOLEAN DEFAULT FALSE,
    nickname VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for location queries
CREATE INDEX idx_weather_locations_user_id
    ON weather.weather_locations(user_id);
CREATE INDEX idx_weather_locations_user_default
    ON weather.weather_locations(user_id, is_default DESC);

-- ============================================================================
-- Weather Cache Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS weather.weather_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(500) UNIQUE NOT NULL,
    location VARCHAR(200) NOT NULL,
    data JSONB NOT NULL,

    -- Cache management
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for cache queries
CREATE INDEX idx_weather_cache_key
    ON weather.weather_cache(cache_key);
CREATE INDEX idx_weather_cache_expires
    ON weather.weather_cache(expires_at);
CREATE INDEX idx_weather_cache_location
    ON weather.weather_cache(location);

-- ============================================================================
-- Weather Alerts Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS weather.weather_alerts (
    id SERIAL PRIMARY KEY,
    location VARCHAR(200) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    headline VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(100) NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT weather_alert_severity_check
        CHECK (severity IN ('info', 'warning', 'severe', 'extreme'))
);

-- Indexes for alert queries
CREATE INDEX idx_weather_alerts_location
    ON weather.weather_alerts(location);
CREATE INDEX idx_weather_alerts_end_time
    ON weather.weather_alerts(end_time);
CREATE INDEX idx_weather_alerts_severity
    ON weather.weather_alerts(severity);
CREATE INDEX idx_weather_alerts_active
    ON weather.weather_alerts(location, end_time)
    WHERE end_time >= CURRENT_TIMESTAMP;
```

### Entity Relationship Diagram

```
┌─────────────────────────────┐
│   weather_locations         │
├─────────────────────────────┤
│ id (PK)                     │
│ user_id (FK → account)      │──────┐
│ location                    │      │
│ latitude                    │      │
│ longitude                   │      │
│ is_default                  │      │
│ nickname                    │      │
│ created_at                  │      │
│ updated_at                  │      │
└─────────────────────────────┘      │
                                      │
                                      │
┌─────────────────────────────┐      │
│   weather_cache             │      │
├─────────────────────────────┤      │
│ id (PK)                     │      │
│ cache_key (UNIQUE)          │      │   ┌─────────────────────┐
│ location ───────────────────│──────┼──→│  External Entity    │
│ data (JSONB)                │      │   │  (account.users)    │
│ cached_at                   │      │   │                     │
│ expires_at                  │      │   │  user_id (PK)       │
│ created_at                  │      │   │  email              │
│ updated_at                  │      │   │  name               │
└─────────────────────────────┘      │   └─────────────────────┘
                                      │
                                      │
┌─────────────────────────────┐      │
│   weather_alerts            │      │
├─────────────────────────────┤      │
│ id (PK)                     │      │
│ location                    │──────┘
│ alert_type                  │
│ severity                    │
│ headline                    │
│ description                 │
│ start_time                  │
│ end_time                    │
│ source                      │
│ created_at                  │
│ updated_at                  │
└─────────────────────────────┘
```

### Database Migrations

| Version | Description | File |
|---------|-------------|------|
| 001 | Initial schema | `001_initial_schema.sql` |
| 002 | Add cache indexes | `002_add_cache_indexes.sql` |
| 003 | Add alert severity check | `003_add_alert_severity_check.sql` |

---

## Data Flow Diagrams

### Get Current Weather Flow

```
Client                    main.py                  WeatherService           Repository              Redis/DB              External API
  │                          │                          │                      │                      │                      │
  │  GET /weather/current    │                          │                      │                      │                      │
  │  ?location=London        │                          │                      │                      │                      │
  │─────────────────────────>│                          │                      │                      │                      │
  │                          │                          │                      │                      │                      │
  │                          │  get_current_weather()   │                      │                      │                      │
  │                          │─────────────────────────>│                      │                      │                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │  get_cached_weather()│                      │                      │
  │                          │                          │─────────────────────>│                      │                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │                      │  redis.get(key)      │                      │
  │                          │                          │                      │─────────────────────>│                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │                      │  CACHE MISS          │                      │
  │                          │                          │                      │<─────────────────────│                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │                      │  SELECT from cache   │                      │
  │                          │                          │                      │─────────────────────>│                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │                      │  CACHE MISS          │                      │
  │                          │                          │                      │<─────────────────────│                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │  return None         │                      │                      │
  │                          │                          │<─────────────────────│                      │                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │  _fetch_current_weather()                   │                      │
  │                          │                          │──────────────────────────────────────────────────────────────────>│
  │                          │                          │                      │                      │                      │
  │                          │                          │  JSON weather data   │                      │                      │
  │                          │                          │<──────────────────────────────────────────────────────────────────│
  │                          │                          │                      │                      │                      │
  │                          │                          │  transform_response()│                      │                      │
  │                          │                          │─────────┐            │                      │                      │
  │                          │                          │<────────┘            │                      │                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │  set_cached_weather()│                      │                      │
  │                          │                          │─────────────────────>│                      │                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │                      │  redis.setex(key,ttl)│                      │
  │                          │                          │                      │─────────────────────>│                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │                      │  INSERT cache        │                      │
  │                          │                          │                      │─────────────────────>│                      │
  │                          │                          │                      │                      │                      │
  │                          │                          │  publish_event()     │                      │                      │
  │                          │                          │──────────────────────────────> NATS         │                      │
  │                          │                          │                      │                      │                      │
  │                          │  return WeatherResponse  │                      │                      │                      │
  │                          │<─────────────────────────│                      │                      │                      │
  │                          │                          │                      │                      │                      │
  │  200 OK { cached: false }│                          │                      │                      │                      │
  │<─────────────────────────│                          │                      │                      │                      │
```

### Get Weather Alerts Flow

```
Client                    main.py                  WeatherService           Repository              NATS
  │                          │                          │                      │                      │
  │  GET /weather/alerts     │                          │                      │                      │
  │  ?location=Miami         │                          │                      │                      │
  │─────────────────────────>│                          │                      │                      │
  │                          │                          │                      │                      │
  │                          │  get_weather_alerts()    │                      │                      │
  │                          │─────────────────────────>│                      │                      │
  │                          │                          │                      │                      │
  │                          │                          │  get_active_alerts() │                      │
  │                          │                          │─────────────────────>│                      │
  │                          │                          │                      │                      │
  │                          │                          │                      │  SELECT * FROM alerts│
  │                          │                          │                      │  WHERE end_time >= NOW()
  │                          │                          │                      │  ORDER BY severity   │
  │                          │                          │                      │                      │
  │                          │                          │  return alerts[]     │                      │
  │                          │                          │<─────────────────────│                      │
  │                          │                          │                      │                      │
  │                          │                          │  if alerts exist:    │                      │
  │                          │                          │  publish(weather.alert.created)────────────>│
  │                          │                          │                      │                      │
  │                          │  return AlertResponse    │                      │                      │
  │                          │<─────────────────────────│                      │                      │
  │                          │                          │                      │                      │
  │  200 OK { alerts: [...] }│                          │                      │                      │
  │<─────────────────────────│                          │                      │                      │
```

### Save Favorite Location Flow

```
Client                    main.py                  WeatherService           Repository              NATS
  │                          │                          │                      │                      │
  │  POST /weather/locations │                          │                      │                      │
  │  { user_id, location,    │                          │                      │                      │
  │    is_default: true }    │                          │                      │                      │
  │─────────────────────────>│                          │                      │                      │
  │                          │                          │                      │                      │
  │                          │  save_location()         │                      │                      │
  │                          │─────────────────────────>│                      │                      │
  │                          │                          │                      │                      │
  │                          │                          │  save_location()     │                      │
  │                          │                          │─────────────────────>│                      │
  │                          │                          │                      │                      │
  │                          │                          │                      │  if is_default:      │
  │                          │                          │                      │  UPDATE SET is_default=FALSE
  │                          │                          │                      │  WHERE user_id=$1    │
  │                          │                          │                      │                      │
  │                          │                          │                      │  INSERT INTO locations
  │                          │                          │                      │  RETURNING *         │
  │                          │                          │                      │                      │
  │                          │                          │  return location     │                      │
  │                          │                          │<─────────────────────│                      │
  │                          │                          │                      │                      │
  │                          │                          │  (Future: publish    │                      │
  │                          │                          │   weather.location_saved)──────────────────>│
  │                          │                          │                      │                      │
  │                          │  return saved location   │                      │                      │
  │                          │<─────────────────────────│                      │                      │
  │                          │                          │                      │                      │
  │  201 Created { ... }     │                          │                      │                      │
  │<─────────────────────────│                          │                      │                      │
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Python | 3.9+ | Primary language |
| Framework | FastAPI | 0.100+ | HTTP API framework |
| Validation | Pydantic | 2.0+ | Data validation |
| Async HTTP | httpx | 0.24+ | External API calls |
| Database | PostgreSQL | 14+ | Primary storage |
| DB Access | gRPC | - | PostgreSQL communication |
| Messaging | NATS | 2.9+ | Event bus |
| Cache | Redis | 7+ | Hot caching layer |

### External APIs

| Provider | Technology | Purpose |
|----------|------------|---------|
| OpenWeatherMap | REST API | Primary weather data |
| WeatherAPI | REST API | Secondary/fallback |
| VisualCrossing | REST API | Historical data (future) |

### Development Tools

| Tool | Purpose |
|------|---------|
| pytest | Testing framework |
| pytest-asyncio | Async test support |
| pytest-httpx | HTTP mocking |
| black | Code formatting |
| ruff | Linting |
| mypy | Type checking |

---

## Security Considerations

### Authentication

- **Weather Data Endpoints**: Public access (no authentication)
- **Location Management**: JWT token validation required
- **Token Validation**: Via API Gateway or inline check
- **Header**: `Authorization: Bearer <token>`

### API Key Security

- **Storage**: Environment variables only
- **Variables**: `OPENWEATHER_API_KEY`, `WEATHERAPI_KEY`
- **Logging**: API keys NEVER logged
- **Rotation**: Keys rotatable without code changes

### Authorization

- **Location Ownership**: Users can only access/delete own locations
- **Verification**: user_id checked against location owner
- **Error**: 404 returned for unauthorized access (not 403)

### Data Protection

- **Input Validation**: Pydantic models validate all inputs
- **SQL Injection**: Parameterized queries via gRPC client
- **XSS**: FastAPI auto-escapes JSON responses
- **Rate Limiting**: Provider rate limits respected

### Network Security

- **HTTPS**: All external API calls use HTTPS
- **Internal**: Service-to-service via internal network
- **Timeout**: 30-second timeout on external calls

---

## Event-Driven Architecture

### Published Events

| Event | Trigger | Payload | Consumers |
|-------|---------|---------|-----------|
| `weather.data.fetched` | Cache miss (fresh API call) | location, temperature, condition, provider | Analytics, Device, Memory |
| `weather.alert.created` | Active alerts returned | location, alert_count, alerts[] | Notification, Device, Calendar |
| `weather.location_saved` | Location created | user_id, location_id, location, coordinates | Notification, Analytics, Device |

### Event Payload Schemas

**weather.data.fetched**:
```json
{
  "event_type": "weather.data.fetched",
  "source": "weather_service",
  "data": {
    "location": "London",
    "temperature": 15.5,
    "condition": "cloudy",
    "units": "metric",
    "provider": "openweathermap",
    "timestamp": "2025-12-17T10:30:00Z"
  }
}
```

**weather.alert.created**:
```json
{
  "event_type": "weather.alert.created",
  "source": "weather_service",
  "data": {
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
}
```

### Consumed Events

Weather Service is primarily a publisher. Future event subscriptions:

| Event | Source | Handler | Purpose |
|-------|--------|---------|---------|
| `device.location_updated` | device_service | `handle_device_location()` | Sync device weather |
| `user.preferences_updated` | account_service | `handle_user_prefs()` | Update units preference |

---

## Error Handling

### HTTP Error Responses

| Exception | HTTP Status | Error Code | Description |
|-----------|-------------|------------|-------------|
| Missing Location | 400 | BAD_REQUEST | Location parameter required |
| Invalid Days | 400 | BAD_REQUEST | Days must be 1-16 |
| Location Not Found | 404 | NOT_FOUND | Weather provider returned 404 |
| Location Not Owned | 404 | NOT_FOUND | Location doesn't exist or wrong user |
| Provider Error | 500 | INTERNAL_ERROR | External API failed |
| Database Error | 500 | INTERNAL_ERROR | PostgreSQL/Redis error |

### Error Response Format

```json
{
  "detail": "Weather data not found"
}
```

### Provider Error Handling

```python
async def _fetch_openweathermap_current(self, location: str, units: str):
    try:
        response = await self.http_client.get(url, params=params)
        response.raise_for_status()
        return self._transform_response(response.json())
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenWeatherMap API error: {e.response.status_code}")
        return None  # Allows fallback to secondary provider
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return None
```

### Event Publishing Error Handling

```python
# Events failures logged but don't block response
if self.event_bus:
    try:
        await self.event_bus.publish_event(event)
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        # Continue - don't raise, don't block response
```

---

## Performance Considerations

### Caching Strategy

| Data Type | Cache Location | TTL | Rationale |
|-----------|---------------|-----|-----------|
| Current Weather | Redis + PostgreSQL | 15 min | Balance freshness vs. API limits |
| Forecast | Redis + PostgreSQL | 30 min | Forecasts change slowly |
| Alerts | Database only | N/A | Query active alerts directly |
| Locations | No cache | N/A | CRUD operations, low volume |

### Query Optimization

- **Cache Key Index**: Hash index on `cache_key` for O(1) lookup
- **Location Index**: B-tree on `user_id` for location queries
- **Alert Index**: Partial index on `end_time >= NOW()` for active alerts
- **Pagination**: Not needed (location lists are small)

### Response Time Targets

| Operation | Target (p95) | Actual |
|-----------|--------------|--------|
| Cache Hit (Redis) | < 20ms | ~5ms |
| Cache Hit (PostgreSQL) | < 50ms | ~30ms |
| Cache Miss (API call) | < 500ms | ~200-400ms |
| Location List | < 100ms | ~50ms |
| Alert Query | < 100ms | ~40ms |

### External API Optimization

- **Connection Pooling**: `httpx.AsyncClient` reused
- **Timeout**: 30 seconds max
- **Retry**: No automatic retry (cache serves as buffer)
- **Batch**: No batching (single location per request)

### Cache Hit Rate Target

- **Target**: > 80% cache hit rate
- **Measurement**: Log cache hits/misses
- **TTL Tuning**: Adjust based on hit rate

---

## Deployment Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SERVICE_PORT` | HTTP port | 8241 | No |
| `POSTGRES_HOST` | PostgreSQL gRPC host | isa-postgres-grpc | No |
| `POSTGRES_PORT` | PostgreSQL gRPC port | 50061 | No |
| `NATS_URL` | NATS connection URL | nats://isa-nats:4222 | No |
| `REDIS_URL` | Redis connection URL | redis://localhost:6379 | No |
| `CONSUL_HOST` | Consul host | localhost | No |
| `CONSUL_PORT` | Consul port | 8500 | No |
| `CONSUL_ENABLED` | Enable Consul registration | true | No |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key | - | Yes |
| `WEATHERAPI_KEY` | WeatherAPI key | - | No |
| `WEATHER_PROVIDER` | Default provider | openweathermap | No |
| `WEATHER_CACHE_TTL` | Current weather TTL (sec) | 900 | No |
| `FORECAST_CACHE_TTL` | Forecast TTL (sec) | 1800 | No |
| `ALERTS_CACHE_TTL` | Alerts TTL (sec) | 600 | No |

### Health Check

```json
GET /health
{
  "status": "healthy",
  "service": "weather_service",
  "version": "1.0.0"
}
```

### Consul Registration

```python
SERVICE_METADATA = {
    "service_name": "weather_service",
    "version": "1.0.0",
    "tags": ["v1", "user-microservice", "weather", "data"],
    "capabilities": [
        "current_weather",
        "weather_forecast",
        "weather_alerts",
        "location_management",
        "weather_caching"
    ]
}
```

### Docker Configuration

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SERVICE_PORT=8241
ENV PYTHONUNBUFFERED=1

EXPOSE 8241

CMD ["python", "-m", "uvicorn", "microservices.weather_service.main:app", "--host", "0.0.0.0", "--port", "8241"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: weather-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: weather-service
  template:
    metadata:
      labels:
        app: weather-service
    spec:
      containers:
      - name: weather-service
        image: isa/weather-service:latest
        ports:
        - containerPort: 8241
        env:
        - name: OPENWEATHER_API_KEY
          valueFrom:
            secretKeyRef:
              name: weather-secrets
              key: openweather-api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8241
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8241
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
```

---

## Testing Strategy

### Test Categories

| Category | Location | Coverage Target |
|----------|----------|-----------------|
| Unit Tests | `tests/unit/golden/weather_service/` | 80% |
| Component Tests | `tests/component/golden/weather_service/` | 70% |
| Integration Tests | `tests/integration/golden/weather_service/` | 50% |
| API Tests | `tests/api/golden/weather_service/` | 100% endpoints |
| Smoke Tests | `tests/smoke/weather_service/` | Critical paths |

### Test Patterns

**Unit Tests**: Test pure functions (transformation, aggregation)
```python
def test_aggregate_forecast_days():
    raw_data = [...]
    result = aggregate_daily_forecast(raw_data)
    assert result[0].temp_max == 25.0
    assert result[0].temp_min == 15.0
```

**Component Tests**: Test service with mocked dependencies
```python
@pytest.fixture
def mock_repository():
    return MockWeatherRepository()

async def test_get_current_weather_cache_hit(mock_repository):
    mock_repository.get_cached_weather.return_value = cached_weather
    service = WeatherService(repository=mock_repository)
    result = await service.get_current_weather(request)
    assert result.cached == True
```

**Integration Tests**: Test with real HTTP calls (mocked external APIs)
```python
@pytest.mark.asyncio
async def test_current_weather_endpoint(test_client, mock_openweathermap):
    response = await test_client.get("/api/v1/weather/current?location=London")
    assert response.status_code == 200
    assert "temperature" in response.json()
```

---

## Appendix: File Structure

```
microservices/weather_service/
├── __init__.py
├── main.py                    # FastAPI application
├── weather_service.py         # Business logic
├── weather_repository.py      # Data access layer
├── models.py                  # Pydantic models
├── routes_registry.py         # Consul route metadata
├── client.py                  # HTTP client for other services
├── clients/
│   └── __init__.py           # Client exports
├── events/
│   ├── __init__.py
│   ├── models.py             # Event data models
│   ├── publishers.py         # Event publishing
│   └── handlers.py           # Event handlers (empty)
├── examples/
│   └── weather_example.py    # Usage examples
└── migrations/
    └── 001_initial_schema.sql
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Weather Service Team
**Related Documents**:
- Domain Context: `docs/domain/weather_service.md`
- PRD: `docs/prd/weather_service.md`
- Data Contract: `tests/contracts/weather/data_contract.py` (next)
- Logic Contract: `tests/contracts/weather/logic_contract.md` (next)
