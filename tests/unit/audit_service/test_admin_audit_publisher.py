"""
Unit Tests — Admin Audit Event Publisher (core/admin_audit.py)

L1: Pure logic, mocked event bus. Verifies:
- Event construction and NATS subject naming
- Fail-open behavior (never raises)
- Graceful handling of missing event bus
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.admin_audit import publish_admin_action


class TestPublishAdminAction:
    """Unit tests for publish_admin_action"""

    @pytest.mark.asyncio
    async def test_publishes_event_with_correct_subject(self):
        """Event is published to admin.action.{resource_type}.{action}"""
        mock_bus = AsyncMock()
        mock_bus.publish_event = AsyncMock(return_value=True)

        result = await publish_admin_action(
            event_bus=mock_bus,
            admin_user_id="admin_001",
            action="create_product",
            resource_type="product",
            resource_id="prod_123",
            changes={"after": {"name": "Widget"}},
        )

        assert result is True
        mock_bus.publish_event.assert_called_once()

        # Verify the subject
        call_args = mock_bus.publish_event.call_args
        event_arg = call_args[0][0]  # first positional arg
        subject_kwarg = call_args[1].get("subject")

        assert subject_kwarg == "admin.action.product.create_product"
        assert event_arg.type == "admin.action.product.create_product"
        assert event_arg.source == "admin_audit"

    @pytest.mark.asyncio
    async def test_event_data_contains_all_fields(self):
        """All provided fields appear in the event data payload"""
        mock_bus = AsyncMock()
        mock_bus.publish_event = AsyncMock(return_value=True)

        await publish_admin_action(
            event_bus=mock_bus,
            admin_user_id="admin_001",
            admin_email="admin@example.com",
            action="update_pricing",
            resource_type="pricing",
            resource_id="price_456",
            changes={"before": {"amount": 10}, "after": {"amount": 20}},
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            metadata={"product_id": "prod_789"},
        )

        event = mock_bus.publish_event.call_args[0][0]
        data = event.data

        assert data["admin_user_id"] == "admin_001"
        assert data["admin_email"] == "admin@example.com"
        assert data["action"] == "update_pricing"
        assert data["resource_type"] == "pricing"
        assert data["resource_id"] == "price_456"
        assert data["changes"]["before"]["amount"] == 10
        assert data["changes"]["after"]["amount"] == 20
        assert data["ip_address"] == "192.168.1.1"
        assert data["user_agent"] == "TestAgent/1.0"
        assert data["metadata"]["product_id"] == "prod_789"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_returns_false_when_event_bus_is_none(self):
        """When event_bus is None, returns False without raising"""
        result = await publish_admin_action(
            event_bus=None,
            admin_user_id="admin_001",
            action="create_product",
            resource_type="product",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_publish_error(self):
        """When publish_event raises, returns False (fail-open)"""
        mock_bus = AsyncMock()
        mock_bus.publish_event = AsyncMock(side_effect=Exception("NATS connection lost"))

        result = await publish_admin_action(
            event_bus=mock_bus,
            admin_user_id="admin_001",
            action="delete_product",
            resource_type="product",
            resource_id="prod_999",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_defaults_changes_and_metadata_to_empty_dicts(self):
        """When changes/metadata are not provided, they default to {}"""
        mock_bus = AsyncMock()
        mock_bus.publish_event = AsyncMock(return_value=True)

        await publish_admin_action(
            event_bus=mock_bus,
            admin_user_id="admin_001",
            action="create_product",
            resource_type="product",
        )

        data = mock_bus.publish_event.call_args[0][0].data
        assert data["changes"] == {}
        assert data["metadata"] == {}
        assert data["resource_id"] is None

    @pytest.mark.asyncio
    async def test_subject_uses_resource_type_and_action(self):
        """Subject format: admin.action.{resource_type}.{action}"""
        mock_bus = AsyncMock()
        mock_bus.publish_event = AsyncMock(return_value=True)

        await publish_admin_action(
            event_bus=mock_bus,
            admin_user_id="admin_001",
            action="rotate_cost_definitions",
            resource_type="cost_definition",
        )

        subject = mock_bus.publish_event.call_args[1]["subject"]
        assert subject == "admin.action.cost_definition.rotate_cost_definitions"
