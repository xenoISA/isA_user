"""
Inventory Models Golden Tests

GOLDEN: These tests document CURRENT behavior of inventory models.
   DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions
- Document what code currently does
- All tests should PASS (they describe existing behavior)

Usage:
    pytest tests/unit/golden/inventory_service -v
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from microservices.inventory_service.models import (
    InventoryPolicy,
    ReservationStatus,
    InventoryItem,
    InventoryReservation,
)

pytestmark = [pytest.mark.unit, pytest.mark.golden]


# =============================================================================
# Enum Tests - Current Behavior
# =============================================================================

class TestInventoryPolicyEnum:
    """Characterization: InventoryPolicy enum current behavior"""

    def test_all_policies_defined(self):
        """CHAR: All expected inventory policies are defined"""
        expected = {"infinite", "finite"}
        actual = {p.value for p in InventoryPolicy}
        assert actual == expected

    def test_policy_values(self):
        """CHAR: Policy values are correct"""
        assert InventoryPolicy.INFINITE.value == "infinite"
        assert InventoryPolicy.FINITE.value == "finite"

    def test_policy_is_string_enum(self):
        """CHAR: InventoryPolicy values are strings"""
        for policy in InventoryPolicy:
            assert isinstance(policy.value, str)


class TestReservationStatusEnum:
    """Characterization: ReservationStatus enum current behavior"""

    def test_all_statuses_defined(self):
        """CHAR: All expected reservation statuses are defined"""
        expected = {"active", "committed", "released", "expired"}
        actual = {s.value for s in ReservationStatus}
        assert actual == expected

    def test_status_values(self):
        """CHAR: Reservation status values are correct"""
        assert ReservationStatus.ACTIVE.value == "active"
        assert ReservationStatus.COMMITTED.value == "committed"
        assert ReservationStatus.RELEASED.value == "released"
        assert ReservationStatus.EXPIRED.value == "expired"

    def test_status_is_string_enum(self):
        """CHAR: ReservationStatus values are strings"""
        for status in ReservationStatus:
            assert isinstance(status.value, str)


# =============================================================================
# InventoryItem Model Tests
# =============================================================================

class TestInventoryItemModel:
    """Characterization: InventoryItem model current behavior"""

    def test_create_minimal_item(self):
        """CHAR: InventoryItem can be created with only sku_id"""
        item = InventoryItem(sku_id="SKU-001")
        assert item.sku_id == "SKU-001"
        assert item.location_id is None
        assert item.inventory_policy == InventoryPolicy.FINITE
        assert item.on_hand == 0
        assert item.reserved == 0
        assert item.available == 0
        assert item.updated_at is None
        assert item.metadata == {}

    def test_create_full_item(self):
        """CHAR: InventoryItem can be created with all fields"""
        now = datetime.utcnow()
        item = InventoryItem(
            sku_id="SKU-002",
            location_id="warehouse-a",
            inventory_policy=InventoryPolicy.INFINITE,
            on_hand=100,
            reserved=20,
            available=80,
            updated_at=now,
            metadata={"category": "electronics"},
        )
        assert item.location_id == "warehouse-a"
        assert item.inventory_policy == InventoryPolicy.INFINITE
        assert item.on_hand == 100
        assert item.reserved == 20
        assert item.available == 80
        assert item.metadata == {"category": "electronics"}

    def test_default_policy_is_finite(self):
        """CHAR: Default inventory policy is FINITE"""
        item = InventoryItem(sku_id="SKU-001")
        assert item.inventory_policy == InventoryPolicy.FINITE

    def test_on_hand_cannot_be_negative(self):
        """CHAR: on_hand must be >= 0"""
        with pytest.raises(ValidationError):
            InventoryItem(sku_id="SKU-001", on_hand=-1)

    def test_reserved_cannot_be_negative(self):
        """CHAR: reserved must be >= 0"""
        with pytest.raises(ValidationError):
            InventoryItem(sku_id="SKU-001", reserved=-1)

    def test_available_cannot_be_negative(self):
        """CHAR: available must be >= 0"""
        with pytest.raises(ValidationError):
            InventoryItem(sku_id="SKU-001", available=-1)

    def test_sku_id_required(self):
        """CHAR: sku_id is a required field"""
        with pytest.raises(ValidationError):
            InventoryItem()

    def test_default_metadata_empty_dict(self):
        """CHAR: Default metadata is empty dict"""
        item = InventoryItem(sku_id="SKU-001")
        assert item.metadata == {}
        assert isinstance(item.metadata, dict)


# =============================================================================
# InventoryReservation Model Tests
# =============================================================================

class TestInventoryReservationModel:
    """Characterization: InventoryReservation model current behavior"""

    def test_create_minimal_reservation(self):
        """CHAR: Reservation can be created with required fields"""
        reservation = InventoryReservation(
            reservation_id="res_001",
            order_id="order_001",
            sku_id="SKU-001",
            quantity=5,
        )
        assert reservation.reservation_id == "res_001"
        assert reservation.order_id == "order_001"
        assert reservation.sku_id == "SKU-001"
        assert reservation.quantity == 5
        assert reservation.status == ReservationStatus.ACTIVE
        assert reservation.expires_at is None
        assert reservation.created_at is None
        assert reservation.updated_at is None
        assert reservation.metadata == {}

    def test_create_full_reservation(self):
        """CHAR: Reservation can be created with all fields"""
        now = datetime.utcnow()
        reservation = InventoryReservation(
            reservation_id="res_002",
            order_id="order_002",
            sku_id="SKU-002",
            quantity=10,
            status=ReservationStatus.COMMITTED,
            expires_at=now,
            created_at=now,
            updated_at=now,
            metadata={"source": "checkout"},
        )
        assert reservation.status == ReservationStatus.COMMITTED
        assert reservation.expires_at == now
        assert reservation.metadata == {"source": "checkout"}

    def test_default_status_is_active(self):
        """CHAR: Default reservation status is ACTIVE"""
        reservation = InventoryReservation(
            reservation_id="r1", order_id="o1", sku_id="s1", quantity=1
        )
        assert reservation.status == ReservationStatus.ACTIVE

    def test_quantity_must_be_positive(self):
        """CHAR: quantity must be > 0"""
        with pytest.raises(ValidationError):
            InventoryReservation(
                reservation_id="r1", order_id="o1", sku_id="s1", quantity=0
            )

    def test_quantity_negative_rejected(self):
        """CHAR: Negative quantity is rejected"""
        with pytest.raises(ValidationError):
            InventoryReservation(
                reservation_id="r1", order_id="o1", sku_id="s1", quantity=-5
            )

    def test_reservation_id_required(self):
        """CHAR: reservation_id is required"""
        with pytest.raises(ValidationError):
            InventoryReservation(order_id="o1", sku_id="s1", quantity=1)

    def test_order_id_required(self):
        """CHAR: order_id is required"""
        with pytest.raises(ValidationError):
            InventoryReservation(reservation_id="r1", sku_id="s1", quantity=1)

    def test_sku_id_required(self):
        """CHAR: sku_id is required"""
        with pytest.raises(ValidationError):
            InventoryReservation(reservation_id="r1", order_id="o1", quantity=1)

    def test_quantity_required(self):
        """CHAR: quantity is required"""
        with pytest.raises(ValidationError):
            InventoryReservation(
                reservation_id="r1", order_id="o1", sku_id="s1"
            )

    def test_all_statuses_assignable(self):
        """CHAR: All ReservationStatus values can be assigned"""
        for status in ReservationStatus:
            reservation = InventoryReservation(
                reservation_id="r1", order_id="o1", sku_id="s1",
                quantity=1, status=status
            )
            assert reservation.status == status
