"""
Unit Golden Tests: Location Service Models

Tests model validation and serialization without external dependencies.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from microservices.location_service.models import (
    LocationMethod,
    GeofenceShapeType,
    GeofenceTriggerType,
    PlaceCategory,
    LocationEventType,
    RouteStatus,
    LocationReportRequest,
    LocationBatchRequest,
    GeofenceCreateRequest,
    GeofenceUpdateRequest,
    PlaceCreateRequest,
    PlaceUpdateRequest,
    RouteStartRequest,
    NearbySearchRequest,
    RadiusSearchRequest,
    PolygonSearchRequest,
    LocationResponse,
    GeofenceResponse,
    LocationEventResponse,
    PlaceResponse,
    RouteResponse,
    DeviceLocationResponse,
    LocationListResponse,
    GeofenceListResponse,
    PlaceListResponse,
    RouteListResponse,
    LocationEventListResponse,
    LocationStatsResponse,
    GeofenceStatsResponse,
    DistanceResponse,
    HeatmapDataResponse,
    LocationServiceStatus,
    LocationOperationResult,
)


class TestEnumTypes:
    """Test enum type definitions"""

    def test_location_method_values(self):
        """Test LocationMethod enum values"""
        assert LocationMethod.GPS == "gps"
        assert LocationMethod.WIFI == "wifi"
        assert LocationMethod.CELLULAR == "cellular"
        assert LocationMethod.BLUETOOTH == "bluetooth"
        assert LocationMethod.MANUAL == "manual"
        assert LocationMethod.HYBRID == "hybrid"

    def test_geofence_shape_type_values(self):
        """Test GeofenceShapeType enum values"""
        assert GeofenceShapeType.CIRCLE == "circle"
        assert GeofenceShapeType.POLYGON == "polygon"
        assert GeofenceShapeType.RECTANGLE == "rectangle"

    def test_geofence_trigger_type_values(self):
        """Test GeofenceTriggerType enum values"""
        assert GeofenceTriggerType.ENTER == "enter"
        assert GeofenceTriggerType.EXIT == "exit"
        assert GeofenceTriggerType.DWELL == "dwell"

    def test_place_category_values(self):
        """Test PlaceCategory enum values"""
        assert PlaceCategory.HOME == "home"
        assert PlaceCategory.WORK == "work"
        assert PlaceCategory.SCHOOL == "school"
        assert PlaceCategory.FAVORITE == "favorite"
        assert PlaceCategory.CUSTOM == "custom"

    def test_location_event_type_values(self):
        """Test LocationEventType enum values"""
        assert LocationEventType.LOCATION_UPDATE == "location_update"
        assert LocationEventType.GEOFENCE_ENTER == "geofence_enter"
        assert LocationEventType.GEOFENCE_EXIT == "geofence_exit"
        assert LocationEventType.GEOFENCE_DWELL == "geofence_dwell"
        assert LocationEventType.SIGNIFICANT_MOVEMENT == "significant_movement"
        assert LocationEventType.LOW_BATTERY_AT_LOCATION == "low_battery_at_location"
        assert LocationEventType.DEVICE_STOPPED == "device_stopped"
        assert LocationEventType.DEVICE_MOVING == "device_moving"

    def test_route_status_values(self):
        """Test RouteStatus enum values"""
        assert RouteStatus.ACTIVE == "active"
        assert RouteStatus.PAUSED == "paused"
        assert RouteStatus.COMPLETED == "completed"
        assert RouteStatus.CANCELLED == "cancelled"


class TestLocationReportRequest:
    """Test LocationReportRequest model validation"""

    def test_location_report_creation_minimal(self):
        """Test creating location report with minimal required fields"""
        request = LocationReportRequest(
            device_id="device_123",
            latitude=37.7749,
            longitude=-122.4194,
            accuracy=10.0,
        )

        assert request.device_id == "device_123"
        assert request.latitude == 37.7749
        assert request.longitude == -122.4194
        assert request.accuracy == 10.0
        assert request.location_method == LocationMethod.GPS
        assert request.source == "device"
        assert request.metadata == {}

    def test_location_report_creation_with_all_fields(self):
        """Test creating location report with all fields"""
        now = datetime.now(timezone.utc)

        request = LocationReportRequest(
            device_id="device_456",
            latitude=40.7128,
            longitude=-74.0060,
            altitude=10.5,
            accuracy=5.0,
            heading=90.0,
            speed=15.5,
            address="123 Main St",
            city="New York",
            state="NY",
            country="USA",
            postal_code="10001",
            location_method=LocationMethod.HYBRID,
            battery_level=75.5,
            timestamp=now,
            source="mobile_app",
            metadata={"network": "5G", "carrier": "Verizon"},
        )

        assert request.device_id == "device_456"
        assert request.latitude == 40.7128
        assert request.longitude == -74.0060
        assert request.altitude == 10.5
        assert request.accuracy == 5.0
        assert request.heading == 90.0
        assert request.speed == 15.5
        assert request.address == "123 Main St"
        assert request.city == "New York"
        assert request.state == "NY"
        assert request.country == "USA"
        assert request.postal_code == "10001"
        assert request.location_method == LocationMethod.HYBRID
        assert request.battery_level == 75.5
        assert request.timestamp == now
        assert request.source == "mobile_app"
        assert request.metadata["network"] == "5G"

    def test_location_report_latitude_validation_min(self):
        """Test latitude validation fails for values less than -90"""
        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=-91.0,
                longitude=0.0,
                accuracy=10.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "latitude" for err in errors)

    def test_location_report_latitude_validation_max(self):
        """Test latitude validation fails for values greater than 90"""
        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=91.0,
                longitude=0.0,
                accuracy=10.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "latitude" for err in errors)

    def test_location_report_longitude_validation_min(self):
        """Test longitude validation fails for values less than -180"""
        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=0.0,
                longitude=-181.0,
                accuracy=10.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "longitude" for err in errors)

    def test_location_report_longitude_validation_max(self):
        """Test longitude validation fails for values greater than 180"""
        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=0.0,
                longitude=181.0,
                accuracy=10.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "longitude" for err in errors)

    def test_location_report_accuracy_validation(self):
        """Test accuracy validation fails for zero or negative values"""
        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=0.0,
                longitude=0.0,
                accuracy=0.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "accuracy" for err in errors)

        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=0.0,
                longitude=0.0,
                accuracy=-5.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "accuracy" for err in errors)

    def test_location_report_heading_validation(self):
        """Test heading validation for 0-359 range"""
        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=0.0,
                longitude=0.0,
                accuracy=10.0,
                heading=360.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "heading" for err in errors)

        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=0.0,
                longitude=0.0,
                accuracy=10.0,
                heading=-1.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "heading" for err in errors)

    def test_location_report_speed_validation(self):
        """Test speed validation fails for negative values"""
        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=0.0,
                longitude=0.0,
                accuracy=10.0,
                speed=-1.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "speed" for err in errors)

    def test_location_report_battery_level_validation(self):
        """Test battery level validation for 0-100 range"""
        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=0.0,
                longitude=0.0,
                accuracy=10.0,
                battery_level=101.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "battery_level" for err in errors)

        with pytest.raises(ValidationError) as exc_info:
            LocationReportRequest(
                device_id="device_123",
                latitude=0.0,
                longitude=0.0,
                accuracy=10.0,
                battery_level=-1.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "battery_level" for err in errors)

    def test_location_report_boundary_values(self):
        """Test boundary values for latitude and longitude"""
        # Test valid boundary values
        request = LocationReportRequest(
            device_id="device_123",
            latitude=-90.0,
            longitude=-180.0,
            accuracy=10.0,
        )
        assert request.latitude == -90.0
        assert request.longitude == -180.0

        request = LocationReportRequest(
            device_id="device_123",
            latitude=90.0,
            longitude=180.0,
            accuracy=10.0,
        )
        assert request.latitude == 90.0
        assert request.longitude == 180.0


class TestLocationBatchRequest:
    """Test LocationBatchRequest model validation"""

    def test_location_batch_creation(self):
        """Test creating batch location report"""
        locations = [
            LocationReportRequest(
                device_id="device_123",
                latitude=37.7749,
                longitude=-122.4194,
                accuracy=10.0,
            ),
            LocationReportRequest(
                device_id="device_123",
                latitude=37.7750,
                longitude=-122.4195,
                accuracy=10.0,
            ),
        ]

        batch = LocationBatchRequest(
            locations=locations,
            compression="gzip",
            batch_id="batch_123",
        )

        assert len(batch.locations) == 2
        assert batch.compression == "gzip"
        assert batch.batch_id == "batch_123"

    def test_location_batch_empty_validation(self):
        """Test batch validation fails for empty locations list"""
        with pytest.raises(ValidationError) as exc_info:
            LocationBatchRequest(locations=[])

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "locations" for err in errors)

    def test_location_batch_max_size_validation(self):
        """Test batch validation fails for too many locations"""
        locations = [
            LocationReportRequest(
                device_id="device_123",
                latitude=37.7749,
                longitude=-122.4194,
                accuracy=10.0,
            )
            for _ in range(1001)
        ]

        with pytest.raises(ValidationError) as exc_info:
            LocationBatchRequest(locations=locations)

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "locations" for err in errors)


class TestGeofenceCreateRequest:
    """Test GeofenceCreateRequest model validation"""

    def test_geofence_create_circle(self):
        """Test creating circular geofence"""
        request = GeofenceCreateRequest(
            name="Office Geofence",
            description="Main office location",
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=37.7749,
            center_lon=-122.4194,
            radius=100.0,
            trigger_on_enter=True,
            trigger_on_exit=True,
        )

        assert request.name == "Office Geofence"
        assert request.description == "Main office location"
        assert request.shape_type == GeofenceShapeType.CIRCLE
        assert request.center_lat == 37.7749
        assert request.center_lon == -122.4194
        assert request.radius == 100.0
        assert request.trigger_on_enter is True
        assert request.trigger_on_exit is True
        assert request.trigger_on_dwell is False

    def test_geofence_create_polygon(self):
        """Test creating polygon geofence"""
        coordinates = [
            (37.7749, -122.4194),
            (37.7750, -122.4195),
            (37.7751, -122.4193),
            (37.7749, -122.4194),
        ]

        request = GeofenceCreateRequest(
            name="Campus Geofence",
            shape_type=GeofenceShapeType.POLYGON,
            center_lat=37.7750,
            center_lon=-122.4194,
            polygon_coordinates=coordinates,
            trigger_on_enter=True,
            trigger_on_exit=False,
        )

        assert request.name == "Campus Geofence"
        assert request.shape_type == GeofenceShapeType.POLYGON
        assert len(request.polygon_coordinates) == 4
        assert request.trigger_on_enter is True
        assert request.trigger_on_exit is False

    def test_geofence_polygon_validation_insufficient_coordinates(self):
        """Test polygon validation fails with less than 3 coordinates"""
        coordinates = [
            (37.7749, -122.4194),
            (37.7750, -122.4195),
        ]

        with pytest.raises(ValidationError) as exc_info:
            GeofenceCreateRequest(
                name="Invalid Polygon",
                shape_type=GeofenceShapeType.POLYGON,
                center_lat=37.7750,
                center_lon=-122.4194,
                polygon_coordinates=coordinates,
            )

        errors = exc_info.value.errors()
        assert any("polygon" in str(err).lower() for err in errors)

    def test_geofence_create_with_dwell(self):
        """Test creating geofence with dwell trigger"""
        request = GeofenceCreateRequest(
            name="Store Geofence",
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=37.7749,
            center_lon=-122.4194,
            radius=50.0,
            trigger_on_enter=False,
            trigger_on_exit=False,
            trigger_on_dwell=True,
            dwell_time_seconds=300,
        )

        assert request.trigger_on_dwell is True
        assert request.dwell_time_seconds == 300

    def test_geofence_create_with_targets(self):
        """Test creating geofence with target devices and groups"""
        request = GeofenceCreateRequest(
            name="Fleet Geofence",
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=37.7749,
            center_lon=-122.4194,
            radius=200.0,
            target_devices=["device_001", "device_002"],
            target_groups=["fleet_a", "fleet_b"],
        )

        assert len(request.target_devices) == 2
        assert len(request.target_groups) == 2
        assert "device_001" in request.target_devices
        assert "fleet_a" in request.target_groups

    def test_geofence_create_with_time_restrictions(self):
        """Test creating geofence with time restrictions"""
        request = GeofenceCreateRequest(
            name="Business Hours Geofence",
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=37.7749,
            center_lon=-122.4194,
            radius=100.0,
            active_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
            active_hours={"start": "09:00", "end": "18:00"},
        )

        assert len(request.active_days) == 5
        assert request.active_hours["start"] == "09:00"
        assert request.active_hours["end"] == "18:00"

    def test_geofence_create_with_notifications(self):
        """Test creating geofence with notification configuration"""
        request = GeofenceCreateRequest(
            name="Alert Geofence",
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=37.7749,
            center_lon=-122.4194,
            radius=100.0,
            notification_channels=["email", "sms", "push"],
            notification_template="geofence_alert_template",
        )

        assert len(request.notification_channels) == 3
        assert "email" in request.notification_channels
        assert request.notification_template == "geofence_alert_template"

    def test_geofence_center_lat_validation(self):
        """Test geofence center latitude validation"""
        with pytest.raises(ValidationError) as exc_info:
            GeofenceCreateRequest(
                name="Invalid Geofence",
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=91.0,
                center_lon=0.0,
                radius=100.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "center_lat" for err in errors)

    def test_geofence_center_lon_validation(self):
        """Test geofence center longitude validation"""
        with pytest.raises(ValidationError) as exc_info:
            GeofenceCreateRequest(
                name="Invalid Geofence",
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=0.0,
                center_lon=181.0,
                radius=100.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "center_lon" for err in errors)

    def test_geofence_radius_validation(self):
        """Test geofence radius validation fails for zero or negative values"""
        with pytest.raises(ValidationError) as exc_info:
            GeofenceCreateRequest(
                name="Invalid Geofence",
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=0.0,
                center_lon=0.0,
                radius=0.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "radius" for err in errors)


class TestGeofenceUpdateRequest:
    """Test GeofenceUpdateRequest model validation"""

    def test_geofence_update_partial(self):
        """Test partial geofence update"""
        request = GeofenceUpdateRequest(
            name="Updated Geofence Name",
            description="Updated description",
        )

        assert request.name == "Updated Geofence Name"
        assert request.description == "Updated description"
        assert request.trigger_on_enter is None
        assert request.target_devices is None

    def test_geofence_update_triggers(self):
        """Test updating geofence triggers"""
        request = GeofenceUpdateRequest(
            trigger_on_enter=False,
            trigger_on_exit=True,
            trigger_on_dwell=True,
            dwell_time_seconds=600,
        )

        assert request.trigger_on_enter is False
        assert request.trigger_on_exit is True
        assert request.trigger_on_dwell is True
        assert request.dwell_time_seconds == 600

    def test_geofence_update_targets(self):
        """Test updating geofence targets"""
        request = GeofenceUpdateRequest(
            target_devices=["device_003", "device_004"],
            target_groups=["group_c"],
        )

        assert len(request.target_devices) == 2
        assert len(request.target_groups) == 1


class TestPlaceCreateRequest:
    """Test PlaceCreateRequest model validation"""

    def test_place_create_minimal(self):
        """Test creating place with minimal fields"""
        request = PlaceCreateRequest(
            name="Home",
            category=PlaceCategory.HOME,
            latitude=37.7749,
            longitude=-122.4194,
        )

        assert request.name == "Home"
        assert request.category == PlaceCategory.HOME
        assert request.latitude == 37.7749
        assert request.longitude == -122.4194
        assert request.radius == 100.0

    def test_place_create_with_all_fields(self):
        """Test creating place with all fields"""
        request = PlaceCreateRequest(
            name="Office",
            category=PlaceCategory.WORK,
            latitude=37.7749,
            longitude=-122.4194,
            address="123 Market St, San Francisco, CA",
            radius=150.0,
            icon="office",
            color="#0000FF",
            tags=["work", "primary"],
        )

        assert request.name == "Office"
        assert request.category == PlaceCategory.WORK
        assert request.address == "123 Market St, San Francisco, CA"
        assert request.radius == 150.0
        assert request.icon == "office"
        assert request.color == "#0000FF"
        assert len(request.tags) == 2

    def test_place_latitude_validation(self):
        """Test place latitude validation"""
        with pytest.raises(ValidationError) as exc_info:
            PlaceCreateRequest(
                name="Invalid Place",
                category=PlaceCategory.HOME,
                latitude=91.0,
                longitude=0.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "latitude" for err in errors)

    def test_place_longitude_validation(self):
        """Test place longitude validation"""
        with pytest.raises(ValidationError) as exc_info:
            PlaceCreateRequest(
                name="Invalid Place",
                category=PlaceCategory.HOME,
                latitude=0.0,
                longitude=181.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "longitude" for err in errors)

    def test_place_radius_validation(self):
        """Test place radius validation for positive values and max limit"""
        with pytest.raises(ValidationError) as exc_info:
            PlaceCreateRequest(
                name="Invalid Place",
                category=PlaceCategory.HOME,
                latitude=0.0,
                longitude=0.0,
                radius=0.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "radius" for err in errors)

        with pytest.raises(ValidationError) as exc_info:
            PlaceCreateRequest(
                name="Invalid Place",
                category=PlaceCategory.HOME,
                latitude=0.0,
                longitude=0.0,
                radius=1001.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "radius" for err in errors)


class TestPlaceUpdateRequest:
    """Test PlaceUpdateRequest model validation"""

    def test_place_update_partial(self):
        """Test partial place update"""
        request = PlaceUpdateRequest(
            name="Updated Home",
            address="New Address",
        )

        assert request.name == "Updated Home"
        assert request.address == "New Address"
        assert request.category is None
        assert request.latitude is None

    def test_place_update_location(self):
        """Test updating place location"""
        request = PlaceUpdateRequest(
            latitude=37.7750,
            longitude=-122.4195,
            radius=200.0,
        )

        assert request.latitude == 37.7750
        assert request.longitude == -122.4195
        assert request.radius == 200.0


class TestRouteStartRequest:
    """Test RouteStartRequest model validation"""

    def test_route_start_minimal(self):
        """Test starting route with minimal fields"""
        start_location = LocationReportRequest(
            device_id="device_123",
            latitude=37.7749,
            longitude=-122.4194,
            accuracy=10.0,
        )

        request = RouteStartRequest(
            device_id="device_123",
            start_location=start_location,
        )

        assert request.device_id == "device_123"
        assert request.start_location.latitude == 37.7749
        assert request.name is None

    def test_route_start_with_name(self):
        """Test starting route with name"""
        start_location = LocationReportRequest(
            device_id="device_123",
            latitude=37.7749,
            longitude=-122.4194,
            accuracy=10.0,
        )

        request = RouteStartRequest(
            device_id="device_123",
            name="Morning Commute",
            start_location=start_location,
        )

        assert request.name == "Morning Commute"


class TestNearbySearchRequest:
    """Test NearbySearchRequest model validation"""

    def test_nearby_search_minimal(self):
        """Test nearby search with minimal fields"""
        request = NearbySearchRequest(
            latitude=37.7749,
            longitude=-122.4194,
            radius_meters=1000.0,
        )

        assert request.latitude == 37.7749
        assert request.longitude == -122.4194
        assert request.radius_meters == 1000.0
        assert request.time_window_minutes == 30
        assert request.limit == 50

    def test_nearby_search_with_filters(self):
        """Test nearby search with filters"""
        request = NearbySearchRequest(
            latitude=37.7749,
            longitude=-122.4194,
            radius_meters=5000.0,
            device_types=["mobile", "tablet"],
            time_window_minutes=60,
            limit=100,
        )

        assert request.radius_meters == 5000.0
        assert len(request.device_types) == 2
        assert request.time_window_minutes == 60
        assert request.limit == 100

    def test_nearby_search_latitude_validation(self):
        """Test nearby search latitude validation"""
        with pytest.raises(ValidationError) as exc_info:
            NearbySearchRequest(
                latitude=91.0,
                longitude=0.0,
                radius_meters=1000.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "latitude" for err in errors)

    def test_nearby_search_radius_validation(self):
        """Test nearby search radius validation for max 50km"""
        with pytest.raises(ValidationError) as exc_info:
            NearbySearchRequest(
                latitude=0.0,
                longitude=0.0,
                radius_meters=50001.0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "radius_meters" for err in errors)

    def test_nearby_search_time_window_validation(self):
        """Test time window validation for 1-1440 minute range"""
        with pytest.raises(ValidationError) as exc_info:
            NearbySearchRequest(
                latitude=0.0,
                longitude=0.0,
                radius_meters=1000.0,
                time_window_minutes=0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "time_window_minutes" for err in errors)

        with pytest.raises(ValidationError) as exc_info:
            NearbySearchRequest(
                latitude=0.0,
                longitude=0.0,
                radius_meters=1000.0,
                time_window_minutes=1441,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "time_window_minutes" for err in errors)

    def test_nearby_search_limit_validation(self):
        """Test limit validation for 1-500 range"""
        with pytest.raises(ValidationError) as exc_info:
            NearbySearchRequest(
                latitude=0.0,
                longitude=0.0,
                radius_meters=1000.0,
                limit=0,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "limit" for err in errors)

        with pytest.raises(ValidationError) as exc_info:
            NearbySearchRequest(
                latitude=0.0,
                longitude=0.0,
                radius_meters=1000.0,
                limit=501,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "limit" for err in errors)


class TestRadiusSearchRequest:
    """Test RadiusSearchRequest model validation"""

    def test_radius_search_creation(self):
        """Test radius search request creation"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        request = RadiusSearchRequest(
            center_lat=37.7749,
            center_lon=-122.4194,
            radius_meters=10000.0,
            start_time=now,
            end_time=future,
            device_ids=["device_001", "device_002"],
            limit=100,
        )

        assert request.center_lat == 37.7749
        assert request.center_lon == -122.4194
        assert request.radius_meters == 10000.0
        assert request.start_time == now
        assert request.end_time == future
        assert len(request.device_ids) == 2
        assert request.limit == 100

    def test_radius_search_max_radius_validation(self):
        """Test radius search max radius validation (100km)"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            RadiusSearchRequest(
                center_lat=0.0,
                center_lon=0.0,
                radius_meters=100001.0,
                start_time=now,
                end_time=future,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "radius_meters" for err in errors)


class TestPolygonSearchRequest:
    """Test PolygonSearchRequest model validation"""

    def test_polygon_search_creation(self):
        """Test polygon search request creation"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        coordinates = [
            (37.7749, -122.4194),
            (37.7750, -122.4195),
            (37.7751, -122.4193),
            (37.7749, -122.4194),
        ]

        request = PolygonSearchRequest(
            polygon_coordinates=coordinates,
            start_time=now,
            end_time=future,
            device_ids=["device_001"],
            limit=200,
        )

        assert len(request.polygon_coordinates) == 4
        assert request.start_time == now
        assert request.end_time == future
        assert request.limit == 200

    def test_polygon_search_min_coordinates_validation(self):
        """Test polygon search requires at least 3 coordinates"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        coordinates = [
            (37.7749, -122.4194),
            (37.7750, -122.4195),
        ]

        with pytest.raises(ValidationError) as exc_info:
            PolygonSearchRequest(
                polygon_coordinates=coordinates,
                start_time=now,
                end_time=future,
            )

        errors = exc_info.value.errors()
        assert any(err["loc"][0] == "polygon_coordinates" for err in errors)


class TestLocationResponse:
    """Test LocationResponse model"""

    def test_location_response_creation(self):
        """Test creating location response"""
        now = datetime.now(timezone.utc)

        response = LocationResponse(
            location_id="loc_123",
            device_id="device_456",
            user_id="user_789",
            latitude=37.7749,
            longitude=-122.4194,
            altitude=10.5,
            accuracy=5.0,
            heading=90.0,
            speed=15.5,
            address="123 Main St",
            city="San Francisco",
            state="CA",
            country="USA",
            postal_code="94102",
            location_method=LocationMethod.GPS,
            battery_level=75.5,
            source="mobile_app",
            metadata={"network": "5G"},
            timestamp=now,
            created_at=now,
        )

        assert response.location_id == "loc_123"
        assert response.device_id == "device_456"
        assert response.user_id == "user_789"
        assert response.latitude == 37.7749
        assert response.longitude == -122.4194
        assert response.location_method == LocationMethod.GPS
        assert response.battery_level == 75.5


class TestGeofenceResponse:
    """Test GeofenceResponse model"""

    def test_geofence_response_creation(self):
        """Test creating geofence response"""
        now = datetime.now(timezone.utc)

        response = GeofenceResponse(
            geofence_id="geo_123",
            name="Office Geofence",
            description="Main office",
            user_id="user_456",
            organization_id="org_789",
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=37.7749,
            center_lon=-122.4194,
            radius=100.0,
            polygon_coordinates=None,
            active=True,
            trigger_on_enter=True,
            trigger_on_exit=True,
            trigger_on_dwell=False,
            dwell_time_seconds=None,
            target_devices=["device_001"],
            target_groups=["group_a"],
            active_days=["monday", "tuesday"],
            active_hours={"start": "09:00", "end": "18:00"},
            notification_channels=["email", "push"],
            notification_template="alert_template",
            total_triggers=42,
            last_triggered=now,
            created_at=now,
            updated_at=now,
            tags=["important"],
            metadata={"priority": "high"},
        )

        assert response.geofence_id == "geo_123"
        assert response.name == "Office Geofence"
        assert response.shape_type == GeofenceShapeType.CIRCLE
        assert response.radius == 100.0
        assert response.active is True
        assert response.total_triggers == 42


class TestLocationEventResponse:
    """Test LocationEventResponse model"""

    def test_location_event_response_creation(self):
        """Test creating location event response"""
        now = datetime.now(timezone.utc)

        location = LocationResponse(
            location_id="loc_123",
            device_id="device_456",
            user_id="user_789",
            latitude=37.7749,
            longitude=-122.4194,
            altitude=None,
            accuracy=10.0,
            heading=None,
            speed=None,
            address=None,
            city=None,
            state=None,
            country=None,
            postal_code=None,
            location_method=LocationMethod.GPS,
            battery_level=None,
            source="device",
            metadata={},
            timestamp=now,
            created_at=now,
        )

        event = LocationEventResponse(
            event_id="evt_123",
            event_type=LocationEventType.GEOFENCE_ENTER,
            device_id="device_456",
            user_id="user_789",
            location=location,
            geofence_id="geo_123",
            geofence_name="Office",
            distance_from_last=100.5,
            time_from_last=60.0,
            estimated_speed=1.67,
            trigger_reason="entered_geofence",
            metadata={"confidence": "high"},
            timestamp=now,
            processed=True,
            created_at=now,
        )

        assert event.event_id == "evt_123"
        assert event.event_type == LocationEventType.GEOFENCE_ENTER
        assert event.geofence_name == "Office"
        assert event.processed is True


class TestPlaceResponse:
    """Test PlaceResponse model"""

    def test_place_response_creation(self):
        """Test creating place response"""
        now = datetime.now(timezone.utc)

        response = PlaceResponse(
            place_id="place_123",
            user_id="user_456",
            name="Home",
            category=PlaceCategory.HOME,
            latitude=37.7749,
            longitude=-122.4194,
            address="123 Main St",
            radius=100.0,
            icon="home",
            color="#FF0000",
            visit_count=42,
            total_time_spent=3600,
            last_visit=now,
            created_at=now,
            updated_at=now,
            tags=["primary"],
        )

        assert response.place_id == "place_123"
        assert response.name == "Home"
        assert response.category == PlaceCategory.HOME
        assert response.visit_count == 42
        assert response.total_time_spent == 3600


class TestRouteResponse:
    """Test RouteResponse model"""

    def test_route_response_creation(self):
        """Test creating route response"""
        now = datetime.now(timezone.utc)

        start_location = LocationResponse(
            location_id="loc_start",
            device_id="device_456",
            user_id="user_789",
            latitude=37.7749,
            longitude=-122.4194,
            altitude=None,
            accuracy=10.0,
            heading=None,
            speed=None,
            address=None,
            city=None,
            state=None,
            country=None,
            postal_code=None,
            location_method=LocationMethod.GPS,
            battery_level=None,
            source="device",
            metadata={},
            timestamp=now,
            created_at=now,
        )

        end_location = LocationResponse(
            location_id="loc_end",
            device_id="device_456",
            user_id="user_789",
            latitude=37.7850,
            longitude=-122.4294,
            altitude=None,
            accuracy=10.0,
            heading=None,
            speed=None,
            address=None,
            city=None,
            state=None,
            country=None,
            postal_code=None,
            location_method=LocationMethod.GPS,
            battery_level=None,
            source="device",
            metadata={},
            timestamp=now + timedelta(hours=1),
            created_at=now + timedelta(hours=1),
        )

        response = RouteResponse(
            route_id="route_123",
            device_id="device_456",
            user_id="user_789",
            name="Morning Commute",
            status=RouteStatus.COMPLETED,
            start_location=start_location,
            end_location=end_location,
            waypoint_count=10,
            total_distance=5000.0,
            total_duration=3600.0,
            avg_speed=1.38,
            max_speed=5.0,
            started_at=now,
            ended_at=now + timedelta(hours=1),
            created_at=now,
        )

        assert response.route_id == "route_123"
        assert response.name == "Morning Commute"
        assert response.status == RouteStatus.COMPLETED
        assert response.waypoint_count == 10
        assert response.total_distance == 5000.0


class TestDeviceLocationResponse:
    """Test DeviceLocationResponse model"""

    def test_device_location_response_creation(self):
        """Test creating device location response for nearby search"""
        now = datetime.now(timezone.utc)

        response = DeviceLocationResponse(
            device_id="device_123",
            device_name="iPhone 14",
            device_type="mobile",
            user_id="user_456",
            latitude=37.7749,
            longitude=-122.4194,
            timestamp=now,
            accuracy=10.0,
            distance=500.0,
            status="online",
        )

        assert response.device_id == "device_123"
        assert response.device_name == "iPhone 14"
        assert response.device_type == "mobile"
        assert response.distance == 500.0
        assert response.status == "online"


class TestLocationStatsResponse:
    """Test LocationStatsResponse model"""

    def test_location_stats_response_creation(self):
        """Test creating location stats response"""
        response = LocationStatsResponse(
            total_locations=10000,
            active_devices=50,
            total_geofences=25,
            active_geofences=20,
            total_places=100,
            total_routes=500,
            last_24h_locations=1000,
            last_24h_events=150,
            last_24h_geofence_triggers=75,
            devices_by_type={"mobile": 30, "tablet": 15, "vehicle": 5},
            top_geofences=[
                {"geofence_id": "geo_1", "name": "Office", "triggers": 100},
                {"geofence_id": "geo_2", "name": "Home", "triggers": 80},
            ],
        )

        assert response.total_locations == 10000
        assert response.active_devices == 50
        assert response.total_geofences == 25
        assert response.last_24h_locations == 1000
        assert len(response.top_geofences) == 2
        assert response.devices_by_type["mobile"] == 30


class TestGeofenceStatsResponse:
    """Test GeofenceStatsResponse model"""

    def test_geofence_stats_response_creation(self):
        """Test creating geofence stats response"""
        now = datetime.now(timezone.utc)

        response = GeofenceStatsResponse(
            geofence_id="geo_123",
            geofence_name="Office",
            total_triggers=100,
            enter_count=50,
            exit_count=48,
            dwell_count=2,
            unique_devices=10,
            avg_dwell_time=1800.0,
            last_triggered=now,
            recent_devices=[
                {"device_id": "device_001", "trigger_type": "enter", "timestamp": now},
                {"device_id": "device_002", "trigger_type": "exit", "timestamp": now},
            ],
        )

        assert response.geofence_id == "geo_123"
        assert response.geofence_name == "Office"
        assert response.total_triggers == 100
        assert response.enter_count == 50
        assert response.exit_count == 48
        assert response.unique_devices == 10


class TestDistanceResponse:
    """Test DistanceResponse model"""

    def test_distance_response_creation(self):
        """Test creating distance response"""
        response = DistanceResponse(
            from_lat=37.7749,
            from_lon=-122.4194,
            to_lat=37.7849,
            to_lon=-122.4294,
            distance_meters=1500.0,
            distance_km=1.5,
        )

        assert response.from_lat == 37.7749
        assert response.from_lon == -122.4194
        assert response.to_lat == 37.7849
        assert response.to_lon == -122.4294
        assert response.distance_meters == 1500.0
        assert response.distance_km == 1.5


class TestHeatmapDataResponse:
    """Test HeatmapDataResponse model"""

    def test_heatmap_data_response_creation(self):
        """Test creating heatmap data response"""
        points = [
            {"lat": 37.7749, "lon": -122.4194, "weight": 10},
            {"lat": 37.7750, "lon": -122.4195, "weight": 5},
            {"lat": 37.7751, "lon": -122.4196, "weight": 8},
        ]
        bounds = {
            "min_lat": 37.7749,
            "max_lat": 37.7751,
            "min_lon": -122.4196,
            "max_lon": -122.4194,
        }

        response = HeatmapDataResponse(
            points=points,
            bounds=bounds,
            total_points=3,
        )

        assert len(response.points) == 3
        assert response.bounds["min_lat"] == 37.7749
        assert response.total_points == 3


class TestLocationListResponse:
    """Test LocationListResponse model"""

    def test_location_list_response_creation(self):
        """Test creating location list response"""
        now = datetime.now(timezone.utc)

        locations = [
            LocationResponse(
                location_id=f"loc_{i}",
                device_id="device_123",
                user_id="user_456",
                latitude=37.7749 + i * 0.001,
                longitude=-122.4194 + i * 0.001,
                altitude=None,
                accuracy=10.0,
                heading=None,
                speed=None,
                address=None,
                city=None,
                state=None,
                country=None,
                postal_code=None,
                location_method=LocationMethod.GPS,
                battery_level=None,
                source="device",
                metadata={},
                timestamp=now,
                created_at=now,
            )
            for i in range(3)
        ]

        response = LocationListResponse(
            locations=locations,
            count=3,
            limit=100,
            offset=0,
        )

        assert len(response.locations) == 3
        assert response.count == 3
        assert response.limit == 100
        assert response.offset == 0


class TestGeofenceListResponse:
    """Test GeofenceListResponse model"""

    def test_geofence_list_response_creation(self):
        """Test creating geofence list response"""
        now = datetime.now(timezone.utc)

        geofences = [
            GeofenceResponse(
                geofence_id=f"geo_{i}",
                name=f"Geofence {i}",
                description=None,
                user_id="user_456",
                organization_id=None,
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=37.7749,
                center_lon=-122.4194,
                radius=100.0,
                polygon_coordinates=None,
                active=True,
                trigger_on_enter=True,
                trigger_on_exit=True,
                trigger_on_dwell=False,
                dwell_time_seconds=None,
                target_devices=[],
                target_groups=[],
                active_days=None,
                active_hours=None,
                notification_channels=[],
                notification_template=None,
                total_triggers=0,
                last_triggered=None,
                created_at=now,
                updated_at=now,
                tags=[],
                metadata={},
            )
            for i in range(2)
        ]

        response = GeofenceListResponse(
            geofences=geofences,
            count=2,
            limit=100,
            offset=0,
        )

        assert len(response.geofences) == 2
        assert response.count == 2


class TestPlaceListResponse:
    """Test PlaceListResponse model"""

    def test_place_list_response_creation(self):
        """Test creating place list response"""
        now = datetime.now(timezone.utc)

        places = [
            PlaceResponse(
                place_id=f"place_{i}",
                user_id="user_456",
                name=f"Place {i}",
                category=PlaceCategory.FAVORITE,
                latitude=37.7749,
                longitude=-122.4194,
                address=None,
                radius=100.0,
                icon=None,
                color=None,
                visit_count=0,
                total_time_spent=0,
                last_visit=None,
                created_at=now,
                updated_at=now,
                tags=[],
            )
            for i in range(3)
        ]

        response = PlaceListResponse(
            places=places,
            count=3,
        )

        assert len(response.places) == 3
        assert response.count == 3


class TestRouteListResponse:
    """Test RouteListResponse model"""

    def test_route_list_response_creation(self):
        """Test creating route list response"""
        now = datetime.now(timezone.utc)

        start_location = LocationResponse(
            location_id="loc_start",
            device_id="device_456",
            user_id="user_789",
            latitude=37.7749,
            longitude=-122.4194,
            altitude=None,
            accuracy=10.0,
            heading=None,
            speed=None,
            address=None,
            city=None,
            state=None,
            country=None,
            postal_code=None,
            location_method=LocationMethod.GPS,
            battery_level=None,
            source="device",
            metadata={},
            timestamp=now,
            created_at=now,
        )

        routes = [
            RouteResponse(
                route_id=f"route_{i}",
                device_id="device_456",
                user_id="user_789",
                name=f"Route {i}",
                status=RouteStatus.COMPLETED,
                start_location=start_location,
                end_location=None,
                waypoint_count=5,
                total_distance=None,
                total_duration=None,
                avg_speed=None,
                max_speed=None,
                started_at=now,
                ended_at=None,
                created_at=now,
            )
            for i in range(2)
        ]

        response = RouteListResponse(
            routes=routes,
            count=2,
            limit=100,
            offset=0,
        )

        assert len(response.routes) == 2
        assert response.count == 2


class TestLocationEventListResponse:
    """Test LocationEventListResponse model"""

    def test_location_event_list_response_creation(self):
        """Test creating location event list response"""
        now = datetime.now(timezone.utc)

        location = LocationResponse(
            location_id="loc_123",
            device_id="device_456",
            user_id="user_789",
            latitude=37.7749,
            longitude=-122.4194,
            altitude=None,
            accuracy=10.0,
            heading=None,
            speed=None,
            address=None,
            city=None,
            state=None,
            country=None,
            postal_code=None,
            location_method=LocationMethod.GPS,
            battery_level=None,
            source="device",
            metadata={},
            timestamp=now,
            created_at=now,
        )

        events = [
            LocationEventResponse(
                event_id=f"evt_{i}",
                event_type=LocationEventType.LOCATION_UPDATE,
                device_id="device_456",
                user_id="user_789",
                location=location,
                geofence_id=None,
                geofence_name=None,
                distance_from_last=None,
                time_from_last=None,
                estimated_speed=None,
                trigger_reason=None,
                metadata={},
                timestamp=now,
                processed=False,
                created_at=now,
            )
            for i in range(2)
        ]

        response = LocationEventListResponse(
            events=events,
            count=2,
            limit=100,
            offset=0,
        )

        assert len(response.events) == 2
        assert response.count == 2


class TestLocationServiceStatus:
    """Test LocationServiceStatus model"""

    def test_location_service_status_creation(self):
        """Test creating location service status"""
        now = datetime.now(timezone.utc)

        status = LocationServiceStatus(
            service="location_service",
            status="healthy",
            version="1.0.0",
            database_connected=True,
            cache_connected=True,
            geofencing_enabled=True,
            route_tracking_enabled=True,
            timestamp=now,
        )

        assert status.service == "location_service"
        assert status.status == "healthy"
        assert status.version == "1.0.0"
        assert status.database_connected is True
        assert status.geofencing_enabled is True


class TestLocationOperationResult:
    """Test LocationOperationResult model"""

    def test_location_operation_result_success(self):
        """Test successful location operation result"""
        result = LocationOperationResult(
            success=True,
            location_id="loc_123",
            operation="create_location",
            message="Location created successfully",
            data={"latitude": 37.7749, "longitude": -122.4194},
            affected_count=1,
        )

        assert result.success is True
        assert result.location_id == "loc_123"
        assert result.operation == "create_location"
        assert result.affected_count == 1

    def test_location_operation_result_failure(self):
        """Test failed location operation result"""
        result = LocationOperationResult(
            success=False,
            operation="delete_location",
            message="Location not found",
            affected_count=0,
        )

        assert result.success is False
        assert result.operation == "delete_location"
        assert result.location_id is None
        assert result.affected_count == 0

    def test_location_operation_result_geofence(self):
        """Test geofence operation result"""
        result = LocationOperationResult(
            success=True,
            geofence_id="geo_123",
            operation="create_geofence",
            message="Geofence created successfully",
            affected_count=1,
        )

        assert result.success is True
        assert result.geofence_id == "geo_123"
        assert result.operation == "create_geofence"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
