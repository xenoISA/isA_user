"""
Event Data Models for Notification Service

Defines Pydantic models for events published and consumed by notification_service
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


# ====================
# Outbound Event Models (Published by notification_service)
# ====================

class NotificationSentEventData(BaseModel):
    """Data for notification.sent event"""
    notification_id: str = Field(..., description="Notification ID")
    notification_type: str = Field(..., description="Type: email, in_app, push, sms, webhook")
    recipient_id: Optional[str] = Field(None, description="Recipient user ID")
    recipient_email: Optional[str] = Field(None, description="Recipient email address")
    status: str = Field(..., description="Notification status")
    subject: Optional[str] = Field(None, description="Notification subject")
    priority: str = Field(..., description="Priority: low, normal, high, urgent")
    timestamp: str = Field(..., description="ISO timestamp of send")


class NotificationFailedEventData(BaseModel):
    """Data for notification.failed event"""
    notification_id: str = Field(..., description="Notification ID")
    notification_type: str = Field(..., description="Type: email, in_app, push, sms, webhook")
    recipient_id: Optional[str] = Field(None, description="Recipient user ID")
    recipient_email: Optional[str] = Field(None, description="Recipient email address")
    error_message: str = Field(..., description="Error message")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    timestamp: str = Field(..., description="ISO timestamp of failure")


class NotificationDeliveredEventData(BaseModel):
    """Data for notification.delivered event"""
    notification_id: str = Field(..., description="Notification ID")
    notification_type: str = Field(..., description="Type: email, in_app, push, sms, webhook")
    recipient_id: Optional[str] = Field(None, description="Recipient user ID")
    delivered_at: str = Field(..., description="ISO timestamp of delivery confirmation")


class NotificationClickedEventData(BaseModel):
    """Data for notification.clicked event"""
    notification_id: str = Field(..., description="Notification ID")
    user_id: str = Field(..., description="User ID who clicked")
    click_url: Optional[str] = Field(None, description="URL that was clicked")
    clicked_at: str = Field(..., description="ISO timestamp of click")


class NotificationBatchCompletedEventData(BaseModel):
    """Data for notification.batch_completed event"""
    batch_id: str = Field(..., description="Batch ID")
    total_recipients: int = Field(..., description="Total number of recipients")
    sent_count: int = Field(..., description="Successfully sent count")
    delivered_count: int = Field(..., description="Delivered count")
    failed_count: int = Field(..., description="Failed count")
    completed_at: str = Field(..., description="ISO timestamp of batch completion")


# ====================
# Inbound Event Models (Consumed by notification_service)
# ====================

class UserLoggedInEventData(BaseModel):
    """Data from user.logged_in event"""
    user_id: str
    email: Optional[str] = None
    provider: Optional[str] = "email"
    timestamp: Optional[str] = None


class UserRegisteredEventData(BaseModel):
    """Data from user.registered event"""
    user_id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    timestamp: Optional[str] = None


class UserPasswordResetEventData(BaseModel):
    """Data from user.password_reset event"""
    user_id: str
    email: str
    reset_token: str
    reset_url: str
    expires_at: Optional[str] = None


class PaymentCompletedEventData(BaseModel):
    """Data from payment.completed event"""
    payment_id: str
    user_id: str
    amount: float
    currency: str = "USD"
    customer_email: Optional[str] = None
    payment_method: Optional[str] = None
    timestamp: Optional[str] = None


class OrganizationMemberAddedEventData(BaseModel):
    """Data from organization.member_added event"""
    organization_id: str
    organization_name: str
    user_id: str
    role: str = "member"
    added_by: Optional[str] = None
    timestamp: Optional[str] = None


class DeviceOfflineEventData(BaseModel):
    """Data from device.offline event"""
    device_id: str
    device_name: str
    user_id: str
    last_seen: Optional[str] = None
    timestamp: Optional[str] = None


class FileUploadedEventData(BaseModel):
    """Data from file.uploaded event"""
    file_id: str
    file_name: str
    user_id: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    timestamp: Optional[str] = None


class FileSharedEventData(BaseModel):
    """Data from file.shared event"""
    share_id: str
    file_id: str
    file_name: str
    shared_by: str
    shared_with: Optional[str] = None  # User ID
    shared_with_email: Optional[str] = None  # For external shares
    permission: Optional[str] = "view"
    timestamp: Optional[str] = None


class OrderCreatedEventData(BaseModel):
    """Data from order.created event"""
    order_id: str
    user_id: str
    customer_email: Optional[str] = None
    total_amount: float
    currency: str = "USD"
    items_count: int
    timestamp: Optional[str] = None


class OrderShippedEventData(BaseModel):
    """Data from order.shipped event"""
    order_id: str
    user_id: str
    customer_email: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    estimated_delivery: Optional[str] = None
    timestamp: Optional[str] = None


class TaskAssignedEventData(BaseModel):
    """Data from task.assigned event"""
    task_id: str
    task_title: str
    assigned_to: str  # User ID
    assigned_by: str  # User ID
    due_date: Optional[str] = None
    priority: Optional[str] = "normal"
    timestamp: Optional[str] = None


class TaskDueSoonEventData(BaseModel):
    """Data from task.due_soon event"""
    task_id: str
    task_title: str
    assigned_to: str  # User ID
    due_date: str
    hours_until_due: int
    timestamp: Optional[str] = None


class InvitationCreatedEventData(BaseModel):
    """Data from invitation.created event"""
    invitation_id: str
    inviter_id: str
    inviter_name: Optional[str] = None
    invitee_email: str
    invitation_type: str  # organization, event, etc.
    invitation_url: str
    expires_at: Optional[str] = None
    timestamp: Optional[str] = None


class ComplianceAlertEventData(BaseModel):
    """Data from compliance.alert event"""
    alert_id: str
    user_id: str
    violation_type: str
    severity: str  # low, medium, high, critical
    description: str
    action_required: Optional[str] = None
    timestamp: Optional[str] = None


class WalletBalanceLowEventData(BaseModel):
    """Data from wallet.balance_low event"""
    wallet_id: str
    user_id: str
    current_balance: float
    currency: str = "USD"
    threshold: float
    timestamp: Optional[str] = None


class BillingInvoiceReadyEventData(BaseModel):
    """Data from billing.invoice_ready event"""
    invoice_id: str
    user_id: str
    customer_email: Optional[str] = None
    amount: float
    currency: str = "USD"
    due_date: Optional[str] = None
    invoice_url: Optional[str] = None
    timestamp: Optional[str] = None
