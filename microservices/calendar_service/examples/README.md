# Calendar Service Examples

本目录包含Calendar Service的集成示例。

## Files

- `calendar_example.py` - 完整的Calendar Service集成示例

## Running Examples

```bash
# Run calendar example
python -m microservices.calendar_service.examples.calendar_example

# Or directly
cd microservices/calendar_service/examples
python calendar_example.py
```

## Usage in Your Service

```python
from microservices.calendar_service.client import CalendarServiceClient

# Initialize client (auto-discovers service URL)
calendar = CalendarServiceClient()

# Create event
event = await calendar.create_event(
    user_id="user123",
    title="Meeting",
    start_time=datetime.now() + timedelta(hours=1),
    end_time=datetime.now() + timedelta(hours=2)
)

# Get upcoming events
upcoming = await calendar.get_upcoming_events(user_id="user123", days=7)
```

## Integration Patterns

### 1. Task Service + Calendar Service
When a task has a due date, create a calendar event as a reminder.

### 2. Notification Service + Calendar Service
Send notifications for upcoming calendar events.

### 3. Event Service + Calendar Service
Publish calendar events to event stream for real-time updates.

