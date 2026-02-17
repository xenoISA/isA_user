"""
Notification Service Data Contract

Defines canonical data structures for notification service testing.
All tests MUST use these Pydantic models and factories for consistency.

This is the SINGLE SOURCE OF TRUTH for notification service test data.
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr, field_validator

# Import from production models for type consistency
from microservices.notification_service.models import (
    NotificationType,
    NotificationStatus,
    NotificationPriority,
    TemplateStatus,
    RecipientType,
    PushPlatform,
)


# ============================================================================
# Request Contracts (Input Schemas)
# ============================================================================

class SendNotificationRequestContract(BaseModel):
    """
    Contract: Send notification request schema

    Used for sending individual notifications in tests.
    Maps to notification service send endpoint.
    """
    type: NotificationType = Field(..., description="Notification type")
    recipient_id: Optional[str] = Field(None, description="Recipient user ID")
    recipient_email: Optional[EmailStr] = Field(None, description="Recipient email address")
    recipient_phone: Optional[str] = Field(None, description="Recipient phone number")
    template_id: Optional[str] = Field(None, description="Template ID to use")
    subject: Optional[str] = Field(None, description="Notification subject")
    content: Optional[str] = Field(None, description="Notification content")
    html_content: Optional[str] = Field(None, description="HTML content for emails")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Template variables")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Notification priority")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule send time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Notification tags")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v, info):
        # If no template is used, content is required
        if info.data.get('template_id') is None and not v:
            raise ValueError("Content is required when not using a template")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "type": "email",
                "recipient_email": "user@example.com",
                "template_id": "tpl_email_welcome_123",
                "variables": {"name": "John Doe", "activation_code": "ABC123"},
                "priority": "normal",
                "metadata": {"source": "user_registration"}
            }
        }


class SendBatchRequestContract(BaseModel):
    """
    Contract: Send batch notifications request schema

    Used for sending bulk notifications in tests.
    """
    name: Optional[str] = Field(None, description="Batch campaign name")
    template_id: str = Field(..., description="Template ID to use")
    type: NotificationType = Field(..., description="Notification type")
    recipients: List[Dict[str, Any]] = Field(..., description="List of recipients with variables")
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="Notification priority")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule send time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Campaign metadata")

    @field_validator('recipients')
    @classmethod
    def validate_recipients(cls, v):
        if not v:
            raise ValueError("At least one recipient is required")
        if len(v) > 10000:
            raise ValueError("Maximum 10,000 recipients per batch")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Welcome Campaign",
                "template_id": "tpl_email_welcome_123",
                "type": "email",
                "recipients": [
                    {"user_id": "user_123", "variables": {"name": "John"}},
                    {"email": "jane@example.com", "variables": {"name": "Jane"}}
                ],
                "priority": "normal",
                "scheduled_at": "2025-12-20T10:00:00Z"
            }
        }


class CreateTemplateRequestContract(BaseModel):
    """
    Contract: Create notification template request schema

    Used for creating notification templates in tests.
    """
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    type: NotificationType = Field(..., description="Template notification type")
    subject: Optional[str] = Field(None, max_length=255, description="Email subject (for email templates)")
    content: str = Field(..., min_length=1, description="Template content with variable placeholders")
    html_content: Optional[str] = Field(None, description="HTML content (for email templates)")
    variables: List[str] = Field(default_factory=list, description="List of template variables")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Template metadata")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Welcome Email Template",
                "description": "Template for user welcome emails",
                "type": "email",
                "subject": "Welcome to {{company_name}}!",
                "content": "Hello {{name}},\n\nWelcome to our platform! Your activation code is {{activation_code}}.\n\nBest regards,\n{{company_name}} Team",
                "html_content": "<p>Hello {{name}},</p><p>Welcome to our platform!</p>",
                "variables": ["name", "company_name", "activation_code"],
                "metadata": {"category": "onboarding"}
            }
        }


class UpdateTemplateRequestContract(BaseModel):
    """
    Contract: Update notification template request schema

    Used for updating notification templates in tests.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    subject: Optional[str] = Field(None, max_length=255, description="Email subject")
    content: Optional[str] = Field(None, min_length=1, description="Template content")
    html_content: Optional[str] = Field(None, description="HTML content")
    variables: Optional[List[str]] = Field(None, description="Template variables")
    status: Optional[TemplateStatus] = Field(None, description="Template status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Template metadata")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Content cannot be empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Welcome Email Template",
                "description": "Updated template with improved content",
                "subject": "Welcome to {{company_name}} - {{offer}}!",
                "content": "Hello {{name}},\n\nWelcome to our platform with special offer!",
                "variables": ["name", "company_name", "offer", "activation_code"],
                "status": "active"
            }
        }


class RegisterPushSubscriptionRequestContract(BaseModel):
    """
    Contract: Register push subscription request schema

    Used for registering device push subscriptions in tests.
    """
    user_id: str = Field(..., min_length=1, description="User ID")
    device_token: str = Field(..., min_length=1, description="Device token or subscription endpoint")
    platform: PushPlatform = Field(..., description="Push platform")
    endpoint: Optional[str] = Field(None, description="Web push endpoint")
    auth_key: Optional[str] = Field(None, description="Web push auth key")
    p256dh_key: Optional[str] = Field(None, description="Web push P256DH key")
    device_name: Optional[str] = Field(None, max_length=100, description="Device name")
    device_model: Optional[str] = Field(None, max_length=100, description="Device model")
    app_version: Optional[str] = Field(None, max_length=50, description="App version")

    @field_validator('device_token')
    @classmethod
    def validate_device_token(cls, v):
        if not v.strip():
            raise ValueError("Device token cannot be empty")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "device_token": "fmK2LxTzR9Q7mP8vX3nY6wJ5bG4fE1dC",
                "platform": "ios",
                "device_name": "iPhone 14 Pro",
                "device_model": "iPhone15,3",
                "app_version": "1.2.0"
            }
        }


class MarkNotificationReadRequestContract(BaseModel):
    """
    Contract: Mark notification as read request schema

    Used for marking in-app notifications as read in tests.
    """
    user_id: str = Field(..., min_length=1, description="User ID")
    read_at: Optional[datetime] = Field(None, description="Read timestamp (default: now)")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "read_at": "2025-12-15T14:30:00Z"
            }
        }


class ListNotificationsRequestContract(BaseModel):
    """
    Contract: List notifications request schema

    Used for listing notifications with pagination and filters in tests.
    """
    user_id: str = Field(..., min_length=1, description="User ID")
    is_read: Optional[bool] = Field(None, description="Filter by read status")
    is_archived: Optional[bool] = Field(None, description="Filter by archived status")
    category: Optional[str] = Field(None, max_length=100, description="Filter by category")
    limit: int = Field(50, ge=1, le=100, description="Results per page")
    offset: int = Field(0, ge=0, description="Results offset")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "is_read": False,
                "category": "account",
                "limit": 20,
                "offset": 0
            }
        }


# ============================================================================
# Response Contracts (Output Schemas)
# ============================================================================

class NotificationResponseContract(BaseModel):
    """
    Contract: Notification response schema

    Validates API response structure for sent notifications.
    """
    notification: Dict[str, Any] = Field(..., description="Notification object")
    message: str = Field(default="Notification processed", description="Response message")
    success: bool = Field(default=True, description="Operation success status")

    class Config:
        json_schema_extra = {
            "example": {
                "notification": {
                    "notification_id": "ntf_email_1234567890",
                    "type": "email",
                    "status": "pending",
                    "recipient_email": "user@example.com",
                    "subject": "Welcome to Our Platform!",
                    "created_at": "2025-12-15T14:30:00Z"
                },
                "message": "Notification created and queued for sending",
                "success": True
            }
        }


class TemplateResponseContract(BaseModel):
    """
    Contract: Template response schema

    Validates API response structure for template operations.
    """
    template: Dict[str, Any] = Field(..., description="Template object")
    message: str = Field(default="Template processed", description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "template": {
                    "template_id": "tpl_email_welcome_123",
                    "name": "Welcome Email Template",
                    "type": "email",
                    "status": "active",
                    "created_at": "2025-12-15T14:30:00Z"
                },
                "message": "Template created successfully"
            }
        }


class BatchResponseContract(BaseModel):
    """
    Contract: Batch notification response schema

    Validates API response structure for batch operations.
    """
    batch: Dict[str, Any] = Field(..., description="Batch object")
    message: str = Field(default="Batch created", description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "batch": {
                    "batch_id": "batch_1234567890",
                    "name": "Welcome Campaign",
                    "total_count": 100,
                    "status": "pending",
                    "created_at": "2025-12-15T14:30:00Z"
                },
                "message": "Batch created with 100 recipients"
            }
        }


class InAppNotificationResponseContract(BaseModel):
    """
    Contract: In-app notification response schema

    Validates API response structure for in-app notifications.
    """
    notifications: List[Dict[str, Any]] = Field(..., description="List of notifications")
    total_count: int = Field(..., ge=0, description="Total notifications count")
    unread_count: int = Field(..., ge=0, description="Unread notifications count")

    class Config:
        json_schema_extra = {
            "example": {
                "notifications": [
                    {
                        "notification_id": "ntf_inapp_123",
                        "user_id": "user_123",
                        "title": "New Message",
                        "message": "You have a new message from John",
                        "is_read": False,
                        "created_at": "2025-12-15T14:30:00Z"
                    }
                ],
                "total_count": 15,
                "unread_count": 3
            }
        }


class PushSubscriptionResponseContract(BaseModel):
    """
    Contract: Push subscription response schema

    Validates API response structure for push subscription operations.
    """
    subscription: Dict[str, Any] = Field(..., description="Subscription object")
    message: str = Field(default="Subscription processed", description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "subscription": {
                    "subscription_id": "sub_1234567890",
                    "user_id": "user_123",
                    "platform": "ios",
                    "device_token": "fmK2LxTzR9Q7mP8vX3nY6wJ5bG4fE1dC",
                    "is_active": True,
                    "created_at": "2025-12-15T14:30:00Z"
                },
                "message": "Push subscription registered successfully"
            }
        }


class NotificationStatsResponseContract(BaseModel):
    """
    Contract: Notification statistics response schema

    Validates API response structure for notification statistics.
    """
    total_sent: int = Field(..., ge=0, description="Total sent notifications")
    total_delivered: int = Field(..., ge=0, description="Total delivered notifications")
    total_failed: int = Field(..., ge=0, description="Total failed notifications")
    total_pending: int = Field(..., ge=0, description="Total pending notifications")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Statistics by notification type")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Statistics by status")
    period: str = Field(default="all_time", description="Statistics period")

    class Config:
        json_schema_extra = {
            "example": {
                "total_sent": 1500,
                "total_delivered": 1350,
                "total_failed": 100,
                "total_pending": 50,
                "by_type": {
                    "email": 800,
                    "push": 500,
                    "in_app": 200
                },
                "by_status": {
                    "sent": 1400,
                    "delivered": 1350,
                    "failed": 100,
                    "pending": 50
                },
                "period": "week"
            }
        }


class UnreadCountResponseContract(BaseModel):
    """
    Contract: Unread count response schema

    Validates API response structure for unread notification count.
    """
    user_id: str = Field(..., description="User ID")
    unread_count: int = Field(..., ge=0, description="Number of unread notifications")
    category_counts: Dict[str, int] = Field(default_factory=dict, description="Unread count by category")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "unread_count": 5,
                "category_counts": {
                    "account": 2,
                    "payment": 1,
                    "system": 2
                }
            }
        }


# ============================================================================
# Test Data Factory
# ============================================================================

class NotificationTestDataFactory:
    """
    Factory for creating test data conforming to contracts.

    Provides methods to generate valid/invalid test data for all scenarios.
    """

    @staticmethod
    def make_notification_id() -> str:
        """Generate unique test notification ID"""
        return f"ntf_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

    @staticmethod
    def make_template_id() -> str:
        """Generate unique test template ID"""
        return f"tpl_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

    @staticmethod
    def make_batch_id() -> str:
        """Generate unique test batch ID"""
        return f"batch_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

    @staticmethod
    def make_subscription_id() -> str:
        """Generate unique test subscription ID"""
        return f"sub_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

    @staticmethod
    def make_email() -> str:
        """Generate unique test email address"""
        return f"test_{uuid.uuid4().hex[:8]}@example.com"

    @staticmethod
    def make_phone() -> str:
        """Generate random test phone number"""
        return f"+1{random.randint(2000000000, 9999999999)}"

    @staticmethod
    def make_device_token() -> str:
        """Generate random test device token"""
        return uuid.uuid4().hex[:32]

    @staticmethod
    def make_notification_type() -> NotificationType:
        """Generate random notification type"""
        return random.choice(list(NotificationType))

    @staticmethod
    def make_notification_priority() -> NotificationPriority:
        """Generate random notification priority"""
        return random.choice(list(NotificationPriority))

    @staticmethod
    def make_push_platform() -> PushPlatform:
        """Generate random push platform"""
        return random.choice(list(PushPlatform))

    @staticmethod
    def make_template_variables() -> List[str]:
        """Generate random template variables"""
        all_vars = ["name", "email", "company_name", "activation_code", "offer", "date", "amount", "product"]
        return random.sample(all_vars, random.randint(2, 5))

    @staticmethod
    def make_template_content(variables: List[str]) -> str:
        """Generate template content with variables"""
        content_parts = ["Hello {{name}},"]
        for var in variables:
            if var != "name":
                content_parts.append(f"Your {var.replace('_', ' ')} is {{{{{var}}}}}.")
        content_parts.extend(["Thank you!", "The Team"])
        return "\n\n".join(content_parts)

    @staticmethod
    def make_send_request(**overrides) -> SendNotificationRequestContract:
        """
        Create valid send notification request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            SendNotificationRequestContract with valid data
        """
        variables = NotificationTestDataFactory.make_template_variables()
        defaults = {
            "type": NotificationType.EMAIL,
            "recipient_email": NotificationTestDataFactory.make_email(),
            "template_id": NotificationTestDataFactory.make_template_id(),
            "subject": "Test Notification",
            "content": NotificationTestDataFactory.make_template_content(variables),
            "variables": {var: f"test_{var}" for var in variables},
            "priority": NotificationPriority.NORMAL,
            "metadata": {"source": "test", "environment": "pytest"}
        }
        defaults.update(overrides)
        return SendNotificationRequestContract(**defaults)

    @staticmethod
    def make_batch_request(**overrides) -> SendBatchRequestContract:
        """
        Create valid batch request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            SendBatchRequestContract with valid data
        """
        recipients = [
            {
                "user_id": f"user_{uuid.uuid4().hex[:8]}",
                "variables": {"name": f"User_{i}"}
            }
            for i in range(random.randint(2, 5))
        ]
        
        defaults = {
            "name": "Test Batch Campaign",
            "template_id": NotificationTestDataFactory.make_template_id(),
            "type": NotificationType.EMAIL,
            "recipients": recipients,
            "priority": NotificationPriority.NORMAL,
            "metadata": {"campaign": "test", "environment": "pytest"}
        }
        defaults.update(overrides)
        return SendBatchRequestContract(**defaults)

    @staticmethod
    def make_create_template_request(**overrides) -> CreateTemplateRequestContract:
        """
        Create valid create template request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            CreateTemplateRequestContract with valid data
        """
        variables = NotificationTestDataFactory.make_template_variables()
        defaults = {
            "name": f"Test Template {uuid.uuid4().hex[:8]}",
            "description": "Template created for testing purposes",
            "type": NotificationType.EMAIL,
            "subject": "Test Notification: {{name}}",
            "content": NotificationTestDataFactory.make_template_content(variables),
            "html_content": f"<p>{NotificationTestDataFactory.make_template_content(variables)}</p>",
            "variables": variables,
            "metadata": {"category": "test", "environment": "pytest"}
        }
        defaults.update(overrides)
        return CreateTemplateRequestContract(**defaults)

    @staticmethod
    def make_update_template_request(**overrides) -> UpdateTemplateRequestContract:
        """
        Create valid update template request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            UpdateTemplateRequestContract with valid data
        """
        variables = NotificationTestDataFactory.make_template_variables()
        defaults = {
            "name": f"Updated Template {uuid.uuid4().hex[:8]}",
            "description": "Updated template description",
            "subject": "Updated: {{name}}",
            "content": NotificationTestDataFactory.make_template_content(variables),
            "html_content": f"<p>Updated: {NotificationTestDataFactory.make_template_content(variables)}</p>",
            "variables": variables,
            "status": TemplateStatus.ACTIVE,
            "metadata": {"category": "updated", "version": "2.0"}
        }
        defaults.update(overrides)
        return UpdateTemplateRequestContract(**defaults)

    @staticmethod
    def make_register_push_subscription_request(**overrides) -> RegisterPushSubscriptionRequestContract:
        """
        Create valid register push subscription request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            RegisterPushSubscriptionRequestContract with valid data
        """
        defaults = {
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "device_token": NotificationTestDataFactory.make_device_token(),
            "platform": NotificationTestDataFactory.make_push_platform(),
            "device_name": "Test Device",
            "device_model": "Test Model",
            "app_version": "1.0.0"
        }
        defaults.update(overrides)
        return RegisterPushSubscriptionRequestContract(**defaults)

    @staticmethod
    def make_list_notifications_request(**overrides) -> ListNotificationsRequestContract:
        """
        Create valid list notifications request with defaults.

        Args:
            **overrides: Override any default fields

        Returns:
            ListNotificationsRequestContract with valid data
        """
        defaults = {
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "is_read": None,
            "is_archived": None,
            "category": None,
            "limit": 50,
            "offset": 0
        }
        defaults.update(overrides)
        return ListNotificationsRequestContract(**defaults)

    @staticmethod
    def make_notification_response(**overrides) -> NotificationResponseContract:
        """
        Create expected notification response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "notification": {
                "notification_id": NotificationTestDataFactory.make_notification_id(),
                "type": "email",
                "status": "pending",
                "recipient_email": NotificationTestDataFactory.make_email(),
                "subject": "Test Notification",
                "created_at": datetime.now(timezone.utc)
            },
            "message": "Notification created and queued for sending",
            "success": True
        }
        defaults.update(overrides)
        return NotificationResponseContract(**defaults)

    @staticmethod
    def make_template_response(**overrides) -> TemplateResponseContract:
        """
        Create expected template response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "template": {
                "template_id": NotificationTestDataFactory.make_template_id(),
                "name": "Test Template",
                "type": "email",
                "status": "active",
                "created_at": datetime.now(timezone.utc)
            },
            "message": "Template created successfully"
        }
        defaults.update(overrides)
        return TemplateResponseContract(**defaults)

    @staticmethod
    def make_batch_response(**overrides) -> BatchResponseContract:
        """
        Create expected batch response for assertions.

        Used in tests to validate API responses match contract.
        """
        defaults = {
            "batch": {
                "batch_id": NotificationTestDataFactory.make_batch_id(),
                "name": "Test Batch",
                "total_count": 100,
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            },
            "message": "Batch created with 100 recipients"
        }
        defaults.update(overrides)
        return BatchResponseContract(**defaults)

    @staticmethod
    def make_stats_response(**overrides) -> NotificationStatsResponseContract:
        """
        Create expected stats response for assertions.

        Used in tests to validate API responses match contract.
        """
        total_sent = random.randint(1000, 5000)
        defaults = {
            "total_sent": total_sent,
            "total_delivered": int(total_sent * 0.9),
            "total_failed": int(total_sent * 0.05),
            "total_pending": int(total_sent * 0.05),
            "by_type": {
                "email": int(total_sent * 0.6),
                "push": int(total_sent * 0.3),
                "in_app": int(total_sent * 0.1)
            },
            "by_status": {
                "sent": int(total_sent * 0.95),
                "delivered": int(total_sent * 0.9),
                "failed": int(total_sent * 0.05),
                "pending": int(total_sent * 0.05)
            },
            "period": "week"
        }
        defaults.update(overrides)
        return NotificationStatsResponseContract(**defaults)

    # ========================================================================
    # Invalid Data Generators (for negative testing)
    # ========================================================================

    @staticmethod
    def make_invalid_send_request_missing_type() -> dict:
        """Generate send request missing required type"""
        return {
            "recipient_email": NotificationTestDataFactory.make_email(),
            "content": "Test content",
        }

    @staticmethod
    def make_invalid_send_request_no_recipient() -> dict:
        """Generate send request with no recipient specified"""
        return {
            "type": "email",
            "content": "Test content",
        }

    @staticmethod
    def make_invalid_send_request_no_content_or_template() -> dict:
        """Generate send request with neither content nor template"""
        return {
            "type": "email",
            "recipient_email": NotificationTestDataFactory.make_email(),
        }

    @staticmethod
    def make_invalid_batch_request_empty_recipients() -> dict:
        """Generate batch request with empty recipients list"""
        return {
            "template_id": NotificationTestDataFactory.make_template_id(),
            "type": "email",
            "recipients": [],
        }

    @staticmethod
    def make_invalid_batch_request_too_many_recipients() -> dict:
        """Generate batch request with too many recipients"""
        recipients = [{"user_id": f"user_{i}"} for i in range(10001)]
        return {
            "template_id": NotificationTestDataFactory.make_template_id(),
            "type": "email",
            "recipients": recipients,
        }

    @staticmethod
    def make_invalid_template_request_empty_content() -> dict:
        """Generate template request with empty content"""
        return {
            "name": "Test Template",
            "type": "email",
            "content": "",
        }

    @staticmethod
    def make_invalid_template_request_missing_name() -> dict:
        """Generate template request missing required name"""
        return {
            "type": "email",
            "content": "Test content",
        }

    @staticmethod
    def make_invalid_push_request_empty_device_token() -> dict:
        """Generate push subscription request with empty device token"""
        return {
            "user_id": "user_123",
            "platform": "ios",
            "device_token": "",
        }


# ============================================================================
# Request Builders (for complex test scenarios)
# ============================================================================

class SendNotificationRequestBuilder:
    """
    Builder pattern for creating complex send notification requests.

    Useful for tests that need to gradually construct requests.

    Example:
        request = (
            SendNotificationRequestBuilder()
            .with_email("user@example.com")
            .with_template("tpl_welcome_123")
            .with_variable("name", "John")
            .with_high_priority()
            .schedule_for(datetime(2025, 12, 20))
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "type": NotificationType.EMAIL,
            "variables": {},
            "metadata": {},
            "tags": [],
            "priority": NotificationPriority.NORMAL
        }

    def with_email(self, email: str) -> "SendNotificationRequestBuilder":
        """Set email recipient"""
        self._data["recipient_email"] = email
        return self

    def with_user(self, user_id: str) -> "SendNotificationRequestBuilder":
        """Set user ID recipient"""
        self._data["recipient_id"] = user_id
        return self

    def with_phone(self, phone: str) -> "SendNotificationRequestBuilder":
        """Set phone recipient"""
        self._data["recipient_phone"] = phone
        return self

    def with_template(self, template_id: str) -> "SendNotificationRequestBuilder":
        """Set template ID"""
        self._data["template_id"] = template_id
        return self

    def with_subject(self, subject: str) -> "SendNotificationRequestBuilder":
        """Set notification subject"""
        self._data["subject"] = subject
        return self

    def with_content(self, content: str) -> "SendNotificationRequestBuilder":
        """Set notification content"""
        self._data["content"] = content
        return self

    def with_html_content(self, html_content: str) -> "SendNotificationRequestBuilder":
        """Set HTML content"""
        self._data["html_content"] = html_content
        return self

    def with_variable(self, key: str, value: Any) -> "SendNotificationRequestBuilder":
        """Add template variable"""
        self._data["variables"][key] = value
        return self

    def with_variables(self, variables: Dict[str, Any]) -> "SendNotificationRequestBuilder":
        """Set all template variables"""
        self._data["variables"].update(variables)
        return self

    def with_low_priority(self) -> "SendNotificationRequestBuilder":
        """Set low priority"""
        self._data["priority"] = NotificationPriority.LOW
        return self

    def with_normal_priority(self) -> "SendNotificationRequestBuilder":
        """Set normal priority"""
        self._data["priority"] = NotificationPriority.NORMAL
        return self

    def with_high_priority(self) -> "SendNotificationRequestBuilder":
        """Set high priority"""
        self._data["priority"] = NotificationPriority.HIGH
        return self

    def with_urgent_priority(self) -> "SendNotificationRequestBuilder":
        """Set urgent priority"""
        self._data["priority"] = NotificationPriority.URGENT
        return self

    def schedule_for(self, scheduled_at: datetime) -> "SendNotificationRequestBuilder":
        """Set schedule time"""
        self._data["scheduled_at"] = scheduled_at
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "SendNotificationRequestBuilder":
        """Set metadata"""
        self._data["metadata"].update(metadata)
        return self

    def with_tags(self, tags: List[str]) -> "SendNotificationRequestBuilder":
        """Set tags"""
        self._data["tags"] = tags
        return self

    def build(self) -> SendNotificationRequestContract:
        """Build the final request"""
        return SendNotificationRequestContract(**self._data)


class CreateTemplateRequestBuilder:
    """
    Builder pattern for creating complex template creation requests.

    Example:
        request = (
            CreateTemplateRequestBuilder()
            .with_name("Welcome Email")
            .with_type_email()
            .with_subject("Welcome {{name}}!")
            .with_content("Hello {{name}}, welcome aboard!")
            .with_variables(["name"])
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "variables": [],
            "metadata": {}
        }

    def with_name(self, name: str) -> "CreateTemplateRequestBuilder":
        """Set template name"""
        self._data["name"] = name
        return self

    def with_description(self, description: str) -> "CreateTemplateRequestBuilder":
        """Set template description"""
        self._data["description"] = description
        return self

    def with_type_email(self) -> "CreateTemplateRequestBuilder":
        """Set type to email"""
        self._data["type"] = NotificationType.EMAIL
        return self

    def with_type_sms(self) -> "CreateTemplateRequestBuilder":
        """Set type to SMS"""
        self._data["type"] = NotificationType.SMS
        return self

    def with_type_push(self) -> "CreateTemplateRequestBuilder":
        """Set type to push"""
        self._data["type"] = NotificationType.PUSH
        return self

    def with_type_in_app(self) -> "CreateTemplateRequestBuilder":
        """Set type to in-app"""
        self._data["type"] = NotificationType.IN_APP
        return self

    def with_subject(self, subject: str) -> "CreateTemplateRequestBuilder":
        """Set email subject"""
        self._data["subject"] = subject
        return self

    def with_content(self, content: str) -> "CreateTemplateRequestBuilder":
        """Set template content"""
        self._data["content"] = content
        return self

    def with_html_content(self, html_content: str) -> "CreateTemplateRequestBuilder":
        """Set HTML content"""
        self._data["html_content"] = html_content
        return self

    def with_variables(self, variables: List[str]) -> "CreateTemplateRequestBuilder":
        """Set template variables"""
        self._data["variables"] = variables
        return self

    def add_variable(self, variable: str) -> "CreateTemplateRequestBuilder":
        """Add template variable"""
        if variable not in self._data["variables"]:
            self._data["variables"].append(variable)
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "CreateTemplateRequestBuilder":
        """Set metadata"""
        self._data["metadata"].update(metadata)
        return self

    def build(self) -> CreateTemplateRequestContract:
        """Build the final request"""
        return CreateTemplateRequestContract(**self._data)


class BatchNotificationRequestBuilder:
    """
    Builder pattern for creating complex batch notification requests.

    Example:
        request = (
            BatchNotificationRequestBuilder()
            .with_name("Welcome Campaign")
            .with_template("tpl_welcome_123")
            .with_type_email()
            .add_recipient("user_123", {"name": "John"})
            .add_recipient("user_456", {"name": "Jane"})
            .with_high_priority()
            .build()
        )
    """

    def __init__(self):
        self._data = {
            "recipients": [],
            "metadata": {},
            "priority": NotificationPriority.NORMAL
        }

    def with_name(self, name: str) -> "BatchNotificationRequestBuilder":
        """Set batch name"""
        self._data["name"] = name
        return self

    def with_template(self, template_id: str) -> "BatchNotificationRequestBuilder":
        """Set template ID"""
        self._data["template_id"] = template_id
        return self

    def with_type_email(self) -> "BatchNotificationRequestBuilder":
        """Set type to email"""
        self._data["type"] = NotificationType.EMAIL
        return self

    def with_type_push(self) -> "BatchNotificationRequestBuilder":
        """Set type to push"""
        self._data["type"] = NotificationType.PUSH
        return self

    def add_recipient(self, user_id: str, variables: Dict[str, Any] = None) -> "BatchNotificationRequestBuilder":
        """Add recipient"""
        recipient = {"user_id": user_id}
        if variables:
            recipient["variables"] = variables
        self._data["recipients"].append(recipient)
        return self

    def add_email_recipient(self, email: str, variables: Dict[str, Any] = None) -> "BatchNotificationRequestBuilder":
        """Add email recipient"""
        recipient = {"email": email}
        if variables:
            recipient["variables"] = variables
        self._data["recipients"].append(recipient)
        return self

    def with_recipients(self, recipients: List[Dict[str, Any]]) -> "BatchNotificationRequestBuilder":
        """Set all recipients"""
        self._data["recipients"] = recipients
        return self

    def with_high_priority(self) -> "BatchNotificationRequestBuilder":
        """Set high priority"""
        self._data["priority"] = NotificationPriority.HIGH
        return self

    def schedule_for(self, scheduled_at: datetime) -> "BatchNotificationRequestBuilder":
        """Set schedule time"""
        self._data["scheduled_at"] = scheduled_at
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "BatchNotificationRequestBuilder":
        """Set metadata"""
        self._data["metadata"].update(metadata)
        return self

    def build(self) -> SendBatchRequestContract:
        """Build the final request"""
        return SendBatchRequestContract(**self._data)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Request Contracts
    "SendNotificationRequestContract",
    "SendBatchRequestContract",
    "CreateTemplateRequestContract",
    "UpdateTemplateRequestContract",
    "RegisterPushSubscriptionRequestContract",
    "MarkNotificationReadRequestContract",
    "ListNotificationsRequestContract",

    # Response Contracts
    "NotificationResponseContract",
    "TemplateResponseContract",
    "BatchResponseContract",
    "InAppNotificationResponseContract",
    "PushSubscriptionResponseContract",
    "NotificationStatsResponseContract",
    "UnreadCountResponseContract",

    # Factory
    "NotificationTestDataFactory",

    # Builders
    "SendNotificationRequestBuilder",
    "CreateTemplateRequestBuilder",
    "BatchNotificationRequestBuilder",
]
