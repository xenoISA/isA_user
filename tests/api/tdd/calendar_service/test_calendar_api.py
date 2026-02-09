"""
API Tests: Calendar Service

Tests calendar service REST API endpoints.
Uses FastAPI TestClient for API testing.
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from microservices.calendar_service.main import app
from microservices.calendar_service.models import EventCategory


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return f"api_test_user_{datetime.now().timestamp()}"


class TestCalendarAPIHealth:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "calendar_service"


class TestCalendarAPICreate:
    """Test event creation API"""

    def test_create_event_success(self, client, test_user_id):
        """Test successful event creation via API"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)

        payload = {
            "user_id": test_user_id,
            "title": "API Test Event",
            "description": "Testing API endpoint",
            "location": "Conference Room",
            "start_time": now.isoformat(),
            "end_time": future.isoformat(),
            "category": "meeting",
            "reminders": [15, 30],
        }

        response = client.post("/api/v1/calendar/events", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["event_id"] is not None
        assert data["user_id"] == test_user_id
        assert data["title"] == "API Test Event"
        assert data["category"] == "meeting"

    def test_create_event_invalid_dates(self, client, test_user_id):
        """Test creating event with invalid dates returns 400"""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        payload = {
            "user_id": test_user_id,
            "title": "Invalid Event",
            "start_time": now.isoformat(),
            "end_time": past.isoformat(),
        }

        response = client.post("/api/v1/calendar/events", json=payload)
        assert response.status_code == 400

    def test_create_event_missing_required_fields(self, client):
        """Test creating event without required fields returns 422"""
        payload = {
            "title": "Incomplete Event",
        }

        response = client.post("/api/v1/calendar/events", json=payload)
        assert response.status_code == 422


class TestCalendarAPIRead:
    """Test event retrieval API"""

    def test_get_event_by_id(self, client, test_user_id):
        """Test getting event by ID"""
        # First create an event
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        create_payload = {
            "user_id": test_user_id,
            "title": "Event to Retrieve",
            "start_time": now.isoformat(),
            "end_time": future.isoformat(),
        }

        create_response = client.post("/api/v1/calendar/events", json=create_payload)
        assert create_response.status_code == 201
        event_id = create_response.json()["event_id"]

        # Get the event
        response = client.get(f"/api/v1/calendar/events/{event_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["event_id"] == event_id
        assert data["title"] == "Event to Retrieve"

    def test_get_event_not_found(self, client):
        """Test getting non-existent event returns 404"""
        response = client.get("/api/v1/calendar/events/evt_nonexistent")
        assert response.status_code == 404

    def test_list_events_by_user(self, client, test_user_id):
        """Test listing events for a user"""
        # Create some events
        now = datetime.now(timezone.utc)
        for i in range(3):
            payload = {
                "user_id": test_user_id,
                "title": f"List Event {i}",
                "start_time": (now + timedelta(hours=i)).isoformat(),
                "end_time": (now + timedelta(hours=i + 1)).isoformat(),
            }
            client.post("/api/v1/calendar/events", json=payload)

        # List events
        response = client.get(
            f"/api/v1/calendar/events?user_id={test_user_id}&limit=10"
        )
        assert response.status_code == 200

        data = response.json()
        assert "events" in data
        assert "total" in data
        assert data["total"] >= 3

    def test_list_events_with_category_filter(self, client, test_user_id):
        """Test listing events with category filter"""
        now = datetime.now(timezone.utc)

        # Create work event
        work_payload = {
            "user_id": test_user_id,
            "title": "Work Event",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "category": "work",
        }
        client.post("/api/v1/calendar/events", json=work_payload)

        # Query work events
        response = client.get(
            f"/api/v1/calendar/events?user_id={test_user_id}&category=work"
        )
        assert response.status_code == 200

        data = response.json()
        assert all(e["category"] == "work" for e in data["events"])

    def test_get_upcoming_events(self, client, test_user_id):
        """Test getting upcoming events"""
        now = datetime.now(timezone.utc)

        # Create future event
        payload = {
            "user_id": test_user_id,
            "title": "Upcoming Event",
            "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": (now + timedelta(days=1, hours=1)).isoformat(),
        }
        client.post("/api/v1/calendar/events", json=payload)

        # Get upcoming events
        response = client.get(f"/api/v1/calendar/upcoming?user_id={test_user_id}&days=7")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_get_today_events(self, client, test_user_id):
        """Test getting today's events"""
        now = datetime.now(timezone.utc)

        # Create today's event
        payload = {
            "user_id": test_user_id,
            "title": "Today Event",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        }
        client.post("/api/v1/calendar/events", json=payload)

        # Get today's events
        response = client.get(f"/api/v1/calendar/today?user_id={test_user_id}")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)


class TestCalendarAPIUpdate:
    """Test event update API"""

    def test_update_event_success(self, client, test_user_id):
        """Test successful event update"""
        # Create event
        now = datetime.now(timezone.utc)
        create_payload = {
            "user_id": test_user_id,
            "title": "Original Title",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        }

        create_response = client.post("/api/v1/calendar/events", json=create_payload)
        event_id = create_response.json()["event_id"]

        # Update event
        update_payload = {
            "title": "Updated Title",
            "description": "Added description",
        }

        response = client.put(
            f"/api/v1/calendar/events/{event_id}",
            json=update_payload,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Added description"

    def test_update_event_not_found(self, client):
        """Test updating non-existent event returns 404"""
        update_payload = {"title": "Updated"}

        response = client.put(
            "/api/v1/calendar/events/evt_nonexistent",
            json=update_payload,
        )
        assert response.status_code == 404

    def test_update_event_invalid_dates(self, client, test_user_id):
        """Test updating event with invalid dates returns 400"""
        # Create event
        now = datetime.now(timezone.utc)
        create_payload = {
            "user_id": test_user_id,
            "title": "Event",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        }

        create_response = client.post("/api/v1/calendar/events", json=create_payload)
        event_id = create_response.json()["event_id"]

        # Try to update with invalid dates
        update_payload = {
            "start_time": now.isoformat(),
            "end_time": (now - timedelta(hours=1)).isoformat(),
        }

        response = client.put(
            f"/api/v1/calendar/events/{event_id}",
            json=update_payload,
        )
        assert response.status_code == 400


class TestCalendarAPIDelete:
    """Test event deletion API"""

    def test_delete_event_success(self, client, test_user_id):
        """Test successful event deletion"""
        # Create event
        now = datetime.now(timezone.utc)
        create_payload = {
            "user_id": test_user_id,
            "title": "Event to Delete",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
        }

        create_response = client.post("/api/v1/calendar/events", json=create_payload)
        event_id = create_response.json()["event_id"]

        # Delete event
        response = client.delete(f"/api/v1/calendar/events/{event_id}")
        assert response.status_code == 204

        # Verify deletion
        get_response = client.get(f"/api/v1/calendar/events/{event_id}")
        assert get_response.status_code == 404

    def test_delete_event_not_found(self, client):
        """Test deleting non-existent event returns 404"""
        response = client.delete("/api/v1/calendar/events/evt_nonexistent")
        assert response.status_code == 404


class TestCalendarAPISync:
    """Test external calendar sync API"""

    def test_sync_external_calendar(self, client, test_user_id):
        """Test syncing with external calendar"""
        response = client.post(
            f"/api/v1/calendar/sync?user_id={test_user_id}&provider=google_calendar",
            json={"access_token": "test_token"},
        )

        # Should return 200 (sync may not be fully implemented but should not crash)
        assert response.status_code == 200

        data = response.json()
        assert "provider" in data
        assert "status" in data

    def test_sync_invalid_provider(self, client, test_user_id):
        """Test syncing with invalid provider returns 400"""
        response = client.post(
            f"/api/v1/calendar/sync?user_id={test_user_id}&provider=invalid_provider",
        )

        assert response.status_code == 400


class TestCalendarAPIPagination:
    """Test API pagination"""

    def test_pagination_params(self, client, test_user_id):
        """Test pagination parameters"""
        now = datetime.now(timezone.utc)

        # Create multiple events
        for i in range(10):
            payload = {
                "user_id": test_user_id,
                "title": f"Pagination Event {i}",
                "start_time": (now + timedelta(hours=i)).isoformat(),
                "end_time": (now + timedelta(hours=i + 1)).isoformat(),
            }
            client.post("/api/v1/calendar/events", json=payload)

        # Query with pagination
        response = client.get(
            f"/api/v1/calendar/events?user_id={test_user_id}&limit=5&offset=0"
        )
        assert response.status_code == 200

        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert data["page_size"] == 5

    def test_pagination_limit_validation(self, client, test_user_id):
        """Test pagination limit validation"""
        # Invalid limit (too high)
        response = client.get(
            f"/api/v1/calendar/events?user_id={test_user_id}&limit=2000"
        )
        assert response.status_code == 422


class TestCalendarAPIRecurrence:
    """Test recurring events API"""

    def test_create_recurring_event(self, client, test_user_id):
        """Test creating recurring event via API"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        recurrence_end = now + timedelta(days=30)

        payload = {
            "user_id": test_user_id,
            "title": "Weekly Meeting",
            "start_time": now.isoformat(),
            "end_time": future.isoformat(),
            "recurrence_type": "weekly",
            "recurrence_end_date": recurrence_end.isoformat(),
            "recurrence_rule": "FREQ=WEEKLY;BYDAY=MO,WE,FR",
        }

        response = client.post("/api/v1/calendar/events", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["recurrence_type"] == "weekly"
        assert data["recurrence_rule"] == "FREQ=WEEKLY;BYDAY=MO,WE,FR"


class TestCalendarAPIAllDay:
    """Test all-day events API"""

    def test_create_all_day_event(self, client, test_user_id):
        """Test creating all-day event via API"""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        payload = {
            "user_id": test_user_id,
            "title": "Conference Day",
            "start_time": today.isoformat(),
            "end_time": tomorrow.isoformat(),
            "all_day": True,
        }

        response = client.post("/api/v1/calendar/events", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["all_day"] is True


class TestCalendarAPISharing:
    """Test shared events API"""

    def test_create_shared_event(self, client, test_user_id):
        """Test creating shared event via API"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=2)

        payload = {
            "user_id": test_user_id,
            "title": "Team Event",
            "start_time": now.isoformat(),
            "end_time": future.isoformat(),
            "is_shared": True,
            "shared_with": ["user_001", "user_002"],
        }

        response = client.post("/api/v1/calendar/events", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["is_shared"] is True
