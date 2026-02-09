"""
Crypto Payment Providers

Extensible crypto payment provider system.

Supported Providers:
- Coinbase Commerce: Full integration
- Mock: For testing

Future Providers:
- Circle: USDC payments
- MoonPay: On-ramp/off-ramp
- Direct Web3: Direct blockchain integration

Usage:
    from crypto_providers import CoinbaseCommerceProvider, CryptoPaymentRequest

    provider = CoinbaseCommerceProvider()
    response = await provider.create_payment(
        CryptoPaymentRequest(
            user_id="user_123",
            amount=Decimal("100.00"),
            currency="USD",
            description="API Credits"
        )
    )
    # Redirect user to response.checkout_url
"""

from .models import (
    # Enums
    Chain,
    Token,
    CryptoPaymentStatus,
    CryptoProvider,
    # Config
    CHAIN_CONFIG,
    TOKEN_CONFIG,
    # Models
    CryptoPaymentRequest,
    CryptoPayment,
    CryptoPaymentResponse,
    CryptoWebhookEvent,
    CryptoRefundRequest,
    CryptoRefund,
)

from .base import (
    CryptoPaymentProvider,
    MockCryptoProvider,
)

from .coinbase_commerce import CoinbaseCommerceProvider


def get_provider(
    provider: CryptoProvider,
    **kwargs
) -> CryptoPaymentProvider:
    """
    Factory function to get a crypto payment provider.

    Args:
        provider: Provider type
        **kwargs: Provider-specific configuration

    Returns:
        Configured provider instance

    Example:
        provider = get_provider(CryptoProvider.COINBASE_COMMERCE)
    """
    providers = {
        CryptoProvider.COINBASE_COMMERCE: CoinbaseCommerceProvider,
        CryptoProvider.DIRECT_WEB3: MockCryptoProvider,  # Placeholder
    }

    provider_class = providers.get(provider)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider}")

    return provider_class(**kwargs)


__all__ = [
    # Enums
    "Chain",
    "Token",
    "CryptoPaymentStatus",
    "CryptoProvider",
    # Config
    "CHAIN_CONFIG",
    "TOKEN_CONFIG",
    # Models
    "CryptoPaymentRequest",
    "CryptoPayment",
    "CryptoPaymentResponse",
    "CryptoWebhookEvent",
    "CryptoRefundRequest",
    "CryptoRefund",
    # Base
    "CryptoPaymentProvider",
    "MockCryptoProvider",
    # Providers
    "CoinbaseCommerceProvider",
    # Factory
    "get_provider",
]
