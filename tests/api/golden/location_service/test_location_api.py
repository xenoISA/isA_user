"""
API Golden Tests: Location Service

Contract-based API tests validating request/response schemas.
All test data generated through LocationTestDataFactory - zero hardcoded data.

Service: location_service
Port: 8224
"""

import pytest
import httpx
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import os
from pydantic import ValidationError

# Test data factory
import sys
sys.path.insert(0, str(__file__).split('/tests/')[0])

from tests.contracts.location.data_contract import (
    LocationTestDataFactory,
    LocationMethod,
    GeofenceShapeType,
    PlaceCategory,
    RouteStatus,
    # Request contracts
    LocationReportRequestContract,
    LocationBatchRequestContract,
    GeofenceCreateRequestContract,
    GeofenceUpdateRequestContract,
    PlaceCreateRequestContract,
    PlaceUpdateRequestContract,
    NearbySearchRequestContract,
    RadiusSearchRequestContract,
    DistanceRequestContract,
    # Response contracts
    LocationResponseContract,
    GeofenceResponseContract,
    PlaceResponseContract,
    LocationOperationResultContract,
    DistanceResponseContract,
    NearbyDeviceResponseContract,
    LocationListResponseContract,
    GeofenceListResponseContract,
    PlaceListResponseContract,
    ErrorResponseContract,
    # Builders
    LocationReportRequestBuilder,
    GeofenceCreateRequestBuilder,
    PlaceCreateRequestBuilder,
)


# =============================================================================
# CONFIGURATION
# =============================================================================


LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL", "http://localhost:8224")
TEST_TIMEOUT = 30.0

# Mark all tests as API tests
pytestmark = pytest.mark.api


# =============================================================================
# REQUEST CONTRACT VALIDATION TESTS
# =============================================================================


class TestLocationReportRequestContract:
    """Test LocationReportRequest contract validation"""

    def test_valid_minimal_request(self):
        """Test valid request with minimal fields"""
        request = LocationReportRequestContract(
            device_id=LocationTestDataFactory.make_device_id(),
            latitude=LocationTestDataFactory.make_latitude(),
            longitude=LocationTestDataFactory.make_longitude(),
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert request.device_id is not None
        assert -90 <= request.latitude <= 90
        assert -180 <= request.longitude <= 180
        assert request.accuracy > 0

    def test_valid_full_request(self):
        """Test valid request with all fields"""
        now = datetime.now(timezone.utc)
        request = LocationReportRequestContract(
            device_id=LocationTestDataFactory.make_device_id(),
            latitude=LocationTestDataFactory.make_latitude(),
            longitude=LocationTestDataFactory.make_longitude(),
            accuracy=LocationTestDataFactory.make_accuracy(),
            altitude=LocationTestDataFactory.make_altitude(),
            heading=LocationTestDataFactory.make_heading(),
            speed=LocationTestDataFactory.make_speed(),
            address=LocationTestDataFactory.make_address(),
            city=LocationTestDataFactory.make_city(),
            state=LocationTestDataFactory.make_state(),
            country=LocationTestDataFactory.make_country(),
            postal_code=LocationTestDataFactory.make_postal_code(),
            location_method=LocationMethod.GPS,
            battery_level=LocationTestDataFactory.make_battery_level(),
            timestamp=now,
            source="mobile_app",
            metadata={"test": "value"},
        )
        assert request.altitude is not None
        assert request.heading is not None
        assert request.timestamp == now

    def test_invalid_latitude_too_low(self):
        """Test invalid latitude below -90"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_invalid_latitude_too_low(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_accuracy(),
            )

    def test_invalid_latitude_too_high(self):
        """Test invalid latitude above 90"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_invalid_latitude_too_high(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_accuracy(),
            )

    def test_invalid_longitude_too_low(self):
        """Test invalid longitude below -180"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_invalid_longitude_too_low(),
                accuracy=LocationTestDataFactory.make_accuracy(),
            )

    def test_invalid_longitude_too_high(self):
        """Test invalid longitude above 180"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_invalid_longitude_too_high(),
                accuracy=LocationTestDataFactory.make_accuracy(),
            )

    def test_invalid_accuracy_zero(self):
        """Test invalid zero accuracy"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_invalid_accuracy_zero(),
            )

    def test_invalid_accuracy_negative(self):
        """Test invalid negative accuracy"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_invalid_accuracy_negative(),
            )

    def test_invalid_heading_negative(self):
        """Test invalid negative heading"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_accuracy(),
                heading=LocationTestDataFactory.make_invalid_heading_negative(),
            )

    def test_invalid_heading_too_high(self):
        """Test invalid heading >= 360"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_accuracy(),
                heading=LocationTestDataFactory.make_invalid_heading_too_high(),
            )

    def test_invalid_battery_negative(self):
        """Test invalid negative battery"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_accuracy(),
                battery_level=LocationTestDataFactory.make_invalid_battery_negative(),
            )

    def test_invalid_battery_too_high(self):
        """Test invalid battery > 100"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_device_id(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_accuracy(),
                battery_level=LocationTestDataFactory.make_invalid_battery_too_high(),
            )

    def test_invalid_device_id_empty(self):
        """Test invalid empty device ID"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_invalid_device_id_empty(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_accuracy(),
            )

    def test_invalid_device_id_whitespace(self):
        """Test invalid whitespace device ID"""
        with pytest.raises(ValidationError):
            LocationReportRequestContract(
                device_id=LocationTestDataFactory.make_invalid_device_id_whitespace(),
                latitude=LocationTestDataFactory.make_latitude(),
                longitude=LocationTestDataFactory.make_longitude(),
                accuracy=LocationTestDataFactory.make_accuracy(),
            )

    def test_boundary_latitude_min(self):
        """Test boundary latitude -90"""
        request = LocationReportRequestContract(
            device_id=LocationTestDataFactory.make_device_id(),
            latitude=LocationTestDataFactory.make_boundary_latitude_min(),
            longitude=LocationTestDataFactory.make_longitude(),
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert request.latitude == -90.0

    def test_boundary_latitude_max(self):
        """Test boundary latitude 90"""
        request = LocationReportRequestContract(
            device_id=LocationTestDataFactory.make_device_id(),
            latitude=LocationTestDataFactory.make_boundary_latitude_max(),
            longitude=LocationTestDataFactory.make_longitude(),
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert request.latitude == 90.0

    def test_boundary_longitude_min(self):
        """Test boundary longitude -180"""
        request = LocationReportRequestContract(
            device_id=LocationTestDataFactory.make_device_id(),
            latitude=LocationTestDataFactory.make_latitude(),
            longitude=LocationTestDataFactory.make_boundary_longitude_min(),
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert request.longitude == -180.0

    def test_boundary_longitude_max(self):
        """Test boundary longitude 180"""
        request = LocationReportRequestContract(
            device_id=LocationTestDataFactory.make_device_id(),
            latitude=LocationTestDataFactory.make_latitude(),
            longitude=LocationTestDataFactory.make_boundary_longitude_max(),
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert request.longitude == 180.0


class TestLocationBatchRequestContract:
    """Test LocationBatchRequest contract validation"""

    def test_valid_batch_request(self):
        """Test valid batch request"""
        locations = [
            LocationTestDataFactory.make_location_report_request()
            for _ in range(5)
        ]
        batch = LocationBatchRequestContract(
            locations=locations,
            batch_id=LocationTestDataFactory.make_uuid(),
        )
        assert len(batch.locations) == 5

    def test_invalid_empty_batch(self):
        """Test invalid empty batch"""
        with pytest.raises(ValidationError):
            LocationBatchRequestContract(locations=[])

    def test_invalid_batch_too_large(self):
        """Test invalid batch exceeding 1000 locations"""
        locations = [
            LocationTestDataFactory.make_location_report_request()
            for _ in range(1001)
        ]
        with pytest.raises(ValidationError):
            LocationBatchRequestContract(locations=locations)


class TestGeofenceCreateRequestContract:
    """Test GeofenceCreateRequest contract validation"""

    def test_valid_circle_geofence(self):
        """Test valid circle geofence request"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        request = GeofenceCreateRequestContract(
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=lat,
            center_lon=lon,
            radius=LocationTestDataFactory.make_radius(100, 1000),
            trigger_on_enter=True,
            trigger_on_exit=True,
        )
        assert request.shape_type == GeofenceShapeType.CIRCLE
        assert request.radius is not None

    def test_valid_polygon_geofence(self):
        """Test valid polygon geofence request"""
        coords = LocationTestDataFactory.make_polygon_coordinates(4)
        request = GeofenceCreateRequestContract(
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type=GeofenceShapeType.POLYGON,
            center_lat=coords[0][0],
            center_lon=coords[0][1],
            polygon_coordinates=coords,
        )
        assert request.shape_type == GeofenceShapeType.POLYGON
        assert len(request.polygon_coordinates) >= 3

    def test_invalid_empty_name(self):
        """Test invalid empty geofence name"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            GeofenceCreateRequestContract(
                name=LocationTestDataFactory.make_invalid_name_empty(),
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=lat,
                center_lon=lon,
                radius=500,
            )

    def test_invalid_whitespace_name(self):
        """Test invalid whitespace-only geofence name"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            GeofenceCreateRequestContract(
                name=LocationTestDataFactory.make_invalid_name_whitespace(),
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=lat,
                center_lon=lon,
                radius=500,
            )

    def test_invalid_name_too_long(self):
        """Test invalid geofence name too long"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            GeofenceCreateRequestContract(
                name=LocationTestDataFactory.make_invalid_name_too_long(),
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=lat,
                center_lon=lon,
                radius=500,
            )

    def test_invalid_polygon_too_few_points(self):
        """Test invalid polygon with < 3 points"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            GeofenceCreateRequestContract(
                name=LocationTestDataFactory.make_geofence_name(),
                shape_type=GeofenceShapeType.POLYGON,
                center_lat=lat,
                center_lon=lon,
                polygon_coordinates=LocationTestDataFactory.make_invalid_polygon_too_few_points(),
            )

    def test_invalid_radius_zero(self):
        """Test invalid zero radius"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            GeofenceCreateRequestContract(
                name=LocationTestDataFactory.make_geofence_name(),
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=lat,
                center_lon=lon,
                radius=LocationTestDataFactory.make_invalid_radius_zero(),
            )

    def test_invalid_center_coordinates(self):
        """Test invalid center coordinates"""
        with pytest.raises(ValidationError):
            GeofenceCreateRequestContract(
                name=LocationTestDataFactory.make_geofence_name(),
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=LocationTestDataFactory.make_invalid_latitude_too_high(),
                center_lon=0.0,
                radius=500,
            )

    def test_valid_geofence_with_dwell_trigger(self):
        """Test valid geofence with dwell trigger"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        request = GeofenceCreateRequestContract(
            name=LocationTestDataFactory.make_geofence_name(),
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=lat,
            center_lon=lon,
            radius=500,
            trigger_on_dwell=True,
            dwell_time_seconds=LocationTestDataFactory.make_dwell_time_seconds(),
        )
        assert request.trigger_on_dwell is True
        assert request.dwell_time_seconds >= 60

    def test_invalid_dwell_time_too_short(self):
        """Test invalid dwell time < 60 seconds"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            GeofenceCreateRequestContract(
                name=LocationTestDataFactory.make_geofence_name(),
                shape_type=GeofenceShapeType.CIRCLE,
                center_lat=lat,
                center_lon=lon,
                radius=500,
                trigger_on_dwell=True,
                dwell_time_seconds=LocationTestDataFactory.make_invalid_dwell_time(),
            )


class TestPlaceCreateRequestContract:
    """Test PlaceCreateRequest contract validation"""

    def test_valid_home_place(self):
        """Test valid home place request"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        request = PlaceCreateRequestContract(
            name=LocationTestDataFactory.make_place_name(),
            category=PlaceCategory.HOME,
            latitude=lat,
            longitude=lon,
            radius=100,
        )
        assert request.category == PlaceCategory.HOME
        assert 0 < request.radius <= 1000

    def test_valid_place_all_fields(self):
        """Test valid place with all fields"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        request = PlaceCreateRequestContract(
            name=LocationTestDataFactory.make_place_name(),
            category=PlaceCategory.WORK,
            latitude=lat,
            longitude=lon,
            address=LocationTestDataFactory.make_address(),
            radius=200,
            icon="office",
            color="#0000FF",
            tags=["work", "primary"],
        )
        assert request.address is not None
        assert request.icon == "office"
        assert len(request.tags) == 2

    def test_invalid_empty_name(self):
        """Test invalid empty place name"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            PlaceCreateRequestContract(
                name=LocationTestDataFactory.make_invalid_name_empty(),
                category=PlaceCategory.HOME,
                latitude=lat,
                longitude=lon,
            )

    def test_invalid_radius_zero(self):
        """Test invalid zero radius"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            PlaceCreateRequestContract(
                name=LocationTestDataFactory.make_place_name(),
                category=PlaceCategory.HOME,
                latitude=lat,
                longitude=lon,
                radius=LocationTestDataFactory.make_invalid_radius_zero(),
            )

    def test_invalid_radius_too_large(self):
        """Test invalid radius > 1000"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            PlaceCreateRequestContract(
                name=LocationTestDataFactory.make_place_name(),
                category=PlaceCategory.HOME,
                latitude=lat,
                longitude=lon,
                radius=1001,  # Max is 1000
            )


class TestNearbySearchRequestContract:
    """Test NearbySearchRequest contract validation"""

    def test_valid_nearby_search(self):
        """Test valid nearby search request"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        request = NearbySearchRequestContract(
            latitude=lat,
            longitude=lon,
            radius_meters=1000,
            time_window_minutes=30,
            limit=50,
        )
        assert request.radius_meters <= 50000  # Max 50km
        assert 1 <= request.time_window_minutes <= 1440
        assert 1 <= request.limit <= 500

    def test_invalid_radius_too_large(self):
        """Test invalid radius > 50km"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            NearbySearchRequestContract(
                latitude=lat,
                longitude=lon,
                radius_meters=50001,  # Max is 50000
            )

    def test_invalid_time_window_zero(self):
        """Test invalid zero time window"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            NearbySearchRequestContract(
                latitude=lat,
                longitude=lon,
                radius_meters=1000,
                time_window_minutes=0,
            )

    def test_invalid_time_window_too_large(self):
        """Test invalid time window > 1440"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            NearbySearchRequestContract(
                latitude=lat,
                longitude=lon,
                radius_meters=1000,
                time_window_minutes=LocationTestDataFactory.make_invalid_time_window(),
            )

    def test_invalid_limit_zero(self):
        """Test invalid zero limit"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            NearbySearchRequestContract(
                latitude=lat,
                longitude=lon,
                radius_meters=1000,
                limit=LocationTestDataFactory.make_invalid_limit_zero(),
            )

    def test_invalid_limit_too_large(self):
        """Test invalid limit > 500"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            NearbySearchRequestContract(
                latitude=lat,
                longitude=lon,
                radius_meters=1000,
                limit=501,  # Max is 500
            )


class TestDistanceRequestContract:
    """Test DistanceRequest contract validation"""

    def test_valid_distance_request(self):
        """Test valid distance request"""
        sf_lat, sf_lon = LocationTestDataFactory.make_san_francisco_coordinates()
        ny_lat, ny_lon = LocationTestDataFactory.make_new_york_coordinates()
        request = DistanceRequestContract(
            from_lat=sf_lat,
            from_lon=sf_lon,
            to_lat=ny_lat,
            to_lon=ny_lon,
        )
        assert -90 <= request.from_lat <= 90
        assert -90 <= request.to_lat <= 90

    def test_invalid_from_coordinates(self):
        """Test invalid from coordinates"""
        ny_lat, ny_lon = LocationTestDataFactory.make_new_york_coordinates()
        with pytest.raises(ValidationError):
            DistanceRequestContract(
                from_lat=LocationTestDataFactory.make_invalid_latitude_too_high(),
                from_lon=0,
                to_lat=ny_lat,
                to_lon=ny_lon,
            )

    def test_invalid_to_coordinates(self):
        """Test invalid to coordinates"""
        sf_lat, sf_lon = LocationTestDataFactory.make_san_francisco_coordinates()
        with pytest.raises(ValidationError):
            DistanceRequestContract(
                from_lat=sf_lat,
                from_lon=sf_lon,
                to_lat=LocationTestDataFactory.make_invalid_latitude_too_low(),
                to_lon=0,
            )


# =============================================================================
# RESPONSE CONTRACT VALIDATION TESTS
# =============================================================================


class TestLocationResponseContract:
    """Test LocationResponse contract validation"""

    def test_valid_location_response(self):
        """Test valid location response"""
        data = LocationTestDataFactory.make_location_response()
        # Validate by parsing
        response = LocationResponseContract(**data)
        assert response.location_id is not None
        assert response.device_id is not None
        assert -90 <= response.latitude <= 90

    def test_location_response_with_all_fields(self):
        """Test location response with all optional fields"""
        data = LocationTestDataFactory.make_location_response(
            altitude=100.0,
            heading=45.0,
            speed=5.0,
            battery_level=75.0,
        )
        response = LocationResponseContract(**data)
        assert response.altitude == 100.0
        assert response.heading == 45.0


class TestGeofenceResponseContract:
    """Test GeofenceResponse contract validation"""

    def test_valid_geofence_response(self):
        """Test valid geofence response"""
        data = LocationTestDataFactory.make_geofence_response()
        response = GeofenceResponseContract(**data)
        assert response.geofence_id is not None
        assert response.name is not None
        assert response.active is True

    def test_geofence_response_circle(self):
        """Test circle geofence response"""
        data = LocationTestDataFactory.make_geofence_response(
            shape_type="circle",
            radius=500,
        )
        response = GeofenceResponseContract(**data)
        assert response.shape_type == "circle"
        assert response.radius == 500

    def test_geofence_response_polygon(self):
        """Test polygon geofence response"""
        coords = LocationTestDataFactory.make_polygon_coordinates(4)
        data = LocationTestDataFactory.make_geofence_response(
            shape_type="polygon",
            polygon_coordinates=coords,
        )
        response = GeofenceResponseContract(**data)
        assert response.shape_type == "polygon"
        assert len(response.polygon_coordinates) >= 3


class TestPlaceResponseContract:
    """Test PlaceResponse contract validation"""

    def test_valid_place_response(self):
        """Test valid place response"""
        data = LocationTestDataFactory.make_place_response()
        response = PlaceResponseContract(**data)
        assert response.place_id is not None
        assert response.name is not None
        assert response.visit_count >= 0


class TestOperationResultContract:
    """Test LocationOperationResult contract validation"""

    def test_successful_operation_result(self):
        """Test successful operation result"""
        data = LocationTestDataFactory.make_operation_result(
            success=True,
            operation="create_location",
            location_id=LocationTestDataFactory.make_location_id(),
        )
        result = LocationOperationResultContract(**data)
        assert result.success is True
        assert result.affected_count >= 0

    def test_failed_operation_result(self):
        """Test failed operation result"""
        data = LocationTestDataFactory.make_operation_result(
            success=False,
            operation="delete_location",
        )
        result = LocationOperationResultContract(**data)
        assert result.success is False


class TestDistanceResponseContract:
    """Test DistanceResponse contract validation"""

    def test_valid_distance_response(self):
        """Test valid distance response"""
        data = LocationTestDataFactory.make_distance_response()
        response = DistanceResponseContract(**data)
        assert response.distance_meters >= 0
        assert response.distance_km >= 0


# =============================================================================
# BUILDER TESTS
# =============================================================================


class TestLocationReportRequestBuilder:
    """Test LocationReportRequest builder"""

    def test_builder_default_values(self):
        """Test builder creates valid request with defaults"""
        request = LocationReportRequestBuilder().build()
        assert request.device_id is not None
        assert -90 <= request.latitude <= 90
        assert -180 <= request.longitude <= 180
        assert request.accuracy > 0

    def test_builder_custom_device_id(self):
        """Test builder with custom device ID"""
        custom_id = LocationTestDataFactory.make_device_id()
        request = LocationReportRequestBuilder()\
            .with_device_id(custom_id)\
            .build()
        assert request.device_id == custom_id

    def test_builder_custom_coordinates(self):
        """Test builder with custom coordinates"""
        request = LocationReportRequestBuilder()\
            .with_coordinates(37.7749, -122.4194)\
            .build()
        assert request.latitude == 37.7749
        assert request.longitude == -122.4194

    def test_builder_with_all_options(self):
        """Test builder with all options"""
        request = LocationReportRequestBuilder()\
            .with_device_id(LocationTestDataFactory.make_device_id())\
            .with_coordinates(37.7749, -122.4194)\
            .with_accuracy(10.0)\
            .with_altitude(100.0)\
            .with_heading(45.0)\
            .with_speed(5.0)\
            .with_battery_level(75.0)\
            .with_location_method(LocationMethod.HYBRID)\
            .build()
        assert request.altitude == 100.0
        assert request.heading == 45.0
        assert request.speed == 5.0
        assert request.battery_level == 75.0
        assert request.location_method == LocationMethod.HYBRID

    def test_builder_build_dict(self):
        """Test builder builds dictionary"""
        data = LocationReportRequestBuilder().build_dict()
        assert isinstance(data, dict)
        assert "device_id" in data
        assert "latitude" in data

    def test_builder_invalid_coordinates(self):
        """Test builder with invalid coordinates raises on build"""
        with pytest.raises(ValidationError):
            LocationReportRequestBuilder()\
                .with_invalid_coordinates()\
                .build()


class TestGeofenceCreateRequestBuilder:
    """Test GeofenceCreateRequest builder"""

    def test_builder_default_circle(self):
        """Test builder creates circle geofence by default"""
        request = GeofenceCreateRequestBuilder().build()
        assert request.shape_type == GeofenceShapeType.CIRCLE
        assert request.radius is not None

    def test_builder_as_circle(self):
        """Test builder as circle"""
        request = GeofenceCreateRequestBuilder()\
            .as_circle(37.7749, -122.4194, 1000)\
            .build()
        assert request.shape_type == GeofenceShapeType.CIRCLE
        assert request.center_lat == 37.7749
        assert request.center_lon == -122.4194
        assert request.radius == 1000

    def test_builder_as_polygon(self):
        """Test builder as polygon"""
        coords = LocationTestDataFactory.make_polygon_coordinates(4)
        request = GeofenceCreateRequestBuilder()\
            .as_polygon(coords)\
            .build()
        assert request.shape_type == GeofenceShapeType.POLYGON
        assert len(request.polygon_coordinates) == 4

    def test_builder_with_triggers(self):
        """Test builder with trigger configuration"""
        request = GeofenceCreateRequestBuilder()\
            .with_enter_trigger(True)\
            .with_exit_trigger(False)\
            .with_dwell_trigger(True, 300)\
            .build()
        assert request.trigger_on_enter is True
        assert request.trigger_on_exit is False
        assert request.trigger_on_dwell is True
        assert request.dwell_time_seconds == 300

    def test_builder_with_targets(self):
        """Test builder with target devices"""
        devices = LocationTestDataFactory.make_batch_device_ids(3)
        request = GeofenceCreateRequestBuilder()\
            .with_target_devices(devices)\
            .build()
        assert len(request.target_devices) == 3


class TestPlaceCreateRequestBuilder:
    """Test PlaceCreateRequest builder"""

    def test_builder_default_home(self):
        """Test builder creates home place by default"""
        request = PlaceCreateRequestBuilder().build()
        assert request.category == PlaceCategory.HOME
        assert request.radius == 100.0

    def test_builder_as_work(self):
        """Test builder as work place"""
        request = PlaceCreateRequestBuilder()\
            .as_work()\
            .build()
        assert request.category == PlaceCategory.WORK
        assert request.icon == "work"

    def test_builder_as_school(self):
        """Test builder as school place"""
        request = PlaceCreateRequestBuilder()\
            .as_school()\
            .build()
        assert request.category == PlaceCategory.SCHOOL
        assert request.icon == "school"

    def test_builder_with_address(self):
        """Test builder with address"""
        address = LocationTestDataFactory.make_address()
        request = PlaceCreateRequestBuilder()\
            .with_address(address)\
            .build()
        assert request.address == address

    def test_builder_with_style(self):
        """Test builder with icon and color"""
        request = PlaceCreateRequestBuilder()\
            .with_icon("star")\
            .with_color("#FFD700")\
            .build()
        assert request.icon == "star"
        assert request.color == "#FFD700"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_coordinates(self):
        """Test coordinates at (0, 0)"""
        lat, lon = LocationTestDataFactory.make_zero_coordinates()
        request = LocationReportRequestContract(
            device_id=LocationTestDataFactory.make_device_id(),
            latitude=lat,
            longitude=lon,
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert request.latitude == 0.0
        assert request.longitude == 0.0

    def test_north_pole_coordinates(self):
        """Test coordinates at North Pole"""
        lat, lon = LocationTestDataFactory.make_north_pole_coordinates()
        request = LocationReportRequestContract(
            device_id=LocationTestDataFactory.make_device_id(),
            latitude=lat,
            longitude=lon,
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert request.latitude == 90.0

    def test_south_pole_coordinates(self):
        """Test coordinates at South Pole"""
        lat, lon = LocationTestDataFactory.make_south_pole_coordinates()
        request = LocationReportRequestContract(
            device_id=LocationTestDataFactory.make_device_id(),
            latitude=lat,
            longitude=lon,
            accuracy=LocationTestDataFactory.make_accuracy(),
        )
        assert request.latitude == -90.0

    def test_unicode_geofence_name(self):
        """Test geofence with unicode name"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        request = GeofenceCreateRequestContract(
            name=LocationTestDataFactory.make_unicode_name(),
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=lat,
            center_lon=lon,
            radius=500,
        )
        assert "中文" in request.name or len(request.name) > 0

    def test_special_chars_place_name(self):
        """Test place with special characters"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        request = PlaceCreateRequestContract(
            name=LocationTestDataFactory.make_special_chars_name(),
            category=PlaceCategory.CUSTOM,
            latitude=lat,
            longitude=lon,
        )
        assert "@" in request.name or "#" in request.name or "!" in request.name

    def test_max_length_name(self):
        """Test geofence with max length name"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        request = GeofenceCreateRequestContract(
            name=LocationTestDataFactory.make_max_length_name(),
            shape_type=GeofenceShapeType.CIRCLE,
            center_lat=lat,
            center_lon=lon,
            radius=500,
        )
        assert len(request.name) == 200

    def test_min_length_name(self):
        """Test place with min length name"""
        lat, lon = LocationTestDataFactory.make_san_francisco_coordinates()
        request = PlaceCreateRequestContract(
            name=LocationTestDataFactory.make_min_length_name(),
            category=PlaceCategory.CUSTOM,
            latitude=lat,
            longitude=lon,
        )
        assert len(request.name) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "api"])
