"""
Notification Service Processing - Component Golden Tests

Focus:
- direct sends claim notifications before delivery
- background polling processes already-claimed notifications without re-claiming
"""

from unittest.mock import AsyncMock

import pytest

from tests.component.golden.notification_service.mocks import (
    MockAccountClient,
    MockEmailClient,
    MockEventBus,
    MockNotificationRepository,
    MockOrganizationClient,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio, pytest.mark.golden]


@pytest.fixture
def mock_notification_repository():
    """Create a fresh MockNotificationRepository"""
    return MockNotificationRepository()


@pytest.fixture
def notification_service(mock_notification_repository):
    """Create NotificationService with all mock dependencies injected"""
    from microservices.notification_service.notification_service import NotificationService

    return NotificationService(
        event_bus=MockEventBus(),
        repository=mock_notification_repository,
        account_client=MockAccountClient(),
        organization_client=MockOrganizationClient(),
        email_client=MockEmailClient(),
    )


class TestNotificationProcessingGolden:
    """Characterization of claim-aware processing behavior"""

    async def test_process_notification_claims_before_direct_send(
        self,
        notification_service,
        mock_notification_repository,
    ):
        """GOLDEN: direct sends claim pending rows before delivery"""
        from microservices.notification_service.models import Notification, NotificationType

        notification = Notification(
            notification_id="ntf_direct_123",
            type=NotificationType.EMAIL,
            recipient_email="user@example.com",
            content="Hello",
        )
        notification_service._send_email_notification = AsyncMock()

        await notification_service._process_notification(notification)

        mock_notification_repository.claim_notification.assert_awaited_once_with(
            "ntf_direct_123"
        )
        notification_service._send_email_notification.assert_awaited_once_with(
            notification
        )

    async def test_process_notification_skips_send_when_claim_fails(
        self,
        notification_service,
        mock_notification_repository,
    ):
        """GOLDEN: direct sends exit early when another worker already claimed the row"""
        from microservices.notification_service.models import Notification, NotificationType

        notification = Notification(
            notification_id="ntf_direct_456",
            type=NotificationType.EMAIL,
            recipient_email="user@example.com",
            content="Hello",
        )
        mock_notification_repository.claim_notification.return_value = False
        notification_service._send_email_notification = AsyncMock()

        await notification_service._process_notification(notification)

        notification_service._send_email_notification.assert_not_awaited()

    async def test_process_pending_notifications_uses_already_claimed_rows(
        self,
        notification_service,
        mock_notification_repository,
    ):
        """GOLDEN: background loop processes rows already claimed by the repository"""
        from microservices.notification_service.models import Notification, NotificationType

        notification = Notification(
            notification_id="ntf_pending_123",
            type=NotificationType.EMAIL,
            recipient_email="user@example.com",
            content="Hello",
        )
        mock_notification_repository.get_pending_notifications.return_value = [notification]
        notification_service._process_notification = AsyncMock()

        processed = await notification_service.process_pending_notifications()

        assert processed == 1
        notification_service._process_notification.assert_awaited_once_with(
            notification,
            claim_if_pending=False,
        )
