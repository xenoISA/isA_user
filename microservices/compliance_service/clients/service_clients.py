"""
Service Clients for Compliance Service

Re-exports official service clients for compliance service to use.
This provides a unified interface for accessing other microservices.
"""

import logging
from typing import Optional

# Import official service clients
from microservices.audit_service.client import AuditServiceClient
from microservices.account_service.client import AccountServiceClient
from microservices.storage_service.client import StorageServiceClient

logger = logging.getLogger(__name__)


# ==================== Service Client Manager ====================

class ServiceClients:
    """
    Service client manager
    Unified interface for managing all external service clients
    """

    def __init__(
        self,
        audit_base_url: Optional[str] = None,
        account_base_url: Optional[str] = None,
        storage_base_url: Optional[str] = None
    ):
        """
        Initialize service client manager

        Args:
            audit_base_url: Audit service URL (optional, uses service discovery by default)
            account_base_url: Account service URL (optional, uses service discovery by default)
            storage_base_url: Storage service URL (optional, uses service discovery by default)
        """
        self.audit = AuditServiceClient(base_url=audit_base_url)
        self.account = AccountServiceClient(base_url=account_base_url)
        self.storage = StorageServiceClient(base_url=storage_base_url)

        logger.info("Initialized service clients for compliance service")

    async def close_all(self):
        """Close all service clients"""
        await self.audit.close()
        await self.account.close()
        await self.storage.close()
        logger.info("Closed all service clients")


# ==================== Singleton Instance ====================

_service_clients: Optional[ServiceClients] = None

def get_service_clients() -> ServiceClients:
    """
    Get service client manager instance (singleton pattern)

    Returns:
        ServiceClients instance

    Example:
        >>> clients = get_service_clients()
        >>> event = await clients.audit.log_event(...)
        >>> profile = await clients.account.get_account_profile(user_id)
        >>> file_info = await clients.storage.get_file_info(file_id, user_id)
    """
    global _service_clients
    if _service_clients is None:
        _service_clients = ServiceClients()
    return _service_clients

async def close_service_clients():
    """Close service client manager"""
    global _service_clients
    if _service_clients:
        await _service_clients.close_all()
        _service_clients = None
