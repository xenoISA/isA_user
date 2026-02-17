"""
Campaign Service Factory

Factory for creating campaign service instances with proper dependency injection.
"""

import logging
from typing import Optional

from core.config_manager import ConfigManager
from core.nats_client import NATSEventBus

from .campaign_repository import CampaignRepository
from .campaign_service import CampaignService
from .clients.account_client import AccountClient
from .clients.task_client import TaskClient
from .clients.notification_client import NotificationClient
from .events.handlers import CampaignEventHandler
from .events.publishers import CampaignEventPublisher

logger = logging.getLogger(__name__)


class CampaignServiceFactory:
    """Factory for creating campaign service components"""

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager("campaign_service")
        self._repository: Optional[CampaignRepository] = None
        self._service: Optional[CampaignService] = None
        self._nats_client: Optional[NATSEventBus] = None
        self._event_handler: Optional[CampaignEventHandler] = None
        self._event_publisher: Optional[CampaignEventPublisher] = None
        self._account_client: Optional[AccountClient] = None
        self._task_client: Optional[TaskClient] = None
        self._notification_client: Optional[NotificationClient] = None

    async def initialize(self) -> None:
        """Initialize all components"""
        logger.info("Initializing Campaign Service components...")

        # Initialize repository
        self._repository = CampaignRepository(self.config)
        await self._repository.initialize()

        # Initialize NATS client
        try:
            self._nats_client = NATSEventBus(
                service_name="campaign_service",
                config=self.config,
            )
            await self._nats_client.connect()
            self._event_publisher = CampaignEventPublisher(self._nats_client)
            logger.info("NATS client connected")
        except Exception as e:
            logger.warning(f"NATS client initialization failed: {e}")
            self._nats_client = None
            self._event_publisher = None

        # Initialize service clients
        self._account_client = AccountClient(self.config)
        self._task_client = TaskClient(self.config)
        self._notification_client = NotificationClient(self.config)

        # Initialize main service
        self._service = CampaignService(
            repository=self._repository,
            event_bus=self._nats_client,
            task_client=self._task_client,
            notification_client=self._notification_client,
            account_client=self._account_client,
        )

        # Initialize event handler
        self._event_handler = CampaignEventHandler(
            campaign_service=self._service,
            campaign_repository=self._repository,
        )

        logger.info("Campaign Service components initialized")

    async def close(self) -> None:
        """Close all components"""
        logger.info("Closing Campaign Service components...")

        if self._nats_client:
            await self._nats_client.close()

        if self._repository:
            await self._repository.close()

        logger.info("Campaign Service components closed")

    @property
    def repository(self) -> CampaignRepository:
        """Get campaign repository"""
        if not self._repository:
            raise RuntimeError("Factory not initialized. Call initialize() first.")
        return self._repository

    @property
    def service(self) -> CampaignService:
        """Get campaign service"""
        if not self._service:
            raise RuntimeError("Factory not initialized. Call initialize() first.")
        return self._service

    @property
    def nats_client(self) -> Optional[NATSEventBus]:
        """Get NATS client"""
        return self._nats_client

    @property
    def event_handler(self) -> CampaignEventHandler:
        """Get event handler"""
        if not self._event_handler:
            raise RuntimeError("Factory not initialized. Call initialize() first.")
        return self._event_handler

    @property
    def event_publisher(self) -> Optional[CampaignEventPublisher]:
        """Get event publisher"""
        return self._event_publisher

    @property
    def account_client(self) -> AccountClient:
        """Get account client"""
        if not self._account_client:
            raise RuntimeError("Factory not initialized. Call initialize() first.")
        return self._account_client

    @property
    def task_client(self) -> TaskClient:
        """Get task client"""
        if not self._task_client:
            raise RuntimeError("Factory not initialized. Call initialize() first.")
        return self._task_client

    @property
    def notification_client(self) -> NotificationClient:
        """Get notification client"""
        if not self._notification_client:
            raise RuntimeError("Factory not initialized. Call initialize() first.")
        return self._notification_client


# Global factory instance
_factory: Optional[CampaignServiceFactory] = None


async def get_factory() -> CampaignServiceFactory:
    """Get or create factory instance"""
    global _factory
    if _factory is None:
        _factory = CampaignServiceFactory()
        await _factory.initialize()
    return _factory


async def close_factory() -> None:
    """Close factory instance"""
    global _factory
    if _factory:
        await _factory.close()
        _factory = None


__all__ = [
    "CampaignServiceFactory",
    "get_factory",
    "close_factory",
]
