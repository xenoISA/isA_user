"""Unit tests for order_repository _dict_to_order datetime handling (Issue #141).

asyncpg returns native datetime objects, but _dict_to_order assumes string
timestamps and calls .replace('Z', '+00:00') which fails with:
  TypeError: 'str' object cannot be interpreted as an integer
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


def _make_order_row(**overrides):
    """Create a minimal order dict as asyncpg would return it."""
    now = datetime.now(timezone.utc)
    base = {
        "order_id": "order_test_001",
        "user_id": "user_001",
        "order_type": "purchase",
        "status": "pending",
        "payment_status": "pending",
        "total_amount": Decimal("10.00"),
        "currency": "USD",
        "payment_method": None,
        "payment_intent_id": None,
        "subscription_id": None,
        "wallet_id": None,
        "items": "[]",
        "subtotal_amount": Decimal("10.00"),
        "tax_amount": Decimal("0.00"),
        "shipping_amount": Decimal("0.00"),
        "discount_amount": Decimal("0.00"),
        "final_amount": Decimal("10.00"),
        "fulfillment_status": "pending",
        "tracking_number": None,
        "shipping_address": None,
        "billing_address": None,
        "metadata": None,
        "created_at": now,      # asyncpg returns datetime, not string
        "updated_at": now,      # asyncpg returns datetime, not string
        "completed_at": None,
        "expires_at": None,
    }
    base.update(overrides)
    return base


class TestDictToOrderDatetimeHandling:
    """Verify _dict_to_order handles both datetime objects and ISO strings."""

    def test_handles_native_datetime_objects(self):
        """asyncpg returns datetime objects — must not crash."""
        from microservices.order_service.order_repository import OrderRepository

        repo = OrderRepository.__new__(OrderRepository)
        row = _make_order_row()

        order = repo._dict_to_order(row)
        assert order.created_at is not None
        assert isinstance(order.created_at, datetime)

    def test_handles_iso_string_timestamps(self):
        """Fallback: if timestamps are strings (e.g. from JSON), parse them."""
        from microservices.order_service.order_repository import OrderRepository

        repo = OrderRepository.__new__(OrderRepository)
        row = _make_order_row(
            created_at="2026-03-18T01:00:00Z",
            updated_at="2026-03-18T01:00:00+00:00",
        )

        order = repo._dict_to_order(row)
        assert order.created_at is not None
        assert isinstance(order.created_at, datetime)

    def test_handles_optional_datetime_fields(self):
        """completed_at and expires_at can be None."""
        from microservices.order_service.order_repository import OrderRepository

        repo = OrderRepository.__new__(OrderRepository)
        row = _make_order_row(completed_at=None, expires_at=None)

        order = repo._dict_to_order(row)
        assert order.completed_at is None
        assert order.expires_at is None

    def test_handles_optional_datetime_as_native(self):
        """completed_at/expires_at as datetime objects."""
        from microservices.order_service.order_repository import OrderRepository

        repo = OrderRepository.__new__(OrderRepository)
        now = datetime.now(timezone.utc)
        row = _make_order_row(completed_at=now, expires_at=now)

        order = repo._dict_to_order(row)
        assert isinstance(order.completed_at, datetime)
        assert isinstance(order.expires_at, datetime)
