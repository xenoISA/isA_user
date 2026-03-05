"""
L1 Unit Tests — Inventory Service Logic

Tests pure functions and static methods with no I/O.
"""

import pytest
from microservices.inventory_service.inventory_service import InventoryService
from microservices.inventory_service.events.models import ReservedItem


@pytest.mark.unit
class TestBuildReservedItems:
    """Test InventoryService._build_reserved_items static helper"""

    def test_builds_from_sku_id(self):
        items = [{"sku_id": "sku_1", "quantity": 3, "unit_price": 9.99}]
        result = InventoryService._build_reserved_items(items)
        assert len(result) == 1
        assert result[0].sku_id == "sku_1"
        assert result[0].quantity == 3
        assert result[0].unit_price == 9.99

    def test_builds_from_product_id_fallback(self):
        items = [{"product_id": "prod_1", "quantity": 1}]
        result = InventoryService._build_reserved_items(items)
        assert result[0].sku_id == "prod_1"

    def test_builds_from_id_fallback(self):
        items = [{"id": "item_1", "quantity": 2}]
        result = InventoryService._build_reserved_items(items)
        assert result[0].sku_id == "item_1"

    def test_skips_items_without_identifiers(self):
        items = [{"name": "Widget", "quantity": 1}]
        result = InventoryService._build_reserved_items(items)
        assert len(result) == 0

    def test_defaults_quantity_to_one(self):
        items = [{"sku_id": "sku_1"}]
        result = InventoryService._build_reserved_items(items)
        assert result[0].quantity == 1

    def test_unit_price_from_price_fallback(self):
        items = [{"sku_id": "sku_1", "price": 14.50}]
        result = InventoryService._build_reserved_items(items)
        assert result[0].unit_price == 14.50

    def test_unit_price_none_when_missing(self):
        items = [{"sku_id": "sku_1"}]
        result = InventoryService._build_reserved_items(items)
        assert result[0].unit_price is None

    def test_empty_items_returns_empty(self):
        assert InventoryService._build_reserved_items([]) == []

    def test_multiple_items_mixed(self):
        items = [
            {"sku_id": "a", "quantity": 1},
            {"name": "no_id"},
            {"product_id": "b", "quantity": 2, "unit_price": 5.0},
        ]
        result = InventoryService._build_reserved_items(items)
        assert len(result) == 2
        assert result[0].sku_id == "a"
        assert result[1].sku_id == "b"

    def test_returns_reserved_item_instances(self):
        items = [{"sku_id": "sku_1"}]
        result = InventoryService._build_reserved_items(items)
        assert isinstance(result[0], ReservedItem)

    def test_sku_id_priority_over_product_id(self):
        items = [{"sku_id": "s1", "product_id": "p1", "id": "i1"}]
        result = InventoryService._build_reserved_items(items)
        assert result[0].sku_id == "s1"


@pytest.mark.unit
class TestReservedItemModel:
    """Test ReservedItem event model"""

    def test_creation(self):
        item = ReservedItem(sku_id="sku_1", quantity=2, unit_price=10.0)
        assert item.sku_id == "sku_1"

    def test_optional_unit_price(self):
        item = ReservedItem(sku_id="sku_1", quantity=1)
        assert item.unit_price is None
