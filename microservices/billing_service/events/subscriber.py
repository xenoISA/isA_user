#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Billing Service Event Subscriber

Sets up event subscriptions and routes events to handlers.
"""

import logging
from typing import TYPE_CHECKING

from isa_common.events import BaseEventSubscriber, BillingEventPublisher
from isa_common.nats_client import NATSClient
from .handlers import UsageEventHandler

if TYPE_CHECKING:
    from ..billing_service import BillingService

logger = logging.getLogger(__name__)


class BillingEventSubscriber(BaseEventSubscriber):
    """
    Billing service event subscriber.

    Subscribes to:
    - usage.recorded.* (from isA_Model, isA_Agent, isA_MCP, storage, etc.)

    Publishes:
    - billing.calculated (after cost calculation)
    - billing.failed (on errors)
    """

    def __init__(
        self,
        billing_service: 'BillingService',
        nats_host: str = 'localhost',
        nats_port: int = 50056,
        nats_client: NATSClient = None
    ):
        """
        Initialize billing event subscriber.

        Args:
            billing_service: Billing service instance
            nats_host: NATS service host
            nats_port: NATS service gRPC port
            nats_client: Optional NATS client (creates new if None)
        """
        # Create or use provided NATS client
        if nats_client is None:
            nats_client = NATSClient(
                host=nats_host,
                port=nats_port,
                user_id="billing_service"
            )

        # Initialize base subscriber
        super().__init__(
            service_name="billing_service",
            nats_client=nats_client,
            idempotency_storage="memory"  # TODO: Use Redis in production
        )

        self.billing_service = billing_service

        # Create event publisher for downstream events
        self.event_publisher = BillingEventPublisher(
            nats_host=nats_host,
            nats_port=nats_port,
            user_id="billing_service"
        )

        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register all event handlers"""
        # Handle usage.recorded events
        self.register_handler(
            UsageEventHandler(self.billing_service, self.event_publisher)
        )

        logger.info("[billing_service] Event handlers registered")

    async def start(self):
        """
        Start event subscriptions.

        This should be called after the service starts.
        """
        logger.info("[billing_service] Starting event subscriptions...")

        # Subscribe to all usage events
        # Queue group ensures load balancing across multiple instances
        await self.subscribe(
            subject="usage.recorded.*",
            queue="billing-workers",
            durable="billing-consumer"
        )

        logger.info("[billing_service] Event subscriptions active")

    async def stop(self):
        """
        Stop event subscriptions and cleanup.
        """
        logger.info("[billing_service] Stopping event subscriptions...")

        # Close NATS connections
        if self.nats_client:
            self.nats_client.close()

        if self.event_publisher:
            self.event_publisher.close()

        logger.info("[billing_service] Event subscriptions stopped")
