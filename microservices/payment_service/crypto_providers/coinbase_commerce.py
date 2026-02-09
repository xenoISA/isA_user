"""
Coinbase Commerce Payment Provider

Implements crypto payments using Coinbase Commerce API.
https://docs.cdp.coinbase.com/commerce-onchain/docs/welcome

Supported:
- Hosted checkout pages
- Multiple cryptocurrencies (BTC, ETH, USDC, etc.)
- Webhook notifications
- Multiple blockchain networks
"""

import httpx
import hmac
import hashlib
import json
import uuid
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal

from .base import CryptoPaymentProvider
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


class CoinbaseCommerceProvider(CryptoPaymentProvider):
    """
    Coinbase Commerce payment provider.

    Environment variables:
        COINBASE_COMMERCE_API_KEY: API key from Coinbase Commerce dashboard
        COINBASE_COMMERCE_WEBHOOK_SECRET: Webhook shared secret

    Usage:
        provider = CoinbaseCommerceProvider()
        response = await provider.create_payment(request)
        # Redirect user to response.checkout_url
    """

    API_BASE = "https://api.commerce.coinbase.com"
    API_VERSION = "2018-03-22"

    # Coinbase Commerce supported assets
    # Maps Coinbase asset codes to our Token enum
    COINBASE_ASSET_MAP = {
        "BTC": Token.BTC,
        "ETH": Token.ETH,
        "USDC": Token.USDC,
        "DAI": Token.DAI,
        "SOL": Token.SOL,
        # Coinbase uses network-specific codes for some tokens
        "PUSDC": Token.USDC,  # Polygon USDC
    }

    # Maps Coinbase network codes to our Chain enum
    COINBASE_NETWORK_MAP = {
        "bitcoin": Chain.BITCOIN,
        "ethereum": Chain.ETHEREUM,
        "polygon": Chain.POLYGON,
        "base": Chain.BASE,
        "solana": Chain.SOLANA,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None
    ):
        """
        Initialize Coinbase Commerce provider.

        Args:
            api_key: Coinbase Commerce API key (or use COINBASE_COMMERCE_API_KEY env)
            webhook_secret: Webhook shared secret (or use COINBASE_COMMERCE_WEBHOOK_SECRET env)
        """
        self.api_key = api_key or os.getenv("COINBASE_COMMERCE_API_KEY")
        self.webhook_secret = webhook_secret or os.getenv("COINBASE_COMMERCE_WEBHOOK_SECRET")

        if not self.api_key:
            logger.warning("Coinbase Commerce API key not configured")

        self._client: Optional[httpx.AsyncClient] = None

        # In-memory payment cache (in production, use database)
        self._payments: Dict[str, CryptoPayment] = {}
        self._provider_id_map: Dict[str, str] = {}  # provider_id -> payment_id

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy HTTP client initialization"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.API_BASE,
                headers={
                    "X-CC-Api-Key": self.api_key,
                    "X-CC-Version": self.API_VERSION,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    def provider_name(self) -> CryptoProvider:
        return CryptoProvider.COINBASE_COMMERCE

    @property
    def supported_chains(self) -> List[Chain]:
        return [
            Chain.BITCOIN,
            Chain.ETHEREUM,
            Chain.POLYGON,
            Chain.BASE,
            Chain.SOLANA,
        ]

    @property
    def supported_tokens(self) -> List[Token]:
        return [
            Token.BTC,
            Token.ETH,
            Token.USDC,
            Token.DAI,
            Token.SOL,
        ]

    async def create_payment(
        self,
        request: CryptoPaymentRequest
    ) -> CryptoPaymentResponse:
        """
        Create a Coinbase Commerce charge (payment).

        Creates a hosted checkout page where users can pay with crypto.
        """
        payment_id = f"crypto_{uuid.uuid4().hex[:16]}"

        # Build charge request
        charge_data = {
            "name": request.description or "Payment",
            "description": request.description or f"Payment for order {request.order_id or payment_id}",
            "pricing_type": "fixed_price",
            "local_price": {
                "amount": str(request.amount),
                "currency": request.currency.upper(),
            },
            "metadata": {
                "payment_id": payment_id,
                "user_id": request.user_id,
                "organization_id": request.organization_id or "",
                "order_id": request.order_id or "",
                **(request.metadata or {}),
            },
        }

        # Add redirect URLs if provided
        if request.success_url:
            charge_data["redirect_url"] = request.success_url
        if request.cancel_url:
            charge_data["cancel_url"] = request.cancel_url

        try:
            response = await self.client.post("/charges", json=charge_data)
            response.raise_for_status()
            charge = response.json()["data"]

            logger.info(f"Created Coinbase Commerce charge: {charge['id']}")

            # Parse response
            provider_payment_id = charge["id"]
            checkout_url = charge["hosted_url"]
            expires_at = datetime.fromisoformat(
                charge["expires_at"].replace("Z", "+00:00")
            )

            # Extract pricing info
            crypto_amounts = {}
            supported_tokens = []

            for address_info in charge.get("addresses", {}).items():
                network, address = address_info
                chain = self.COINBASE_NETWORK_MAP.get(network.lower())
                if chain:
                    # Get tokens for this network from pricing
                    for pricing_key, pricing_info in charge.get("pricing", {}).items():
                        if pricing_key != "local":
                            token = self.COINBASE_ASSET_MAP.get(pricing_key.upper())
                            if token:
                                crypto_amounts[token.value] = Decimal(pricing_info["amount"])
                                supported_tokens.append({
                                    "token": token.value,
                                    "chain": chain.value,
                                    "address": address,
                                    "amount": pricing_info["amount"],
                                })

            # Create payment record
            payment = CryptoPayment(
                payment_id=payment_id,
                user_id=request.user_id,
                organization_id=request.organization_id,
                fiat_amount=request.amount,
                fiat_currency=request.currency,
                status=CryptoPaymentStatus.PENDING,
                provider=self.provider_name,
                provider_payment_id=provider_payment_id,
                provider_checkout_url=checkout_url,
                provider_response=charge,
                expires_at=expires_at,
                description=request.description,
                order_id=request.order_id,
                metadata=request.metadata,
                created_at=datetime.utcnow(),
            )

            # Store payment
            self._payments[payment_id] = payment
            self._provider_id_map[provider_payment_id] = payment_id

            return CryptoPaymentResponse(
                payment_id=payment_id,
                status=CryptoPaymentStatus.PENDING,
                checkout_url=checkout_url,
                supported_tokens=supported_tokens,
                fiat_amount=request.amount,
                fiat_currency=request.currency,
                crypto_amounts=crypto_amounts if crypto_amounts else None,
                expires_at=expires_at,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Coinbase Commerce API error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating Coinbase Commerce charge: {e}")
            raise

    async def get_payment(self, payment_id: str) -> Optional[CryptoPayment]:
        """Get payment by internal ID"""
        return self._payments.get(payment_id)

    async def get_payment_by_provider_id(
        self,
        provider_payment_id: str
    ) -> Optional[CryptoPayment]:
        """Get payment by Coinbase charge ID"""
        payment_id = self._provider_id_map.get(provider_payment_id)
        if payment_id:
            return self._payments.get(payment_id)
        return None

    async def check_payment_status(self, payment_id: str) -> CryptoPaymentStatus:
        """Check payment status from Coinbase Commerce API"""
        payment = self._payments.get(payment_id)
        if not payment or not payment.provider_payment_id:
            return CryptoPaymentStatus.FAILED

        try:
            response = await self.client.get(f"/charges/{payment.provider_payment_id}")
            response.raise_for_status()
            charge = response.json()["data"]

            # Map Coinbase status to our status
            new_status = self._map_coinbase_status(charge)

            # Update stored payment
            payment.status = new_status
            payment.provider_response = charge

            if new_status == CryptoPaymentStatus.CONFIRMED:
                payment.confirmed_at = datetime.utcnow()
            elif new_status == CryptoPaymentStatus.COMPLETED:
                payment.completed_at = datetime.utcnow()

            # Extract transaction details if available
            timeline = charge.get("timeline", [])
            for event in timeline:
                if event.get("status") == "COMPLETED" and "payment" in event:
                    payment_info = event["payment"]
                    payment.tx_hash = payment_info.get("transaction_id")
                    payment.crypto_amount = Decimal(payment_info.get("value", {}).get("crypto", {}).get("amount", "0"))

                    # Map network/token
                    network = payment_info.get("network")
                    if network:
                        payment.chain = self.COINBASE_NETWORK_MAP.get(network.lower())

            return new_status

        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return payment.status if payment else CryptoPaymentStatus.FAILED

    def _map_coinbase_status(self, charge: Dict[str, Any]) -> CryptoPaymentStatus:
        """Map Coinbase Commerce charge status to our status"""
        timeline = charge.get("timeline", [])
        if not timeline:
            return CryptoPaymentStatus.PENDING

        latest_status = timeline[-1].get("status", "").upper()

        status_map = {
            "NEW": CryptoPaymentStatus.PENDING,
            "PENDING": CryptoPaymentStatus.DETECTED,
            "COMPLETED": CryptoPaymentStatus.COMPLETED,
            "EXPIRED": CryptoPaymentStatus.EXPIRED,
            "CANCELED": CryptoPaymentStatus.EXPIRED,
            "UNRESOLVED": CryptoPaymentStatus.FAILED,
            "RESOLVED": CryptoPaymentStatus.COMPLETED,
        }

        # Check for underpaid/overpaid
        if latest_status == "UNRESOLVED":
            context = timeline[-1].get("context", "")
            if "UNDERPAID" in context:
                return CryptoPaymentStatus.UNDERPAID
            elif "OVERPAID" in context:
                return CryptoPaymentStatus.OVERPAID

        return status_map.get(latest_status, CryptoPaymentStatus.PENDING)

    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Cancel a pending payment.

        Note: Coinbase Commerce charges can't be cancelled via API.
        We can only mark them as cancelled locally.
        """
        payment = self._payments.get(payment_id)
        if payment and payment.status == CryptoPaymentStatus.PENDING:
            payment.status = CryptoPaymentStatus.EXPIRED
            return True
        return False

    async def process_webhook(
        self,
        payload: bytes,
        signature: str,
        headers: Dict[str, str]
    ) -> Optional[CryptoWebhookEvent]:
        """
        Process Coinbase Commerce webhook.

        Verifies signature and parses event.
        """
        # Verify signature
        if self.webhook_secret:
            expected_sig = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Coinbase sends signature in X-CC-Webhook-Signature header
            received_sig = headers.get("X-CC-Webhook-Signature", "")

            if not hmac.compare_digest(expected_sig, received_sig):
                logger.warning("Invalid webhook signature")
                return None

        try:
            data = json.loads(payload)
            event = data.get("event", {})
            event_type = event.get("type", "")
            charge = event.get("data", {})

            logger.info(f"Processing Coinbase webhook: {event_type}")

            # Map event type
            provider_payment_id = charge.get("id")
            if not provider_payment_id:
                logger.warning("No charge ID in webhook")
                return None

            # Get our payment
            payment = await self.get_payment_by_provider_id(provider_payment_id)
            payment_id = payment.payment_id if payment else charge.get("metadata", {}).get("payment_id", "")

            # Determine status
            status = self._map_coinbase_status(charge)

            # Update payment if we have it
            if payment:
                payment.status = status
                payment.provider_response = charge

                if status == CryptoPaymentStatus.COMPLETED:
                    payment.completed_at = datetime.utcnow()

            # Extract transaction details
            chain = None
            token = None
            crypto_amount = None
            tx_hash = None

            timeline = charge.get("timeline", [])
            for timeline_event in timeline:
                if "payment" in timeline_event:
                    payment_info = timeline_event["payment"]
                    tx_hash = payment_info.get("transaction_id")
                    network = payment_info.get("network")
                    if network:
                        chain = self.COINBASE_NETWORK_MAP.get(network.lower())

                    crypto_value = payment_info.get("value", {}).get("crypto", {})
                    if crypto_value:
                        crypto_amount = Decimal(crypto_value.get("amount", "0"))
                        currency = crypto_value.get("currency", "").upper()
                        token = self.COINBASE_ASSET_MAP.get(currency)

            return CryptoWebhookEvent(
                provider=self.provider_name,
                event_type=event_type,
                payment_id=payment_id,
                provider_payment_id=provider_payment_id,
                status=status,
                chain=chain,
                token=token,
                crypto_amount=crypto_amount,
                tx_hash=tx_hash,
                raw_data=data,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid webhook JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return None

    async def create_refund(
        self,
        request: CryptoRefundRequest
    ) -> Optional[CryptoRefund]:
        """
        Create a refund.

        Note: Coinbase Commerce doesn't support automatic refunds.
        This creates a refund record that must be processed manually.
        """
        payment = await self.get_payment(request.payment_id)
        if not payment:
            logger.error(f"Payment not found: {request.payment_id}")
            return None

        if payment.status != CryptoPaymentStatus.COMPLETED:
            logger.error(f"Cannot refund payment in status: {payment.status}")
            return None

        refund = CryptoRefund(
            refund_id=f"refund_{uuid.uuid4().hex[:16]}",
            payment_id=request.payment_id,
            user_id=payment.user_id,
            fiat_amount=request.amount or payment.fiat_amount,
            crypto_amount=payment.crypto_amount,
            token=payment.token,
            chain=payment.chain,
            status=CryptoPaymentStatus.PENDING,
            wallet_address=request.wallet_address,
            reason=request.reason,
            requested_by=request.requested_by,
        )

        logger.info(
            f"Created refund request {refund.refund_id} for payment {request.payment_id}. "
            f"Manual processing required - send {refund.crypto_amount} {refund.token} to {refund.wallet_address}"
        )

        return refund

    async def health_check(self) -> bool:
        """Check if Coinbase Commerce API is accessible"""
        if not self.api_key:
            return False

        try:
            response = await self.client.get("/charges", params={"limit": 1})
            return response.status_code == 200
        except Exception:
            return False


__all__ = ["CoinbaseCommerceProvider"]
