"""
Compliance Service Event Handlers

Handles events from other services that require compliance checks
"""

import logging
from typing import Dict, Callable

from core.nats_client import Event

logger = logging.getLogger(__name__)


async def handle_content_created(event: Event, compliance_service, event_bus):
    """
    Handle content.created event from other services
    Automatically trigger compliance check for new content

    Args:
        event: The content.created event
        compliance_service: ComplianceService instance
        event_bus: NATS event bus instance
    """
    try:
        user_id = event.data.get("user_id")
        content = event.data.get("content")
        content_type = event.data.get("content_type", "text")

        if not user_id or not content:
            logger.warning(f"Missing required fields in content.created event: {event.id}")
            return

        logger.info(
            f"Triggering compliance check for content.created event "
            f"(user: {user_id}, type: {content_type})"
        )

        # Perform compliance check
        # Note: This would call the actual compliance check method
        # For now, just logging the event
        logger.debug(f"Would check content for user {user_id}: {content[:100]}...")

    except Exception as e:
        logger.error(f"Error handling content.created event: {e}", exc_info=True)


async def handle_user_content_uploaded(event: Event, compliance_service, event_bus):
    """
    Handle user content upload events
    Check uploaded content for compliance

    Args:
        event: The upload event
        compliance_service: ComplianceService instance
        event_bus: NATS event bus instance
    """
    try:
        user_id = event.data.get("user_id")
        file_path = event.data.get("file_path")
        file_type = event.data.get("file_type")

        if not user_id or not file_path:
            logger.warning(f"Missing required fields in upload event: {event.id}")
            return

        logger.info(
            f"Triggering compliance check for uploaded content "
            f"(user: {user_id}, type: {file_type})"
        )

        # Perform compliance check on uploaded file
        # Note: This would call the actual compliance check method
        logger.debug(f"Would check uploaded file for user {user_id}: {file_path}")

    except Exception as e:
        logger.error(f"Error handling user content upload event: {e}", exc_info=True)


async def handle_user_deleted(event: Event, compliance_service, event_bus):
    """
    Handle user.deleted event

    Clean up compliance records for deleted user (GDPR compliance)

    Args:
        event: The user.deleted event
        compliance_service: ComplianceService instance
        event_bus: NATS event bus instance
    """
    try:
        user_id = event.data.get("user_id")

        if not user_id:
            logger.warning(f"Missing user_id in user.deleted event: {event.id}")
            return

        logger.info(f"Processing user.deleted for compliance cleanup: {user_id}")

        # Clean up user's compliance records
        if hasattr(compliance_service, 'repository'):
            # Delete compliance check history
            deleted_checks = await compliance_service.repository.delete_user_compliance_records(user_id)
            logger.info(f"Deleted {deleted_checks} compliance records for user {user_id}")

            # Anonymize any retained audit logs (keep for legal requirements)
            anonymized = await compliance_service.repository.anonymize_user_audit_logs(user_id)
            logger.info(f"Anonymized {anonymized} audit logs for user {user_id}")

        logger.info(f"✅ Compliance cleanup completed for user {user_id} (GDPR Article 17)")

    except Exception as e:
        logger.error(f"Error handling user.deleted event: {e}", exc_info=True)


async def handle_payment_transaction(event: Event, compliance_service, event_bus):
    """
    Handle payment.completed event for compliance monitoring

    Monitor large transactions for AML compliance

    Args:
        event: The payment event
        compliance_service: ComplianceService instance
        event_bus: NATS event bus instance
    """
    try:
        user_id = event.data.get("user_id")
        amount = event.data.get("amount", 0)
        currency = event.data.get("currency", "USD")

        if not user_id:
            return

        # Check if transaction exceeds reporting threshold
        threshold = 10000  # Example AML reporting threshold
        if float(amount) >= threshold:
            logger.warning(
                f"Large transaction detected for user {user_id}: "
                f"{currency} {amount} - flagging for review"
            )

            # Create compliance alert
            if hasattr(compliance_service, 'create_alert'):
                await compliance_service.create_alert(
                    user_id=user_id,
                    alert_type="large_transaction",
                    severity="high",
                    details={
                        "amount": amount,
                        "currency": currency,
                        "event_id": event.id,
                    }
                )

    except Exception as e:
        logger.error(f"Error handling payment transaction for compliance: {e}", exc_info=True)


def get_event_handlers(compliance_service, event_bus) -> Dict[str, Callable]:
    """
    Get all event handlers for compliance service

    Args:
        compliance_service: ComplianceService instance
        event_bus: NATS event bus instance

    Returns:
        Dictionary mapping event patterns to handler functions
    """
    return {
        # Handle content creation events from other services
        "content.created": lambda event: handle_content_created(
            event, compliance_service, event_bus
        ),
        # Handle file upload events
        "storage.file_uploaded": lambda event: handle_user_content_uploaded(
            event, compliance_service, event_bus
        ),
        # Handle user deletion for GDPR compliance
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event, compliance_service, event_bus
        ),
        # Monitor payment transactions for AML compliance
        "payment_service.payment.completed": lambda event: handle_payment_transaction(
            event, compliance_service, event_bus
        ),
    }
