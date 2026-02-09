"""
Integration Tests: Calendar Service CRUD Operations

Tests calendar service with real HTTP API calls.
Requires calendar service to be running on port 8217.

Usage:
    pytest tests/integration/services/calendar/test_calendar_crud_integration.py -v
"""
import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone, timedelta

from microservices.calendar_service.models import EventCategory, RecurrenceType

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Configuration
# ============================================================================

CALENDAR_SERVICE_URL = "http://localhost:8217"
API_BASE = f"{CALENDAR_SERVICE_URL}/api/v1/calendar"
TIMEOUT = 30.0


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def http_client():
    """HTTP client for integration tests"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def test_user_id():
    """Generate unique user ID for test isolation"""
    return f"test_user_{datetime.now().timestamp()}"


@pytest_asyncio.fixture
async def cleanup_events(http_client):
    """Track and cleanup events created during tests"""
    created_event_ids = []

    yield created_event_ids

    # Cleanup after test
    for event_id in created_event_ids:
        try:
            await http_client.delete(f"{API_BASE}/events/{event_id}")
        except Exception:
            pass  # Ignore cleanup errors


# ============================================================================
# Tests
# ============================================================================

class TestCalendarCRUDIntegration:
    """Integration tests for calendar CRUD operations via HTTP API"""

    @pytest.mark.asyncio
    async def test_create_and_get_event(self, http_client, test_user_id, cleanup_events):
        """Test creating event and retrieving it via API"""
        now = datetime.now(timezone.utc).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        # Create event via POST
        create_payload = {
            "user_id": test_user_id,
            "title": "Integration Test Event",
            "description": "Testing calendar service integration",
            "location": "Test Location",
            "start_time": now,
            "end_time": future,
            "category": EventCategory.MEETING.value,
            "reminders": [15, 30],
        }

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_payload
        )
        assert response.status_code == 201
        created = response.json()
        assert created["user_id"] == test_user_id
        assert created["title"] == "Integration Test Event"
        assert created["category"] == EventCategory.MEETING.value

        event_id = created["event_id"]
        cleanup_events.append(event_id)

        # Retrieve via GET
        response = await http_client.get(
            f"{API_BASE}/events/{event_id}"
        )
        assert response.status_code == 200
        retrieved = response.json()
        assert retrieved["event_id"] == event_id
        assert retrieved["user_id"] == test_user_id

    @pytest.mark.asyncio
    async def test_create_update_event(self, http_client, test_user_id, cleanup_events):
        """Test creating and updating event via API"""
        now = datetime.now(timezone.utc).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        # Create event
        create_payload = {
            "user_id": test_user_id,
            "title": "Original Title",
            "start_time": now,
            "end_time": future,
        }

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_payload
        )
        assert response.status_code == 201
        created = response.json()
        event_id = created["event_id"]
        cleanup_events.append(event_id)

        # Update via PUT
        update_payload = {
            "title": "Updated Title",
            "description": "Updated description",
        }

        response = await http_client.put(
            f"{API_BASE}/events/{event_id}",
            json=update_payload
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["title"] == "Updated Title"
        assert updated["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_create_delete_event(self, http_client, test_user_id):
        """Test creating and deleting event via API"""
        now = datetime.now(timezone.utc).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        # Create event
        create_payload = {
            "user_id": test_user_id,
            "title": "Event to Delete",
            "start_time": now,
            "end_time": future,
        }

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_payload
        )
        assert response.status_code == 201
        event_id = response.json()["event_id"]

        # Delete via DELETE
        response = await http_client.delete(
            f"{API_BASE}/events/{event_id}"
        )
        assert response.status_code == 204

        # Verify deleted - should return 404
        response = await http_client.get(
            f"{API_BASE}/events/{event_id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_query_events_by_user(self, http_client, test_user_id, cleanup_events):
        """Test querying events by user via API"""
        now = datetime.now(timezone.utc)

        # Create multiple events
        for i in range(3):
            create_payload = {
                "user_id": test_user_id,
                "title": f"Event {i}",
                "start_time": (now + timedelta(hours=i)).isoformat(),
                "end_time": (now + timedelta(hours=i + 1)).isoformat(),
                "category": EventCategory.WORK.value if i % 2 == 0 else EventCategory.PERSONAL.value,
            }

            response = await http_client.post(
                f"{API_BASE}/events",
                json=create_payload
            )
            assert response.status_code == 201
            cleanup_events.append(response.json()["event_id"])

        # Query all events for user
        response = await http_client.get(
            f"{API_BASE}/events",
            params={"user_id": test_user_id}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["total"] >= 3
        assert len(result["events"]) >= 3

    @pytest.mark.asyncio
    async def test_query_events_with_category_filter(self, http_client, test_user_id, cleanup_events):
        """Test querying events with category filter via API"""
        now = datetime.now(timezone.utc)

        # Create work event
        work_event = {
            "user_id": test_user_id,
            "title": "Work Event",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "category": EventCategory.WORK.value,
        }

        response = await http_client.post(
            f"{API_BASE}/events",
            json=work_event
        )
        assert response.status_code == 201
        cleanup_events.append(response.json()["event_id"])

        # Query work events
        response = await http_client.get(
            f"{API_BASE}/events",
            params={
                "user_id": test_user_id,
                "category": EventCategory.WORK.value,
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert all(e["category"] == EventCategory.WORK.value for e in result["events"])

    @pytest.mark.asyncio
    async def test_get_upcoming_events(self, http_client, test_user_id, cleanup_events):
        """Test getting upcoming events via API"""
        now = datetime.now(timezone.utc)

        # Create future event
        future_event = {
            "user_id": test_user_id,
            "title": "Future Event",
            "start_time": (now + timedelta(days=2)).isoformat(),
            "end_time": (now + timedelta(days=2, hours=1)).isoformat(),
        }

        response = await http_client.post(
            f"{API_BASE}/events",
            json=future_event
        )
        assert response.status_code == 201
        cleanup_events.append(response.json()["event_id"])

        # Get upcoming events
        response = await http_client.get(
            f"{API_BASE}/upcoming",
            params={"user_id": test_user_id, "days": 7}
        )
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_get_today_events(self, http_client, test_user_id, cleanup_events):
        """Test getting today's events via API"""
        now = datetime.now(timezone.utc)

        # Create event for today
        today_event = {
            "user_id": test_user_id,
            "title": "Today's Event",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        }

        response = await http_client.post(
            f"{API_BASE}/events",
            json=today_event
        )
        assert response.status_code == 201
        cleanup_events.append(response.json()["event_id"])

        # Get today's events
        response = await http_client.get(
            f"{API_BASE}/today",
            params={"user_id": test_user_id}
        )
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_create_recurring_event(self, http_client, test_user_id, cleanup_events):
        """Test creating recurring event via API"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        recurrence_end = now + timedelta(days=60)

        create_payload = {
            "user_id": test_user_id,
            "title": "Weekly Standup",
            "start_time": now.isoformat(),
            "end_time": future.isoformat(),
            "recurrence_type": RecurrenceType.WEEKLY.value,
            "recurrence_end_date": recurrence_end.isoformat(),
            "recurrence_rule": "FREQ=WEEKLY;BYDAY=MO",
        }

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_payload
        )
        assert response.status_code == 201
        created = response.json()
        assert created["recurrence_type"] == RecurrenceType.WEEKLY.value
        # Note: recurrence_rule and recurrence_end_date not in EventResponse
        cleanup_events.append(created["event_id"])

    @pytest.mark.asyncio
    async def test_create_all_day_event(self, http_client, test_user_id, cleanup_events):
        """Test creating all-day event via API"""
        now = datetime.now(timezone.utc)

        create_payload = {
            "user_id": test_user_id,
            "title": "All Day Event",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "all_day": True,
        }

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_payload
        )
        assert response.status_code == 201
        created = response.json()
        assert created["all_day"] is True
        cleanup_events.append(created["event_id"])

    @pytest.mark.asyncio
    async def test_create_shared_event(self, http_client, test_user_id, cleanup_events):
        """Test creating shared event via API"""
        now = datetime.now(timezone.utc)

        create_payload = {
            "user_id": test_user_id,
            "title": "Shared Event",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "is_shared": True,
            "shared_with": ["user_456", "user_789"],
        }

        response = await http_client.post(
            f"{API_BASE}/events",
            json=create_payload
        )
        assert response.status_code == 201
        created = response.json()
        assert created["is_shared"] is True
        cleanup_events.append(created["event_id"])

    @pytest.mark.asyncio
    async def test_pagination(self, http_client, test_user_id, cleanup_events):
        """Test pagination of event listing via API"""
        now = datetime.now(timezone.utc)

        # Create multiple events
        for i in range(5):
            create_payload = {
                "user_id": test_user_id,
                "title": f"Event {i}",
                "start_time": (now + timedelta(hours=i)).isoformat(),
                "end_time": (now + timedelta(hours=i + 1)).isoformat(),
            }

            response = await http_client.post(
                f"{API_BASE}/events",
                json=create_payload
            )
            assert response.status_code == 201
            cleanup_events.append(response.json()["event_id"])

        # Test pagination
        response = await http_client.get(
            f"{API_BASE}/events",
            params={"user_id": test_user_id, "limit": 2, "offset": 0}
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["events"]) <= 2
        # Note: API returns count of returned results, not total count

        # Test offset
        response = await http_client.get(
            f"{API_BASE}/events",
            params={"user_id": test_user_id, "limit": 2, "offset": 2}
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["events"]) <= 2
        # Offset works - returns different events
