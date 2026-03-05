"""
L1 Unit Tests — Fulfillment Service Logic

Tests pure functions and static methods with no I/O.
"""

import pytest
from microservices.fulfillment_service.fulfillment_service import FulfillmentService
from microservices.fulfillment_service.events.models import ShipmentItem


@pytest.mark.unit
class TestBuildShipmentItems:
    """Test FulfillmentService._build_shipment_items static helper"""

    def test_builds_items_from_sku_id(self):
        items = [{"sku_id": "sku_abc", "quantity": 3, "weight_grams": 200}]
        result = FulfillmentService._build_shipment_items(items)
        assert len(result) == 1
        assert result[0].sku_id == "sku_abc"
        assert result[0].quantity == 3
        assert result[0].weight_grams == 200

    def test_builds_items_from_product_id_fallback(self):
        items = [{"product_id": "prod_xyz", "quantity": 2}]
        result = FulfillmentService._build_shipment_items(items)
        assert result[0].sku_id == "prod_xyz"

    def test_falls_back_to_unknown_sku(self):
        items = [{"name": "Widget"}]
        result = FulfillmentService._build_shipment_items(items)
        assert result[0].sku_id == "unknown"

    def test_defaults_quantity_to_one(self):
        items = [{"sku_id": "sku_1"}]
        result = FulfillmentService._build_shipment_items(items)
        assert result[0].quantity == 1

    def test_defaults_weight_to_500(self):
        items = [{"sku_id": "sku_1"}]
        result = FulfillmentService._build_shipment_items(items)
        assert result[0].weight_grams == 500

    def test_empty_items_returns_empty(self):
        assert FulfillmentService._build_shipment_items([]) == []

    def test_multiple_items(self):
        items = [
            {"sku_id": "a", "quantity": 1, "weight_grams": 100},
            {"sku_id": "b", "quantity": 5, "weight_grams": 300},
        ]
        result = FulfillmentService._build_shipment_items(items)
        assert len(result) == 2
        assert result[1].sku_id == "b"
        assert result[1].quantity == 5

    def test_returns_shipment_item_instances(self):
        items = [{"sku_id": "sku_1"}]
        result = FulfillmentService._build_shipment_items(items)
        assert isinstance(result[0], ShipmentItem)

    def test_sku_id_takes_priority_over_product_id(self):
        items = [{"sku_id": "sku_1", "product_id": "prod_2"}]
        result = FulfillmentService._build_shipment_items(items)
        assert result[0].sku_id == "sku_1"


@pytest.mark.unit
class TestFulfillmentEventModels:
    """Test event model construction"""

    def test_shipment_item_creation(self):
        item = ShipmentItem(sku_id="sku_1", quantity=2, weight_grams=500)
        assert item.sku_id == "sku_1"
        assert item.quantity == 2

    def test_shipment_item_optional_weight(self):
        item = ShipmentItem(sku_id="sku_1", quantity=1)
        assert item.weight_grams is None
