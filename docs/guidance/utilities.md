# Utilities

Calendar, weather, and location services.

## Overview

Utility services provide supporting functionality:

| Service | Port | Purpose |
|---------|------|---------|
| calendar_service | 8217 | Events, scheduling, sync |
| weather_service | 8218 | Weather data, forecasts |
| location_service | 8224 | Geolocation, geofencing |

## Calendar Service (8217)

### Create Event

```bash
curl -X POST "http://localhost:8217/api/v1/calendar/events" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Meeting",
    "description": "Weekly sync with the team",
    "start_time": "2024-01-29T10:00:00Z",
    "end_time": "2024-01-29T11:00:00Z",
    "location": "Conference Room A",
    "category": "meeting",
    "attendees": ["user_456", "user_789"],
    "reminders": [
      {"minutes_before": 15, "type": "notification"},
      {"minutes_before": 60, "type": "email"}
    ],
    "recurrence": {
      "type": "weekly",
      "interval": 1,
      "days": ["monday"],
      "end_date": "2024-06-30"
    }
  }'
```

Response:
```json
{
  "event_id": "evt_abc123",
  "title": "Team Meeting",
  "start_time": "2024-01-29T10:00:00Z",
  "end_time": "2024-01-29T11:00:00Z",
  "status": "confirmed",
  "recurrence_id": "rec_xyz789",
  "created_at": "2024-01-28T10:30:00Z"
}
```

### Get Event

```bash
curl "http://localhost:8217/api/v1/calendar/events/evt_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### List Events

```bash
curl "http://localhost:8217/api/v1/calendar/events?from=2024-01-01&to=2024-01-31&category=meeting" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Event

```bash
curl -X PUT "http://localhost:8217/api/v1/calendar/events/evt_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Standup",
    "start_time": "2024-01-29T09:30:00Z",
    "update_series": false
  }'
```

### Delete Event

```bash
curl -X DELETE "http://localhost:8217/api/v1/calendar/events/evt_abc123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Sync with External Calendar

```bash
curl -X POST "http://localhost:8217/api/v1/calendar/sync" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "access_token": "google_oauth_token",
    "sync_direction": "bidirectional",
    "calendars": ["primary", "work"]
  }'
```

### Get Sync Status

```bash
curl "http://localhost:8217/api/v1/calendar/sync/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "provider": "google",
  "last_sync": "2024-01-28T10:00:00Z",
  "status": "synced",
  "events_synced": 150,
  "next_sync": "2024-01-28T10:15:00Z"
}
```

### Event Categories

| Category | Description |
|----------|-------------|
| `meeting` | Meetings, calls |
| `task` | Tasks, deadlines |
| `reminder` | Reminders |
| `personal` | Personal events |
| `holiday` | Holidays |
| `birthday` | Birthdays |

### Recurrence Types

| Type | Description |
|------|-------------|
| `daily` | Every day |
| `weekly` | Weekly on specific days |
| `monthly` | Monthly on date or day |
| `yearly` | Yearly on date |
| `custom` | Custom RRULE pattern |

## Weather Service (8218)

### Get Current Weather

```bash
curl "http://localhost:8218/api/v1/weather/current?lat=37.7749&lon=-122.4194" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "location": {
    "name": "San Francisco",
    "lat": 37.7749,
    "lon": -122.4194,
    "timezone": "America/Los_Angeles"
  },
  "current": {
    "temperature": 15.5,
    "feels_like": 14.2,
    "humidity": 72,
    "pressure": 1015,
    "wind_speed": 12.5,
    "wind_direction": 280,
    "condition": "partly_cloudy",
    "description": "Partly cloudy",
    "icon": "02d",
    "uv_index": 3,
    "visibility": 10000
  },
  "updated_at": "2024-01-28T10:30:00Z"
}
```

### Get Weather Forecast

```bash
curl "http://localhost:8218/api/v1/weather/forecast?lat=37.7749&lon=-122.4194&days=7" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "location": {
    "name": "San Francisco",
    "lat": 37.7749,
    "lon": -122.4194
  },
  "forecast": [
    {
      "date": "2024-01-29",
      "temperature_high": 18,
      "temperature_low": 10,
      "condition": "sunny",
      "precipitation_probability": 10,
      "humidity": 65,
      "wind_speed": 8
    },
    {
      "date": "2024-01-30",
      "temperature_high": 16,
      "temperature_low": 9,
      "condition": "cloudy",
      "precipitation_probability": 40,
      "humidity": 75,
      "wind_speed": 15
    }
  ]
}
```

### Get Weather Alerts

```bash
curl "http://localhost:8218/api/v1/weather/alerts?lat=37.7749&lon=-122.4194" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "alerts": [
    {
      "alert_id": "alert_123",
      "type": "wind_advisory",
      "severity": "moderate",
      "title": "Wind Advisory",
      "description": "Strong winds expected...",
      "start_time": "2024-01-29T06:00:00Z",
      "end_time": "2024-01-29T18:00:00Z"
    }
  ]
}
```

### Save Location

```bash
curl -X POST "http://localhost:8218/api/v1/weather/locations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Home",
    "lat": 37.7749,
    "lon": -122.4194,
    "is_default": true
  }'
```

### List Saved Locations

```bash
curl "http://localhost:8218/api/v1/weather/locations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Weather Conditions

| Condition | Description |
|-----------|-------------|
| `sunny` | Clear sky |
| `partly_cloudy` | Partial clouds |
| `cloudy` | Overcast |
| `rain` | Rain |
| `snow` | Snow |
| `thunderstorm` | Thunderstorm |
| `fog` | Foggy |

### Alert Severity

| Severity | Description |
|----------|-------------|
| `minor` | Advisory |
| `moderate` | Watch |
| `severe` | Warning |
| `extreme` | Emergency |

## Location Service (8224)

### Report Location

```bash
curl -X POST "http://localhost:8224/api/v1/locations/report" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 37.7749,
    "longitude": -122.4194,
    "accuracy": 10,
    "altitude": 50,
    "speed": 0,
    "heading": 180,
    "method": "gps",
    "device_id": "device_123"
  }'
```

### Batch Location Report

```bash
curl -X POST "http://localhost:8224/api/v1/locations/batch" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "locations": [
      {"latitude": 37.7749, "longitude": -122.4194, "timestamp": "2024-01-28T10:00:00Z"},
      {"latitude": 37.7750, "longitude": -122.4195, "timestamp": "2024-01-28T10:01:00Z"}
    ],
    "device_id": "device_123"
  }'
```

### Get Current Location

```bash
curl "http://localhost:8224/api/v1/locations/current" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "latitude": 37.7749,
  "longitude": -122.4194,
  "accuracy": 10,
  "timestamp": "2024-01-28T10:30:00Z",
  "address": "123 Main St, San Francisco, CA 94102"
}
```

### Get Location History

```bash
curl "http://localhost:8224/api/v1/locations/history?from=2024-01-27&to=2024-01-28" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Create Geofence

```bash
curl -X POST "http://localhost:8224/api/v1/geofences" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Home",
    "shape": "circle",
    "center": {
      "latitude": 37.7749,
      "longitude": -122.4194
    },
    "radius": 100,
    "triggers": ["enter", "exit"],
    "actions": [
      {"type": "notification", "message": "Welcome home!"}
    ]
  }'
```

### Create Polygon Geofence

```bash
curl -X POST "http://localhost:8224/api/v1/geofences" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Office Campus",
    "shape": "polygon",
    "coordinates": [
      {"latitude": 37.7749, "longitude": -122.4194},
      {"latitude": 37.7759, "longitude": -122.4194},
      {"latitude": 37.7759, "longitude": -122.4184},
      {"latitude": 37.7749, "longitude": -122.4184}
    ],
    "triggers": ["enter", "exit", "dwell"],
    "dwell_time": 300
  }'
```

### List Geofences

```bash
curl "http://localhost:8224/api/v1/geofences" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Geofence

```bash
curl -X PUT "http://localhost:8224/api/v1/geofences/geo_123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Home - Updated",
    "radius": 150
  }'
```

### Delete Geofence

```bash
curl -X DELETE "http://localhost:8224/api/v1/geofences/geo_123" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Create Place

```bash
curl -X POST "http://localhost:8224/api/v1/places" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Favorite Coffee Shop",
    "category": "food_drink",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "address": "123 Main St, San Francisco",
    "metadata": {
      "hours": "7am-7pm"
    }
  }'
```

### List Places

```bash
curl "http://localhost:8224/api/v1/places?category=food_drink&near_lat=37.7749&near_lon=-122.4194&radius=1000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Start Route Tracking

```bash
curl -X POST "http://localhost:8224/api/v1/routes/start" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Morning Run",
    "activity_type": "running",
    "device_id": "device_123"
  }'
```

### Geofence Triggers

| Trigger | Description |
|---------|-------------|
| `enter` | Device enters geofence |
| `exit` | Device exits geofence |
| `dwell` | Device stays for specified time |

### Place Categories

| Category | Description |
|----------|-------------|
| `home` | Home locations |
| `work` | Work locations |
| `food_drink` | Restaurants, cafes |
| `shopping` | Retail stores |
| `entertainment` | Entertainment venues |
| `travel` | Airports, stations |

### Location Methods

| Method | Description |
|--------|-------------|
| `gps` | GPS satellite |
| `network` | Cell/WiFi triangulation |
| `ip` | IP geolocation |
| `manual` | User-entered |

## Python SDK

```python
from isa_user import CalendarClient, WeatherClient, LocationClient

# Calendar
calendar = CalendarClient("http://localhost:8217")
event = await calendar.create_event(
    token=access_token,
    title="Team Meeting",
    start_time="2024-01-29T10:00:00Z",
    end_time="2024-01-29T11:00:00Z",
    recurrence={"type": "weekly", "days": ["monday"]}
)

events = await calendar.list_events(
    token=access_token,
    from_date="2024-01-01",
    to_date="2024-01-31"
)

# Weather
weather = WeatherClient("http://localhost:8218")
current = await weather.get_current(
    token=access_token,
    lat=37.7749,
    lon=-122.4194
)

forecast = await weather.get_forecast(
    token=access_token,
    lat=37.7749,
    lon=-122.4194,
    days=7
)

# Location
location = LocationClient("http://localhost:8224")
await location.report(
    token=access_token,
    latitude=37.7749,
    longitude=-122.4194
)

geofence = await location.create_geofence(
    token=access_token,
    name="Home",
    center={"lat": 37.7749, "lon": -122.4194},
    radius=100
)

history = await location.get_history(
    token=access_token,
    from_date="2024-01-27",
    to_date="2024-01-28"
)
```

## Next Steps

- [Devices](./devices) - IoT management
- [Operations](./operations) - Tasks & events
- [Security](./security) - Vault & secrets
