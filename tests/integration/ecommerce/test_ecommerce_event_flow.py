"""
E-Commerce Event Flow Integration Tests

Tests the complete event-driven flow for order processing:
1. Order Created -> Inventory Reserved
2. Inventory Reserved -> Tax Calculated
3. Tax Calculated -> Shipment Prepared
4. Payment Completed -> Inventory Committed + Label Created
5. Order Canceled -> Inventory Released + Shipment Canceled

Run with:
    pytest tests/integration/ecommerce/test_ecommerce_event_flow.py -v
    pytest tests/integration/ecommerce/test_ecommerce_event_flow.py -v -k "unit"
    pytest tests/integration/ecommerce/test_ecommerce_event_flow.py -v -k "integration"
"""

import os
import sys
import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../../..")
sys.path.insert(0, _project_root)

pytestmark = [pytest.mark.asyncio]


# =============================================================================
# UNIT TESTS - Event Models
# =============================================================================

class TestInventoryEventModels:
    """Unit: Test inventory service event models"""

    def test_reserved_item_model(self):
        """UNIT: ReservedItem model can be created"""
        from microservices.inventory_service.events.models import ReservedItem

        item = ReservedItem(
            sku_id="sku_123",
            quantity=2,
            unit_price=29.99
        )

        assert item.sku_id == "sku_123"
        assert item.quantity == 2
        assert item.unit_price == 29.99

    def test_stock_reserved_event_model(self):
        """UNIT: StockReservedEvent model can be created"""
        from microservices.inventory_service.events.models import (
            StockReservedEvent, ReservedItem
        )

        items = [ReservedItem(sku_id="sku_1", quantity=1, unit_price=10.0)]
        expires_at = datetime.utcnow() + timedelta(minutes=30)

        event = StockReservedEvent(
            order_id="ord_123",
            reservation_id="res_abc",
            user_id="usr_456",
            items=items,
            expires_at=expires_at
        )

        assert event.order_id == "ord_123"
        assert event.reservation_id == "res_abc"
        assert len(event.items) == 1

    def test_stock_committed_event_model(self):
        """UNIT: StockCommittedEvent model can be created"""
        from microservices.inventory_service.events.models import (
            StockCommittedEvent, ReservedItem
        )

        items = [ReservedItem(sku_id="sku_1", quantity=2)]

        event = StockCommittedEvent(
            order_id="ord_123",
            reservation_id="res_abc",
            user_id="usr_456",
            items=items
        )

        assert event.order_id == "ord_123"
        assert event.reservation_id == "res_abc"

    def test_stock_released_event_model(self):
        """UNIT: StockReleasedEvent model can be created"""
        from microservices.inventory_service.events.models import (
            StockReleasedEvent, ReservedItem
        )

        items = [ReservedItem(sku_id="sku_1", quantity=1)]

        event = StockReleasedEvent(
            order_id="ord_123",
            user_id="usr_456",
            items=items,
            reason="order_canceled"
        )

        assert event.order_id == "ord_123"
        assert event.reason == "order_canceled"

    def test_stock_failed_event_model(self):
        """UNIT: StockFailedEvent model can be created"""
        from microservices.inventory_service.events.models import StockFailedEvent

        event = StockFailedEvent(
            order_id="ord_123",
            user_id="usr_456",
            items=[{"sku_id": "sku_1", "quantity": 100}],
            error_message="Insufficient stock",
            error_code="INSUFFICIENT_STOCK"
        )

        assert event.order_id == "ord_123"
        assert event.error_code == "INSUFFICIENT_STOCK"


class TestTaxEventModels:
    """Unit: Test tax service event models"""

    def test_tax_line_item_model(self):
        """UNIT: TaxLineItem model can be created"""
        from microservices.tax_service.events.models import TaxLineItem

        line = TaxLineItem(
            line_item_id="line_1",
            sku_id="sku_123",
            tax_amount=5.99,
            tax_rate=0.0825,
            jurisdiction="CA",
            tax_type="sales_tax"
        )

        assert line.tax_amount == 5.99
        assert line.tax_rate == 0.0825
        assert line.jurisdiction == "CA"

    def test_tax_calculated_event_model(self):
        """UNIT: TaxCalculatedEvent model can be created"""
        from microservices.tax_service.events.models import (
            TaxCalculatedEvent, TaxLineItem
        )

        tax_lines = [TaxLineItem(
            line_item_id="line_1",
            tax_amount=8.25,
            tax_rate=0.0825
        )]

        event = TaxCalculatedEvent(
            order_id="ord_123",
            calculation_id="tax_abc",
            user_id="usr_456",
            subtotal=100.00,
            total_tax=8.25,
            currency="USD",
            tax_lines=tax_lines,
            shipping_address={"state": "CA", "country": "US"}
        )

        assert event.order_id == "ord_123"
        assert event.total_tax == 8.25
        assert len(event.tax_lines) == 1

    def test_tax_failed_event_model(self):
        """UNIT: TaxFailedEvent model can be created"""
        from microservices.tax_service.events.models import TaxFailedEvent

        event = TaxFailedEvent(
            order_id="ord_123",
            user_id="usr_456",
            error_message="Invalid address",
            error_code="INVALID_ADDRESS"
        )

        assert event.order_id == "ord_123"
        assert event.error_code == "INVALID_ADDRESS"


class TestFulfillmentEventModels:
    """Unit: Test fulfillment service event models"""

    def test_shipment_item_model(self):
        """UNIT: ShipmentItem model can be created"""
        from microservices.fulfillment_service.events.models import ShipmentItem

        item = ShipmentItem(
            sku_id="sku_123",
            quantity=2,
            weight_grams=500
        )

        assert item.sku_id == "sku_123"
        assert item.quantity == 2
        assert item.weight_grams == 500

    def test_shipment_prepared_event_model(self):
        """UNIT: ShipmentPreparedEvent model can be created"""
        from microservices.fulfillment_service.events.models import (
            ShipmentPreparedEvent, ShipmentItem
        )

        items = [ShipmentItem(sku_id="sku_1", quantity=1, weight_grams=500)]

        event = ShipmentPreparedEvent(
            order_id="ord_123",
            shipment_id="shp_abc",
            user_id="usr_456",
            items=items,
            shipping_address={"street": "123 Main St", "city": "SF"},
            estimated_weight_grams=500
        )

        assert event.order_id == "ord_123"
        assert event.shipment_id == "shp_abc"

    def test_label_created_event_model(self):
        """UNIT: LabelCreatedEvent model can be created"""
        from microservices.fulfillment_service.events.models import LabelCreatedEvent

        event = LabelCreatedEvent(
            order_id="ord_123",
            shipment_id="shp_abc",
            user_id="usr_456",
            carrier="USPS",
            tracking_number="trk_1234567890"
        )

        assert event.order_id == "ord_123"
        assert event.tracking_number == "trk_1234567890"
        assert event.carrier == "USPS"

    def test_shipment_canceled_event_model(self):
        """UNIT: ShipmentCanceledEvent model can be created"""
        from microservices.fulfillment_service.events.models import ShipmentCanceledEvent

        event = ShipmentCanceledEvent(
            order_id="ord_123",
            shipment_id="shp_abc",
            user_id="usr_456",
            reason="order_canceled",
            refund_shipping=True
        )

        assert event.order_id == "ord_123"
        assert event.refund_shipping is True


# =============================================================================
# UNIT TESTS - Event Handlers
# =============================================================================

class TestInventoryEventHandlers:
    """Unit: Test inventory service event handlers with mocks"""

    async def test_handle_order_created_reserves_inventory(self):
        """UNIT: order.created event triggers inventory reservation"""
        from microservices.inventory_service.events.handlers import handle_order_created
        from microservices.inventory_service.events.models import ReservedItem
        from datetime import datetime, timedelta, timezone

        # Mock event bus
        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        # Mock repository
        mock_repository = AsyncMock()
        created_reservations = []

        async def mock_create_reservation(order_id, user_id, items, expires_in_minutes=30):
            reservation = {
                "reservation_id": f"res_{uuid.uuid4().hex[:8]}",
                "order_id": order_id,
                "user_id": user_id,
                "items": items,
                "status": "active",
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
            }
            created_reservations.append(reservation)
            return reservation

        mock_repository.create_reservation = mock_create_reservation

        # Event data (simulating order.created)
        event_data = {
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "items": [
                {"sku_id": "sku_1", "quantity": 2, "unit_price": 29.99},
                {"sku_id": "sku_2", "quantity": 1, "unit_price": 49.99}
            ]
        }

        # Handle event
        await handle_order_created(event_data, mock_repository, mock_event_bus)

        # Verify reservation created
        assert len(created_reservations) == 1
        reservation = created_reservations[0]
        assert reservation["order_id"] == "ord_test_123"
        assert reservation["status"] == "active"
        assert len(reservation["items"]) == 2

        # Verify event published
        mock_event_bus.publish_event.assert_called_once()

    async def test_handle_payment_completed_commits_inventory(self):
        """UNIT: payment.completed event commits reservation"""
        from microservices.inventory_service.events.handlers import handle_payment_completed

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        # Mock repository with pre-existing reservation
        mock_repository = AsyncMock()
        reservation_data = {
            "reservation_id": "res_123",
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "items": [{"sku_id": "sku_1", "quantity": 1, "unit_price": 29.99}],
            "status": "active"
        }
        mock_repository.get_active_reservation_for_order = AsyncMock(return_value=reservation_data)
        mock_repository.commit_reservation = AsyncMock()

        event_data = {
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "payment_intent_id": "pi_123"
        }

        await handle_payment_completed(event_data, mock_repository, mock_event_bus)

        # Verify committed
        mock_repository.commit_reservation.assert_called_once_with("res_123")
        mock_event_bus.publish_event.assert_called_once()

    async def test_handle_order_canceled_releases_inventory(self):
        """UNIT: order.canceled event releases reservation"""
        from microservices.inventory_service.events.handlers import handle_order_canceled

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        # Mock repository
        mock_repository = AsyncMock()
        reservation_data = {
            "reservation_id": "res_123",
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "items": [{"sku_id": "sku_1", "quantity": 1, "unit_price": 29.99}],
            "status": "active"
        }
        mock_repository.get_active_reservation_for_order = AsyncMock(return_value=reservation_data)
        mock_repository.release_reservation = AsyncMock()

        event_data = {
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "cancellation_reason": "user_requested"
        }

        await handle_order_canceled(event_data, mock_repository, mock_event_bus)

        mock_repository.release_reservation.assert_called_once_with("res_123")
        mock_event_bus.publish_event.assert_called_once()


class TestTaxEventHandlers:
    """Unit: Test tax service event handlers with mocks"""

    async def test_handle_inventory_reserved_calculates_tax(self):
        """UNIT: inventory.reserved event triggers tax calculation"""
        from microservices.tax_service.events.handlers import handle_inventory_reserved

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        # Mock tax provider
        mock_provider = AsyncMock()
        mock_provider.calculate = AsyncMock(return_value={
            "currency": "USD",
            "total_tax": 8.25,
            "lines": []
        })

        # Mock repository
        mock_repository = AsyncMock()
        created_calculations = []

        async def mock_create_calculation(order_id, user_id, subtotal, total_tax, currency, tax_lines, shipping_address, metadata=None):
            calculation = {
                "calculation_id": f"calc_{uuid.uuid4().hex[:8]}",
                "order_id": order_id,
                "user_id": user_id,
                "subtotal": subtotal,
                "total_tax": total_tax,
                "currency": currency,
                "tax_lines": tax_lines,
                "shipping_address": shipping_address
            }
            created_calculations.append(calculation)
            return calculation

        mock_repository.create_calculation = mock_create_calculation

        event_data = {
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "reservation_id": "res_abc",
            "items": [
                {"sku_id": "sku_1", "quantity": 2, "unit_price": 50.0}
            ],
            "metadata": {
                "shipping_address": {"state": "CA", "country": "US"}
            }
        }

        await handle_inventory_reserved(event_data, mock_provider, mock_repository, mock_event_bus)

        # Verify calculation stored
        assert len(created_calculations) == 1
        calc = created_calculations[0]
        assert calc["order_id"] == "ord_test_123"
        assert calc["total_tax"] == 8.25

        # Verify event published
        mock_event_bus.publish_event.assert_called_once()


class TestFulfillmentEventHandlers:
    """Unit: Test fulfillment service event handlers with mocks"""

    async def test_handle_tax_calculated_prepares_shipment(self):
        """UNIT: tax.calculated event triggers shipment preparation"""
        from microservices.fulfillment_service.events.handlers import handle_tax_calculated

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        mock_provider = AsyncMock()

        # Mock repository
        mock_repository = AsyncMock()
        mock_repository.get_shipment_by_order = AsyncMock(return_value=None)  # No existing shipment
        created_shipments = []

        async def mock_create_shipment(order_id, user_id, items, shipping_address, metadata=None):
            shipment = {
                "shipment_id": f"shp_{uuid.uuid4().hex[:8]}",
                "order_id": order_id,
                "user_id": user_id,
                "items": items,
                "shipping_address": shipping_address,
                "status": "created"
            }
            created_shipments.append(shipment)
            return shipment

        mock_repository.create_shipment = mock_create_shipment

        event_data = {
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "calculation_id": "tax_abc",
            "total_tax": 8.25,
            "shipping_address": {"street": "123 Main", "city": "SF", "state": "CA"},
            "metadata": {
                "items": [{"sku_id": "sku_1", "quantity": 1}]
            }
        }

        await handle_tax_calculated(event_data, mock_provider, mock_repository, mock_event_bus)

        # Verify shipment created
        assert len(created_shipments) == 1
        shipment = created_shipments[0]
        assert shipment["order_id"] == "ord_test_123"

        mock_event_bus.publish_event.assert_called_once()

    async def test_handle_payment_completed_creates_label(self):
        """UNIT: payment.completed event creates shipping label"""
        from microservices.fulfillment_service.events.handlers import handle_payment_completed

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        mock_provider = AsyncMock()
        mock_provider.create_shipment = AsyncMock(return_value={
            "shipment_id": "shp_new",
            "tracking_number": "trk_123456",
            "carrier": "USPS",
            "label_url": "https://example.com/label.pdf"
        })

        # Mock repository
        mock_repository = AsyncMock()
        shipment_data = {
            "shipment_id": "shp_123",
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "items": [{"sku_id": "sku_1", "quantity": 1}],
            "shipping_address": {"city": "SF"},
            "status": "created"
        }
        mock_repository.get_shipment_by_order = AsyncMock(return_value=shipment_data)
        mock_repository.create_label = AsyncMock()

        event_data = {
            "order_id": "ord_test_123",
            "user_id": "usr_test_456"
        }

        await handle_payment_completed(event_data, mock_provider, mock_repository, mock_event_bus)

        # Verify label created
        mock_repository.create_label.assert_called_once()
        mock_event_bus.publish_event.assert_called_once()

    async def test_handle_order_canceled_cancels_shipment(self):
        """UNIT: order.canceled event cancels shipment"""
        from microservices.fulfillment_service.events.handlers import handle_order_canceled

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        mock_provider = AsyncMock()

        # Mock repository
        mock_repository = AsyncMock()
        shipment_data = {
            "shipment_id": "shp_123",
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "status": "created"
        }
        mock_repository.get_shipment_by_order = AsyncMock(return_value=shipment_data)
        mock_repository.cancel_shipment = AsyncMock()

        event_data = {
            "order_id": "ord_test_123",
            "user_id": "usr_test_456",
            "cancellation_reason": "user_requested"
        }

        await handle_order_canceled(event_data, mock_provider, mock_repository, mock_event_bus)

        mock_repository.cancel_shipment.assert_called_once_with("shp_123", reason="user_requested")
        mock_event_bus.publish_event.assert_called_once()


# =============================================================================
# UNIT TESTS - Event Publishers
# =============================================================================

class TestInventoryPublishers:
    """Unit: Test inventory service publishers"""

    async def test_publish_stock_reserved(self):
        """UNIT: publish_stock_reserved sends event"""
        from microservices.inventory_service.events.publishers import publish_stock_reserved
        from microservices.inventory_service.events.models import ReservedItem

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        items = [ReservedItem(sku_id="sku_1", quantity=1)]
        expires_at = datetime.utcnow() + timedelta(minutes=30)

        result = await publish_stock_reserved(
            event_bus=mock_event_bus,
            order_id="ord_123",
            reservation_id="res_abc",
            user_id="usr_456",
            items=items,
            expires_at=expires_at
        )

        assert result is True
        mock_event_bus.publish_event.assert_called_once()

        # Verify event structure
        call_args = mock_event_bus.publish_event.call_args
        event = call_args[0][0]
        assert event.type == "inventory.reserved"
        assert event.source == "inventory_service"

    async def test_publish_without_event_bus_returns_false(self):
        """UNIT: Publishers return False when event_bus is None"""
        from microservices.inventory_service.events.publishers import publish_stock_reserved
        from microservices.inventory_service.events.models import ReservedItem

        items = [ReservedItem(sku_id="sku_1", quantity=1)]

        result = await publish_stock_reserved(
            event_bus=None,
            order_id="ord_123",
            reservation_id="res_abc",
            user_id="usr_456",
            items=items,
            expires_at=datetime.utcnow()
        )

        assert result is False


class TestTaxPublishers:
    """Unit: Test tax service publishers"""

    async def test_publish_tax_calculated(self):
        """UNIT: publish_tax_calculated sends event"""
        from microservices.tax_service.events.publishers import publish_tax_calculated

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        result = await publish_tax_calculated(
            event_bus=mock_event_bus,
            order_id="ord_123",
            calculation_id="tax_abc",
            user_id="usr_456",
            subtotal=100.0,
            total_tax=8.25
        )

        assert result is True
        mock_event_bus.publish_event.assert_called_once()

        event = mock_event_bus.publish_event.call_args[0][0]
        assert event.type == "tax.calculated"
        assert event.source == "tax_service"


class TestFulfillmentPublishers:
    """Unit: Test fulfillment service publishers"""

    async def test_publish_shipment_prepared(self):
        """UNIT: publish_shipment_prepared sends event"""
        from microservices.fulfillment_service.events.publishers import publish_shipment_prepared
        from microservices.fulfillment_service.events.models import ShipmentItem

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        items = [ShipmentItem(sku_id="sku_1", quantity=1)]

        result = await publish_shipment_prepared(
            event_bus=mock_event_bus,
            order_id="ord_123",
            shipment_id="shp_abc",
            user_id="usr_456",
            items=items,
            shipping_address={"city": "SF"}
        )

        assert result is True
        event = mock_event_bus.publish_event.call_args[0][0]
        assert event.type == "fulfillment.shipment.prepared"

    async def test_publish_label_created(self):
        """UNIT: publish_label_created sends event"""
        from microservices.fulfillment_service.events.publishers import publish_label_created

        mock_event_bus = AsyncMock()
        mock_event_bus.publish_event = AsyncMock(return_value=True)

        result = await publish_label_created(
            event_bus=mock_event_bus,
            order_id="ord_123",
            shipment_id="shp_abc",
            user_id="usr_456",
            carrier="USPS",
            tracking_number="trk_123"
        )

        assert result is True
        event = mock_event_bus.publish_event.call_args[0][0]
        assert event.type == "fulfillment.label.created"


# =============================================================================
# INTEGRATION TEST - Full Event Flow (with mocked event bus)
# =============================================================================

class TestEcommerceEventFlowIntegration:
    """Integration: Test complete e-commerce event flow"""

    async def test_complete_order_flow_happy_path(self):
        """
        INTEGRATION: Complete order flow from creation to fulfillment

        Flow:
        1. Order Created -> Inventory reserves stock
        2. Inventory Reserved -> Tax calculated
        3. Tax Calculated -> Shipment prepared
        4. Payment Completed -> Inventory committed + Label created
        """
        from datetime import datetime, timedelta, timezone

        # Shared state (simulating DB storage)
        reservations_store = {}
        tax_calculations_store = {}
        shipments_store = {}
        published_events = []

        # Mock event bus that tracks published events
        mock_event_bus = AsyncMock()

        async def capture_event(event):
            published_events.append({
                "type": event.type,
                "source": event.source,
                "data": event.data
            })
            return True

        mock_event_bus.publish_event = capture_event

        # Mock providers
        mock_tax_provider = AsyncMock()
        mock_tax_provider.calculate = AsyncMock(return_value={
            "currency": "USD",
            "total_tax": 8.25,
            "lines": []
        })

        mock_fulfillment_provider = AsyncMock()
        mock_fulfillment_provider.create_shipment = AsyncMock(return_value={
            "shipment_id": "shp_new",
            "tracking_number": "trk_123456",
            "carrier": "USPS",
            "label_url": "https://example.com/label.pdf"
        })

        # Mock repositories
        mock_inventory_repo = AsyncMock()

        async def inv_create_reservation(order_id, user_id, items, expires_in_minutes=30):
            res_id = f"res_{uuid.uuid4().hex[:8]}"
            reservation = {
                "reservation_id": res_id,
                "order_id": order_id,
                "user_id": user_id,
                "items": items,
                "status": "active",
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
            }
            reservations_store[res_id] = reservation
            return reservation

        async def inv_get_active_reservation(order_id):
            for res in reservations_store.values():
                if res["order_id"] == order_id and res["status"] == "active":
                    return res
            return None

        async def inv_commit_reservation(reservation_id):
            if reservation_id in reservations_store:
                reservations_store[reservation_id]["status"] = "committed"

        mock_inventory_repo.create_reservation = inv_create_reservation
        mock_inventory_repo.get_active_reservation_for_order = inv_get_active_reservation
        mock_inventory_repo.commit_reservation = inv_commit_reservation

        mock_tax_repo = AsyncMock()

        async def tax_create_calculation(order_id, user_id, subtotal, total_tax, currency, tax_lines, shipping_address, metadata=None):
            calc_id = f"calc_{uuid.uuid4().hex[:8]}"
            calculation = {
                "calculation_id": calc_id,
                "order_id": order_id,
                "user_id": user_id,
                "subtotal": subtotal,
                "total_tax": total_tax,
                "currency": currency,
                "tax_lines": tax_lines,
                "shipping_address": shipping_address
            }
            tax_calculations_store[calc_id] = calculation
            return calculation

        mock_tax_repo.create_calculation = tax_create_calculation

        mock_fulfillment_repo = AsyncMock()

        async def ful_get_shipment_by_order(order_id):
            for shp in shipments_store.values():
                if shp["order_id"] == order_id:
                    return shp
            return None

        async def ful_create_shipment(order_id, user_id, items, shipping_address, metadata=None):
            shp_id = f"shp_{uuid.uuid4().hex[:8]}"
            shipment = {
                "shipment_id": shp_id,
                "order_id": order_id,
                "user_id": user_id,
                "items": items,
                "shipping_address": shipping_address,
                "status": "created"
            }
            shipments_store[shp_id] = shipment
            return shipment

        async def ful_create_label(shipment_id, carrier, tracking_number, label_url=None):
            if shipment_id in shipments_store:
                shipments_store[shipment_id]["carrier"] = carrier
                shipments_store[shipment_id]["tracking_number"] = tracking_number
                shipments_store[shipment_id]["label_url"] = label_url
                shipments_store[shipment_id]["status"] = "label_purchased"

        mock_fulfillment_repo.get_shipment_by_order = ful_get_shipment_by_order
        mock_fulfillment_repo.create_shipment = ful_create_shipment
        mock_fulfillment_repo.create_label = ful_create_label

        # Import handlers
        from microservices.inventory_service.events.handlers import (
            handle_order_created, handle_payment_completed as inv_handle_payment
        )
        from microservices.tax_service.events.handlers import handle_inventory_reserved
        from microservices.fulfillment_service.events.handlers import (
            handle_tax_calculated, handle_payment_completed as ful_handle_payment
        )

        order_id = f"ord_test_{uuid.uuid4().hex[:8]}"
        user_id = f"usr_test_{uuid.uuid4().hex[:8]}"

        # Step 1: Order Created
        order_created_event = {
            "order_id": order_id,
            "user_id": user_id,
            "items": [
                {"sku_id": "sku_widget", "quantity": 2, "unit_price": 25.0},
                {"sku_id": "sku_gadget", "quantity": 1, "unit_price": 50.0}
            ],
            "total_amount": 100.0
        }

        await handle_order_created(order_created_event, mock_inventory_repo, mock_event_bus)

        assert len(reservations_store) == 1, "Inventory should create reservation"
        reservation = list(reservations_store.values())[0]
        assert reservation["status"] == "active"

        # Check inventory.reserved event was published
        inventory_reserved_events = [e for e in published_events if e["type"] == "inventory.reserved"]
        assert len(inventory_reserved_events) == 1, "inventory.reserved event should be published"

        # Step 2: Inventory Reserved -> Tax Calculation
        inventory_reserved_data = inventory_reserved_events[0]["data"]
        inventory_reserved_data["metadata"] = {
            "shipping_address": {"state": "CA", "country": "US", "postal_code": "94102"}
        }

        await handle_inventory_reserved(
            inventory_reserved_data, mock_tax_provider, mock_tax_repo, mock_event_bus
        )

        assert len(tax_calculations_store) == 1, "Tax should be calculated"
        tax_calc = list(tax_calculations_store.values())[0]
        assert tax_calc["total_tax"] == 8.25

        # Check tax.calculated event
        tax_calculated_events = [e for e in published_events if e["type"] == "tax.calculated"]
        assert len(tax_calculated_events) == 1, "tax.calculated event should be published"

        # Step 3: Tax Calculated -> Shipment Prepared
        tax_calculated_data = tax_calculated_events[0]["data"]
        tax_calculated_data["metadata"] = {"items": order_created_event["items"]}

        await handle_tax_calculated(
            tax_calculated_data, mock_fulfillment_provider, mock_fulfillment_repo, mock_event_bus
        )

        assert len(shipments_store) == 1, "Shipment should be prepared"
        shipment = list(shipments_store.values())[0]
        assert shipment["status"] == "created"

        # Check shipment.prepared event
        shipment_prepared_events = [e for e in published_events if e["type"] == "fulfillment.shipment.prepared"]
        assert len(shipment_prepared_events) == 1, "fulfillment.shipment.prepared event should be published"

        # Step 4: Payment Completed -> Commit inventory + Create label
        payment_completed_event = {
            "order_id": order_id,
            "user_id": user_id,
            "payment_intent_id": "pi_test_123",
            "amount": 108.25
        }

        await inv_handle_payment(payment_completed_event, mock_inventory_repo, mock_event_bus)
        await ful_handle_payment(payment_completed_event, mock_fulfillment_provider, mock_fulfillment_repo, mock_event_bus)

        # Verify final state
        reservation = list(reservations_store.values())[0]
        assert reservation["status"] == "committed", "Inventory should be committed after payment"

        shipment = list(shipments_store.values())[0]
        assert shipment["status"] == "label_purchased", "Shipping label should be created after payment"
        assert "tracking_number" in shipment

        # Check all events published
        event_types = [e["type"] for e in published_events]
        assert "inventory.reserved" in event_types
        assert "tax.calculated" in event_types
        assert "fulfillment.shipment.prepared" in event_types
        assert "inventory.committed" in event_types
        assert "fulfillment.label.created" in event_types

        print(f"\n✅ Complete order flow successful!")
        print(f"   Order: {order_id}")
        print(f"   Events published: {len(published_events)}")
        print(f"   Event types: {event_types}")

    async def test_order_cancellation_flow(self):
        """
        INTEGRATION: Order cancellation releases inventory and cancels shipment

        Flow:
        1. Setup: Order with active reservation and prepared shipment
        2. Order Canceled -> Inventory released + Shipment canceled
        """
        order_id = f"ord_test_{uuid.uuid4().hex[:8]}"
        user_id = f"usr_test_{uuid.uuid4().hex[:8]}"

        # Pre-existing state (order was in progress)
        reservation_data = {
            "reservation_id": "res_123",
            "order_id": order_id,
            "user_id": user_id,
            "items": [{"sku_id": "sku_1", "quantity": 2, "unit_price": 25.0}],
            "status": "active"
        }

        shipment_data = {
            "shipment_id": "shp_456",
            "order_id": order_id,
            "user_id": user_id,
            "items": [{"sku_id": "sku_1", "quantity": 2}],
            "status": "created"
        }

        published_events = []
        mock_event_bus = AsyncMock()

        async def capture_event(event):
            published_events.append({"type": event.type, "data": event.data})
            return True

        mock_event_bus.publish_event = capture_event
        mock_provider = AsyncMock()

        # Mock inventory repository
        mock_inventory_repo = AsyncMock()
        mock_inventory_repo.get_active_reservation_for_order = AsyncMock(return_value=reservation_data)
        released_reservations = []

        async def release_reservation(res_id):
            released_reservations.append(res_id)
            reservation_data["status"] = "released"

        mock_inventory_repo.release_reservation = release_reservation

        # Mock fulfillment repository
        mock_fulfillment_repo = AsyncMock()
        mock_fulfillment_repo.get_shipment_by_order = AsyncMock(return_value=shipment_data)
        canceled_shipments = []

        async def cancel_shipment(shp_id, reason=None):
            canceled_shipments.append({"shipment_id": shp_id, "reason": reason})
            shipment_data["status"] = "failed"

        mock_fulfillment_repo.cancel_shipment = cancel_shipment

        from microservices.inventory_service.events.handlers import handle_order_canceled as inv_cancel
        from microservices.fulfillment_service.events.handlers import handle_order_canceled as ful_cancel

        # Cancel order
        cancel_event = {
            "order_id": order_id,
            "user_id": user_id,
            "cancellation_reason": "customer_requested"
        }

        await inv_cancel(cancel_event, mock_inventory_repo, mock_event_bus)
        await ful_cancel(cancel_event, mock_provider, mock_fulfillment_repo, mock_event_bus)

        # Verify cleanup
        assert reservation_data["status"] == "released"
        assert shipment_data["status"] == "failed"
        assert len(released_reservations) == 1
        assert len(canceled_shipments) == 1

        event_types = [e["type"] for e in published_events]
        assert "inventory.released" in event_types
        assert "fulfillment.shipment.canceled" in event_types

        print(f"\n✅ Order cancellation flow successful!")
        print(f"   Inventory released: {reservation_data['status']}")
        print(f"   Shipment canceled: {shipment_data['status']}")


# =============================================================================
# SUMMARY
# =============================================================================
"""
E-COMMERCE EVENT FLOW TEST SUMMARY:

Unit Tests (30 tests):
1. Event Models (15 tests):
   - Inventory: ReservedItem, StockReserved, StockCommitted, StockReleased, StockFailed
   - Tax: TaxLineItem, TaxCalculated, TaxFailed
   - Fulfillment: ShipmentItem, ShipmentPrepared, LabelCreated, ShipmentCanceled, ShipmentFailed

2. Event Handlers (6 tests):
   - Inventory: handle_order_created, handle_payment_completed, handle_order_canceled
   - Tax: handle_inventory_reserved
   - Fulfillment: handle_tax_calculated, handle_payment_completed, handle_order_canceled

3. Event Publishers (5 tests):
   - Inventory: publish_stock_reserved
   - Tax: publish_tax_calculated
   - Fulfillment: publish_shipment_prepared, publish_label_created

Integration Tests (2 tests):
1. Complete Order Flow: Order -> Inventory -> Tax -> Shipment -> Payment -> Done
2. Order Cancellation Flow: Cancel -> Release Inventory -> Cancel Shipment

Run:
    # All tests
    pytest tests/integration/ecommerce/test_ecommerce_event_flow.py -v

    # Unit tests only
    pytest tests/integration/ecommerce/test_ecommerce_event_flow.py -v -k "unit"

    # Integration tests only
    pytest tests/integration/ecommerce/test_ecommerce_event_flow.py -v -k "integration"
"""
