# Calendar Service

日历事件管理微服务 - Calendar event management with external calendar sync.

## Features

- 📅 **Event Management** - Create, read, update, delete calendar events
- 🔄 **External Sync** - Sync with Google Calendar, Apple Calendar, Outlook
- 🔁 **Recurring Events** - Support daily, weekly, monthly recurring events
- ⏰ **Reminders** - Event reminder notifications
- 🎨 **Categories & Colors** - Organize events with categories and colors
- 🔍 **Query Events** - Filter events by date range, category
- 👥 **Event Sharing** - Share events between users

## Quick Start

### Start Service

```bash
python -m microservices.calendar_service.main
# Service runs on http://localhost:8240
```

### Run Tests

```bash
./tests/calendar_test.sh
```

## API Endpoints

### Events
- `POST /api/v1/calendar/events` - Create event
- `GET /api/v1/calendar/events` - List events (with filters)
- `GET /api/v1/calendar/events/{id}` - Get event details
- `PUT /api/v1/calendar/events/{id}` - Update event
- `DELETE /api/v1/calendar/events/{id}` - Delete event

### Sync
- `POST /api/v1/calendar/sync` - Sync with external calendars
- `GET /api/v1/calendar/sync/status` - Get sync status

### Query
- `GET /api/v1/calendar/upcoming` - Get upcoming events
- `GET /api/v1/calendar/today` - Get today's events

## Integration Example

```python
from microservices.calendar_service.client import CalendarServiceClient

calendar = CalendarServiceClient("http://localhost:8240")

# Create event
event = await calendar.create_event(
    user_id="user123",
    title="Team Meeting",
    start_time=datetime(2025, 10, 23, 10, 0),
    end_time=datetime(2025, 10, 23, 11, 0),
    category="meeting"
)

# Get upcoming events
upcoming = await calendar.get_upcoming_events(user_id="user123", days=7)
```

## External Calendar Sync

Supports:
- Google Calendar API
- Apple iCloud Calendar
- Microsoft Outlook Calendar

## Port

- Default: `8240`
- Configure: `CALENDAR_SERVICE_PORT=8240`

## See Also

- [Examples](examples/) - Integration examples
- [Tests](tests/) - Test scripts
- [Migrations](migrations/) - Database schema

