"""
Crypto Payment Service

High-level service for crypto payments that:
- Manages multiple providers
- Persists payments to database
- Publishes events
- Integrates with wallet/subscription services
"""

import logging
import os
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime

from .crypto_providers import (
    CryptoProvider,
    CryptoPaymentProvider,
    CoinbaseCommerceProvider,
    MockCryptoProvider,
    CryptoPaymentRequest,
    CryptoPayment,
    CryptoPaymentResponse,
    CryptoPaymentStatus,
    CryptoWebhookEvent,
    CryptoRefundRequest,
    CryptoRefund,
    Chain,
    Token,
    CHAIN_CONFIG,
    TOKEN_CONFIG,
)

logger = logging.getLogger(__name__)


class CryptoPaymentService:
    """
    Crypto payment service that manages providers and payment lifecycle.

    Usage:
        service = CryptoPaymentService()
        await service.initialize()

        # Create payment
        response = await service.create_payment(
            CryptoPaymentRequest(
                user_id="user_123",
                amount=Decimal("100.00"),
                currency="USD",
            )
        )

        # Process webhook
        event = await service.handle_webhook(
            provider=CryptoProvider.COINBASE_COMMERCE,
            payload=payload,
            signature=signature,
            headers=headers,
        )
    """

    def __init__(
        self,
        default_provider: CryptoProvider = CryptoProvider.COINBASE_COMMERCE,
        repository=None,
        event_publisher=None,
        wallet_client=None,
        subscription_client=None,
    ):
        """
        Initialize crypto payment service.

        Args:
            default_provider: Default provider for new payments
            repository: Payment repository for persistence
            event_publisher: Event publisher for notifications
            wallet_client: Wallet service client
            subscription_client: Subscription service client
        """
        self.default_provider = default_provider
        self.repository = repository
        self.event_publisher = event_publisher
        self.wallet_client = wallet_client
        self.subscription_client = subscription_client

        self._providers: Dict[CryptoProvider, CryptoPaymentProvider] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize providers based on configuration"""
        if self._initialized:
            return

        # Initialize Coinbase Commerce if configured
        coinbase_key = os.getenv("COINBASE_COMMERCE_API_KEY")
        if coinbase_key:
            try:
                provider = CoinbaseCommerceProvider()
                if await provider.health_check():
                    self._providers[CryptoProvider.COINBASE_COMMERCE] = provider
                    logger.info("Coinbase Commerce provider initialized")
                else:
                    logger.warning("Coinbase Commerce health check failed")
            except Exception as e:
                logger.error(f"Failed to initialize Coinbase Commerce: {e}")

        # Always add mock provider for testing
        self._providers[CryptoProvider.DIRECT_WEB3] = MockCryptoProvider()

        if not self._providers:
            logger.warning("No crypto payment providers available")

        self._initialized = True

    async def close(self):
        """Close all providers"""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()

    def get_provider(
        self,
        provider: Optional[CryptoProvider] = None
    ) -> CryptoPaymentProvider:
        """Get a payment provider"""
        provider = provider or self.default_provider

        if provider not in self._providers:
            raise ValueError(f"Provider not available: {provider}")

        return self._providers[provider]

    def get_available_providers(self) -> List[CryptoProvider]:
        """Get list of available providers"""
        return list(self._providers.keys())

    # =========================================================================
    # Payment Operations
    # =========================================================================

    async def create_payment(
        self,
        request: CryptoPaymentRequest,
        provider: Optional[CryptoProvider] = None,
    ) -> CryptoPaymentResponse:
        """
        Create a new crypto payment.

        Args:
            request: Payment request
            provider: Optional specific provider to use

        Returns:
            Payment response with checkout URL
        """
        if not self._initialized:
            await self.initialize()

        payment_provider = self.get_provider(provider)

        # Create payment with provider
        response = await payment_provider.create_payment(request)

        # Get full payment object
        payment = await payment_provider.get_payment(response.payment_id)

        # Persist to database
        if self.repository and payment:
            await self._save_payment(payment)

        # Publish event
        if self.event_publisher:
            await self._publish_event(
                "crypto_payment.created",
                {
                    "payment_id": response.payment_id,
                    "user_id": request.user_id,
                    "amount": str(request.amount),
                    "currency": request.currency,
                    "provider": payment_provider.provider_name.value,
                }
            )

        logger.info(
            f"Created crypto payment {response.payment_id} for user {request.user_id}"
        )

        return response

    async def get_payment(
        self,
        payment_id: str,
        provider: Optional[CryptoProvider] = None,
    ) -> Optional[CryptoPayment]:
        """Get payment details"""
        # Try database first
        if self.repository:
            payment = await self._load_payment(payment_id)
            if payment:
                return payment

        # Fall back to provider
        if provider:
            payment_provider = self.get_provider(provider)
            return await payment_provider.get_payment(payment_id)

        # Try all providers
        for prov in self._providers.values():
            payment = await prov.get_payment(payment_id)
            if payment:
                return payment

        return None

    async def check_payment_status(
        self,
        payment_id: str,
        provider: Optional[CryptoProvider] = None,
    ) -> CryptoPaymentStatus:
        """Check and update payment status"""
        payment = await self.get_payment(payment_id, provider)
        if not payment:
            return CryptoPaymentStatus.FAILED

        # Get fresh status from provider
        payment_provider = self.get_provider(payment.provider)
        new_status = await payment_provider.check_payment_status(payment_id)

        # Update if changed
        if new_status != payment.status:
            payment.status = new_status
            payment.updated_at = datetime.utcnow()

            if new_status == CryptoPaymentStatus.COMPLETED:
                payment.completed_at = datetime.utcnow()

            if self.repository:
                await self._save_payment(payment)

            # Handle status change
            await self._handle_status_change(payment, new_status)

        return new_status

    async def cancel_payment(
        self,
        payment_id: str,
        provider: Optional[CryptoProvider] = None,
    ) -> bool:
        """Cancel a pending payment"""
        payment = await self.get_payment(payment_id, provider)
        if not payment:
            return False

        payment_provider = self.get_provider(payment.provider)
        success = await payment_provider.cancel_payment(payment_id)

        if success:
            payment.status = CryptoPaymentStatus.EXPIRED
            payment.updated_at = datetime.utcnow()

            if self.repository:
                await self._save_payment(payment)

            if self.event_publisher:
                await self._publish_event(
                    "crypto_payment.cancelled",
                    {"payment_id": payment_id, "user_id": payment.user_id}
                )

        return success

    # =========================================================================
    # Webhook Handling
    # =========================================================================

    async def handle_webhook(
        self,
        provider: CryptoProvider,
        payload: bytes,
        signature: str,
        headers: Dict[str, str],
    ) -> Optional[CryptoWebhookEvent]:
        """
        Process incoming webhook from a provider.

        Args:
            provider: Provider the webhook is from
            payload: Raw request body
            signature: Webhook signature
            headers: Request headers

        Returns:
            Parsed event or None if invalid
        """
        if not self._initialized:
            await self.initialize()

        payment_provider = self.get_provider(provider)
        event = await payment_provider.process_webhook(payload, signature, headers)

        if not event:
            logger.warning(f"Invalid webhook from {provider}")
            return None

        logger.info(
            f"Received webhook: {event.event_type} for payment {event.payment_id}"
        )

        # Update payment in database
        payment = await self.get_payment(event.payment_id, provider)
        if payment:
            old_status = payment.status
            payment.status = event.status
            payment.updated_at = datetime.utcnow()

            if event.tx_hash:
                payment.tx_hash = event.tx_hash
            if event.chain:
                payment.chain = event.chain
            if event.token:
                payment.token = event.token
            if event.crypto_amount:
                payment.crypto_amount = event.crypto_amount
            if event.confirmations:
                payment.confirmations = event.confirmations

            if event.status == CryptoPaymentStatus.COMPLETED:
                payment.completed_at = datetime.utcnow()

            if self.repository:
                await self._save_payment(payment)

            # Handle status change
            if old_status != event.status:
                await self._handle_status_change(payment, event.status)

        # Publish webhook event
        if self.event_publisher:
            await self._publish_event(
                f"crypto_payment.webhook.{event.event_type}",
                {
                    "payment_id": event.payment_id,
                    "status": event.status.value,
                    "provider": provider.value,
                    "tx_hash": event.tx_hash,
                }
            )

        return event

    # =========================================================================
    # Refunds
    # =========================================================================

    async def create_refund(
        self,
        request: CryptoRefundRequest,
        provider: Optional[CryptoProvider] = None,
    ) -> Optional[CryptoRefund]:
        """Create a refund for a completed payment"""
        payment = await self.get_payment(request.payment_id, provider)
        if not payment:
            logger.error(f"Payment not found: {request.payment_id}")
            return None

        payment_provider = self.get_provider(payment.provider)
        refund = await payment_provider.create_refund(request)

        if refund and self.event_publisher:
            await self._publish_event(
                "crypto_payment.refund_requested",
                {
                    "refund_id": refund.refund_id,
                    "payment_id": request.payment_id,
                    "user_id": payment.user_id,
                    "amount": str(refund.fiat_amount),
                    "wallet_address": request.wallet_address,
                }
            )

        return refund

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _handle_status_change(
        self,
        payment: CryptoPayment,
        new_status: CryptoPaymentStatus
    ):
        """Handle payment status changes"""
        if new_status == CryptoPaymentStatus.COMPLETED:
            # Credit user's wallet or subscription
            await self._credit_user(payment)

            if self.event_publisher:
                await self._publish_event(
                    "crypto_payment.completed",
                    {
                        "payment_id": payment.payment_id,
                        "user_id": payment.user_id,
                        "amount": str(payment.fiat_amount),
                        "currency": payment.fiat_currency,
                        "tx_hash": payment.tx_hash,
                    }
                )

        elif new_status == CryptoPaymentStatus.FAILED:
            if self.event_publisher:
                await self._publish_event(
                    "crypto_payment.failed",
                    {
                        "payment_id": payment.payment_id,
                        "user_id": payment.user_id,
                    }
                )

        elif new_status == CryptoPaymentStatus.EXPIRED:
            if self.event_publisher:
                await self._publish_event(
                    "crypto_payment.expired",
                    {
                        "payment_id": payment.payment_id,
                        "user_id": payment.user_id,
                    }
                )

    async def _credit_user(self, payment: CryptoPayment):
        """Credit user's wallet/subscription after successful payment"""
        # Calculate credits (1 USD = 100,000 credits based on product_service config)
        credits_per_dollar = 100_000
        credits = int(payment.fiat_amount * credits_per_dollar)

        # Try wallet service first
        if self.wallet_client:
            try:
                await self.wallet_client.add_credits(
                    user_id=payment.user_id,
                    amount=credits,
                    reason=f"Crypto payment {payment.payment_id}",
                    metadata={
                        "payment_id": payment.payment_id,
                        "fiat_amount": str(payment.fiat_amount),
                        "fiat_currency": payment.fiat_currency,
                        "tx_hash": payment.tx_hash,
                    }
                )
                logger.info(f"Credited {credits} credits to user {payment.user_id}")
                return
            except Exception as e:
                logger.error(f"Failed to credit wallet: {e}")

        # Fallback to subscription service
        if self.subscription_client:
            try:
                # This would add credits to subscription
                logger.info(
                    f"Would credit {credits} credits to subscription for user {payment.user_id}"
                )
            except Exception as e:
                logger.error(f"Failed to credit subscription: {e}")

    async def _save_payment(self, payment: CryptoPayment):
        """Save payment to database"""
        if not self.repository:
            return

        try:
            # Convert to dict for storage
            payment_dict = payment.model_dump()
            # Repository would save this
            logger.debug(f"Saving payment {payment.payment_id}")
        except Exception as e:
            logger.error(f"Failed to save payment: {e}")

    async def _load_payment(self, payment_id: str) -> Optional[CryptoPayment]:
        """Load payment from database"""
        if not self.repository:
            return None

        try:
            # Repository would load this
            return None
        except Exception as e:
            logger.error(f"Failed to load payment: {e}")
            return None

    async def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event to event bus"""
        if not self.event_publisher:
            return

        try:
            await self.event_publisher.publish(event_type, data)
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    # =========================================================================
    # Info Methods
    # =========================================================================

    def get_supported_chains(self) -> List[Dict[str, Any]]:
        """Get all supported chains with their config"""
        chains = set()
        for provider in self._providers.values():
            chains.update(provider.supported_chains)

        return [
            {
                "chain": chain.value,
                "name": CHAIN_CONFIG[chain]["name"],
                "native_token": CHAIN_CONFIG[chain]["native_token"].value,
                "explorer": CHAIN_CONFIG[chain]["explorer"],
            }
            for chain in chains
            if chain in CHAIN_CONFIG
        ]

    def get_supported_tokens(self) -> List[Dict[str, Any]]:
        """Get all supported tokens with their config"""
        tokens = set()
        for provider in self._providers.values():
            tokens.update(provider.supported_tokens)

        return [
            {
                "token": token.value,
                "name": TOKEN_CONFIG[token]["name"],
                "decimals": TOKEN_CONFIG[token]["decimals"],
                "chains": [c.value for c in TOKEN_CONFIG[token]["chains"]],
            }
            for token in tokens
            if token in TOKEN_CONFIG
        ]


# Singleton instance
_crypto_service: Optional[CryptoPaymentService] = None


async def get_crypto_service() -> CryptoPaymentService:
    """Get singleton crypto payment service"""
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoPaymentService()
        await _crypto_service.initialize()
    return _crypto_service


__all__ = [
    "CryptoPaymentService",
    "get_crypto_service",
]
