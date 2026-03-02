"""
Fulfillment Models Golden Tests

GOLDEN: These tests document CURRENT behavior of fulfillment models.
   DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions
- Document what code currently does
- All tests should PASS (they describe existing behavior)

Usage:
    pytest tests/unit/golden/fulfillment_service -v
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from microservices.fulfillment_service.models import (
    ShipmentStatus,
    Parcel,
    Shipment,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# Enum Tests - Current Behavior
# =============================================================================

class TestShipmentStatusEnum:
    """Characterization: ShipmentStatus enum current behavior"""

    def test_all_shipment_statuses_defined(self):
        """CHAR: All expected shipment statuses are defined"""
        expected = {"created", "label_purchased", "in_transit", "delivered", "failed"}
        actual = {s.value for s in ShipmentStatus}
        assert actual == expected

    def test_shipment_status_values(self):
        """CHAR: Shipment status values are correct"""
        assert ShipmentStatus.CREATED.value == "created"
        assert ShipmentStatus.LABEL_PURCHASED.value == "label_purchased"
        assert ShipmentStatus.IN_TRANSIT.value == "in_transit"
        assert ShipmentStatus.DELIVERED.value == "delivered"
        assert ShipmentStatus.FAILED.value == "failed"

    def test_shipment_status_is_string_enum(self):
        """CHAR: ShipmentStatus values are strings"""
        for status in ShipmentStatus:
            assert isinstance(status.value, str)


# =============================================================================
# Parcel Model Tests
# =============================================================================

class TestParcelModel:
    """Characterization: Parcel model current behavior"""

    def test_create_valid_parcel(self):
        """CHAR: Parcel can be created with valid data"""
        parcel = Parcel(
            weight_grams=500,
            dimensions_cm={"length": 30, "width": 20, "height": 10},
        )
        assert parcel.weight_grams == 500
        assert parcel.dimensions_cm == {"length": 30, "width": 20, "height": 10}

    def test_parcel_weight_must_be_positive(self):
        """CHAR: Parcel weight must be > 0"""
        with pytest.raises(ValidationError):
            Parcel(weight_grams=0, dimensions_cm={"length": 10})

    def test_parcel_negative_weight_rejected(self):
        """CHAR: Negative weight is rejected"""
        with pytest.raises(ValidationError):
            Parcel(weight_grams=-1, dimensions_cm={"length": 10})

    def test_parcel_weight_required(self):
        """CHAR: weight_grams is a required field"""
        with pytest.raises(ValidationError):
            Parcel(dimensions_cm={"length": 10})

    def test_parcel_dimensions_required(self):
        """CHAR: dimensions_cm is a required field"""
        with pytest.raises(ValidationError):
            Parcel(weight_grams=100)


# =============================================================================
# Shipment Model Tests
# =============================================================================

class TestShipmentModel:
    """Characterization: Shipment model current behavior"""

    def test_create_minimal_shipment(self):
        """CHAR: Shipment can be created with only required fields"""
        shipment = Shipment(
            shipment_id="ship_001",
            order_id="order_001",
        )
        assert shipment.shipment_id == "ship_001"
        assert shipment.order_id == "order_001"
        assert shipment.status == ShipmentStatus.CREATED
        assert shipment.carrier is None
        assert shipment.tracking_number is None
        assert shipment.label_url is None
        assert shipment.parcels == []
        assert shipment.created_at is None
        assert shipment.updated_at is None
        assert shipment.metadata == {}

    def test_create_full_shipment(self):
        """CHAR: Shipment can be created with all fields"""
        now = datetime.utcnow()
        parcel = Parcel(weight_grams=500, dimensions_cm={"l": 30})
        shipment = Shipment(
            shipment_id="ship_002",
            order_id="order_002",
            carrier="fedex",
            tracking_number="TRACK123",
            status=ShipmentStatus.IN_TRANSIT,
            label_url="https://labels.example.com/ship_002.pdf",
            parcels=[parcel],
            created_at=now,
            updated_at=now,
            metadata={"priority": "express"},
        )
        assert shipment.carrier == "fedex"
        assert shipment.tracking_number == "TRACK123"
        assert shipment.status == ShipmentStatus.IN_TRANSIT
        assert shipment.label_url == "https://labels.example.com/ship_002.pdf"
        assert len(shipment.parcels) == 1
        assert shipment.parcels[0].weight_grams == 500
        assert shipment.metadata == {"priority": "express"}

    def test_shipment_default_status_is_created(self):
        """CHAR: Default status is CREATED"""
        shipment = Shipment(shipment_id="s1", order_id="o1")
        assert shipment.status == ShipmentStatus.CREATED

    def test_shipment_default_parcels_empty_list(self):
        """CHAR: Default parcels is empty list"""
        shipment = Shipment(shipment_id="s1", order_id="o1")
        assert shipment.parcels == []
        assert isinstance(shipment.parcels, list)

    def test_shipment_default_metadata_empty_dict(self):
        """CHAR: Default metadata is empty dict"""
        shipment = Shipment(shipment_id="s1", order_id="o1")
        assert shipment.metadata == {}
        assert isinstance(shipment.metadata, dict)

    def test_shipment_id_required(self):
        """CHAR: shipment_id is required"""
        with pytest.raises(ValidationError):
            Shipment(order_id="o1")

    def test_order_id_required(self):
        """CHAR: order_id is required"""
        with pytest.raises(ValidationError):
            Shipment(shipment_id="s1")

    def test_shipment_multiple_parcels(self):
        """CHAR: Shipment supports multiple parcels"""
        parcels = [
            Parcel(weight_grams=100, dimensions_cm={"l": 10}),
            Parcel(weight_grams=200, dimensions_cm={"l": 20}),
            Parcel(weight_grams=300, dimensions_cm={"l": 30}),
        ]
        shipment = Shipment(
            shipment_id="s1", order_id="o1", parcels=parcels
        )
        assert len(shipment.parcels) == 3

    def test_shipment_all_statuses_assignable(self):
        """CHAR: All ShipmentStatus values can be assigned"""
        for status in ShipmentStatus:
            shipment = Shipment(
                shipment_id="s1", order_id="o1", status=status
            )
            assert shipment.status == status
