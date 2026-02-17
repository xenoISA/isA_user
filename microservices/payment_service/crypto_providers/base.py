"""
Crypto Payment Provider Base Class

Abstract base class that defines the interface for all crypto payment providers.
Implement this interface to add new providers (Coinbase Commerce, Circle, MoonPay, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from decimal import Decimal
import logging

from .models import (
    Chain,
    Token,
    CryptoPaymentRequest,
    CryptoPayment,
    CryptoPaymentResponse,
    CryptoPaymentStatus,
    CryptoWebhookEvent,
    CryptoRefundRequest,
    CryptoRefund,
    CryptoProvider,
)

logger = logging.getLogger(__name__)


class CryptoPaymentProvider(ABC):
    """
    Abstract base class for crypto payment providers.

    To add a new provider:
    1. Create a new class that inherits from CryptoPaymentProvider
    2. Implement all abstract methods
    3. Register the provider in CryptoPaymentService

    Example:
        class MyProvider(CryptoPaymentProvider):
            def __init__(self, api_key: str):
                self.api_key = api_key

            @property
            def provider_name(self) -> CryptoProvider:
                return CryptoProvider.MY_PROVIDER

            async def create_payment(self, request: CryptoPaymentRequest) -> CryptoPaymentResponse:
                # Implementation here
                pass
    """

    @property
    @abstractmethod
    def provider_name(self) -> CryptoProvider:
        """Return the provider identifier"""
        pass

    @property
    @abstractmethod
    def supported_chains(self) -> List[Chain]:
        """Return list of supported blockchain networks"""
        pass

    @property
    @abstractmethod
    def supported_tokens(self) -> List[Token]:
        """Return list of supported tokens"""
        pass

    @abstractmethod
    async def create_payment(
        self,
        request: CryptoPaymentRequest
    ) -> CryptoPaymentResponse:
        """
        Create a new crypto payment.

        Args:
            request: Payment request with amount, currency, user info

        Returns:
            CryptoPaymentResponse with checkout URL or wallet address
        """
        pass

    @abstractmethod
    async def get_payment(
        self,
        payment_id: str
    ) -> Optional[CryptoPayment]:
        """
        Get payment details by internal payment ID.

        Args:
            payment_id: Internal payment ID

        Returns:
            CryptoPayment if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_payment_by_provider_id(
        self,
        provider_payment_id: str
    ) -> Optional[CryptoPayment]:
        """
        Get payment details by provider's payment ID.

        Args:
            provider_payment_id: Provider's payment/charge ID

        Returns:
            CryptoPayment if found, None otherwise
        """
        pass

    @abstractmethod
    async def check_payment_status(
        self,
        payment_id: str
    ) -> CryptoPaymentStatus:
        """
        Check current payment status from provider.

        Args:
            payment_id: Internal payment ID

        Returns:
            Current payment status
        """
        pass

    @abstractmethod
    async def cancel_payment(
        self,
        payment_id: str
    ) -> bool:
        """
        Cancel a pending payment.

        Args:
            payment_id: Internal payment ID

        Returns:
            True if cancelled successfully
        """
        pass

    @abstractmethod
    async def process_webhook(
        self,
        payload: bytes,
        signature: str,
        headers: Dict[str, str]
    ) -> Optional[CryptoWebhookEvent]:
        """
        Process incoming webhook from provider.

        Args:
            payload: Raw webhook payload
            signature: Webhook signature for verification
            headers: Request headers

        Returns:
            Parsed webhook event or None if invalid
        """
        pass

    @abstractmethod
    async def create_refund(
        self,
        request: CryptoRefundRequest
    ) -> Optional[CryptoRefund]:
        """
        Create a refund for a completed payment.

        Note: Many crypto providers don't support automatic refunds.
        This may just record the refund intent and require manual processing.

        Args:
            request: Refund request with payment ID and wallet address

        Returns:
            CryptoRefund record or None if not supported
        """
        pass

    async def health_check(self) -> bool:
        """
        Check if provider is accessible.

        Returns:
            True if provider is healthy
        """
        return True

    def get_supported_tokens_for_chain(self, chain: Chain) -> List[Token]:
        """
        Get tokens supported on a specific chain.

        Args:
            chain: Blockchain network

        Returns:
            List of supported tokens on that chain
        """
        from .models import TOKEN_CONFIG

        supported = []
        for token in self.supported_tokens:
            token_config = TOKEN_CONFIG.get(token, {})
            if chain in token_config.get("chains", []):
                supported.append(token)
        return supported

    def format_amount_for_display(
        self,
        amount: Decimal,
        token: Token
    ) -> str:
        """
        Format crypto amount for display.

        Args:
            amount: Amount in token's smallest unit
            token: Token type

        Returns:
            Formatted amount string
        """
        from .models import TOKEN_CONFIG

        decimals = TOKEN_CONFIG.get(token, {}).get("decimals", 18)
        display_amount = amount / Decimal(10 ** decimals)
        return f"{display_amount:.8f}".rstrip("0").rstrip(".")


class MockCryptoProvider(CryptoPaymentProvider):
    """
    Mock provider for testing.
    Always succeeds with fake data.
    """

    def __init__(self):
        self._payments: Dict[str, CryptoPayment] = {}

    @property
    def provider_name(self) -> CryptoProvider:
        return CryptoProvider.DIRECT_WEB3

    @property
    def supported_chains(self) -> List[Chain]:
        return [Chain.ETHEREUM, Chain.POLYGON, Chain.BASE]

    @property
    def supported_tokens(self) -> List[Token]:
        return [Token.ETH, Token.USDC, Token.USDT]

    async def create_payment(
        self,
        request: CryptoPaymentRequest
    ) -> CryptoPaymentResponse:
        import uuid
        from datetime import datetime, timedelta

        payment_id = f"mock_{uuid.uuid4().hex[:12]}"

        payment = CryptoPayment(
            payment_id=payment_id,
            user_id=request.user_id,
            organization_id=request.organization_id,
            fiat_amount=request.amount,
            fiat_currency=request.currency,
            status=CryptoPaymentStatus.PENDING,
            provider=self.provider_name,
            provider_payment_id=payment_id,
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            description=request.description,
            order_id=request.order_id,
            metadata=request.metadata,
            created_at=datetime.utcnow(),
        )

        self._payments[payment_id] = payment

        return CryptoPaymentResponse(
            payment_id=payment_id,
            status=CryptoPaymentStatus.PENDING,
            wallet_address=payment.wallet_address,
            supported_tokens=[
                {"token": Token.USDC.value, "chain": Chain.ETHEREUM.value},
                {"token": Token.ETH.value, "chain": Chain.ETHEREUM.value},
            ],
            fiat_amount=request.amount,
            fiat_currency=request.currency,
            expires_at=payment.expires_at,
        )

    async def get_payment(self, payment_id: str) -> Optional[CryptoPayment]:
        return self._payments.get(payment_id)

    async def get_payment_by_provider_id(
        self,
        provider_payment_id: str
    ) -> Optional[CryptoPayment]:
        return self._payments.get(provider_payment_id)

    async def check_payment_status(self, payment_id: str) -> CryptoPaymentStatus:
        payment = self._payments.get(payment_id)
        if payment:
            return payment.status
        return CryptoPaymentStatus.FAILED

    async def cancel_payment(self, payment_id: str) -> bool:
        if payment_id in self._payments:
            self._payments[payment_id].status = CryptoPaymentStatus.EXPIRED
            return True
        return False

    async def process_webhook(
        self,
        payload: bytes,
        signature: str,
        headers: Dict[str, str]
    ) -> Optional[CryptoWebhookEvent]:
        # Mock provider doesn't process real webhooks
        return None

    async def create_refund(
        self,
        request: CryptoRefundRequest
    ) -> Optional[CryptoRefund]:
        import uuid
        from datetime import datetime

        payment = self._payments.get(request.payment_id)
        if not payment:
            return None

        return CryptoRefund(
            refund_id=f"mock_refund_{uuid.uuid4().hex[:12]}",
            payment_id=request.payment_id,
            user_id=payment.user_id,
            fiat_amount=request.amount or payment.fiat_amount,
            status=CryptoPaymentStatus.PENDING,
            wallet_address=request.wallet_address,
            reason=request.reason,
            requested_by=request.requested_by,
        )


__all__ = [
    "CryptoPaymentProvider",
    "MockCryptoProvider",
]
