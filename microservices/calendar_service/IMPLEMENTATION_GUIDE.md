# Calendar Service & Weather Service Implementation Guide

## Status: ⚠️ SKELETON CREATED - NEEDS IMPLEMENTATION

I've created the directory structure and key files for both services. Here's what's been created and what needs to be completed:

---

## Calendar Service (Port 8240)

### ✅ Created Files
- `models.py` - Complete data models
- `__init__.py` - Package init
- `README.md` - Service documentation
- `migrations/001_create_calendar_tables.sql` - Database schema

### 📝 Files Needed (Copy from existing services and adapt)

#### 1. `calendar_repository.py`
**Pattern:** Copy from `task_service/task_repository.py`

```python
"""
Calendar Repository - Data Access Layer
"""
from core.database.supabase_client import get_supabase_client
from .models import CalendarEvent

class CalendarRepository:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def create_event(self, event: CalendarEvent):
        # Insert into calendar_events table
        pass
    
    async def get_event(self, event_id: str):
        # Get event by ID
        pass
    
    async def get_events_by_user(self, user_id: str, start_date, end_date):
        # Query events in date range
        pass
    
    async def update_event(self, event_id: str, updates: dict):
        # Update event
        pass
    
    async def delete_event(self, event_id: str):
        # Delete event
        pass
```

#### 2. `calendar_service.py`
**Pattern:** Copy from `task_service/task_service.py`

```python
"""
Calendar Service - Business Logic
"""
from .calendar_repository import CalendarRepository
from .models import EventCreateRequest, EventUpdateRequest

class CalendarService:
    def __init__(self):
        self.repository = CalendarRepository()
    
    async def create_event(self, request: EventCreateRequest):
        # Validate dates
        # Create event
        # Send to event_service for notifications
        pass
    
    async def get_upcoming_events(self, user_id: str, days: int = 7):
        # Get events in next N days
        pass
    
    async def sync_with_google_calendar(self, user_id: str):
        # Sync with Google Calendar API
        # Use OAuth2 credentials
        pass
```

#### 3. `main.py`
**Pattern:** Copy from `compliance_service/main.py` or `event_service/main.py`

```python
"""
Calendar Service Main Application
"""
from fastapi import FastAPI
from core.config_manager import ConfigManager
from core.consul_registry import ConsulRegistry
from core.logger import setup_service_logger

SERVICE_NAME = "calendar_service"
SERVICE_PORT = 8240

# ... FastAPI setup with all endpoints
# POST /api/v1/calendar/events
# GET /api/v1/calendar/events
# PUT /api/v1/calendar/events/{id}
# DELETE /api/v1/calendar/events/{id}
# GET /api/v1/calendar/upcoming
# POST /api/v1/calendar/sync
```

#### 4. `client.py`
**Pattern:** Copy from `compliance_service/client.py`

```python
"""
Calendar Service Client
"""
import httpx

class CalendarServiceClient:
    def __init__(self, base_url="http://localhost:8240"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def create_event(self, user_id, title, start_time, end_time, **kwargs):
        # POST to /api/v1/calendar/events
        pass
    
    async def get_upcoming_events(self, user_id, days=7):
        # GET /api/v1/calendar/upcoming
        pass
```

#### 5. `tests/calendar_test.sh`
**Pattern:** Copy from `compliance_service/tests/compliance_check.sh`

```bash
#!/bin/bash
BASE_URL="http://localhost:8240"

# Test 1: Health check
curl $BASE_URL/health

# Test 2: Create event
curl -X POST $BASE_URL/api/v1/calendar/events \
  -d '{"user_id":"test","title":"Meeting","start_time":"2025-10-23T10:00:00Z","end_time":"2025-10-23T11:00:00Z"}'

# Test 3: Get upcoming events
curl $BASE_URL/api/v1/calendar/upcoming?user_id=test
```

#### 6. `examples/calendar_example.py`
**Pattern:** Copy from `compliance_service/examples/account_service_example.py`

---

## Weather Service (Port 8241)

### ✅ Created Files
- Directory structure: `weather_service/`

### 📝 All Files Needed

#### 1. `models.py`

```python
"""
Weather Service Models
"""
from pydantic import BaseModel
from datetime import datetime

class WeatherData(BaseModel):
    location: str
    temperature: float
    humidity: int
    conditions: str
    icon: str
    forecast_time: datetime

class WeatherForecast(BaseModel):
    location: str
    days: list[WeatherData]

class LocationRequest(BaseModel):
    user_id: str
    location: str
    latitude: float
    longitude: float
```

#### 2. `weather_repository.py`

```python
"""
Weather Repository - Cache layer
"""
from core.database.supabase_client import get_supabase_client
import redis

class WeatherRepository:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.redis = redis.Redis()  # Cache
    
    async def get_cached_weather(self, location: str):
        # Check Redis cache (TTL 15 min)
        pass
    
    async def cache_weather(self, location: str, data: dict):
        # Cache in Redis with 15min TTL
        pass
    
    async def save_favorite_location(self, user_id: str, location: str):
        # Save to database
        pass
```

#### 3. `weather_service.py`

```python
"""
Weather Service - Business Logic
"""
import httpx

class WeatherService:
    def __init__(self):
        self.repository = WeatherRepository()
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
    
    async def get_current_weather(self, location: str):
        # Check cache
        # If not cached, fetch from OpenWeatherMap API
        # Cache result
        pass
    
    async def get_forecast(self, location: str, days: int = 5):
        # Fetch forecast from API
        pass
```

#### 4. `main.py`

```python
"""
Weather Service Main Application
Port: 8241
"""
# Endpoints:
# GET /api/v1/weather/current?location={location}
# GET /api/v1/weather/forecast?location={location}&days={days}
# POST /api/v1/weather/locations
# GET /api/v1/weather/locations/{user_id}
```

#### 5. `migrations/001_create_weather_tables.sql`

```sql
-- Weather favorite locations
CREATE TABLE weather_locations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    location VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Quick Implementation Steps

### Step 1: Copy Template Files

```bash
# Copy from existing services
cp microservices/task_service/task_repository.py microservices/calendar_service/calendar_repository.py
cp microservices/event_service/main.py microservices/calendar_service/main.py
cp microservices/compliance_service/client.py microservices/calendar_service/client.py

# Do same for weather_service
```

### Step 2: Find & Replace

```bash
# In calendar_service files:
sed -i 's/task/calendar/g' calendar_repository.py
sed -i 's/Task/Calendar/g' calendar_repository.py
sed -i 's/8230/8240/g' main.py  # Change port

# In weather_service files:
sed -i 's/8230/8241/g' main.py  # Change port
```

### Step 3: Adapt Logic

- Update repository methods to match calendar/weather models
- Update service logic for calendar/weather specific features
- Update endpoints in main.py

### Step 4: External API Integration

#### Calendar - Google Calendar API

```python
# Install: pip install google-auth google-auth-oauthlib google-api-python-client
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

async def sync_google_calendar(user_id: str, credentials_json: str):
    creds = Credentials.from_authorized_user_info(json.loads(credentials_json))
    service = build('calendar', 'v3', credentials=creds)
    
    events = service.events().list(calendarId='primary').execute()
    # Sync events to local database
```

#### Weather - OpenWeatherMap API

```python
# Install: pip install httpx
async def fetch_weather(location: str, api_key: str):
    async with httpx.AsyncClient() as client:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}"
        response = await client.get(url)
        return response.json()
```

---

## Integration with Existing Services

### Calendar + Event Service

```python
# In calendar_service.py
from microservices.event_service.client import EventServiceClient

async def create_event_with_notification(self, event):
    # Create calendar event
    calendar_event = await self.repository.create_event(event)
    
    # Send to event_service for tracking
    event_service = EventServiceClient()
    await event_service.create_event({
        "event_type": "calendar_event_created",
        "user_id": event.user_id,
        "data": calendar_event.dict()
    })
```

### Calendar + Task Service

```python
# Calendar events can have associated tasks
from microservices.task_service.client import TaskServiceClient

async def create_event_with_task(self, event, task_data):
    # Create calendar event
    calendar_event = await self.create_event(event)
    
    # Create associated task
    task_service = TaskServiceClient()
    await task_service.create_task({
        **task_data,
        "calendar_event_id": calendar_event.event_id
    })
```

---

## Testing

```bash
# Start Calendar Service
python -m microservices.calendar_service.main

# Start Weather Service
python -m microservices.weather_service.main

# Run tests
cd microservices/calendar_service && ./tests/calendar_test.sh
cd microservices/weather_service && ./tests/weather_test.sh
```

---

## Environment Variables Needed

```bash
# Calendar Service
export CALENDAR_SERVICE_PORT=8240
export GOOGLE_CALENDAR_CLIENT_ID="..."
export GOOGLE_CALENDAR_CLIENT_SECRET="..."

# Weather Service
export WEATHER_SERVICE_PORT=8241
export OPENWEATHER_API_KEY="..."
export REDIS_URL="redis://localhost:6379"
```

---

## Next Steps

1. ✅ Database schema created
2. ✅ Models created
3. ⏳ Copy & adapt repository from task_service
4. ⏳ Copy & adapt service logic
5. ⏳ Copy & adapt main.py from event_service
6. ⏳ Create client.py
7. ⏳ Create test scripts
8. ⏳ Create examples
9. ⏳ Implement external API integrations (Google, OpenWeatherMap)

**Estimated Time:** 2-3 hours to complete both services by adapting existing code.

---

## Quick Command to Complete

I can create a Python script that automatically generates all the files by copying and adapting from existing services. Would you like me to create that?

Or I can continue creating each file manually - let me know your preference!

