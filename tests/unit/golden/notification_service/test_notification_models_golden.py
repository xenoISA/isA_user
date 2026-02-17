"""
Unit Tests for Notification Service Models

Tests core notification service models and business logic.
"""

import pytest
from datetime import datetime, timezone
from microservices.notification_service.models import (
    NotificationType,
    NotificationStatus,
    NotificationPriority,
    TemplateStatus,
    RecipientType,
    PushPlatform,
    Notification,
    NotificationTemplate,
    InAppNotification,
    NotificationBatch,
    PushSubscription,
    SendNotificationRequest,
    CreateTemplateRequest,
    RegisterPushSubscriptionRequest
)


class TestNotificationType:
    """Test NotificationType enum"""
    
    def test_notification_type_values(self):
        """Test all notification type values are defined"""
        assert NotificationType.EMAIL.value == "email"
        assert NotificationType.SMS.value == "sms"
        assert NotificationType.IN_APP.value == "in_app"
        assert NotificationType.PUSH.value == "push"
        assert NotificationType.WEBHOOK.value == "webhook"
    
    def test_notification_type_comparison(self):
        """Test notification type comparison"""
        # str(Enum) returns the name representation, .value returns the string value
        assert NotificationType.EMAIL.value == "email"
        assert NotificationType.EMAIL != NotificationType.SMS
        # Note: str() on str Enum in Python 3.11+ returns "ClassName.VALUE"
        assert NotificationType.EMAIL.value == "email"


class TestNotificationStatus:
    """Test NotificationStatus enum"""
    
    def test_notification_status_values(self):
        """Test all notification status values"""
        assert NotificationStatus.PENDING.value == "pending"
        assert NotificationStatus.SENDING.value == "sending"
        assert NotificationStatus.SENT.value == "sent"
        assert NotificationStatus.DELIVERED.value == "delivered"
        assert NotificationStatus.FAILED.value == "failed"
        assert NotificationStatus.BOUNCED.value == "bounced"
        assert NotificationStatus.CANCELLED.value == "cancelled"


class TestNotificationPriority:
    """Test NotificationPriority enum"""
    
    def test_notification_priority_values(self):
        """Test all priority values"""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


class TestNotificationTemplate:
    """Test NotificationTemplate model"""
    
    def test_template_creation_minimal(self):
        """Test template creation with minimal fields"""
        template = NotificationTemplate(
            template_id="tpl_test_123",
            name="Test Template",
            type=NotificationType.EMAIL,
            content="Hello {{name}}"
        )
        
        assert template.template_id == "tpl_test_123"
        assert template.name == "Test Template"
        assert template.type == NotificationType.EMAIL
        assert template.content == "Hello {{name}}"
        assert template.status == TemplateStatus.ACTIVE
        assert template.version == 1
        assert template.variables == []
    
    def test_template_creation_with_html(self):
        """Test template creation with HTML content"""
        template = NotificationTemplate(
            template_id="tpl_html_123",
            name="HTML Template",
            type=NotificationType.EMAIL,
            subject="Welcome {{name}}",
            content="Plain text",
            html_content="<h1>Hello {{name}}</h1>",
            variables=["name"]
        )
        
        assert template.subject == "Welcome {{name}}"
        assert template.html_content == "<h1>Hello {{name}}</h1>"
        assert template.variables == ["name"]
    
    def test_template_with_metadata(self):
        """Test template with metadata"""
        metadata = {"category": "welcome", "locale": "en"}
        template = NotificationTemplate(
            template_id="tpl_meta_123",
            name="Meta Template",
            type=NotificationType.EMAIL,
            content="Test content",
            metadata=metadata
        )
        
        assert template.metadata == metadata
    
    def test_template_accepts_empty_template_id(self):
        """CHAR: Model accepts empty template_id (no min_length validation)"""
        # Current behavior: no validation on empty strings
        template = NotificationTemplate(
            template_id="",
            name="Test",
            type=NotificationType.EMAIL,
            content="Test"
        )
        assert template.template_id == ""

    def test_template_accepts_empty_name(self):
        """CHAR: Model accepts empty name (no min_length validation)"""
        # Current behavior: no validation on empty strings
        template = NotificationTemplate(
            template_id="tpl_test_123",
            name="",
            type=NotificationType.EMAIL,
            content="Test"
        )
        assert template.name == ""


class TestNotification:
    """Test Notification model"""
    
    def test_notification_creation_minimal(self):
        """Test notification creation with minimal fields"""
        notification = Notification(
            notification_id="ntf_test_123",
            type=NotificationType.EMAIL,
            content="Test message"
        )
        
        assert notification.notification_id == "ntf_test_123"
        assert notification.type == NotificationType.EMAIL
        assert notification.content == "Test message"
        assert notification.priority == NotificationPriority.NORMAL
        assert notification.status == NotificationStatus.PENDING
        assert notification.retry_count == 0
        assert notification.max_retries == 3
    
    def test_notification_with_email_recipient(self):
        """Test notification with email recipient"""
        notification = Notification(
            notification_id="ntf_email_123",
            type=NotificationType.EMAIL,
            recipient_type=RecipientType.EMAIL,
            recipient_email="test@example.com",
            content="Email content"
        )
        
        assert notification.recipient_type == RecipientType.EMAIL
        assert notification.recipient_email == "test@example.com"
    
    def test_notification_with_template(self):
        """Test notification with template"""
        notification = Notification(
            notification_id="ntf_tpl_123",
            type=NotificationType.EMAIL,
            template_id="tpl_welcome_123",
            recipient_type=RecipientType.USER,
            recipient_id="user_123",
            content="Welcome {{name}}",
            variables={"name": "John"}
        )
        
        assert notification.template_id == "tpl_welcome_123"
        assert notification.variables == {"name": "John"}
    
    def test_notification_with_priority(self):
        """Test notification with high priority"""
        notification = Notification(
            notification_id="ntf_high_123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
            content="Urgent message"
        )
        
        assert notification.priority == NotificationPriority.HIGH
    
    def test_notification_with_scheduling(self):
        """Test notification with scheduling"""
        scheduled_time = datetime.now(timezone.utc)
        notification = Notification(
            notification_id="ntf_scheduled_123",
            type=NotificationType.EMAIL,
            scheduled_at=scheduled_time,
            content="Scheduled message"
        )
        
        assert notification.scheduled_at == scheduled_time
    
    def test_notification_with_metadata(self):
        """Test notification with metadata"""
        metadata = {"campaign": "welcome", "source": "registration"}
        notification = Notification(
            notification_id="ntf_meta_123",
            type=NotificationType.EMAIL,
            content="Message with metadata",
            metadata=metadata
        )
        
        assert notification.metadata == metadata
    
    def test_notification_accepts_empty_notification_id(self):
        """CHAR: Model accepts empty notification_id (no min_length validation)"""
        # Current behavior: no validation on empty strings
        notification = Notification(
            notification_id="",
            type=NotificationType.EMAIL,
            content="Test"
        )
        assert notification.notification_id == ""

    def test_notification_accepts_empty_content(self):
        """CHAR: Model accepts empty content (no min_length validation)"""
        # Current behavior: no validation on empty strings
        notification = Notification(
            notification_id="ntf_test_123",
            type=NotificationType.EMAIL,
            content=""
        )
        assert notification.content == ""


class TestInAppNotification:
    """Test InAppNotification model"""
    
    def test_in_app_notification_creation(self):
        """Test in-app notification creation"""
        notification = InAppNotification(
            notification_id="ntf_inapp_123",
            user_id="user_123",
            title="New Message",
            message="You have a new message"
        )
        
        assert notification.notification_id == "ntf_inapp_123"
        assert notification.user_id == "user_123"
        assert notification.title == "New Message"
        assert notification.message == "You have a new message"
        assert notification.priority == NotificationPriority.NORMAL
        assert notification.is_read is False
        assert notification.is_archived is False
    
    def test_in_app_notification_with_action(self):
        """Test in-app notification with action URL"""
        notification = InAppNotification(
            notification_id="ntf_action_123",
            user_id="user_123",
            title="Update Available",
            message="A new update is available",
            action_url="https://example.com/update"
        )
        
        assert notification.action_url == "https://example.com/update"
    
    def test_in_app_notification_with_category(self):
        """Test in-app notification with category"""
        notification = InAppNotification(
            notification_id="ntf_cat_123",
            user_id="user_123",
            title="System Alert",
            message="System maintenance scheduled",
            category="system"
        )
        
        assert notification.category == "system"
    
    def test_in_app_notification_mark_read(self):
        """Test marking in-app notification as read"""
        notification = InAppNotification(
            notification_id="ntf_read_123",
            user_id="user_123",
            title="Test",
            message="Test message"
        )
        
        read_time = datetime.now(timezone.utc)
        notification.is_read = True
        notification.read_at = read_time
        
        assert notification.is_read is True
        assert notification.read_at == read_time
    
    def test_in_app_notification_archive(self):
        """Test archiving in-app notification"""
        notification = InAppNotification(
            notification_id="ntf_archive_123",
            user_id="user_123",
            title="Test",
            message="Test message"
        )
        
        archive_time = datetime.now(timezone.utc)
        notification.is_archived = True
        notification.archived_at = archive_time
        
        assert notification.is_archived is True
        assert notification.archived_at == archive_time


class TestNotificationBatch:
    """Test NotificationBatch model"""
    
    def test_batch_creation_minimal(self):
        """Test batch creation with minimal fields"""
        recipients = [
            {"user_id": "user_1", "variables": {"name": "John"}},
            {"user_id": "user_2", "variables": {"name": "Jane"}}
        ]
        
        batch = NotificationBatch(
            batch_id="batch_test_123",
            template_id="tpl_welcome_123",
            type=NotificationType.EMAIL,
            recipients=recipients,
            total_recipients=2
        )
        
        assert batch.batch_id == "batch_test_123"
        assert batch.template_id == "tpl_welcome_123"
        assert batch.type == NotificationType.EMAIL
        assert batch.recipients == recipients
        assert batch.total_recipients == 2
        assert batch.priority == NotificationPriority.NORMAL
        assert batch.sent_count == 0
        assert batch.delivered_count == 0
        assert batch.failed_count == 0
    
    def test_batch_with_name_and_priority(self):
        """Test batch with name and high priority"""
        recipients = [{"user_id": "user_1"}]
        
        batch = NotificationBatch(
            batch_id="batch_priority_123",
            name="Welcome Campaign",
            template_id="tpl_welcome_123",
            type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
            recipients=recipients,
            total_recipients=1
        )
        
        assert batch.name == "Welcome Campaign"
        assert batch.priority == NotificationPriority.HIGH
    
    def test_batch_progress_tracking(self):
        """Test batch progress tracking"""
        recipients = [{"user_id": "user_1"}]
        
        batch = NotificationBatch(
            batch_id="batch_progress_123",
            template_id="tpl_test_123",
            type=NotificationType.EMAIL,
            recipients=recipients,
            total_recipients=1
        )
        
        # Update progress
        batch.sent_count = 1
        batch.delivered_count = 1
        
        assert batch.sent_count == 1
        assert batch.delivered_count == 1
        assert batch.failed_count == 0
    
    def test_batch_with_scheduling(self):
        """Test batch with scheduling"""
        scheduled_time = datetime.now(timezone.utc)
        recipients = [{"user_id": "user_1"}]
        
        batch = NotificationBatch(
            batch_id="batch_scheduled_123",
            template_id="tpl_test_123",
            type=NotificationType.EMAIL,
            recipients=recipients,
            total_recipients=1,
            scheduled_at=scheduled_time
        )
        
        assert batch.scheduled_at == scheduled_time


class TestPushSubscription:
    """Test PushSubscription model"""
    
    def test_subscription_creation_minimal(self):
        """Test subscription creation with minimal fields"""
        subscription = PushSubscription(
            user_id="user_123",
            device_token="token_abc123",
            platform=PushPlatform.IOS
        )
        
        assert subscription.user_id == "user_123"
        assert subscription.device_token == "token_abc123"
        assert subscription.platform == PushPlatform.IOS
        assert subscription.is_active is True
    
    def test_subscription_web_push(self):
        """Test web push subscription"""
        subscription = PushSubscription(
            user_id="user_123",
            device_token="web_token_123",
            platform=PushPlatform.WEB,
            endpoint="https://push.example.com/endpoint",
            auth_key="auth_key_123",
            p256dh_key="p256dh_key_123"
        )
        
        assert subscription.platform == PushPlatform.WEB
        assert subscription.endpoint == "https://push.example.com/endpoint"
        assert subscription.auth_key == "auth_key_123"
        assert subscription.p256dh_key == "p256dh_key_123"
    
    def test_subscription_with_device_info(self):
        """Test subscription with device information"""
        subscription = PushSubscription(
            user_id="user_123",
            device_token="android_token_123",
            platform=PushPlatform.ANDROID,
            device_name="Pixel 6",
            device_model="Google Pixel 6",
            app_version="1.2.3"
        )
        
        assert subscription.device_name == "Pixel 6"
        assert subscription.device_model == "Google Pixel 6"
        assert subscription.app_version == "1.2.3"
    
    def test_subscription_deactivation(self):
        """Test subscription deactivation"""
        subscription = PushSubscription(
            user_id="user_123",
            device_token="token_123",
            platform=PushPlatform.IOS
        )
        
        subscription.is_active = False
        
        assert subscription.is_active is False


class TestRequestModels:
    """Test request models"""
    
    def test_send_notification_request_minimal(self):
        """Test minimal send notification request"""
        request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_email="test@example.com",
            content="Test message"
        )
        
        assert request.type == NotificationType.EMAIL
        assert request.recipient_email == "test@example.com"
        assert request.content == "Test message"
        assert request.priority == NotificationPriority.NORMAL
    
    def test_send_notification_request_with_template(self):
        """Test send notification request with template"""
        request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_id="user_123",
            template_id="tpl_welcome_123",
            variables={"name": "John"},
            priority=NotificationPriority.HIGH
        )
        
        assert request.template_id == "tpl_welcome_123"
        assert request.variables == {"name": "John"}
        assert request.priority == NotificationPriority.HIGH
    
    def test_create_template_request(self):
        """Test create template request"""
        request = CreateTemplateRequest(
            name="Welcome Email",
            type=NotificationType.EMAIL,
            subject="Welcome {{name}}",
            content="Hello {{name}}, welcome!",
            variables=["name"]
        )
        
        assert request.name == "Welcome Email"
        assert request.type == NotificationType.EMAIL
        assert request.subject == "Welcome {{name}}"
        assert request.content == "Hello {{name}}, welcome!"
        assert request.variables == ["name"]
    
    def test_register_push_subscription_request(self):
        """Test register push subscription request"""
        request = RegisterPushSubscriptionRequest(
            user_id="user_123",
            device_token="token_abc123",
            platform=PushPlatform.IOS,
            device_name="iPhone 14"
        )
        
        assert request.user_id == "user_123"
        assert request.device_token == "token_abc123"
        assert request.platform == PushPlatform.IOS
        assert request.device_name == "iPhone 14"


if __name__ == "__main__":
    pytest.main([__file__])
