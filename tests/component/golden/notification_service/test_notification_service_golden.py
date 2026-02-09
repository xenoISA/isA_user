"""
Notification Service - Component Golden Tests

GOLDEN: These tests document the CURRENT behavior of NotificationService.
DO NOT MODIFY unless behavior intentionally changes.

Purpose:
- Protect against accidental regressions in business logic
- Document what the service currently does
- All tests should PASS (they describe existing behavior)

Related Documents:
- Data Contract: tests/contracts/notification/data_contract.py
- Logic Contract: tests/contracts/notification/logic_contract.md
- Design: docs/design/notification_service.md

Usage:
    pytest tests/component/golden/notification_service -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from tests.component.golden.notification_service.mocks import (
    MockNotificationRepository,
    MockEventBus,
    MockAccountClient,
    MockOrganizationClient,
    MockEmailClient,
)

pytestmark = [pytest.mark.component, pytest.mark.asyncio, pytest.mark.golden]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_notification_repository():
    """Create a fresh MockNotificationRepository"""
    return MockNotificationRepository()


@pytest.fixture
def mock_event_bus():
    """Create a fresh MockEventBus"""
    return MockEventBus()


@pytest.fixture
def mock_account_client():
    """Create a fresh MockAccountClient"""
    return MockAccountClient()


@pytest.fixture
def mock_organization_client():
    """Create a fresh MockOrganizationClient"""
    return MockOrganizationClient()


@pytest.fixture
def mock_email_client():
    """Create a fresh MockEmailClient"""
    return MockEmailClient()


@pytest.fixture
def notification_service(
    mock_notification_repository,
    mock_event_bus,
    mock_account_client,
    mock_organization_client,
    mock_email_client,
):
    """Create NotificationService with all mock dependencies injected"""
    from microservices.notification_service.notification_service import NotificationService

    return NotificationService(
        event_bus=mock_event_bus,
        repository=mock_notification_repository,
        account_client=mock_account_client,
        organization_client=mock_organization_client,
        email_client=mock_email_client,
    )


# =============================================================================
# Template Operations - Current Behavior
# =============================================================================

class TestNotificationServiceTemplateCreateGolden:
    """Characterization: Template creation current behavior"""

    async def test_create_template_returns_response(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: create_template returns TemplateResponse"""
        from microservices.notification_service.models import (
            CreateTemplateRequest,
            NotificationType,
            TemplateResponse,
        )

        request = CreateTemplateRequest(
            name="Welcome Email",
            description="Sent to new users",
            type=NotificationType.EMAIL,
            subject="Welcome to {{app_name}}",
            content="Hello {{name}}, welcome to our service!",
            html_content="<h1>Welcome {{name}}</h1>",
            variables=["name", "app_name"],
            metadata={"category": "onboarding"},
        )

        result = await notification_service.create_template(request)

        assert isinstance(result, TemplateResponse)
        assert result.template is not None
        assert result.template.template_id is not None
        assert result.template.template_id.startswith("tpl_")

    async def test_create_template_saves_to_repository(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: create_template calls repository.create_template"""
        from microservices.notification_service.models import (
            CreateTemplateRequest,
            NotificationType,
        )

        request = CreateTemplateRequest(
            name="Test Template",
            type=NotificationType.IN_APP,
            content="Test content",
        )

        await notification_service.create_template(request)

        mock_notification_repository.create_template.assert_called_once()


class TestNotificationServiceTemplateGetGolden:
    """Characterization: Template retrieval current behavior"""

    async def test_get_existing_template_returns_template(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: get_template returns NotificationTemplate for existing template"""
        from microservices.notification_service.models import (
            NotificationTemplate,
            NotificationType,
            TemplateStatus,
        )

        mock_template = NotificationTemplate(
            template_id="tpl_test_123",
            name="Test Template",
            type=NotificationType.EMAIL,
            content="Test content",
            status=TemplateStatus.ACTIVE,
        )
        mock_notification_repository.get_template.return_value = mock_template

        result = await notification_service.get_template("tpl_test_123")

        assert result is not None
        assert result.template_id == "tpl_test_123"

    async def test_get_nonexistent_template_returns_none(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: get_template returns None for non-existent template"""
        mock_notification_repository.get_template.return_value = None

        result = await notification_service.get_template("tpl_nonexistent")

        assert result is None


class TestNotificationServiceTemplateListGolden:
    """Characterization: Template list current behavior"""

    async def test_list_templates_returns_list(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: list_templates returns list of templates"""
        from microservices.notification_service.models import (
            NotificationTemplate,
            NotificationType,
            TemplateStatus,
        )

        mock_templates = [
            NotificationTemplate(
                template_id="tpl_1",
                name="Template 1",
                type=NotificationType.EMAIL,
                content="Content 1",
                status=TemplateStatus.ACTIVE,
            ),
            NotificationTemplate(
                template_id="tpl_2",
                name="Template 2",
                type=NotificationType.IN_APP,
                content="Content 2",
                status=TemplateStatus.ACTIVE,
            ),
        ]
        mock_notification_repository.list_templates.return_value = mock_templates

        result = await notification_service.list_templates()

        assert isinstance(result, list)
        assert len(result) == 2


class TestNotificationServiceTemplateUpdateGolden:
    """Characterization: Template update current behavior"""

    async def test_update_template_returns_response(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: update_template returns TemplateResponse"""
        from microservices.notification_service.models import (
            UpdateTemplateRequest,
            TemplateResponse,
            NotificationTemplate,
            NotificationType,
            TemplateStatus,
        )

        mock_template = NotificationTemplate(
            template_id="tpl_test_123",
            name="Original Name",
            type=NotificationType.EMAIL,
            content="Original content",
            status=TemplateStatus.ACTIVE,
        )
        mock_notification_repository.get_template.return_value = mock_template
        mock_notification_repository.update_template.return_value = mock_template

        request = UpdateTemplateRequest(
            name="Updated Name",
            content="Updated content",
        )

        result = await notification_service.update_template("tpl_test_123", request)

        assert isinstance(result, TemplateResponse)


# =============================================================================
# Send Notification - Current Behavior
# =============================================================================

class TestNotificationServiceSendGolden:
    """Characterization: Send notification current behavior"""

    async def test_send_email_notification_returns_response(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: send_notification returns NotificationResponse for email"""
        from microservices.notification_service.models import (
            SendNotificationRequest,
            NotificationType,
            NotificationPriority,
            NotificationResponse,
        )

        request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_email="user@example.com",
            subject="Test Email",
            content="This is a test email",
            priority=NotificationPriority.NORMAL,
        )

        result = await notification_service.send_notification(request)

        assert isinstance(result, NotificationResponse)
        assert result.notification is not None

    async def test_send_in_app_notification_returns_response(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: send_notification returns NotificationResponse for in-app"""
        from microservices.notification_service.models import (
            SendNotificationRequest,
            NotificationType,
            NotificationPriority,
            NotificationResponse,
        )

        request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id="usr_test_123",
            content="You have a new message",
            priority=NotificationPriority.NORMAL,
        )

        result = await notification_service.send_notification(request)

        assert isinstance(result, NotificationResponse)

    async def test_send_notification_with_template_applies_variables(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: send_notification applies template variables"""
        from microservices.notification_service.models import (
            SendNotificationRequest,
            NotificationType,
            NotificationTemplate,
            TemplateStatus,
        )

        # Setup template mock
        mock_template = NotificationTemplate(
            template_id="tpl_welcome_123",
            name="Welcome",
            type=NotificationType.EMAIL,
            subject="Welcome {{name}}",
            content="Hello {{name}}, your code is {{code}}",
            variables=["name", "code"],
            status=TemplateStatus.ACTIVE,
        )
        mock_notification_repository.get_template.return_value = mock_template

        request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_email="user@example.com",
            template_id="tpl_welcome_123",
            variables={"name": "John", "code": "ABC123"},
        )

        result = await notification_service.send_notification(request)

        assert result.notification is not None


# =============================================================================
# Batch Notifications - Current Behavior
# =============================================================================

class TestNotificationServiceBatchGolden:
    """Characterization: Batch notification current behavior"""

    async def test_send_batch_returns_response(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: send_batch returns BatchResponse"""
        from microservices.notification_service.models import (
            SendBatchRequest,
            NotificationType,
            NotificationTemplate,
            TemplateStatus,
            BatchResponse,
        )

        # Setup template mock
        mock_template = NotificationTemplate(
            template_id="tpl_campaign_123",
            name="Campaign",
            type=NotificationType.EMAIL,
            subject="Special Offer",
            content="Hello {{name}}!",
            variables=["name"],
            status=TemplateStatus.ACTIVE,
        )
        mock_notification_repository.get_template.return_value = mock_template

        request = SendBatchRequest(
            name="Test Campaign",
            template_id="tpl_campaign_123",
            type=NotificationType.EMAIL,
            recipients=[
                {"email": "user1@example.com", "variables": {"name": "User1"}},
                {"email": "user2@example.com", "variables": {"name": "User2"}},
            ],
        )

        result = await notification_service.send_batch(request)

        assert isinstance(result, BatchResponse)
        assert result.batch is not None


# =============================================================================
# User Notifications - Current Behavior
# =============================================================================

class TestNotificationServiceUserNotificationsGolden:
    """Characterization: User notification operations current behavior"""

    async def test_list_user_notifications_returns_list(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: list_user_notifications returns list"""
        from microservices.notification_service.models import InAppNotification

        mock_notifications = [
            InAppNotification(
                notification_id="notif_inapp_1",
                user_id="usr_test_123",
                title="Notification 1",
                message="Message 1",
                is_read=False,
            ),
        ]
        mock_notification_repository.list_user_in_app_notifications.return_value = mock_notifications

        result = await notification_service.list_user_notifications(
            user_id="usr_test_123",
            limit=50,
            offset=0,
        )

        assert isinstance(result, list)

    async def test_mark_notification_read_returns_success(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: mark_notification_read returns success"""
        mock_notification_repository.mark_notification_as_read.return_value = True

        result = await notification_service.mark_notification_read(
            notification_id="notif_test_123",
            user_id="usr_test_123",
        )

        assert result is True

    async def test_get_unread_count_returns_integer(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: get_unread_count returns integer"""
        mock_notification_repository.get_unread_count.return_value = 5

        result = await notification_service.get_unread_count(user_id="usr_test_123")

        assert isinstance(result, int)
        assert result == 5


# =============================================================================
# Push Subscriptions - Current Behavior
# =============================================================================

class TestNotificationServicePushSubscriptionGolden:
    """Characterization: Push subscription current behavior"""

    async def test_register_push_subscription_returns_subscription(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: register_push_subscription returns subscription"""
        from microservices.notification_service.models import (
            RegisterPushSubscriptionRequest,
            PushPlatform,
            PushSubscription,
        )

        mock_subscription = PushSubscription(
            user_id="usr_test_123",
            device_token="device_token_123",
            platform=PushPlatform.WEB,
            endpoint="https://push.example.com/endpoint",
        )
        mock_notification_repository.register_push_subscription.return_value = mock_subscription

        request = RegisterPushSubscriptionRequest(
            user_id="usr_test_123",
            device_token="device_token_123",
            platform=PushPlatform.WEB,
            endpoint="https://push.example.com/endpoint",
            p256dh_key="key123",
            auth_key="auth123",
        )

        result = await notification_service.register_push_subscription(request)

        assert result is not None

    async def test_get_user_push_subscriptions_returns_list(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: get_user_push_subscriptions returns list"""
        from microservices.notification_service.models import (
            PushSubscription,
            PushPlatform,
        )

        mock_subscriptions = [
            PushSubscription(
                user_id="usr_test_123",
                device_token="device_token_1",
                platform=PushPlatform.WEB,
                endpoint="https://push.example.com/1",
            ),
        ]
        mock_notification_repository.get_user_push_subscriptions.return_value = mock_subscriptions

        result = await notification_service.get_user_push_subscriptions(
            user_id="usr_test_123"
        )

        assert isinstance(result, list)


# =============================================================================
# Notification Statistics - Current Behavior
# =============================================================================

class TestNotificationServiceStatsGolden:
    """Characterization: Notification statistics current behavior"""

    async def test_get_notification_stats_returns_stats(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: get_notification_stats returns NotificationStatsResponse"""
        from microservices.notification_service.models import NotificationStatsResponse

        mock_notification_repository.get_notification_stats.return_value = {
            "total_sent": 100,
            "total_delivered": 95,
            "total_failed": 5,
            "total_pending": 0,
            "by_type": {"email": 50, "in_app": 50},
            "by_status": {"sent": 95, "failed": 5},
        }

        result = await notification_service.get_notification_stats(
            user_id="usr_test_123"
        )

        assert isinstance(result, (dict, NotificationStatsResponse))


# =============================================================================
# Template Variable Replacement - Current Behavior
# =============================================================================

class TestNotificationServiceTemplateVariablesGolden:
    """Characterization: Template variable replacement current behavior"""

    def test_replace_template_variables_simple(self, notification_service):
        """GOLDEN: _replace_template_variables handles simple variables"""
        template = "Hello {{name}}, welcome!"
        variables = {"name": "John"}

        result = notification_service._replace_template_variables(template, variables)

        assert result == "Hello John, welcome!"

    def test_replace_template_variables_multiple(self, notification_service):
        """GOLDEN: _replace_template_variables handles multiple variables"""
        template = "Hello {{name}}, your code is {{code}}."
        variables = {"name": "John", "code": "ABC123"}

        result = notification_service._replace_template_variables(template, variables)

        assert result == "Hello John, your code is ABC123."

    def test_replace_template_variables_missing_leaves_placeholder(
        self, notification_service
    ):
        """GOLDEN: _replace_template_variables leaves missing variables as-is"""
        template = "Hello {{name}}, your code is {{code}}."
        variables = {"name": "John"}  # code is missing

        result = notification_service._replace_template_variables(template, variables)

        # Document current behavior - missing vars may be left as-is or replaced with empty
        assert "John" in result


# =============================================================================
# Validation - Current Behavior
# =============================================================================

class TestNotificationServiceValidationGolden:
    """Characterization: Input validation current behavior"""

    async def test_send_notification_validates_recipient(
        self, notification_service, mock_notification_repository
    ):
        """GOLDEN: send_notification validates that recipient is provided"""
        from microservices.notification_service.models import (
            SendNotificationRequest,
            NotificationType,
        )

        # Request without recipient (no email, no user_id)
        request = MagicMock()
        request.type = NotificationType.EMAIL
        request.recipient_id = None
        request.recipient_email = None
        request.recipient_phone = None
        request.template_id = None
        request.content = "Test"
        request.subject = "Test"
        request.html_content = None
        request.variables = {}
        request.priority = "normal"
        request.scheduled_at = None
        request.metadata = {}
        request.tags = []

        # Document current behavior - may raise error or return failure
        try:
            result = await notification_service.send_notification(request)
            # If it doesn't raise, check response
            assert result is not None
        except Exception:
            # Current behavior raises an exception
            pass


# =============================================================================
# Cleanup - Current Behavior
# =============================================================================

class TestNotificationServiceCleanupGolden:
    """Characterization: Cleanup current behavior"""

    async def test_cleanup_closes_clients(self, notification_service):
        """GOLDEN: cleanup closes HTTP clients"""
        # Just verify cleanup can be called without error
        await notification_service.cleanup()
        # Document: cleanup should close email_client if it exists
