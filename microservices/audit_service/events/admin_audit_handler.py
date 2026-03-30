"""
Admin Audit Event Handler

Subscribes to admin.action.* NATS events and persists them
to the admin_audit_log table.
"""

import logging
import uuid
from datetime import datetime, timezone

from ..admin_audit_models import AdminAuditLogEntry
from ..admin_audit_repository import AdminAuditRepository

logger = logging.getLogger(__name__)


class AdminAuditEventHandler:
    """Handles admin.action.* NATS events"""

    def __init__(self, admin_audit_repo: AdminAuditRepository):
        self.repo = admin_audit_repo
        self._processed_ids: set = set()

    async def handle_admin_action_event(self, event):
        """
        Handle an admin.action.* event from NATS.

        Persists the action to admin_audit_log.
        Idempotent: skips duplicate event IDs.
        """
        try:
            # Idempotency check
            if event.id in self._processed_ids:
                logger.debug(f"Admin audit event {event.id} already processed, skipping")
                return

            data = event.data
            if not data:
                logger.warning(f"Admin audit event {event.id} has no data, skipping")
                return

            # Parse timestamp
            ts_str = data.get("timestamp")
            if ts_str:
                try:
                    timestamp = datetime.fromisoformat(ts_str)
                except (ValueError, TypeError):
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            entry = AdminAuditLogEntry(
                audit_id=f"admin_audit_{uuid.uuid4().hex[:16]}",
                admin_user_id=data.get("admin_user_id", "unknown"),
                admin_email=data.get("admin_email"),
                action=data.get("action", "unknown"),
                resource_type=data.get("resource_type", "unknown"),
                resource_id=data.get("resource_id"),
                changes=data.get("changes", {}),
                ip_address=data.get("ip_address"),
                user_agent=data.get("user_agent"),
                timestamp=timestamp,
                metadata={
                    "nats_event_id": event.id,
                    "nats_source": event.source,
                    **(data.get("metadata") or {}),
                },
            )

            result = await self.repo.create_admin_audit_entry(entry)

            if result:
                self._processed_ids.add(event.id)
                # Cap cache size
                if len(self._processed_ids) > 10000:
                    self._processed_ids = set(list(self._processed_ids)[5000:])
                logger.info(
                    f"Persisted admin audit: {entry.action} on {entry.resource_type}"
                    f" by {entry.admin_user_id} (audit_id={entry.audit_id})"
                )
            else:
                logger.error(f"Failed to persist admin audit event {event.id}")

        except Exception as e:
            # Fail-open: log but don't crash the consumer loop
            logger.error(f"Error handling admin audit event {getattr(event, 'id', '?')}: {e}")
