"""
Audit Service Event Handlers

事件订阅处理器 - 订阅所有服务的事件并记录审计日志
"""

import logging
from typing import Optional
from ..models import (
    AuditEventCreateRequest, EventSeverity,
    EventStatus, AuditCategory, EventType
)

logger = logging.getLogger(__name__)


class AuditEventHandlers:
    """审计服务事件处理器"""

    def __init__(self, audit_service):
        """
        初始化事件处理器

        Args:
            audit_service: AuditService 实例
        """
        self.audit_service = audit_service
        self.processed_event_ids = set()  # For idempotency

    async def handle_nats_event(self, event):
        """
        Handle events from NATS event bus
        Logs all events to audit trail for compliance and security monitoring
        """
        try:
            # Check idempotency
            if event.id in self.processed_event_ids:
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            # Extract event details
            event_type_str = event.type
            source = event.source
            data = event.data
            timestamp = event.timestamp
            metadata = event.metadata or {}

            # Map NATS event to audit event type
            audit_event_type = self._map_nats_event_to_audit_type(event_type_str)
            category = self._determine_audit_category(event_type_str)
            severity = self._determine_event_severity(event_type_str, data)

            # Extract user_id from event data
            user_id = data.get("user_id") or data.get("shared_by") or data.get("added_by") or "system"
            organization_id = data.get("organization_id")

            # Determine resource information
            resource_type, resource_id, resource_name = self._extract_resource_info(event_type_str, data)

            # Build description
            description = f"NATS event: {event_type_str} from {source}"

            # Create audit event request
            audit_request = AuditEventCreateRequest(
                event_type=audit_event_type,
                category=category,
                severity=severity,
                action=event_type_str,
                description=description,
                user_id=user_id,
                session_id=None,
                organization_id=organization_id,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                ip_address=None,
                user_agent=None,
                api_endpoint=None,
                http_method=None,
                success=True,  # NATS events are typically success events
                error_code=None,
                error_message=None,
                metadata={
                    "nats_event_id": event.id,
                    "nats_event_source": source,
                    "nats_event_type": event_type_str,
                    "nats_timestamp": timestamp,
                    "original_data": data,
                    **metadata
                },
                tags=["nats_event", source, event_type_str]
            )

            # Log the audit event
            result = await self.audit_service.log_event(audit_request)

            if result:
                # Mark as processed
                self.processed_event_ids.add(event.id)
                # Limit cache size
                if len(self.processed_event_ids) > 10000:
                    self.processed_event_ids = set(list(self.processed_event_ids)[5000:])

                logger.info(f"Logged NATS event {event.id} ({event_type_str}) to audit trail")
            else:
                logger.error(f"Failed to log NATS event {event.id} to audit trail")

        except Exception as e:
            logger.error(f"Failed to handle NATS event {event.id}: {e}")

    def _map_nats_event_to_audit_type(self, nats_event_type: str) -> EventType:
        """Map NATS event type to audit EventType"""
        # Map based on event type patterns
        if "user." in nats_event_type:
            if "created" in nats_event_type:
                return "user.registered"
            elif "updated" in nats_event_type or "logged_in" in nats_event_type:
                return "user.logged_in" if "logged_in" in nats_event_type else "user.updated"
            elif "deleted" in nats_event_type:
                return "user.deleted"
        elif "payment." in nats_event_type or "subscription." in nats_event_type:
            return "audit.resource.update"  # Payment/subscription events as resource updates
        elif "organization." in nats_event_type:
            if "created" in nats_event_type:
                return "organization.created"
            elif "member_added" in nats_event_type:
                return "organization.member_added"
            elif "member_removed" in nats_event_type:
                return "organization.member_removed"
            else:
                return "organization.updated"
        elif "device." in nats_event_type:
            if "registered" in nats_event_type:
                return "resource.created"
            else:
                return "audit.resource.update"
        elif "file." in nats_event_type:
            if "uploaded" in nats_event_type:
                return "resource.created"
            elif "deleted" in nats_event_type:
                return "resource.deleted"
            elif "shared" in nats_event_type:
                return "authorization.permission.granted"

        # Default to resource access
        return "audit.resource.access"

    def _determine_audit_category(self, nats_event_type: str) -> AuditCategory:
        """Determine audit category based on event type"""
        if "user." in nats_event_type or "device.authenticated" in nats_event_type:
            return AuditCategory.AUTHENTICATION
        elif "permission" in nats_event_type or "member" in nats_event_type or "file.shared" in nats_event_type:
            return AuditCategory.AUTHORIZATION
        elif "payment" in nats_event_type or "subscription" in nats_event_type:
            return AuditCategory.CONFIGURATION  # Use CONFIGURATION instead of FINANCIAL
        elif "file." in nats_event_type or "device." in nats_event_type:
            return AuditCategory.DATA_ACCESS

        return AuditCategory.SYSTEM

    def _determine_event_severity(self, nats_event_type: str, data: dict) -> EventSeverity:
        """Determine event severity"""
        # High severity events
        if any(keyword in nats_event_type for keyword in ["deleted", "removed", "failed", "offline"]):
            return EventSeverity.HIGH
        # Medium severity events
        elif any(keyword in nats_event_type for keyword in ["updated", "shared", "member_added"]):
            return EventSeverity.MEDIUM
        # Low severity events
        else:
            return EventSeverity.LOW

    def _extract_resource_info(self, nats_event_type: str, data: dict) -> tuple:
        """Extract resource information from event"""
        resource_type = None
        resource_id = None
        resource_name = None

        # Determine resource based on event type
        if "payment" in nats_event_type or "subscription" in nats_event_type:
            resource_type = "payment"
            resource_id = data.get("payment_id") or data.get("subscription_id")
        elif "organization" in nats_event_type:
            resource_type = "organization"
            resource_id = data.get("organization_id")
            resource_name = data.get("organization_name")
        elif "device" in nats_event_type:
            resource_type = "device"
            resource_id = data.get("device_id")
            resource_name = data.get("device_name")
        elif "file" in nats_event_type:
            resource_type = "file"
            resource_id = data.get("file_id") or data.get("share_id")
            resource_name = data.get("file_name")

        return resource_type, resource_id, resource_name
