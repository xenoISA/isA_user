"""
Unit Tests �� Admin Audit Event Handler

L1: Verifies event parsing, idempotency, and error handling
with a mocked repository.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from microservices.audit_service.events.admin_audit_handler import AdminAuditEventHandler
from microservices.audit_service.admin_audit_models import AdminAuditLogEntry


def _make_event(data=None, event_id="evt_001"):
    """Create a mock NATS event"""
    event = MagicMock()
    event.id = event_id
    event.source = "admin_audit"
    event.data = data or {
        "admin_user_id": "admin_001",
        "admin_email": "admin@test.com",
        "action": "create_product",
        "resource_type": "product",
        "resource_id": "prod_123",
        "changes": {"after": {"name": "Widget"}},
        "ip_address": "10.0.0.1",
        "user_agent": "TestAgent",
        "timestamp": "2026-03-28T12:00:00",
        "metadata": {"source_service": "product_service"},
    }
    return event


class TestAdminAuditEventHandler:

    @pytest.mark.asyncio
    async def test_persists_admin_action_from_event(self):
        """Handler creates an admin audit log entry from event data"""
        mock_repo = AsyncMock()
        mock_entry = AdminAuditLogEntry(
            audit_id="admin_audit_abc123",
            admin_user_id="admin_001",
            action="create_product",
            resource_type="product",
        )
        mock_repo.create_admin_audit_entry = AsyncMock(return_value=mock_entry)

        handler = AdminAuditEventHandler(mock_repo)
        event = _make_event()

        await handler.handle_admin_action_event(event)

        mock_repo.create_admin_audit_entry.assert_called_once()
        entry_arg = mock_repo.create_admin_audit_entry.call_args[0][0]
        assert entry_arg.admin_user_id == "admin_001"
        assert entry_arg.action == "create_product"
        assert entry_arg.resource_type == "product"
        assert entry_arg.resource_id == "prod_123"
        assert entry_arg.changes == {"after": {"name": "Widget"}}

    @pytest.mark.asyncio
    async def test_idempotent_skips_duplicate_events(self):
        """Same event ID processed twice should only persist once"""
        mock_repo = AsyncMock()
        mock_repo.create_admin_audit_entry = AsyncMock(
            return_value=AdminAuditLogEntry(
                audit_id="x", admin_user_id="a", action="b", resource_type="c"
            )
        )

        handler = AdminAuditEventHandler(mock_repo)
        event = _make_event(event_id="evt_dup")

        await handler.handle_admin_action_event(event)
        await handler.handle_admin_action_event(event)

        assert mock_repo.create_admin_audit_entry.call_count == 1

    @pytest.mark.asyncio
    async def test_handles_missing_data_gracefully(self):
        """Event with no data should be skipped without error"""
        mock_repo = AsyncMock()
        handler = AdminAuditEventHandler(mock_repo)

        event = MagicMock()
        event.id = "evt_empty"
        event.data = None

        await handler.handle_admin_action_event(event)
        mock_repo.create_admin_audit_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_survives_repo_failure(self):
        """Handler does not raise when repository fails (fail-open)"""
        mock_repo = AsyncMock()
        mock_repo.create_admin_audit_entry = AsyncMock(side_effect=Exception("DB down"))

        handler = AdminAuditEventHandler(mock_repo)
        event = _make_event(event_id="evt_fail")

        # Should not raise
        await handler.handle_admin_action_event(event)

    @pytest.mark.asyncio
    async def test_parses_timestamp_from_event(self):
        """Timestamp from event data is parsed into the entry"""
        mock_repo = AsyncMock()
        mock_repo.create_admin_audit_entry = AsyncMock(
            return_value=AdminAuditLogEntry(
                audit_id="x", admin_user_id="a", action="b", resource_type="c"
            )
        )

        handler = AdminAuditEventHandler(mock_repo)
        event = _make_event()

        await handler.handle_admin_action_event(event)

        entry = mock_repo.create_admin_audit_entry.call_args[0][0]
        assert entry.timestamp == datetime(2026, 3, 28, 12, 0, 0)

    @pytest.mark.asyncio
    async def test_metadata_includes_nats_event_id(self):
        """Persisted entry metadata includes the NATS event ID for traceability"""
        mock_repo = AsyncMock()
        mock_repo.create_admin_audit_entry = AsyncMock(
            return_value=AdminAuditLogEntry(
                audit_id="x", admin_user_id="a", action="b", resource_type="c"
            )
        )

        handler = AdminAuditEventHandler(mock_repo)
        event = _make_event(event_id="evt_trace")

        await handler.handle_admin_action_event(event)

        entry = mock_repo.create_admin_audit_entry.call_args[0][0]
        assert entry.metadata["nats_event_id"] == "evt_trace"
        assert entry.metadata["nats_source"] == "admin_audit"
