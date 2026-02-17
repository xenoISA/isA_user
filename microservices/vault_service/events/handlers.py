"""
Vault Service Event Handlers

处理来自其他服务的事件订阅
"""

import logging
from typing import Callable, Dict

from core.nats_client import Event

from .models import parse_user_deleted_event

logger = logging.getLogger(__name__)


# =============================================================================
# Event Handlers (Async Functions)
# =============================================================================


async def handle_user_deleted(event: Event, vault_service):
    """
    Handle user.deleted event

    当用户被删除时，自动清理该用户的所有 vault 数据
    包括: vault items, shares, access logs
    符合 GDPR Article 17: Right to Erasure

    Args:
        event: NATS event object
        vault_service: VaultService instance

    Event Data:
        - user_id: str
        - timestamp: str (optional)
        - reason: str (optional)

    Workflow:
        1. Parse event data
        2. Delete all user vault data (items, shares, logs)
        3. Log completion for compliance
    """
    try:
        # Parse event data
        event_data = parse_user_deleted_event(event.data)
        user_id = event_data.user_id

        if not user_id:
            logger.warning("Received user.deleted event without user_id")
            return

        logger.info(f"Handling user.deleted event for user: {user_id}")

        # Delete all user vault data
        deleted_count = await vault_service.repository.delete_user_data(user_id)

        logger.info(
            f"✅ Successfully deleted {deleted_count} vault records for user {user_id} "
            f"(GDPR compliance)"
        )

    except Exception as e:
        logger.error(
            f"❌ Error handling user.deleted event for user {event.data.get('user_id')}: {e}",
            exc_info=True,
        )
        # Don't raise - we don't want to break the event processing chain


# =============================================================================
# Event Handler Registry
# =============================================================================


def get_event_handlers(vault_service) -> Dict[str, Callable]:
    """
    Get all event handlers for vault service.

    Returns a dict mapping event patterns to handler functions.
    This is used by main.py to register all event subscriptions.

    Args:
        vault_service: VaultService instance

    Returns:
        Dict[str, callable]: Event pattern -> handler function mapping
    """
    return {
        "account_service.user.deleted": lambda event: handle_user_deleted(
            event, vault_service
        ),
        "*.user.deleted": lambda event: handle_user_deleted(event, vault_service),
    }


__all__ = [
    "handle_user_deleted",
    "get_event_handlers",
]
