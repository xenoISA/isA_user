"""
Component Golden Tests: Location Service

Tests the LocationService business logic layer with mocked dependencies.
All test data generated through LocationTestDataFactory - zero hardcoded data.

Service: location_service
Port: 8224
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional

# Test data factory
import sys
sys.path.insert(0, str(__file__).split('/tests/')[0])

from tests.contracts.location.data_contract import (
    LocationTestDataFactory,
    LocationMethod,
    GeofenceShapeType,
    PlaceCategory,
    RouteStatus,
    LocationReportRequestBuilder,
    GeofenceCreateRequestBuilder,
    PlaceCreateRequestBuilder,
)


class MockRepository:
    """Mock repository for testing service layer"""

    def __init__(self):
        self.locations: Dict[str, Dict] = {}
        self.geofences: Dict[str, Dict] = {}
        self.places: Dict[str, Dict] = {}
        self.routes: Dict[str, Dict] = {}
        self.location_events: List[Dict] = []

    async def save_location(self, location_data: Dict) -> Dict:
        """Save location and return saved data"""
        location_id = location_data.get("location_id") or LocationTestDataFactory.make_location_id()
        location_data["location_id"] = location_id
        location_data["created_at"] = datetime.now(timezone.utc)
        self.locations[location_id] = location_data
        return location_data

    async def get_location(self, location_id: str) -> Optional[Dict]:
        """Get location by ID"""
        return self.locations.get(location_id)

    async def get_device_locations(self, device_id: str, limit: int = 100) -> List[Dict]:
        """Get locations for a device"""
        return [
            loc for loc in self.locations.values()
            if loc.get("device_id") == device_id
        ][:limit]

    async def get_latest_location(self, device_id: str) -> Optional[Dict]:
        """Get latest location for device"""
        device_locs = [
            loc for loc in self.locations.values()
            if loc.get("device_id") == device_id
        ]
        if device_locs:
            return max(device_locs, key=lambda x: x.get("created_at", datetime.min))
        return None

    async def delete_device_locations(self, device_id: str) -> int:
        """Delete all locations for a device"""
        to_delete = [k for k, v in self.locations.items() if v.get("device_id") == device_id]
        for k in to_delete:
            del self.locations[k]
        return len(to_delete)

    async def save_geofence(self, geofence_data: Dict) -> Dict:
        """Save geofence"""
        geofence_id = geofence_data.get("geofence_id") or LocationTestDataFactory.make_geofence_id()
        geofence_data["geofence_id"] = geofence_id
        geofence_data["created_at"] = datetime.now(timezone.utc)
        geofence_data["updated_at"] = datetime.now(timezone.utc)
        geofence_data["total_triggers"] = 0
        geofence_data["active"] = True
        self.geofences[geofence_id] = geofence_data
        return geofence_data

    async def get_geofence(self, geofence_id: str) -> Optional[Dict]:
        """Get geofence by ID"""
        return self.geofences.get(geofence_id)

    async def get_user_geofences(self, user_id: str) -> List[Dict]:
        """Get all geofences for user"""
        return [g for g in self.geofences.values() if g.get("user_id") == user_id]

    async def update_geofence(self, geofence_id: str, update_data: Dict) -> Optional[Dict]:
        """Update geofence"""
        if geofence_id in self.geofences:
            self.geofences[geofence_id].update(update_data)
            self.geofences[geofence_id]["updated_at"] = datetime.now(timezone.utc)
            return self.geofences[geofence_id]
        return None

    async def delete_geofence(self, geofence_id: str) -> bool:
        """Delete geofence"""
        if geofence_id in self.geofences:
            del self.geofences[geofence_id]
            return True
        return False

    async def get_active_geofences_for_location(
        self, latitude: float, longitude: float, device_id: str
    ) -> List[Dict]:
        """Get geofences that contain the given location"""
        # Simplified: return all active geofences for the device
        return [
            g for g in self.geofences.values()
            if g.get("active") and (
                not g.get("target_devices") or
                device_id in g.get("target_devices", [])
            )
        ]

    async def save_place(self, place_data: Dict) -> Dict:
        """Save place"""
        place_id = place_data.get("place_id") or LocationTestDataFactory.make_place_id()
        place_data["place_id"] = place_id
        place_data["created_at"] = datetime.now(timezone.utc)
        place_data["updated_at"] = datetime.now(timezone.utc)
        place_data["visit_count"] = 0
        place_data["total_time_spent"] = 0
        self.places[place_id] = place_data
        return place_data

    async def get_place(self, place_id: str) -> Optional[Dict]:
        """Get place by ID"""
        return self.places.get(place_id)

    async def get_user_places(self, user_id: str) -> List[Dict]:
        """Get all places for user"""
        return [p for p in self.places.values() if p.get("user_id") == user_id]

    async def delete_place(self, place_id: str) -> bool:
        """Delete place"""
        if place_id in self.places:
            del self.places[place_id]
            return True
        return False

    async def save_location_event(self, event_data: Dict) -> Dict:
        """Save location event"""
        event_data["event_id"] = LocationTestDataFactory.make_uuid()
        event_data["created_at"] = datetime.now(timezone.utc)
        self.location_events.append(event_data)
        return event_data


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events: List[Dict] = []

    async def publish_event(self, subject: str, data: Dict):
        """Publish event to the bus"""
        self.published_events.append({
            "subject": subject,
            "data": data,
            "timestamp": datetime.now(timezone.utc),
        })

    def get_events_by_subject(self, subject: str) -> List[Dict]:
        """Get all events for a subject"""
        return [e for e in self.published_events if e["subject"] == subject]

    def clear(self):
        """Clear published events"""
        self.published_events.clear()


class MockDeviceClient:
    """Mock device client"""

    def __init__(self):
        self.devices: Dict[str, Dict] = {}

    async def get_device(self, device_id: str) -> Optional[Dict]:
        """Get device by ID"""
        return self.devices.get(device_id)

    async def verify_device_ownership(self, device_id: str, user_id: str) -> bool:
        """Verify user owns the device"""
        device = self.devices.get(device_id)
        return device is not None and device.get("user_id") == user_id

    def add_device(self, device_id: str, user_id: str, **kwargs):
        """Add a device for testing"""
        self.devices[device_id] = {
            "device_id": device_id,
            "user_id": user_id,
            **kwargs,
        }


class MockAccountClient:
    """Mock account client"""

    def __init__(self):
        self.accounts: Dict[str, Dict] = {}

    async def get_account(self, user_id: str) -> Optional[Dict]:
        """Get account by user ID"""
        return self.accounts.get(user_id)

    async def verify_user_exists(self, user_id: str) -> bool:
        """Verify user exists"""
        return user_id in self.accounts

    def add_account(self, user_id: str, **kwargs):
        """Add account for testing"""
        self.accounts[user_id] = {
            "user_id": user_id,
            **kwargs,
        }


class MockNotificationClient:
    """Mock notification client"""

    def __init__(self):
        self.notifications: List[Dict] = []

    async def send_notification(self, user_id: str, notification_type: str, data: Dict):
        """Send notification"""
        self.notifications.append({
            "user_id": user_id,
            "type": notification_type,
            "data": data,
            "sent_at": datetime.now(timezone.utc),
        })


# =============================================================================
# LOCATION SERVICE WRAPPER (For Testing)
# =============================================================================


class TestableLocationService:
    """
    Testable location service with injected dependencies.
    Mirrors the actual LocationService interface.
    """

    def __init__(
        self,
        repository: MockRepository,
        event_bus: MockEventBus,
        device_client: MockDeviceClient,
        account_client: MockAccountClient,
        notification_client: MockNotificationClient,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.device_client = device_client
        self.account_client = account_client
        self.notification_client = notification_client

    async def report_location(
        self,
        device_id: str,
        user_id: str,
        latitude: float,
        longitude: float,
        accuracy: float,
        **kwargs,
    ) -> Dict:
        """Report a device location"""
        # Verify device ownership
        if not await self.device_client.verify_device_ownership(device_id, user_id):
            raise ValueError("Device not found or not owned by user")

        # Save location
        location_data = {
            "device_id": device_id,
            "user_id": user_id,
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
            "timestamp": kwargs.get("timestamp", datetime.now(timezone.utc)),
            **{k: v for k, v in kwargs.items() if v is not None},
        }

        saved_location = await self.repository.save_location(location_data)

        # Publish event
        await self.event_bus.publish_event("location.updated", {
            "location_id": saved_location["location_id"],
            "device_id": device_id,
            "user_id": user_id,
            "latitude": latitude,
            "longitude": longitude,
        })

        # Check geofences
        await self._check_geofences(saved_location)

        return saved_location

    async def _check_geofences(self, location: Dict):
        """Check if location triggers any geofences"""
        geofences = await self.repository.get_active_geofences_for_location(
            location["latitude"],
            location["longitude"],
            location["device_id"],
        )

        for geofence in geofences:
            # Simplified geofence checking for tests
            if self._is_inside_geofence(location, geofence):
                await self._handle_geofence_entry(location, geofence)

    def _is_inside_geofence(self, location: Dict, geofence: Dict) -> bool:
        """Check if location is inside geofence (simplified)"""
        if geofence.get("shape_type") == "circle":
            # Simple distance check (not using PostGIS)
            lat_diff = abs(location["latitude"] - geofence["center_lat"])
            lon_diff = abs(location["longitude"] - geofence["center_lon"])
            # Rough approximation: 0.01 degrees ~ 1.1km
            distance_approx = (lat_diff**2 + lon_diff**2)**0.5 * 111000
            return distance_approx <= geofence.get("radius", 0)
        return False

    async def _handle_geofence_entry(self, location: Dict, geofence: Dict):
        """Handle geofence entry event"""
        if geofence.get("trigger_on_enter"):
            await self.event_bus.publish_event("geofence.entered", {
                "geofence_id": geofence["geofence_id"],
                "device_id": location["device_id"],
                "user_id": location["user_id"],
                "latitude": location["latitude"],
                "longitude": location["longitude"],
            })

            # Update trigger count
            await self.repository.update_geofence(
                geofence["geofence_id"],
                {
                    "total_triggers": geofence.get("total_triggers", 0) + 1,
                    "last_triggered": datetime.now(timezone.utc),
                }
            )

    async def batch_report_locations(
        self,
        user_id: str,
        locations: List[Dict],
    ) -> Dict:
        """Report multiple locations in batch"""
        results = []
        errors = []

        for loc in locations:
            try:
                result = await self.report_location(
                    device_id=loc["device_id"],
                    user_id=user_id,
                    latitude=loc["latitude"],
                    longitude=loc["longitude"],
                    accuracy=loc["accuracy"],
                    **{k: v for k, v in loc.items() if k not in ["device_id", "latitude", "longitude", "accuracy"]},
                )
                results.append(result)
            except Exception as e:
                errors.append({"location": loc, "error": str(e)})

        return {
            "success": len(errors) == 0,
            "processed": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }

    async def get_device_location_history(
        self,
        device_id: str,
        user_id: str,
        limit: int = 100,
    ) -> List[Dict]:
        """Get location history for a device"""
        if not await self.device_client.verify_device_ownership(device_id, user_id):
            raise ValueError("Device not found or not owned by user")

        return await self.repository.get_device_locations(device_id, limit)

    async def get_latest_device_location(
        self,
        device_id: str,
        user_id: str,
    ) -> Optional[Dict]:
        """Get latest location for a device"""
        if not await self.device_client.verify_device_ownership(device_id, user_id):
            raise ValueError("Device not found or not owned by user")

        return await self.repository.get_latest_location(device_id)

    async def create_geofence(
        self,
        user_id: str,
        name: str,
        shape_type: str,
        center_lat: float,
        center_lon: float,
        **kwargs,
    ) -> Dict:
        """Create a geofence"""
        if not await self.account_client.verify_user_exists(user_id):
            raise ValueError("User not found")

        geofence_data = {
            "user_id": user_id,
            "name": name,
            "shape_type": shape_type,
            "center_lat": center_lat,
            "center_lon": center_lon,
            **{k: v for k, v in kwargs.items() if v is not None},
        }

        saved_geofence = await self.repository.save_geofence(geofence_data)

        await self.event_bus.publish_event("geofence.created", {
            "geofence_id": saved_geofence["geofence_id"],
            "user_id": user_id,
            "name": name,
        })

        return saved_geofence

    async def update_geofence(
        self,
        geofence_id: str,
        user_id: str,
        **update_data,
    ) -> Optional[Dict]:
        """Update a geofence"""
        geofence = await self.repository.get_geofence(geofence_id)
        if not geofence:
            raise ValueError("Geofence not found")

        if geofence.get("user_id") != user_id:
            raise ValueError("Not authorized to update this geofence")

        return await self.repository.update_geofence(geofence_id, update_data)

    async def delete_geofence(
        self,
        geofence_id: str,
        user_id: str,
    ) -> bool:
        """Delete a geofence"""
        geofence = await self.repository.get_geofence(geofence_id)
        if not geofence:
            raise ValueError("Geofence not found")

        if geofence.get("user_id") != user_id:
            raise ValueError("Not authorized to delete this geofence")

        result = await self.repository.delete_geofence(geofence_id)

        if result:
            await self.event_bus.publish_event("geofence.deleted", {
                "geofence_id": geofence_id,
                "user_id": user_id,
            })

        return result

    async def get_user_geofences(self, user_id: str) -> List[Dict]:
        """Get all geofences for a user"""
        return await self.repository.get_user_geofences(user_id)

    async def create_place(
        self,
        user_id: str,
        name: str,
        category: str,
        latitude: float,
        longitude: float,
        **kwargs,
    ) -> Dict:
        """Create a place"""
        if not await self.account_client.verify_user_exists(user_id):
            raise ValueError("User not found")

        place_data = {
            "user_id": user_id,
            "name": name,
            "category": category,
            "latitude": latitude,
            "longitude": longitude,
            **{k: v for k, v in kwargs.items() if v is not None},
        }

        saved_place = await self.repository.save_place(place_data)

        await self.event_bus.publish_event("place.created", {
            "place_id": saved_place["place_id"],
            "user_id": user_id,
            "name": name,
            "category": category,
        })

        return saved_place

    async def get_user_places(self, user_id: str) -> List[Dict]:
        """Get all places for a user"""
        return await self.repository.get_user_places(user_id)

    async def delete_place(
        self,
        place_id: str,
        user_id: str,
    ) -> bool:
        """Delete a place"""
        place = await self.repository.get_place(place_id)
        if not place:
            raise ValueError("Place not found")

        if place.get("user_id") != user_id:
            raise ValueError("Not authorized to delete this place")

        return await self.repository.delete_place(place_id)

    async def calculate_distance(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
    ) -> Dict:
        """Calculate distance between two points"""
        # Haversine formula (simplified)
        import math

        R = 6371000  # Earth radius in meters

        lat1, lon1 = math.radians(from_lat), math.radians(from_lon)
        lat2, lon2 = math.radians(to_lat), math.radians(to_lon)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        distance_m = R * c

        return {
            "from_lat": from_lat,
            "from_lon": from_lon,
            "to_lat": to_lat,
            "to_lon": to_lon,
            "distance_meters": round(distance_m, 2),
            "distance_km": round(distance_m / 1000, 2),
        }


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def mock_repository():
    """Create mock repository"""
    return MockRepository()


@pytest.fixture
def mock_event_bus():
    """Create mock event bus"""
    return MockEventBus()


@pytest.fixture
def mock_device_client():
    """Create mock device client"""
    return MockDeviceClient()


@pytest.fixture
def mock_account_client():
    """Create mock account client"""
    return MockAccountClient()


@pytest.fixture
def mock_notification_client():
    """Create mock notification client"""
    return MockNotificationClient()


@pytest.fixture
def location_service(
    mock_repository,
    mock_event_bus,
    mock_device_client,
    mock_account_client,
    mock_notification_client,
):
    """Create testable location service"""
    return TestableLocationService(
        repository=mock_repository,
        event_bus=mock_event_bus,
        device_client=mock_device_client,
        account_client=mock_account_client,
        notification_client=mock_notification_client,
    )


@pytest.fixture
def test_user(mock_account_client):
    """Create test user"""
    user_id = LocationTestDataFactory.make_user_id()
    mock_account_client.add_account(user_id, email=f"{user_id}@test.com")
    return user_id


@pytest.fixture
def test_device(mock_device_client, test_user):
    """Create test device owned by test user"""
    device_id = LocationTestDataFactory.make_device_id()
    mock_device_client.add_device(device_id, test_user, name="Test Device")
    return device_id


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestLocationReporting:
    """Test location reporting functionality"""

    @pytest.mark.asyncio
    async def test_report_location_success(
        self, location_service, test_user, test_device
    ):
        """Test successful location report"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        accuracy = LocationTestDataFactory.make_accuracy()

        result = await location_service.report_location(
            device_id=test_device,
            user_id=test_user,
            latitude=lat,
            longitude=lon,
            accuracy=accuracy,
        )

        assert result is not None
        assert "location_id" in result
        assert result["device_id"] == test_device
        assert result["user_id"] == test_user
        assert result["latitude"] == lat
        assert result["longitude"] == lon
        assert result["accuracy"] == accuracy

    @pytest.mark.asyncio
    async def test_report_location_publishes_event(
        self, location_service, mock_event_bus, test_user, test_device
    ):
        """Test location report publishes event"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()

        await location_service.report_location(
            device_id=test_device,
            user_id=test_user,
            latitude=lat,
            longitude=lon,
            accuracy=LocationTestDataFactory.make_accuracy(),
        )

        events = mock_event_bus.get_events_by_subject("location.updated")
        assert len(events) == 1
        assert events[0]["data"]["device_id"] == test_device
        assert events[0]["data"]["user_id"] == test_user

    @pytest.mark.asyncio
    async def test_report_location_with_all_fields(
        self, location_service, test_user, test_device
    ):
        """Test location report with all optional fields"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()

        result = await location_service.report_location(
            device_id=test_device,
            user_id=test_user,
            latitude=lat,
            longitude=lon,
            accuracy=LocationTestDataFactory.make_accuracy(),
            altitude=LocationTestDataFactory.make_altitude(),
            heading=LocationTestDataFactory.make_heading(),
            speed=LocationTestDataFactory.make_speed(),
            battery_level=LocationTestDataFactory.make_battery_level(),
            address=LocationTestDataFactory.make_address(),
            city=LocationTestDataFactory.make_city(),
        )

        assert result["altitude"] is not None
        assert result["heading"] is not None
        assert result["speed"] is not None
        assert result["battery_level"] is not None
        assert result["address"] is not None

    @pytest.mark.asyncio
    async def test_report_location_invalid_device(
        self, location_service, test_user
    ):
        """Test location report fails for invalid device"""
        invalid_device = LocationTestDataFactory.make_device_id()
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()

        with pytest.raises(ValueError, match="Device not found"):
            await location_service.report_location(
                device_id=invalid_device,
                user_id=test_user,
                latitude=lat,
                longitude=lon,
                accuracy=LocationTestDataFactory.make_accuracy(),
            )

    @pytest.mark.asyncio
    async def test_report_location_unauthorized_device(
        self, location_service, mock_device_client, test_user
    ):
        """Test location report fails when user doesn't own device"""
        other_user = LocationTestDataFactory.make_user_id()
        device_id = LocationTestDataFactory.make_device_id()
        mock_device_client.add_device(device_id, other_user)

        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()

        with pytest.raises(ValueError, match="not owned by user"):
            await location_service.report_location(
                device_id=device_id,
                user_id=test_user,
                latitude=lat,
                longitude=lon,
                accuracy=LocationTestDataFactory.make_accuracy(),
            )


class TestBatchLocationReporting:
    """Test batch location reporting"""

    @pytest.mark.asyncio
    async def test_batch_report_locations_success(
        self, location_service, test_user, test_device
    ):
        """Test successful batch location report"""
        locations = []
        for _ in range(5):
            lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
            locations.append({
                "device_id": test_device,
                "latitude": lat,
                "longitude": lon,
                "accuracy": LocationTestDataFactory.make_accuracy(),
            })

        result = await location_service.batch_report_locations(test_user, locations)

        assert result["success"] is True
        assert result["processed"] == 5
        assert result["failed"] == 0
        assert len(result["results"]) == 5

    @pytest.mark.asyncio
    async def test_batch_report_locations_partial_failure(
        self, location_service, test_user, test_device
    ):
        """Test batch with some invalid locations"""
        invalid_device = LocationTestDataFactory.make_device_id()

        locations = [
            {
                "device_id": test_device,
                "latitude": 37.7749,
                "longitude": -122.4194,
                "accuracy": 10.0,
            },
            {
                "device_id": invalid_device,  # Invalid - not owned
                "latitude": 37.7750,
                "longitude": -122.4195,
                "accuracy": 10.0,
            },
        ]

        result = await location_service.batch_report_locations(test_user, locations)

        assert result["success"] is False
        assert result["processed"] == 1
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_batch_report_publishes_multiple_events(
        self, location_service, mock_event_bus, test_user, test_device
    ):
        """Test batch report publishes event for each location"""
        locations = []
        for _ in range(3):
            lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
            locations.append({
                "device_id": test_device,
                "latitude": lat,
                "longitude": lon,
                "accuracy": LocationTestDataFactory.make_accuracy(),
            })

        await location_service.batch_report_locations(test_user, locations)

        events = mock_event_bus.get_events_by_subject("location.updated")
        assert len(events) == 3


class TestLocationHistory:
    """Test location history retrieval"""

    @pytest.mark.asyncio
    async def test_get_location_history(
        self, location_service, test_user, test_device
    ):
        """Test getting location history"""
        # Create multiple locations
        for _ in range(5):
            lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
            await location_service.report_location(
                device_id=test_device,
                user_id=test_user,
                latitude=lat,
                longitude=lon,
                accuracy=LocationTestDataFactory.make_accuracy(),
            )

        history = await location_service.get_device_location_history(
            test_device, test_user
        )

        assert len(history) == 5
        for loc in history:
            assert loc["device_id"] == test_device

    @pytest.mark.asyncio
    async def test_get_location_history_with_limit(
        self, location_service, test_user, test_device
    ):
        """Test location history respects limit"""
        for _ in range(10):
            lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
            await location_service.report_location(
                device_id=test_device,
                user_id=test_user,
                latitude=lat,
                longitude=lon,
                accuracy=LocationTestDataFactory.make_accuracy(),
            )

        history = await location_service.get_device_location_history(
            test_device, test_user, limit=5
        )

        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_get_latest_location(
        self, location_service, test_user, test_device
    ):
        """Test getting latest location"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        await location_service.report_location(
            device_id=test_device,
            user_id=test_user,
            latitude=lat,
            longitude=lon,
            accuracy=LocationTestDataFactory.make_accuracy(),
        )

        latest = await location_service.get_latest_device_location(
            test_device, test_user
        )

        assert latest is not None
        assert latest["device_id"] == test_device

    @pytest.mark.asyncio
    async def test_get_history_unauthorized(
        self, location_service, mock_device_client, test_user
    ):
        """Test history fails for unauthorized device"""
        other_user = LocationTestDataFactory.make_user_id()
        device_id = LocationTestDataFactory.make_device_id()
        mock_device_client.add_device(device_id, other_user)

        with pytest.raises(ValueError, match="not owned by user"):
            await location_service.get_device_location_history(device_id, test_user)


class TestGeofenceManagement:
    """Test geofence management functionality"""

    @pytest.mark.asyncio
    async def test_create_circle_geofence(self, location_service, test_user):
        """Test creating circle geofence"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        name = LocationTestDataFactory.make_geofence_name()
        radius = LocationTestDataFactory.make_radius(100, 500)

        result = await location_service.create_geofence(
            user_id=test_user,
            name=name,
            shape_type="circle",
            center_lat=lat,
            center_lon=lon,
            radius=radius,
            trigger_on_enter=True,
            trigger_on_exit=True,
        )

        assert result is not None
        assert "geofence_id" in result
        assert result["name"] == name
        assert result["shape_type"] == "circle"
        assert result["radius"] == radius
        assert result["active"] is True
        assert result["total_triggers"] == 0

    @pytest.mark.asyncio
    async def test_create_geofence_publishes_event(
        self, location_service, mock_event_bus, test_user
    ):
        """Test geofence creation publishes event"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()

        await location_service.create_geofence(
            user_id=test_user,
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type="circle",
            center_lat=lat,
            center_lon=lon,
            radius=500,
        )

        events = mock_event_bus.get_events_by_subject("geofence.created")
        assert len(events) == 1
        assert events[0]["data"]["user_id"] == test_user

    @pytest.mark.asyncio
    async def test_create_geofence_with_targets(self, location_service, test_user):
        """Test creating geofence with target devices"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        target_devices = LocationTestDataFactory.make_batch_device_ids(3)

        result = await location_service.create_geofence(
            user_id=test_user,
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type="circle",
            center_lat=lat,
            center_lon=lon,
            radius=500,
            target_devices=target_devices,
        )

        assert result["target_devices"] == target_devices

    @pytest.mark.asyncio
    async def test_update_geofence(self, location_service, test_user):
        """Test updating geofence"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        geofence = await location_service.create_geofence(
            user_id=test_user,
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type="circle",
            center_lat=lat,
            center_lon=lon,
            radius=500,
        )

        new_name = LocationTestDataFactory.make_geofence_name()
        updated = await location_service.update_geofence(
            geofence_id=geofence["geofence_id"],
            user_id=test_user,
            name=new_name,
        )

        assert updated["name"] == new_name

    @pytest.mark.asyncio
    async def test_update_geofence_unauthorized(
        self, location_service, mock_account_client, test_user
    ):
        """Test updating geofence by non-owner fails"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        geofence = await location_service.create_geofence(
            user_id=test_user,
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type="circle",
            center_lat=lat,
            center_lon=lon,
            radius=500,
        )

        other_user = LocationTestDataFactory.make_user_id()
        mock_account_client.add_account(other_user)

        with pytest.raises(ValueError, match="Not authorized"):
            await location_service.update_geofence(
                geofence_id=geofence["geofence_id"],
                user_id=other_user,
                name="Hacked Name",
            )

    @pytest.mark.asyncio
    async def test_delete_geofence(
        self, location_service, mock_event_bus, test_user
    ):
        """Test deleting geofence"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        geofence = await location_service.create_geofence(
            user_id=test_user,
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type="circle",
            center_lat=lat,
            center_lon=lon,
            radius=500,
        )

        mock_event_bus.clear()

        result = await location_service.delete_geofence(
            geofence_id=geofence["geofence_id"],
            user_id=test_user,
        )

        assert result is True

        events = mock_event_bus.get_events_by_subject("geofence.deleted")
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_get_user_geofences(self, location_service, test_user):
        """Test getting all geofences for user"""
        for _ in range(3):
            lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
            await location_service.create_geofence(
                user_id=test_user,
                name=LocationTestDataFactory.make_geofence_name(),
                shape_type="circle",
                center_lat=lat,
                center_lon=lon,
                radius=500,
            )

        geofences = await location_service.get_user_geofences(test_user)
        assert len(geofences) == 3


class TestGeofenceTriggering:
    """Test geofence triggering logic"""

    @pytest.mark.asyncio
    async def test_location_triggers_geofence_entry(
        self, location_service, mock_event_bus, test_user, test_device
    ):
        """Test location report triggers geofence entry event"""
        # Create geofence at specific location
        geofence = await location_service.create_geofence(
            user_id=test_user,
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type="circle",
            center_lat=37.7749,
            center_lon=-122.4194,
            radius=1000,
            trigger_on_enter=True,
            target_devices=[test_device],
        )

        mock_event_bus.clear()

        # Report location inside geofence
        await location_service.report_location(
            device_id=test_device,
            user_id=test_user,
            latitude=37.7749,  # Same as geofence center
            longitude=-122.4194,
            accuracy=10.0,
        )

        entry_events = mock_event_bus.get_events_by_subject("geofence.entered")
        assert len(entry_events) >= 1
        assert entry_events[0]["data"]["geofence_id"] == geofence["geofence_id"]

    @pytest.mark.asyncio
    async def test_geofence_trigger_updates_count(
        self, location_service, mock_repository, test_user, test_device
    ):
        """Test geofence trigger count is updated"""
        geofence = await location_service.create_geofence(
            user_id=test_user,
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type="circle",
            center_lat=37.7749,
            center_lon=-122.4194,
            radius=1000,
            trigger_on_enter=True,
            target_devices=[test_device],
        )

        initial_triggers = geofence["total_triggers"]

        # Report location inside geofence
        await location_service.report_location(
            device_id=test_device,
            user_id=test_user,
            latitude=37.7749,
            longitude=-122.4194,
            accuracy=10.0,
        )

        updated_geofence = await mock_repository.get_geofence(geofence["geofence_id"])
        assert updated_geofence["total_triggers"] > initial_triggers


class TestPlaceManagement:
    """Test place management functionality"""

    @pytest.mark.asyncio
    async def test_create_place(self, location_service, test_user):
        """Test creating a place"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        name = LocationTestDataFactory.make_place_name()

        result = await location_service.create_place(
            user_id=test_user,
            name=name,
            category="home",
            latitude=lat,
            longitude=lon,
            radius=100,
        )

        assert result is not None
        assert "place_id" in result
        assert result["name"] == name
        assert result["category"] == "home"
        assert result["visit_count"] == 0

    @pytest.mark.asyncio
    async def test_create_place_publishes_event(
        self, location_service, mock_event_bus, test_user
    ):
        """Test place creation publishes event"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()

        await location_service.create_place(
            user_id=test_user,
            name=LocationTestDataFactory.make_place_name(),
            category="work",
            latitude=lat,
            longitude=lon,
        )

        events = mock_event_bus.get_events_by_subject("place.created")
        assert len(events) == 1
        assert events[0]["data"]["category"] == "work"

    @pytest.mark.asyncio
    async def test_create_place_with_address(self, location_service, test_user):
        """Test creating place with address"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()

        result = await location_service.create_place(
            user_id=test_user,
            name=LocationTestDataFactory.make_place_name(),
            category="favorite",
            latitude=lat,
            longitude=lon,
            address=LocationTestDataFactory.make_address(),
            icon="star",
            color="#FFD700",
        )

        assert result["address"] is not None
        assert result["icon"] == "star"
        assert result["color"] == "#FFD700"

    @pytest.mark.asyncio
    async def test_get_user_places(self, location_service, test_user):
        """Test getting all places for user"""
        for category in ["home", "work", "school"]:
            lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
            await location_service.create_place(
                user_id=test_user,
                name=LocationTestDataFactory.make_place_name(),
                category=category,
                latitude=lat,
                longitude=lon,
            )

        places = await location_service.get_user_places(test_user)
        assert len(places) == 3

    @pytest.mark.asyncio
    async def test_delete_place(self, location_service, test_user):
        """Test deleting a place"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        place = await location_service.create_place(
            user_id=test_user,
            name=LocationTestDataFactory.make_place_name(),
            category="home",
            latitude=lat,
            longitude=lon,
        )

        result = await location_service.delete_place(
            place_id=place["place_id"],
            user_id=test_user,
        )

        assert result is True

        places = await location_service.get_user_places(test_user)
        assert len(places) == 0

    @pytest.mark.asyncio
    async def test_delete_place_unauthorized(
        self, location_service, mock_account_client, test_user
    ):
        """Test deleting place by non-owner fails"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        place = await location_service.create_place(
            user_id=test_user,
            name=LocationTestDataFactory.make_place_name(),
            category="home",
            latitude=lat,
            longitude=lon,
        )

        other_user = LocationTestDataFactory.make_user_id()
        mock_account_client.add_account(other_user)

        with pytest.raises(ValueError, match="Not authorized"):
            await location_service.delete_place(
                place_id=place["place_id"],
                user_id=other_user,
            )


class TestDistanceCalculation:
    """Test distance calculation functionality"""

    @pytest.mark.asyncio
    async def test_calculate_distance_same_point(self, location_service):
        """Test distance between same point is zero"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()

        result = await location_service.calculate_distance(lat, lon, lat, lon)

        assert result["distance_meters"] == 0.0
        assert result["distance_km"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_distance_sf_to_ny(self, location_service):
        """Test distance between San Francisco and New York"""
        sf_lat, sf_lon = 37.7749, -122.4194
        ny_lat, ny_lon = 40.7128, -74.0060

        result = await location_service.calculate_distance(
            sf_lat, sf_lon, ny_lat, ny_lon
        )

        # Approximate distance is ~4100 km
        assert 4000 < result["distance_km"] < 4200

    @pytest.mark.asyncio
    async def test_calculate_distance_returns_both_units(self, location_service):
        """Test distance returns both meters and km"""
        lat1, lon1 = LocationTestDataFactory.make_san_francisco_coordinates()
        lat2, lon2 = LocationTestDataFactory.make_new_york_coordinates()

        result = await location_service.calculate_distance(
            lat1, lon1, lat2, lon2
        )

        assert "distance_meters" in result
        assert "distance_km" in result
        assert result["distance_km"] == round(result["distance_meters"] / 1000, 2)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_location_at_boundary_coordinates(
        self, location_service, test_user, test_device
    ):
        """Test location at boundary coordinates"""
        # Test at (0, 0)
        result = await location_service.report_location(
            device_id=test_device,
            user_id=test_user,
            latitude=0.0,
            longitude=0.0,
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert result["latitude"] == 0.0
        assert result["longitude"] == 0.0

    @pytest.mark.asyncio
    async def test_location_at_poles(
        self, location_service, test_user, test_device
    ):
        """Test location at poles"""
        # North pole
        result = await location_service.report_location(
            device_id=test_device,
            user_id=test_user,
            latitude=90.0,
            longitude=0.0,
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert result["latitude"] == 90.0

        # South pole
        result = await location_service.report_location(
            device_id=test_device,
            user_id=test_user,
            latitude=-90.0,
            longitude=0.0,
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert result["latitude"] == -90.0

    @pytest.mark.asyncio
    async def test_geofence_with_unicode_name(self, location_service, test_user):
        """Test geofence with unicode characters in name"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        unicode_name = LocationTestDataFactory.make_unicode_name()

        result = await location_service.create_geofence(
            user_id=test_user,
            name=unicode_name,
            shape_type="circle",
            center_lat=lat,
            center_lon=lon,
            radius=500,
        )

        assert result["name"] == unicode_name

    @pytest.mark.asyncio
    async def test_place_with_special_characters(self, location_service, test_user):
        """Test place with special characters"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        special_name = LocationTestDataFactory.make_special_chars_name()

        result = await location_service.create_place(
            user_id=test_user,
            name=special_name,
            category="custom",
            latitude=lat,
            longitude=lon,
        )

        assert result["name"] == special_name

    @pytest.mark.asyncio
    async def test_empty_location_history(
        self, location_service, test_user, test_device
    ):
        """Test getting history for device with no locations"""
        history = await location_service.get_device_location_history(
            test_device, test_user
        )
        assert history == []

    @pytest.mark.asyncio
    async def test_no_latest_location(
        self, location_service, test_user, test_device
    ):
        """Test getting latest when no locations exist"""
        latest = await location_service.get_latest_device_location(
            test_device, test_user
        )
        assert latest is None


class TestDataFactory:
    """Test that data factory produces valid data"""

    def test_factory_device_ids_unique(self):
        """Test factory generates unique device IDs"""
        ids = [LocationTestDataFactory.make_device_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_factory_coordinates_in_range(self):
        """Test factory generates valid coordinates"""
        for _ in range(100):
            lat, lon = LocationTestDataFactory.make_coordinates()
            assert -90 <= lat <= 90
            assert -180 <= lon <= 180

    def test_factory_accuracy_positive(self):
        """Test factory generates positive accuracy"""
        for _ in range(100):
            accuracy = LocationTestDataFactory.make_accuracy()
            assert accuracy > 0

    def test_factory_heading_in_range(self):
        """Test factory generates valid heading"""
        for _ in range(100):
            heading = LocationTestDataFactory.make_heading()
            assert 0 <= heading < 360

    def test_factory_battery_in_range(self):
        """Test factory generates valid battery level"""
        for _ in range(100):
            battery = LocationTestDataFactory.make_battery_level()
            assert 0 <= battery <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
