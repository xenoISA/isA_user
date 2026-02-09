"""
Event Handlers for Notification Service

Handles events from other services and triggers appropriate notifications
"""

import logging
from datetime import datetime
from typing import Set

from core.nats_client import Event

logger = logging.getLogger(__name__)


# =============================================================================
# Idempotency Tracking
# =============================================================================

_processed_event_ids: Set[str] = set()


def _is_event_processed(event_id: str) -> bool:
    """Check if event has already been processed (idempotency)"""
    return event_id in _processed_event_ids


def _mark_event_processed(event_id: str):
    """Mark event as processed"""
    global _processed_event_ids
    _processed_event_ids.add(event_id)
    # Limit in-memory cache size
    if len(_processed_event_ids) > 10000:
        # Remove oldest half
        _processed_event_ids = set(list(_processed_event_ids)[5000:])


# =============================================================================
# Event Handlers
# =============================================================================


async def handle_user_logged_in(event: Event, notification_service):
    """
    Handle user.logged_in event
    Send welcome back in-app notification
    """
    try:
        # Import models here to avoid circular imports
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        user_id = event.data.get("user_id")
        email = event.data.get("email")
        provider = event.data.get("provider", "email")

        if not user_id:
            logger.warning(f"user.logged_in event missing user_id: {event.id}")
            return

        # Send in-app notification
        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            recipient_email=email,
            subject="Welcome back!",
            content=f"You've successfully logged in via {provider}.",
            priority=NotificationPriority.NORMAL,
            metadata={
                "event_id": event.id,
                "event_type": event.type,
                "provider": provider,
                "timestamp": event.timestamp,
            },
        )

        result = await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(
            f"Sent welcome back notification to user {user_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(f"Failed to handle user.logged_in event {event.id}: {e}")


async def handle_payment_completed(event: Event, notification_service):
    """
    Handle payment.completed event
    Send receipt email
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        payment_id = event.data.get("payment_id")
        user_id = event.data.get("user_id")
        amount = event.data.get("amount")
        currency = event.data.get("currency", "USD")
        customer_email = event.data.get("customer_email")

        if not user_id or not payment_id:
            logger.warning(
                f"payment.completed event missing required fields: {event.id}"
            )
            return

        amount_str = f"{currency} {amount:.2f}" if amount else "N/A"

        # Send email receipt
        email_request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_id=user_id,
            recipient_email=customer_email,
            subject=f"Payment Receipt - {payment_id}",
            content=f"Your payment of {amount_str} has been completed successfully.\n\nPayment ID: {payment_id}\nDate: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            html_content=f"""
            <h2>Payment Receipt</h2>
            <p>Thank you for your payment!</p>
            <table style="border: 1px solid #ddd; padding: 10px;">
                <tr><td><strong>Payment ID:</strong></td><td>{payment_id}</td></tr>
                <tr><td><strong>Amount:</strong></td><td>{amount_str}</td></tr>
                <tr><td><strong>Status:</strong></td><td>Completed</td></tr>
                <tr><td><strong>Date:</strong></td><td>{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</td></tr>
            </table>
            <p>If you have any questions, please contact support.</p>
            """,
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "event_type": event.type,
                "payment_id": payment_id,
                "amount": amount,
            },
        )

        # Also send in-app notification
        in_app_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject="Payment Completed",
            content=f"Your payment of {amount_str} has been completed successfully.",
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "payment_id": payment_id,
                "category": "payment",
            },
        )

        await notification_service.send_notification(email_request)
        await notification_service.send_notification(in_app_request)
        _mark_event_processed(event.id)

        logger.info(
            f"Sent payment receipt to user {user_id} for payment {payment_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(f"Failed to handle payment.completed event {event.id}: {e}")


async def handle_organization_member_added(event: Event, notification_service):
    """
    Handle organization.member_added event
    Send invitation/welcome notification to new member
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        organization_id = event.data.get("organization_id")
        organization_name = event.data.get("organization_name")
        user_id = event.data.get("user_id")
        role = event.data.get("role", "member")
        added_by = event.data.get("added_by")

        if not user_id or not organization_id:
            logger.warning(
                f"organization.member_added event missing required fields: {event.id}"
            )
            return

        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject=f"Added to {organization_name}",
            content=f"You have been added to the organization '{organization_name}' as a {role}.",
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "event_type": event.type,
                "organization_id": organization_id,
                "role": role,
                "category": "organization",
            },
        )

        result = await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(
            f"Sent organization invitation notification to user {user_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(
            f"Failed to handle organization.member_added event {event.id}: {e}"
        )


async def handle_device_offline(event: Event, notification_service):
    """
    Handle device.offline event
    Send device offline alert to user
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        device_id = event.data.get("device_id")
        device_name = event.data.get("device_name")
        user_id = event.data.get("user_id")

        if not user_id or not device_id:
            logger.warning(f"device.offline event missing required fields: {event.id}")
            return

        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject=f"Device Offline: {device_name}",
            content=f"Your device '{device_name}' is now offline.",
            priority=NotificationPriority.NORMAL,
            metadata={
                "event_id": event.id,
                "event_type": event.type,
                "device_id": device_id,
                "device_name": device_name,
                "category": "device",
            },
        )

        result = await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(
            f"Sent device offline alert to user {user_id} for device {device_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(f"Failed to handle device.offline event {event.id}: {e}")


async def handle_file_uploaded(event: Event, notification_service):
    """
    Handle file.uploaded event
    Send file upload confirmation notification
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        file_id = event.data.get("file_id")
        file_name = event.data.get("file_name")
        user_id = event.data.get("user_id")
        file_size = event.data.get("file_size")

        if not user_id or not file_id:
            logger.warning(f"file.uploaded event missing required fields: {event.id}")
            return

        size_mb = file_size / (1024 * 1024) if file_size else 0
        size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{file_size / 1024:.2f} KB"

        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject="File Uploaded Successfully",
            content=f"'{file_name}' ({size_str}) has been uploaded successfully.",
            priority=NotificationPriority.LOW,
            metadata={
                "event_id": event.id,
                "event_type": event.type,
                "file_id": file_id,
                "file_name": file_name,
                "category": "storage",
            },
        )

        result = await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(
            f"Sent file upload notification to user {user_id} for file {file_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(f"Failed to handle file.uploaded event {event.id}: {e}")


async def handle_file_shared(event: Event, notification_service):
    """
    Handle file.shared event
    Notify recipient that a file has been shared with them
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        file_name = event.data.get("file_name")
        shared_by = event.data.get("shared_by")
        shared_with = event.data.get("shared_with")
        shared_with_email = event.data.get("shared_with_email")
        share_id = event.data.get("share_id")

        if shared_with:
            notification_request = SendNotificationRequest(
                type=NotificationType.IN_APP,
                recipient_id=shared_with,
                recipient_email=shared_with_email,
                subject="File Shared With You",
                content=f"'{file_name}' has been shared with you.",
                priority=NotificationPriority.NORMAL,
                metadata={
                    "event_id": event.id,
                    "event_type": event.type,
                    "share_id": share_id,
                    "file_name": file_name,
                    "shared_by": shared_by,
                    "category": "storage",
                },
            )

            await notification_service.send_notification(notification_request)

        elif shared_with_email:
            email_request = SendNotificationRequest(
                type=NotificationType.EMAIL,
                recipient_id="external_user",
                recipient_email=shared_with_email,
                subject="A file has been shared with you",
                content=f"Someone shared '{file_name}' with you.",
                html_content=f"""
                <h2>File Shared</h2>
                <p>A file has been shared with you:</p>
                <p><strong>{file_name}</strong></p>
                <p>Check your email for the access link.</p>
                """,
                priority=NotificationPriority.NORMAL,
                metadata={
                    "event_id": event.id,
                    "share_id": share_id,
                    "category": "storage",
                },
            )

            await notification_service.send_notification(email_request)

        _mark_event_processed(event.id)
        logger.info(f"Sent file share notification (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle file.shared event {event.id}: {e}")


async def handle_user_registered(event: Event, notification_service):
    """
    Handle user.registered event
    Send welcome email to new user
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        user_id = event.data.get("user_id")
        email = event.data.get("email")
        username = event.data.get("username")
        full_name = event.data.get("full_name")

        if not user_id or not email:
            logger.warning(f"user.registered event missing required fields: {event.id}")
            return

        display_name = full_name or username or email

        email_request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_id=user_id,
            recipient_email=email,
            subject="Welcome to isA!",
            content=f"Hi {display_name},\n\nWelcome to isA! We're excited to have you on board.\n\nGet started by exploring our features.",
            html_content=f"""
            <h2>Welcome to isA!</h2>
            <p>Hi {display_name},</p>
            <p>We're excited to have you on board! Thank you for registering.</p>
            <p>Get started by exploring our features and setting up your profile.</p>
            <p>If you have any questions, feel free to reach out to our support team.</p>
            <p>Best regards,<br>The isA Team</p>
            """,
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "event_type": event.type,
                "category": "onboarding",
            },
        )

        await notification_service.send_notification(email_request)
        _mark_event_processed(event.id)

        logger.info(f"Sent welcome email to new user {user_id} (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle user.registered event {event.id}: {e}")


async def handle_order_created(event: Event, notification_service):
    """
    Handle order.created event
    Send order confirmation notification
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        order_id = event.data.get("order_id")
        user_id = event.data.get("user_id")
        customer_email = event.data.get("customer_email")
        total_amount = event.data.get("total_amount")
        currency = event.data.get("currency", "USD")
        items_count = event.data.get("items_count", 0)

        if not order_id or not user_id:
            logger.warning(f"order.created event missing required fields: {event.id}")
            return

        amount_str = f"{currency} {total_amount:.2f}" if total_amount else "N/A"

        email_request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_id=user_id,
            recipient_email=customer_email,
            subject=f"Order Confirmation - {order_id}",
            content=f"Your order has been confirmed!\n\nOrder ID: {order_id}\nItems: {items_count}\nTotal: {amount_str}",
            html_content=f"""
            <h2>Order Confirmation</h2>
            <p>Thank you for your order!</p>
            <table style="border: 1px solid #ddd; padding: 10px;">
                <tr><td><strong>Order ID:</strong></td><td>{order_id}</td></tr>
                <tr><td><strong>Items:</strong></td><td>{items_count}</td></tr>
                <tr><td><strong>Total:</strong></td><td>{amount_str}</td></tr>
            </table>
            <p>We'll send you another notification when your order ships.</p>
            """,
            priority=NotificationPriority.HIGH,
            metadata={"event_id": event.id, "order_id": order_id, "category": "order"},
        )

        in_app_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject="Order Confirmed",
            content=f"Your order ({items_count} items, {amount_str}) has been confirmed!",
            priority=NotificationPriority.NORMAL,
            metadata={"event_id": event.id, "order_id": order_id, "category": "order"},
        )

        await notification_service.send_notification(email_request)
        await notification_service.send_notification(in_app_request)
        _mark_event_processed(event.id)

        logger.info(f"Sent order confirmation for order {order_id} (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle order.created event {event.id}: {e}")


async def handle_task_assigned(event: Event, notification_service):
    """
    Handle task.assigned event
    Notify user about new task assignment
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        task_id = event.data.get("task_id")
        task_title = event.data.get("task_title")
        assigned_to = event.data.get("assigned_to")
        assigned_by = event.data.get("assigned_by")
        due_date = event.data.get("due_date")
        priority = event.data.get("priority", "normal")

        if not task_id or not assigned_to:
            logger.warning(f"task.assigned event missing required fields: {event.id}")
            return

        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=assigned_to,
            subject=f"New Task Assigned: {task_title}",
            content=f"You have been assigned a new task: {task_title}"
            + (f" (Due: {due_date})" if due_date else ""),
            priority=NotificationPriority.HIGH
            if priority == "urgent"
            else NotificationPriority.NORMAL,
            metadata={
                "event_id": event.id,
                "task_id": task_id,
                "assigned_by": assigned_by,
                "category": "task",
            },
        )

        await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(
            f"Sent task assignment notification for task {task_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(f"Failed to handle task.assigned event {event.id}: {e}")


async def handle_task_due_soon(event: Event, notification_service):
    """
    Handle task.due_soon event
    Send reminder notification about upcoming task
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        task_id = event.data.get("task_id")
        name = event.data.get("name")
        user_id = event.data.get("user_id")
        due_date = event.data.get("due_date")
        hours_until_due = event.data.get("hours_until_due", 24)

        if not task_id or not user_id:
            logger.warning(f"task.due_soon event missing required fields: {event.id}")
            return

        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject=f"Task Due Soon: {name}",
            content=f"Your task '{name}' is due in {hours_until_due} hours.",
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "task_id": task_id,
                "due_date": due_date,
                "category": "task",
            },
        )

        await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(
            f"Sent task due soon reminder for task {task_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(f"Failed to handle task.due_soon event {event.id}: {e}")


async def handle_invoice_created(event: Event, notification_service):
    """
    Handle invoice.created event
    Send invoice notification to user
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        invoice_id = event.data.get("invoice_id")
        user_id = event.data.get("user_id")
        customer_email = event.data.get("customer_email")
        amount = event.data.get("amount")
        currency = event.data.get("currency", "USD")
        due_date = event.data.get("due_date")
        invoice_url = event.data.get("invoice_url")

        if not invoice_id or not user_id:
            logger.warning(f"invoice.created event missing required fields: {event.id}")
            return

        amount_str = f"{currency} {amount:.2f}" if amount else "N/A"

        email_request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_id=user_id,
            recipient_email=customer_email,
            subject=f"Invoice #{invoice_id}",
            content=f"Your invoice for {amount_str} is ready.\n\nInvoice ID: {invoice_id}\nDue Date: {due_date or 'N/A'}",
            html_content=f"""
            <h2>Invoice Ready</h2>
            <p>Your invoice is ready for review.</p>
            <table style="border: 1px solid #ddd; padding: 10px;">
                <tr><td><strong>Invoice ID:</strong></td><td>{invoice_id}</td></tr>
                <tr><td><strong>Amount:</strong></td><td>{amount_str}</td></tr>
                <tr><td><strong>Due Date:</strong></td><td>{due_date or 'Upon Receipt'}</td></tr>
            </table>
            {f'<p><a href="{invoice_url}">View Invoice</a></p>' if invoice_url else ''}
            """,
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "invoice_id": invoice_id,
                "category": "billing",
            },
        )

        in_app_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject=f"Invoice Ready: {amount_str}",
            content=f"Invoice #{invoice_id} for {amount_str} is ready.",
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "invoice_id": invoice_id,
                "category": "billing",
            },
        )

        await notification_service.send_notification(email_request)
        await notification_service.send_notification(in_app_request)
        _mark_event_processed(event.id)

        logger.info(f"Sent invoice notification for invoice {invoice_id} (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle invoice.created event {event.id}: {e}")


async def handle_payment_refunded(event: Event, notification_service):
    """
    Handle payment.refunded event
    Send refund confirmation to user
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        payment_id = event.data.get("payment_id")
        refund_id = event.data.get("refund_id")
        user_id = event.data.get("user_id")
        customer_email = event.data.get("customer_email")
        amount = event.data.get("amount")
        currency = event.data.get("currency", "USD")
        reason = event.data.get("reason", "Refund processed")

        if not user_id:
            logger.warning(f"payment.refunded event missing user_id: {event.id}")
            return

        amount_str = f"{currency} {amount:.2f}" if amount else "N/A"

        email_request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_id=user_id,
            recipient_email=customer_email,
            subject=f"Refund Processed - {amount_str}",
            content=f"Your refund of {amount_str} has been processed.\n\nRefund ID: {refund_id or payment_id}\nReason: {reason}",
            html_content=f"""
            <h2>Refund Confirmation</h2>
            <p>Your refund has been processed successfully.</p>
            <table style="border: 1px solid #ddd; padding: 10px;">
                <tr><td><strong>Amount:</strong></td><td>{amount_str}</td></tr>
                <tr><td><strong>Refund ID:</strong></td><td>{refund_id or payment_id}</td></tr>
                <tr><td><strong>Reason:</strong></td><td>{reason}</td></tr>
            </table>
            <p>The refund should appear in your account within 5-10 business days.</p>
            """,
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "payment_id": payment_id,
                "refund_id": refund_id,
                "category": "payment",
            },
        )

        in_app_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject="Refund Processed",
            content=f"Your refund of {amount_str} has been processed.",
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "payment_id": payment_id,
                "category": "payment",
            },
        )

        await notification_service.send_notification(email_request)
        await notification_service.send_notification(in_app_request)
        _mark_event_processed(event.id)

        logger.info(f"Sent refund confirmation for payment {payment_id} (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle payment.refunded event {event.id}: {e}")


async def handle_invitation_created(event: Event, notification_service):
    """
    Handle invitation.created event
    Send invitation email to invitee
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        invitation_id = event.data.get("invitation_id")
        inviter_name = event.data.get("inviter_name", "Someone")
        invitee_email = event.data.get("invitee_email")
        invitation_type = event.data.get("invitation_type", "invitation")
        invitation_url = event.data.get("invitation_url")
        expires_at = event.data.get("expires_at")

        if not invitation_id or not invitee_email or not invitation_url:
            logger.warning(
                f"invitation.created event missing required fields: {event.id}"
            )
            return

        email_request = SendNotificationRequest(
            type=NotificationType.EMAIL,
            recipient_id="external_user",
            recipient_email=invitee_email,
            subject=f"You've been invited by {inviter_name}",
            content=f"{inviter_name} has invited you!\n\nClick here to accept: {invitation_url}",
            html_content=f"""
            <h2>You've been invited!</h2>
            <p><strong>{inviter_name}</strong> has invited you to join.</p>
            <p><a href="{invitation_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Accept Invitation</a></p>
            {f"<p><small>This invitation expires on {expires_at}</small></p>" if expires_at else ""}
            """,
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "invitation_id": invitation_id,
                "category": "invitation",
            },
        )

        await notification_service.send_notification(email_request)
        _mark_event_processed(event.id)

        logger.info(
            f"Sent invitation email for invitation {invitation_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(f"Failed to handle invitation.created event {event.id}: {e}")


async def handle_subscription_renewed(event: Event, notification_service):
    """
    Handle subscription.renewed event
    Send renewal confirmation
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        subscription_id = event.data.get("subscription_id")
        user_id = event.data.get("user_id")
        credits_allocated = event.data.get("credits_allocated")
        new_period_end = event.data.get("new_period_end")

        if not user_id:
            logger.warning(f"subscription.renewed event missing user_id: {event.id}")
            return

        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject="Subscription Renewed",
            content=f"Your subscription has been renewed! {credits_allocated} credits have been added to your account.",
            priority=NotificationPriority.NORMAL,
            metadata={
                "event_id": event.id,
                "subscription_id": subscription_id,
                "category": "subscription",
            },
        )

        await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(f"Sent subscription renewal notification (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle subscription.renewed event {event.id}: {e}")


async def handle_trial_ending_soon(event: Event, notification_service):
    """
    Handle subscription.trial.ending_soon event
    Send reminder about trial expiring
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        subscription_id = event.data.get("subscription_id")
        user_id = event.data.get("user_id")
        days_remaining = event.data.get("days_remaining", 3)
        trial_end_date = event.data.get("trial_end_date")

        if not user_id:
            logger.warning(f"trial.ending_soon event missing user_id: {event.id}")
            return

        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject=f"Trial Ending in {days_remaining} Days",
            content=f"Your free trial ends in {days_remaining} days. Upgrade now to keep access to all features!",
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "subscription_id": subscription_id,
                "trial_end_date": trial_end_date,
                "category": "subscription",
            },
        )

        await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(f"Sent trial ending soon notification (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle trial.ending_soon event {event.id}: {e}")


async def handle_credits_low(event: Event, notification_service):
    """
    Handle subscription.credits.low event
    Send low credits warning
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        subscription_id = event.data.get("subscription_id")
        user_id = event.data.get("user_id")
        credits_remaining = event.data.get("credits_remaining")
        percentage_remaining = event.data.get("percentage_remaining")

        if not user_id:
            logger.warning(f"credits.low event missing user_id: {event.id}")
            return

        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject="Low Credits Warning",
            content=f"You have {credits_remaining} credits remaining ({percentage_remaining:.0f}%). Consider upgrading or purchasing more credits.",
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "subscription_id": subscription_id,
                "category": "subscription",
            },
        )

        await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(f"Sent credits low notification (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle credits.low event {event.id}: {e}")


async def handle_wallet_balance_low(event: Event, notification_service):
    """
    Handle wallet.balance_low event
    Send low balance alert to user
    """
    try:
        from ..models import (
            NotificationPriority,
            NotificationType,
            SendNotificationRequest,
        )

        if _is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        wallet_id = event.data.get("wallet_id")
        user_id = event.data.get("user_id")
        current_balance = event.data.get("current_balance")
        currency = event.data.get("currency", "USD")
        threshold = event.data.get("threshold")

        if not user_id or current_balance is None:
            logger.warning(
                f"wallet.balance_low event missing required fields: {event.id}"
            )
            return

        balance_str = f"{currency} {current_balance:.2f}"
        threshold_str = f"{currency} {threshold:.2f}" if threshold else "threshold"

        notification_request = SendNotificationRequest(
            type=NotificationType.IN_APP,
            recipient_id=user_id,
            subject="Low Wallet Balance Alert",
            content=f"Your wallet balance ({balance_str}) is below {threshold_str}. Please top up to continue using services.",
            priority=NotificationPriority.HIGH,
            metadata={
                "event_id": event.id,
                "wallet_id": wallet_id,
                "category": "wallet",
            },
        )

        await notification_service.send_notification(notification_request)
        _mark_event_processed(event.id)

        logger.info(
            f"Sent low balance alert for wallet {wallet_id} (event: {event.id})"
        )

    except Exception as e:
        logger.error(f"Failed to handle wallet.balance_low event {event.id}: {e}")


# =============================================================================
# Event Handler Registry
# =============================================================================


def get_event_handlers(notification_service):
    """
    Get all event handlers for notification service.

    Returns a dict mapping event patterns to handler functions.
    This is used by main.py to register all event subscriptions.

    Args:
        notification_service: NotificationService instance

    Returns:
        Dict[str, callable]: Event pattern -> handler function mapping
    """
    return {
        "auth_service.user.logged_in": lambda event: handle_user_logged_in(
            event, notification_service
        ),
        "payment_service.payment.completed": lambda event: handle_payment_completed(
            event, notification_service
        ),
        "organization_service.organization.member_added": lambda event: handle_organization_member_added(
            event, notification_service
        ),
        "device_service.device.offline": lambda event: handle_device_offline(
            event, notification_service
        ),
        "storage_service.file.uploaded": lambda event: handle_file_uploaded(
            event, notification_service
        ),
        "storage_service.file.shared": lambda event: handle_file_shared(
            event, notification_service
        ),
        "account_service.user.registered": lambda event: handle_user_registered(
            event, notification_service
        ),
        "order_service.order.created": lambda event: handle_order_created(
            event, notification_service
        ),
        "task_service.task.assigned": lambda event: handle_task_assigned(
            event, notification_service
        ),
        "task_service.task.due_soon": lambda event: handle_task_due_soon(
            event, notification_service
        ),
        "payment_service.invoice.created": lambda event: handle_invoice_created(
            event, notification_service
        ),
        "payment_service.payment.refunded": lambda event: handle_payment_refunded(
            event, notification_service
        ),
        "invitation_service.invitation.created": lambda event: handle_invitation_created(
            event, notification_service
        ),
        "wallet_service.wallet.balance_low": lambda event: handle_wallet_balance_low(
            event, notification_service
        ),
        "subscription_service.subscription.renewed": lambda event: handle_subscription_renewed(
            event, notification_service
        ),
        "subscription_service.subscription.trial.ending_soon": lambda event: handle_trial_ending_soon(
            event, notification_service
        ),
        "subscription_service.subscription.credits.low": lambda event: handle_credits_low(
            event, notification_service
        ),
    }


__all__ = [
    "get_event_handlers",
    "handle_user_logged_in",
    "handle_payment_completed",
    "handle_payment_refunded",
    "handle_organization_member_added",
    "handle_device_offline",
    "handle_file_uploaded",
    "handle_file_shared",
    "handle_user_registered",
    "handle_order_created",
    "handle_task_assigned",
    "handle_task_due_soon",
    "handle_invoice_created",
    "handle_invitation_created",
    "handle_wallet_balance_low",
    "handle_subscription_renewed",
    "handle_trial_ending_soon",
    "handle_credits_low",
]
