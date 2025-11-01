"""
Event Handlers for Notification Service

Handles events from other services and triggers appropriate notifications
"""

import logging
from datetime import datetime
from typing import Set

from core.nats_client import Event
from ..notification_service import NotificationService
from ..models import (
    SendNotificationRequest,
    NotificationType,
    NotificationPriority
)

logger = logging.getLogger(__name__)


class NotificationEventHandlers:
    """Event handlers for notification service"""

    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        # Track processed event IDs for idempotency
        self.processed_event_ids: Set[str] = set()
        # TODO: In production, use Redis or database for distributed idempotency

    def is_event_processed(self, event_id: str) -> bool:
        """Check if event has already been processed (idempotency)"""
        return event_id in self.processed_event_ids

    def mark_event_processed(self, event_id: str):
        """Mark event as processed"""
        self.processed_event_ids.add(event_id)
        # Limit in-memory cache size
        if len(self.processed_event_ids) > 10000:
            # Remove oldest half
            self.processed_event_ids = set(list(self.processed_event_ids)[5000:])

    async def handle_user_logged_in(self, event: Event):
        """
        Handle user.logged_in event
        Send welcome back in-app notification
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
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
                    "timestamp": event.timestamp
                }
            )

            result = await self.notification_service.send_notification(notification_request)

            # Mark as processed
            self.mark_event_processed(event.id)

            logger.info(f"Sent welcome back notification to user {user_id} (event: {event.id})")

        except Exception as e:
            logger.error(f"Failed to handle user.logged_in event {event.id}: {e}")

    async def handle_payment_completed(self, event: Event):
        """
        Handle payment.completed event
        Send receipt email
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            payment_id = event.data.get("payment_id")
            user_id = event.data.get("user_id")
            amount = event.data.get("amount")
            currency = event.data.get("currency", "USD")
            customer_email = event.data.get("customer_email")

            if not user_id or not payment_id:
                logger.warning(f"payment.completed event missing required fields: {event.id}")
                return

            # Format amount for display
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
                    <tr><td><strong>Date:</strong></td><td>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</td></tr>
                </table>
                <p>If you have any questions, please contact support.</p>
                """,
                priority=NotificationPriority.HIGH,
                metadata={
                    "event_id": event.id,
                    "event_type": event.type,
                    "payment_id": payment_id,
                    "amount": amount
                }
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
                    "category": "payment"
                }
            )

            # Send both notifications
            await self.notification_service.send_notification(email_request)
            await self.notification_service.send_notification(in_app_request)

            # Mark as processed
            self.mark_event_processed(event.id)

            logger.info(f"Sent payment receipt to user {user_id} for payment {payment_id} (event: {event.id})")

        except Exception as e:
            logger.error(f"Failed to handle payment.completed event {event.id}: {e}")

    async def handle_organization_member_added(self, event: Event):
        """
        Handle organization.member_added event
        Send invitation/welcome notification to new member
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            organization_id = event.data.get("organization_id")
            organization_name = event.data.get("organization_name")
            user_id = event.data.get("user_id")
            role = event.data.get("role", "member")
            added_by = event.data.get("added_by")

            if not user_id or not organization_id:
                logger.warning(f"organization.member_added event missing required fields: {event.id}")
                return

            # Send in-app notification
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
                    "category": "organization"
                }
            )

            result = await self.notification_service.send_notification(notification_request)

            # Mark as processed
            self.mark_event_processed(event.id)

            logger.info(f"Sent organization invitation notification to user {user_id} (event: {event.id})")

        except Exception as e:
            logger.error(f"Failed to handle organization.member_added event {event.id}: {e}")

    async def handle_device_offline(self, event: Event):
        """
        Handle device.offline event
        Send device offline alert to user
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            device_id = event.data.get("device_id")
            device_name = event.data.get("device_name")
            user_id = event.data.get("user_id")

            if not user_id or not device_id:
                logger.warning(f"device.offline event missing required fields: {event.id}")
                return

            # Send in-app notification
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
                    "category": "device"
                }
            )

            result = await self.notification_service.send_notification(notification_request)

            # Mark as processed
            self.mark_event_processed(event.id)

            logger.info(f"Sent device offline alert to user {user_id} for device {device_id} (event: {event.id})")

        except Exception as e:
            logger.error(f"Failed to handle device.offline event {event.id}: {e}")

    async def handle_file_uploaded(self, event: Event):
        """
        Handle file.uploaded event
        Send file upload confirmation notification
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            file_id = event.data.get("file_id")
            file_name = event.data.get("file_name")
            user_id = event.data.get("user_id")
            file_size = event.data.get("file_size")

            if not user_id or not file_id:
                logger.warning(f"file.uploaded event missing required fields: {event.id}")
                return

            # Format file size
            size_mb = file_size / (1024 * 1024) if file_size else 0
            size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{file_size / 1024:.2f} KB"

            # Send in-app notification
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
                    "category": "storage"
                }
            )

            result = await self.notification_service.send_notification(notification_request)

            # Mark as processed
            self.mark_event_processed(event.id)

            logger.info(f"Sent file upload notification to user {user_id} for file {file_id} (event: {event.id})")

        except Exception as e:
            logger.error(f"Failed to handle file.uploaded event {event.id}: {e}")

    async def handle_file_shared(self, event: Event):
        """
        Handle file.shared event
        Notify recipient that a file has been shared with them
        """
        try:
            # Check idempotency
            if self.is_event_processed(event.id):
                logger.debug(f"Event {event.id} already processed, skipping")
                return

            file_name = event.data.get("file_name")
            shared_by = event.data.get("shared_by")
            shared_with = event.data.get("shared_with")
            shared_with_email = event.data.get("shared_with_email")
            share_id = event.data.get("share_id")

            # Send notification to recipient if user_id is provided
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
                        "category": "storage"
                    }
                )

                await self.notification_service.send_notification(notification_request)

            # If only email is provided, send email notification
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
                        "category": "storage"
                    }
                )

                await self.notification_service.send_notification(email_request)

            # Mark as processed
            self.mark_event_processed(event.id)

            logger.info(f"Sent file share notification (event: {event.id})")

        except Exception as e:
            logger.error(f"Failed to handle file.shared event {event.id}: {e}")

    def get_event_handler_map(self):
        """
        Return mapping of event types to handler functions
        """
        return {
            "user.logged_in": self.handle_user_logged_in,
            "payment.completed": self.handle_payment_completed,
            "organization.member_added": self.handle_organization_member_added,
            "device.offline": self.handle_device_offline,
            "file.uploaded": self.handle_file_uploaded,
            "file.shared": self.handle_file_shared
        }
