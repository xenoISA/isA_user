"""Unit tests for order item normalization in _dict_to_order (Issue #143).

Existing DB data uses legacy item format with 'price' and 'name' fields,
but OrderLineItem model requires 'unit_price', 'product_id', etc.
The repository must normalize legacy items before Pydantic validation.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest


def _make_order_row(items):
    """Create a minimal order dict with given items."""
    now = datetime.now(timezone.utc)
    return {
        "order_id": "order_test_001",
        "user_id": "user_001",
        "order_type": "purchase",
        "status": "pending",
        "total_amount": Decimal("49.99"),
        "currency": "USD",
        "payment_status": "pending",
        "payment_method": None,
        "payment_intent_id": None,
        "subscription_id": None,
        "wallet_id": None,
        "items": items,
        "subtotal_amount": Decimal("49.99"),
        "tax_amount": Decimal("0.00"),
        "shipping_amount": Decimal("0.00"),
        "discount_amount": Decimal("0.00"),
        "final_amount": Decimal("49.99"),
        "fulfillment_status": "pending",
        "tracking_number": None,
        "shipping_address": None,
        "billing_address": None,
        "metadata": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "expires_at": None,
    }


class TestOrderItemsNormalization:
    """Verify _dict_to_order handles legacy item formats from the DB."""

    def test_legacy_items_with_price_field(self):
        """Items with 'price' instead of 'unit_price' must be normalized."""
        from microservices.order_service.order_repository import OrderRepository

        repo = OrderRepository.__new__(OrderRepository)
        row = _make_order_row([
            {"name": "Test Product", "price": 49.99, "quantity": 2, "product_id": "prod_001"}
        ])

        order = repo._dict_to_order(row)
        assert len(order.items) == 1
        assert order.items[0].unit_price == Decimal("49.99")
        assert order.items[0].product_id == "prod_001"

    def test_legacy_items_with_name_only(self):
        """Items with 'name' but no 'title' or 'product_id' must get defaults."""
        from microservices.order_service.order_repository import OrderRepository

        repo = OrderRepository.__new__(OrderRepository)
        row = _make_order_row([
            {"name": "Premium Subscription", "quantity": 1, "price": 99.99}
        ])

        order = repo._dict_to_order(row)
        assert len(order.items) == 1
        assert order.items[0].unit_price == Decimal("99.99")
        assert order.items[0].product_id is not None  # should have a default

    def test_modern_items_with_unit_price(self):
        """Items already using 'unit_price' must pass through unchanged."""
        from microservices.order_service.order_repository import OrderRepository

        repo = OrderRepository.__new__(OrderRepository)
        row = _make_order_row([
            {"product_id": "prod_001", "quantity": 1, "unit_price": "25.00"}
        ])

        order = repo._dict_to_order(row)
        assert len(order.items) == 1
        assert order.items[0].unit_price == Decimal("25.00")

    def test_empty_items_list(self):
        """Empty items list must not crash."""
        from microservices.order_service.order_repository import OrderRepository

        repo = OrderRepository.__new__(OrderRepository)
        row = _make_order_row([])

        order = repo._dict_to_order(row)
        assert order.items == []

    def test_mixed_legacy_and_modern_items(self):
        """Mix of legacy and modern item formats."""
        from microservices.order_service.order_repository import OrderRepository

        repo = OrderRepository.__new__(OrderRepository)
        row = _make_order_row([
            {"name": "Old Item", "price": 10.00, "quantity": 1, "product_id": "prod_old"},
            {"product_id": "prod_new", "quantity": 2, "unit_price": "20.00"},
        ])

        order = repo._dict_to_order(row)
        assert len(order.items) == 2
        assert order.items[0].unit_price == Decimal("10.00")
        assert order.items[1].unit_price == Decimal("20.00")
