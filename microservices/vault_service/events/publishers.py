"""
Vault Service Event Publishers

Centralized event publishing functions for vault service.
All events published by vault service should be defined here.
"""

import logging
from typing import Optional

from core.nats_client import Event

from .models import (
    create_secret_accessed_event_data,
    create_secret_created_event_data,
    create_secret_deleted_event_data,
    create_secret_shared_event_data,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Event Publishers
# =============================================================================


async def publish_secret_created(
    event_bus,
    user_id: str,
    vault_id: str,
    secret_type: str,
    name: str,
) -> bool:
    """
    Publish vault.secret.created event

    Notifies other services that a new secret has been created.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID who created the secret
        vault_id: Vault secret ID
        secret_type: Type of secret (api_key, password, etc.)
        name: Secret name/title

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - audit_service: Log secret creation for compliance
        - compliance_service: Track sensitive data creation
    """
    try:
        event_data = create_secret_created_event_data(
            user_id=user_id,
            vault_id=vault_id,
            secret_type=secret_type,
            name=name,
        )

        event = Event(
            event_type="vault.created",
            source="vault_service",
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "vault.secret.created"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f" Published vault.secret.created event for vault {vault_id}"
            )
        else:
            logger.error(
                f"L Failed to publish vault.secret.created event for vault {vault_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing secret.created event: {e}", exc_info=True)
        return False


async def publish_secret_accessed(
    event_bus,
    user_id: str,
    vault_id: str,
    access_type: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    """
    Publish vault.secret.accessed event

    Notifies when a secret is accessed (read, decrypted, etc.).

    Args:
        event_bus: NATS event bus instance
        user_id: User ID who accessed the secret
        vault_id: Vault secret ID
        access_type: Type of access (read, decrypt, rotate)
        ip_address: Client IP address
        user_agent: Client user agent

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - audit_service: Log access for security audit
        - compliance_service: Track data access patterns
    """
    try:
        event_data = create_secret_accessed_event_data(
            user_id=user_id,
            vault_id=vault_id,
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        event = Event(
            event_type="vault.accessed",
            source="vault_service",
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "vault.secret.accessed"

        result = await event_bus.publish_event(event)

        if result:
            logger.debug(
                f"Published vault.secret.accessed event for vault {vault_id}"
            )
        else:
            logger.warning(
                f"Failed to publish vault.secret.accessed event for vault {vault_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing secret.accessed event: {e}", exc_info=True)
        return False


async def publish_secret_deleted(
    event_bus,
    user_id: str,
    vault_id: str,
    secret_type: str,
) -> bool:
    """
    Publish vault.secret.deleted event

    Notifies when a secret is deleted.

    Args:
        event_bus: NATS event bus instance
        user_id: User ID who deleted the secret
        vault_id: Vault secret ID
        secret_type: Type of secret

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - audit_service: Log deletion for compliance
        - compliance_service: Track data deletion
    """
    try:
        event_data = create_secret_deleted_event_data(
            user_id=user_id,
            vault_id=vault_id,
            secret_type=secret_type,
        )

        event = Event(
            event_type="vault.deleted",
            source="vault_service",
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "vault.secret.deleted"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f" Published vault.secret.deleted event for vault {vault_id}"
            )
        else:
            logger.error(
                f"L Failed to publish vault.secret.deleted event for vault {vault_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing secret.deleted event: {e}", exc_info=True)
        return False


async def publish_secret_shared(
    event_bus,
    owner_user_id: str,
    vault_id: str,
    permission: str,
    shared_with_user_id: Optional[str] = None,
    shared_with_org_id: Optional[str] = None,
) -> bool:
    """
    Publish vault.secret.shared event

    Notifies when a secret is shared with another user or organization.

    Args:
        event_bus: NATS event bus instance
        owner_user_id: Owner user ID
        vault_id: Vault secret ID
        permission: Permission level (read, write)
        shared_with_user_id: User ID to share with
        shared_with_org_id: Organization ID to share with

    Returns:
        True if event published successfully, False otherwise

    Subscribers:
        - audit_service: Log sharing for security audit
        - notification_service: Notify recipient about shared secret
    """
    try:
        event_data = create_secret_shared_event_data(
            owner_user_id=owner_user_id,
            vault_id=vault_id,
            permission=permission,
            shared_with_user_id=shared_with_user_id,
            shared_with_org_id=shared_with_org_id,
        )

        event = Event(
            event_type="vault.shared",
            source="vault_service",
            data=event_data.model_dump(),
        )

        # Override with specific event type
        event.type = "vault.secret.shared"

        result = await event_bus.publish_event(event)

        if result:
            logger.info(
                f" Published vault.secret.shared event for vault {vault_id}"
            )
        else:
            logger.error(
                f"L Failed to publish vault.secret.shared event for vault {vault_id}"
            )

        return result

    except Exception as e:
        logger.error(f"Error publishing secret.shared event: {e}", exc_info=True)
        return False


__all__ = [
    "publish_secret_created",
    "publish_secret_accessed",
    "publish_secret_deleted",
    "publish_secret_shared",
]
