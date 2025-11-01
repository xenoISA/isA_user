#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wallet Service Event Subscriber

Sets up event subscriptions and routes events to handlers.
"""

import logging
from typing import TYPE_CHECKING

from core.events.event_subscriber import BaseEventSubscriber
from core.events.event_publisher import BillingEventPublisher
from core.grpc_clients.nats_client import NATSClient
from .handlers import BillingCalculatedEventHandler

if TYPE_CHECKING:
    from ..wallet_service import WalletService

logger = logging.getLogger(__name__)


class WalletEventSubscriber(BaseEventSubscriber):
    """
    Wallet service event subscriber.

    Subscribes to:
    - billing.calculated (from billing_service)

    Publishes:
    - wallet.tokens.deducted (after successful deduction)
    - wallet.tokens.insufficient (when user has insufficient balance)
    """

    def __init__(
        self,
        wallet_service: 'WalletService',
        nats_host: str = 'localhost',
        nats_port: int = 50056,
        nats_client: NATSClient = None
    ):
        """
        Initialize wallet event subscriber.

        Args:
            wallet_service: Wallet service instance
            nats_host: NATS service host
            nats_port: NATS service gRPC port
            nats_client: Optional NATS client (creates new if None)
        """
        # Create or use provided NATS client
        if nats_client is None:
            nats_client = NATSClient(
                host=nats_host,
                port=nats_port,
                user_id="wallet_service"
            )

        # Initialize base subscriber
        super().__init__(
            service_name="wallet_service",
            nats_client=nats_client,
            idempotency_storage="memory"  # TODO: Use Redis in production
        )

        self.wallet_service = wallet_service

        # Create event publisher for downstream events
        self.event_publisher = BillingEventPublisher(
            nats_host=nats_host,
            nats_port=nats_port,
            user_id="wallet_service"
        )

        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register all event handlers"""
        # Handle billing.calculated events
        self.register_handler(
            BillingCalculatedEventHandler(self.wallet_service, self.event_publisher)
        )

        logger.info("[wallet_service] Event handlers registered")

    async def start(self):
        """
        Start event subscriptions.

        This should be called after the service starts.
        """
        logger.info("[wallet_service] Starting event subscriptions...")

        # Subscribe to billing calculated events
        # Queue group ensures load balancing across multiple instances
        await self.subscribe(
            subject="billing.calculated",
            queue="wallet-workers",
            durable="wallet-consumer"
        )

        logger.info("[wallet_service] Event subscriptions active")

    async def stop(self):
        """
        Stop event subscriptions and cleanup.
        """
        logger.info("[wallet_service] Stopping event subscriptions...")

        # Close NATS connections
        if self.nats_client:
            self.nats_client.close()

        if self.event_publisher:
            self.event_publisher.close()

        logger.info("[wallet_service] Event subscriptions stopped")
