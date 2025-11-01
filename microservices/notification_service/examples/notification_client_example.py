"""
Notification Service Client Example

Professional client for notification management operations including email, in-app, push notifications, templates, and batch sending.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Notification channel types"""
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"
    WEBHOOK = "webhook"


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    CANCELLED = "cancelled"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TemplateStatus(str, Enum):
    """Template status"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PushPlatform(str, Enum):
    """Push notification platforms"""
    WEB = "web"
    IOS = "ios"
    ANDROID = "android"


@dataclass
class NotificationTemplate:
    """Notification template model"""
    template_id: str
    name: str
    type: str
    content: str
    status: str
    variables: List[str]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    id: Optional[int] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    html_content: Optional[str] = None
    version: Optional[int] = None
    created_by: Optional[str] = None


@dataclass
class Notification:
    """Notification model"""
    notification_id: str
    type: str
    priority: str
    recipient_type: str
    content: str
    status: str
    created_at: str
    metadata: Dict[str, Any]
    id: Optional[int] = None
    recipient_id: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    subject: Optional[str] = None
    html_content: Optional[str] = None
    template_id: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[str] = None
    expires_at: Optional[str] = None
    retry_count: Optional[int] = None
    max_retries: Optional[int] = None
    error_message: Optional[str] = None
    provider: Optional[str] = None
    provider_message_id: Optional[str] = None
    tags: Optional[List[str]] = None
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    failed_at: Optional[str] = None


@dataclass
class InAppNotification:
    """In-app notification model"""
    notification_id: str
    user_id: str
    title: str
    message: str
    priority: str
    is_read: bool
    is_archived: bool
    created_at: str
    id: Optional[int] = None
    read_at: Optional[str] = None
    archived_at: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    image_url: Optional[str] = None
    action_url: Optional[str] = None


@dataclass
class PushSubscription:
    """Push subscription model"""
    user_id: str
    device_token: str
    platform: str
    is_active: bool
    created_at: str
    id: Optional[int] = None
    endpoint: Optional[str] = None
    auth_key: Optional[str] = None
    p256dh_key: Optional[str] = None
    device_name: Optional[str] = None
    device_model: Optional[str] = None
    app_version: Optional[str] = None
    updated_at: Optional[str] = None
    last_used_at: Optional[str] = None


@dataclass
class NotificationStats:
    """Notification statistics"""
    total_sent: int
    total_delivered: int
    total_failed: int
    total_pending: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    period: str


class NotificationClient:
    """Professional Notification Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8206",
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=60.0
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "notification-client/1.0",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                if 400 <= e.response.status_code < 500:
                    self.error_count += 1
                    try:
                        error_detail = e.response.json()
                        raise Exception(error_detail.get("detail", str(e)))
                    except:
                        raise Exception(str(e))
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise
        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    # Template Management
    async def create_template(
        self,
        name: str,
        notification_type: NotificationType,
        content: str,
        description: Optional[str] = None,
        subject: Optional[str] = None,
        html_content: Optional[str] = None,
        variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationTemplate:
        """Create a new notification template"""
        payload = {
            "name": name,
            "type": notification_type.value,
            "content": content
        }
        if description:
            payload["description"] = description
        if subject:
            payload["subject"] = subject
        if html_content:
            payload["html_content"] = html_content
        if variables:
            payload["variables"] = variables
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "POST",
            "/api/v1/notifications/templates",
            json=payload
        )
        return NotificationTemplate(**result["template"])

    async def get_template(self, template_id: str) -> NotificationTemplate:
        """Get a specific template by ID"""
        result = await self._make_request(
            "GET",
            f"/api/v1/notifications/templates/{template_id}"
        )
        return NotificationTemplate(**result)

    async def list_templates(
        self,
        notification_type: Optional[NotificationType] = None,
        status: Optional[TemplateStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[NotificationTemplate]:
        """List notification templates"""
        params = {"limit": limit, "offset": offset}
        if notification_type:
            params["type"] = notification_type.value
        if status:
            params["status"] = status.value

        result = await self._make_request(
            "GET",
            "/api/v1/notifications/templates",
            params=params
        )
        return [NotificationTemplate(**t) for t in result]

    async def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        html_content: Optional[str] = None,
        variables: Optional[List[str]] = None,
        status: Optional[TemplateStatus] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationTemplate:
        """Update a template"""
        payload = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if subject:
            payload["subject"] = subject
        if content:
            payload["content"] = content
        if html_content:
            payload["html_content"] = html_content
        if variables:
            payload["variables"] = variables
        if status:
            payload["status"] = status.value
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "PUT",
            f"/api/v1/notifications/templates/{template_id}",
            json=payload
        )
        return NotificationTemplate(**result["template"])

    # Send Notifications
    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Send an email notification"""
        payload = {
            "type": NotificationType.EMAIL.value,
            "recipient_email": recipient_email,
            "subject": subject,
            "content": content,
            "priority": priority.value
        }
        if html_content:
            payload["html_content"] = html_content
        if template_id:
            payload["template_id"] = template_id
        if variables:
            payload["variables"] = variables
        if tags:
            payload["tags"] = tags
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "POST",
            "/api/v1/notifications/send",
            json=payload
        )
        return Notification(**result["notification"])

    async def send_in_app(
        self,
        recipient_id: str,
        subject: str,
        content: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        template_id: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Send an in-app notification"""
        payload = {
            "type": NotificationType.IN_APP.value,
            "recipient_id": recipient_id,
            "subject": subject,
            "content": content,
            "priority": priority.value
        }
        if template_id:
            payload["template_id"] = template_id
        if variables:
            payload["variables"] = variables
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "POST",
            "/api/v1/notifications/send",
            json=payload
        )
        return Notification(**result["notification"])

    async def send_push(
        self,
        recipient_id: str,
        subject: str,
        content: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Send a push notification"""
        payload = {
            "type": NotificationType.PUSH.value,
            "recipient_id": recipient_id,
            "subject": subject,
            "content": content,
            "priority": priority.value
        }
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "POST",
            "/api/v1/notifications/send",
            json=payload
        )
        return Notification(**result["notification"])

    async def send_webhook(
        self,
        webhook_url: str,
        subject: str,
        content: str,
        variables: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """Send a webhook notification"""
        payload = {
            "type": NotificationType.WEBHOOK.value,
            "subject": subject,
            "content": content,
            "metadata": {"webhook_url": webhook_url, **(metadata or {})}
        }
        if variables:
            payload["variables"] = variables

        result = await self._make_request(
            "POST",
            "/api/v1/notifications/send",
            json=payload
        )
        return Notification(**result["notification"])

    async def send_batch(
        self,
        template_id: str,
        notification_type: NotificationType,
        recipients: List[Dict[str, Any]],
        name: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send notifications to multiple recipients"""
        payload = {
            "template_id": template_id,
            "type": notification_type.value,
            "recipients": recipients,
            "priority": priority.value
        }
        if name:
            payload["name"] = name
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "POST",
            "/api/v1/notifications/batch",
            json=payload
        )
        return result

    # Notification Management
    async def list_notifications(
        self,
        user_id: Optional[str] = None,
        notification_type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        priority: Optional[NotificationPriority] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Notification]:
        """List notifications with filters"""
        params = {"limit": limit, "offset": offset}
        if user_id:
            params["user_id"] = user_id
        if notification_type:
            params["type"] = notification_type.value
        if status:
            params["status"] = status.value
        if priority:
            params["priority"] = priority.value

        result = await self._make_request(
            "GET",
            "/api/v1/notifications",
            params=params
        )
        return [Notification(**n) for n in result]

    # In-App Notifications
    async def get_user_notifications(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[InAppNotification]:
        """Get user's in-app notifications"""
        params = {"limit": limit, "offset": offset}
        if is_read is not None:
            params["is_read"] = is_read
        if is_archived is not None:
            params["is_archived"] = is_archived
        if category:
            params["category"] = category

        result = await self._make_request(
            "GET",
            f"/api/v1/notifications/in-app/{user_id}",
            params=params
        )
        return [InAppNotification(**n) for n in result]

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for user"""
        result = await self._make_request(
            "GET",
            f"/api/v1/notifications/in-app/{user_id}/unread-count"
        )
        return result["unread_count"]

    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        result = await self._make_request(
            "POST",
            f"/api/v1/notifications/in-app/{notification_id}/read",
            params={"user_id": user_id}
        )
        return "read" in result.get("message", "").lower()

    async def mark_as_archived(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as archived"""
        result = await self._make_request(
            "POST",
            f"/api/v1/notifications/in-app/{notification_id}/archive",
            params={"user_id": user_id}
        )
        return "archived" in result.get("message", "").lower()

    # Push Subscriptions
    async def register_push_subscription(
        self,
        user_id: str,
        device_token: str,
        platform: PushPlatform,
        endpoint: Optional[str] = None,
        auth_key: Optional[str] = None,
        p256dh_key: Optional[str] = None,
        device_name: Optional[str] = None,
        device_model: Optional[str] = None,
        app_version: Optional[str] = None
    ) -> PushSubscription:
        """Register a push notification subscription"""
        payload = {
            "user_id": user_id,
            "device_token": device_token,
            "platform": platform.value
        }
        if endpoint:
            payload["endpoint"] = endpoint
        if auth_key:
            payload["auth_key"] = auth_key
        if p256dh_key:
            payload["p256dh_key"] = p256dh_key
        if device_name:
            payload["device_name"] = device_name
        if device_model:
            payload["device_model"] = device_model
        if app_version:
            payload["app_version"] = app_version

        result = await self._make_request(
            "POST",
            "/api/v1/notifications/push/subscribe",
            json=payload
        )
        return PushSubscription(**result)

    async def get_user_subscriptions(
        self,
        user_id: str,
        platform: Optional[PushPlatform] = None
    ) -> List[PushSubscription]:
        """Get user's push subscriptions"""
        params = {}
        if platform:
            params["platform"] = platform.value

        result = await self._make_request(
            "GET",
            f"/api/v1/notifications/push/subscriptions/{user_id}",
            params=params
        )
        return [PushSubscription(**s) for s in result]

    async def unsubscribe_push(self, user_id: str, device_token: str) -> bool:
        """Unsubscribe from push notifications"""
        result = await self._make_request(
            "DELETE",
            "/api/v1/notifications/push/unsubscribe",
            params={"user_id": user_id, "device_token": device_token}
        )
        return "removed" in result.get("message", "").lower()

    # Statistics
    async def get_stats(
        self,
        user_id: Optional[str] = None,
        period: str = "all_time"
    ) -> NotificationStats:
        """Get notification statistics"""
        params = {"period": period}
        if user_id:
            params["user_id"] = user_id

        result = await self._make_request(
            "GET",
            "/api/v1/notifications/stats",
            params=params
        )
        return NotificationStats(**result)

    # Health & Info
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._make_request("GET", "/health")

    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return await self._make_request("GET", "/info")

    # Testing Endpoints
    async def test_email(self, to: str, subject: str = "Test Email") -> Notification:
        """Send a test email (development only)"""
        result = await self._make_request(
            "POST",
            "/api/v1/notifications/test/email",
            params={"to": to, "subject": subject}
        )
        return Notification(**result["notification"])

    async def test_in_app(self, user_id: str, title: str = "Test Notification") -> Notification:
        """Send a test in-app notification (development only)"""
        result = await self._make_request(
            "POST",
            "/api/v1/notifications/test/in-app",
            params={"user_id": user_id, "title": title}
        )
        return Notification(**result["notification"])

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Example Usage
async def main():
    print("=" * 70)
    print("Notification Service Client Examples")
    print("=" * 70)

    async with NotificationClient() as client:
        # Example 1: Health Check
        print("\n1. Health Check")
        print("-" * 70)
        health = await client.health_check()
        print(f"  Service: {health['service']}")
        print(f"  Status: {health['status']}")
        print(f"  Port: {health['port']}")

        # Example 2: Service Info
        print("\n2. Get Service Information")
        print("-" * 70)
        info = await client.get_service_info()
        print(f"  Service: {info['service']}")
        print(f"  Version: {info['version']}")
        print(f"  Capabilities:")
        for cap, enabled in info['capabilities'].items():
            print(f"    {cap}: {'✓' if enabled else '✗'}")

        test_user_id = "client_test_user"
        timestamp = int(datetime.now().timestamp())

        # Example 3: Create Email Template
        print("\n3. Create Email Template")
        print("-" * 70)
        template = await client.create_template(
            name=f"Welcome Email {timestamp}",
            notification_type=NotificationType.EMAIL,
            content="Hello {{user_name}}, welcome to {{app_name}}!",
            subject="Welcome to {{app_name}}!",
            html_content="<h1>Welcome {{user_name}}!</h1><p>Thank you for joining <strong>{{app_name}}</strong>!</p>",
            variables=["user_name", "app_name"],
            description="Welcome email for new users",
            metadata={"category": "onboarding", "created_by": "client_example"}
        )
        print(f"  Template created: {template.template_id}")
        print(f"  Name: {template.name}")
        print(f"  Type: {template.type}")
        print(f"  Variables: {', '.join(template.variables)}")

        # Example 4: List Templates
        print("\n4. List All Templates")
        print("-" * 70)
        templates = await client.list_templates(limit=5)
        print(f"  Total templates: {len(templates)}")
        for t in templates[:3]:
            print(f"    - {t.name} ({t.type}) - {t.status}")

        # Example 5: Update Template
        print("\n5. Update Template")
        print("-" * 70)
        updated_template = await client.update_template(
            template_id=template.template_id,
            description="Updated welcome email template",
            metadata={"category": "onboarding", "version": "2.0"}
        )
        print(f"  Template updated: {updated_template.template_id}")
        print(f"  Description: {updated_template.metadata.get('version')}")

        # Example 6: Send Direct Email
        print("\n6. Send Direct Email Notification")
        print("-" * 70)
        email_notif = await client.send_email(
            recipient_email="test@example.com",
            subject="Test Email from Client",
            content="This is a test email sent from the notification client.",
            html_content="<h2>Test Email</h2><p>This is a <strong>test email</strong> from the notification client.</p>",
            priority=NotificationPriority.HIGH,
            tags=["client_test", "example"],
            metadata={"source": "client_example"}
        )
        print(f"  Notification sent: {email_notif.notification_id}")
        print(f"  Type: {email_notif.type}")
        print(f"  Status: {email_notif.status}")
        print(f"  Priority: {email_notif.priority}")

        # Example 7: Send In-App Notification
        print("\n7. Send In-App Notification")
        print("-" * 70)
        in_app_notif = await client.send_in_app(
            recipient_id=test_user_id,
            subject="New Feature Available",
            content="Check out our new feature in the dashboard!",
            priority=NotificationPriority.NORMAL,
            metadata={
                "action_url": "/dashboard/features",
                "category": "product_update"
            }
        )
        print(f"  Notification sent: {in_app_notif.notification_id}")
        print(f"  Recipient: {in_app_notif.recipient_id}")
        print(f"  Status: {in_app_notif.status}")

        # Example 8: Send Email with Template
        print("\n8. Send Email Using Template")
        print("-" * 70)
        template_email = await client.send_email(
            recipient_email="newuser@example.com",
            subject="",  # Will be filled by template
            content="",  # Will be filled by template
            template_id=template.template_id,
            variables={
                "user_name": "Alice Johnson",
                "app_name": "iaPro Platform"
            },
            priority=NotificationPriority.HIGH
        )
        print(f"  Notification sent: {template_email.notification_id}")
        print(f"  Template used: {template_email.template_id}")
        print(f"  Content preview: {template_email.content[:50]}...")

        # Example 9: Get User In-App Notifications
        print("\n9. Get User's In-App Notifications")
        print("-" * 70)
        user_notifs = await client.get_user_notifications(
            user_id=test_user_id,
            is_read=False,
            limit=10
        )
        print(f"  Total notifications: {len(user_notifs)}")
        for notif in user_notifs[:3]:
            print(f"    - {notif.title} ({'read' if notif.is_read else 'unread'})")

        # Example 10: Get Unread Count
        print("\n10. Get Unread Notification Count")
        print("-" * 70)
        unread_count = await client.get_unread_count(test_user_id)
        print(f"  Unread notifications: {unread_count}")

        # Example 11: Mark Notification as Read
        if user_notifs:
            print("\n11. Mark Notification as Read")
            print("-" * 70)
            first_notif = user_notifs[0]
            marked_read = await client.mark_as_read(
                notification_id=first_notif.notification_id,
                user_id=test_user_id
            )
            print(f"  Notification marked as read: {marked_read}")
            print(f"  Notification ID: {first_notif.notification_id}")

        # Example 12: Register Push Subscription
        print("\n12. Register Push Notification Subscription")
        print("-" * 70)
        push_sub = await client.register_push_subscription(
            user_id=test_user_id,
            device_token=f"client_test_device_{timestamp}",
            platform=PushPlatform.WEB,
            endpoint="https://fcm.googleapis.com/fcm/send/test_endpoint",
            auth_key="test_auth_key",
            p256dh_key="test_p256dh_key",
            device_name="Chrome Browser",
            device_model="Desktop",
            app_version="1.0.0"
        )
        print(f"  Subscription registered: ID {push_sub.id}")
        print(f"  Platform: {push_sub.platform}")
        print(f"  Device: {push_sub.device_name}")
        print(f"  Active: {push_sub.is_active}")

        # Example 13: Get User Push Subscriptions
        print("\n13. Get User's Push Subscriptions")
        print("-" * 70)
        subscriptions = await client.get_user_subscriptions(
            user_id=test_user_id,
            platform=PushPlatform.WEB
        )
        print(f"  Total subscriptions: {len(subscriptions)}")
        for sub in subscriptions:
            print(f"    - {sub.device_name} ({sub.platform}) - {'active' if sub.is_active else 'inactive'}")

        # Example 14: Send Batch Notifications
        print("\n14. Send Batch Notifications")
        print("-" * 70)
        batch_result = await client.send_batch(
            template_id=template.template_id,
            notification_type=NotificationType.EMAIL,
            recipients=[
                {
                    "email": "user1@example.com",
                    "variables": {"user_name": "Alice", "app_name": "iaPro"}
                },
                {
                    "email": "user2@example.com",
                    "variables": {"user_name": "Bob", "app_name": "iaPro"}
                },
                {
                    "email": "user3@example.com",
                    "variables": {"user_name": "Charlie", "app_name": "iaPro"}
                }
            ],
            name="Client Example Batch Campaign",
            priority=NotificationPriority.NORMAL,
            metadata={"campaign_id": f"client_batch_{timestamp}"}
        )
        print(f"  Batch created: {batch_result['batch']['batch_id']}")
        print(f"  Total recipients: {batch_result['batch']['total_recipients']}")
        print(f"  Message: {batch_result['message']}")

        # Example 15: List All Notifications
        print("\n15. List All Notifications (Filtered)")
        print("-" * 70)
        all_notifs = await client.list_notifications(
            notification_type=NotificationType.EMAIL,
            status=NotificationStatus.DELIVERED,
            limit=5
        )
        print(f"  Total notifications: {len(all_notifs)}")
        for notif in all_notifs[:3]:
            print(f"    - {notif.subject or 'No subject'} ({notif.status})")

        # Example 16: Send Webhook Notification
        print("\n16. Send Webhook Notification")
        print("-" * 70)
        webhook_notif = await client.send_webhook(
            webhook_url="https://webhook.site/unique-url",
            subject="Order Completed",
            content="Order #12345 has been completed successfully",
            metadata={"order_id": "12345", "amount": 99.99}
        )
        print(f"  Webhook notification sent: {webhook_notif.notification_id}")
        print(f"  Status: {webhook_notif.status}")

        # Example 17: Get Overall Statistics
        print("\n17. Get Notification Statistics (All Time)")
        print("-" * 70)
        stats = await client.get_stats(period="all_time")
        print(f"  Total sent: {stats.total_sent}")
        print(f"  Total delivered: {stats.total_delivered}")
        print(f"  Total failed: {stats.total_failed}")
        print(f"  Total pending: {stats.total_pending}")
        print(f"  By type:")
        for ntype, count in stats.by_type.items():
            print(f"    {ntype}: {count}")

        # Example 18: Get Weekly Statistics
        print("\n18. Get Weekly Statistics")
        print("-" * 70)
        weekly_stats = await client.get_stats(period="week")
        print(f"  Period: {weekly_stats.period}")
        print(f"  Total sent (this week): {weekly_stats.total_sent}")
        print(f"  Total delivered: {weekly_stats.total_delivered}")

        # Example 19: Test Email Endpoint
        print("\n19. Send Test Email (Development)")
        print("-" * 70)
        test_email = await client.test_email(
            to="developer@example.com",
            subject="Quick Test Email"
        )
        print(f"  Test email sent: {test_email.notification_id}")
        print(f"  Status: {test_email.status}")

        # Example 20: Test In-App Endpoint
        print("\n20. Send Test In-App Notification (Development)")
        print("-" * 70)
        test_in_app = await client.test_in_app(
            user_id=test_user_id,
            title="Quick Test Notification"
        )
        print(f"  Test in-app sent: {test_in_app.notification_id}")
        print(f"  Status: {test_in_app.status}")

        # Example 21: Unsubscribe Push
        print("\n21. Unsubscribe Push Notification")
        print("-" * 70)
        unsubscribed = await client.unsubscribe_push(
            user_id=test_user_id,
            device_token=push_sub.device_token
        )
        print(f"  Unsubscribed: {unsubscribed}")
        print(f"  Device token removed: {push_sub.device_token}")

        # Show Client Metrics
        print("\n22. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"  Total requests: {metrics['total_requests']}")
        print(f"  Total errors: {metrics['total_errors']}")
        print(f"  Error rate: {metrics['error_rate']:.2%}")

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())

