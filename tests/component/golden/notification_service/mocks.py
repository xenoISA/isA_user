"""
Notification Service - Mock Dependencies (Golden)

Mock implementations for component golden testing.
These mocks simulate external dependencies (repository, event bus, clients)
without requiring real infrastructure.

Usage:
    from tests.component.golden.notification_service.mocks import (
        MockNotificationRepository,
        MockEventBus,
        MockAccountClient,
    )
"""

from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, Any, List
import uuid


class MockNotificationRepository:
    """
    Mock notification repository for golden component testing.

    Simple mock that allows tests to override return_value for each method.
    Create methods return the input data by default.
    """

    def __init__(self):
        # Template methods - create returns input
        self.create_template = AsyncMock(side_effect=lambda x: x)
        self.get_template = AsyncMock(return_value=None)
        self.list_templates = AsyncMock(return_value=[])
        self.update_template = AsyncMock(return_value=True)
        self.delete_template = AsyncMock(return_value=True)

        # Notification methods - create returns input
        self.create_notification = AsyncMock(side_effect=lambda x: x)
        self.get_notification = AsyncMock(return_value=None)
        self.update_notification_status = AsyncMock(return_value=True)
        self.list_user_notifications = AsyncMock(return_value=[])
        self.get_pending_notifications = AsyncMock(return_value=[])

        # Batch methods - create returns input
        self.create_batch = AsyncMock(side_effect=lambda x: x)
        self.get_batch = AsyncMock(return_value=None)
        self.update_batch_stats = AsyncMock(return_value=True)

        # In-app notification methods - create returns input
        self.create_in_app_notification = AsyncMock(side_effect=lambda x: x)
        self.get_in_app_notification = AsyncMock(return_value=None)
        self.list_user_in_app_notifications = AsyncMock(return_value=[])
        self.mark_notification_as_read = AsyncMock(return_value=True)
        self.mark_notification_as_archived = AsyncMock(return_value=True)
        self.get_unread_count = AsyncMock(return_value=0)

        # Push subscription methods - create returns input
        self.register_push_subscription = AsyncMock(side_effect=lambda x: x)
        self.get_user_push_subscriptions = AsyncMock(return_value=[])
        self.unsubscribe_push = AsyncMock(return_value=True)
        self.update_push_last_used = AsyncMock(return_value=True)

        # Stats methods
        self.get_notification_stats = AsyncMock(return_value={
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "total_pending": 0,
            "by_type": {},
            "by_status": {},
        })


class MockEventBus:
    """Mock NATS event bus for golden component testing."""

    def __init__(self):
        self.published_events: List[Any] = []
        self.publish = AsyncMock(side_effect=self._publish)
        self.publish_event = AsyncMock(side_effect=self._publish)

    async def _publish(self, event: Any) -> None:
        """Track published event"""
        self.published_events.append(event)

    def get_published_events(self, event_type: Optional[str] = None) -> List[Any]:
        """Get published events, optionally filtered by type"""
        if event_type is None:
            return self.published_events
        return [
            e for e in self.published_events
            if hasattr(e, 'type') and e.type == event_type
            or isinstance(e, dict) and e.get('type') == event_type
        ]

    def assert_event_published(self, event_type: str) -> None:
        """Assert that an event of given type was published"""
        events = self.get_published_events(event_type)
        assert len(events) > 0, f"Expected event '{event_type}' to be published"

    def clear(self):
        """Clear all published events"""
        self.published_events.clear()


class MockAccountClient:
    """Mock Account Service client for testing"""

    def __init__(self):
        self.get_user = AsyncMock(return_value=None)
        self.get_user_email = AsyncMock(return_value=None)
        self.close = AsyncMock()


class MockOrganizationClient:
    """Mock Organization Service client for testing"""

    def __init__(self):
        self.get_organization = AsyncMock(return_value=None)
        self.get_organization_members = AsyncMock(return_value=[])
        self.close = AsyncMock()


class MockEmailClient:
    """Mock email client (Resend) for testing"""

    def __init__(self):
        self.sent_emails: List[Dict] = []
        self.post = AsyncMock(side_effect=self._send_email)
        self.aclose = AsyncMock()

    async def _send_email(self, url: str, json: Dict = None, **kwargs) -> MagicMock:
        """Simulate email sending"""
        self.sent_emails.append(json or {})
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"id": f"email_{uuid.uuid4().hex[:12]}"}
        return response

    def clear(self):
        """Clear sent emails"""
        self.sent_emails.clear()
