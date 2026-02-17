"""
Crypto Payment API Routes

FastAPI routes for crypto payment operations.
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Header
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field

from .crypto_service import get_crypto_service, CryptoPaymentService
from .crypto_providers import (
    CryptoProvider,
    CryptoPaymentRequest,
    CryptoPaymentResponse,
    CryptoPaymentStatus,
    CryptoRefundRequest,
    Chain,
    Token,
)

router = APIRouter(prefix="/crypto", tags=["crypto-payments"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateCryptoPaymentRequest(BaseModel):
    """API request to create crypto payment"""
    user_id: str
    organization_id: Optional[str] = None
    amount: Decimal = Field(..., gt=0, description="Amount in fiat currency")
    currency: str = Field(default="USD", description="Fiat currency (USD, EUR, etc.)")
    description: Optional[str] = None
    order_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    provider: Optional[str] = None  # coinbase_commerce, etc.


class CryptoPaymentDetail(BaseModel):
    """Detailed payment information"""
    payment_id: str
    user_id: str
    organization_id: Optional[str] = None
    fiat_amount: Decimal
    fiat_currency: str
    crypto_amount: Optional[Decimal] = None
    token: Optional[str] = None
    chain: Optional[str] = None
    status: str
    provider: str
    checkout_url: Optional[str] = None
    wallet_address: Optional[str] = None
    tx_hash: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class CreateRefundRequest(BaseModel):
    """API request to create refund"""
    payment_id: str
    amount: Optional[Decimal] = None
    reason: str
    wallet_address: str
    requested_by: str


class SupportedChainsResponse(BaseModel):
    """Response with supported chains"""
    chains: List[Dict[str, Any]]


class SupportedTokensResponse(BaseModel):
    """Response with supported tokens"""
    tokens: List[Dict[str, Any]]


class ProvidersResponse(BaseModel):
    """Response with available providers"""
    providers: List[str]
    default_provider: str


# ============================================================================
# Dependencies
# ============================================================================

async def get_service() -> CryptoPaymentService:
    """Get crypto payment service"""
    return await get_crypto_service()


# ============================================================================
# Routes
# ============================================================================

@router.get("/info", summary="Get crypto payment service info")
async def get_info(
    service: CryptoPaymentService = Depends(get_service)
):
    """Get crypto payment service information and capabilities"""
    return {
        "service": "crypto_payments",
        "version": "1.0.0",
        "providers": [p.value for p in service.get_available_providers()],
        "default_provider": service.default_provider.value,
        "supported_chains": len(service.get_supported_chains()),
        "supported_tokens": len(service.get_supported_tokens()),
    }


@router.get("/providers", response_model=ProvidersResponse, summary="List available providers")
async def list_providers(
    service: CryptoPaymentService = Depends(get_service)
):
    """Get list of available crypto payment providers"""
    return ProvidersResponse(
        providers=[p.value for p in service.get_available_providers()],
        default_provider=service.default_provider.value,
    )


@router.get("/chains", response_model=SupportedChainsResponse, summary="List supported chains")
async def list_chains(
    service: CryptoPaymentService = Depends(get_service)
):
    """Get list of supported blockchain networks"""
    return SupportedChainsResponse(chains=service.get_supported_chains())


@router.get("/tokens", response_model=SupportedTokensResponse, summary="List supported tokens")
async def list_tokens(
    service: CryptoPaymentService = Depends(get_service)
):
    """Get list of supported cryptocurrencies/tokens"""
    return SupportedTokensResponse(tokens=service.get_supported_tokens())


@router.post("/payments", response_model=CryptoPaymentResponse, summary="Create crypto payment")
async def create_payment(
    request: CreateCryptoPaymentRequest,
    service: CryptoPaymentService = Depends(get_service)
):
    """
    Create a new crypto payment.

    Returns a checkout URL where the user can complete the payment.
    """
    try:
        # Map provider string to enum
        provider = None
        if request.provider:
            try:
                provider = CryptoProvider(request.provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {request.provider}"
                )

        # Create payment request
        payment_request = CryptoPaymentRequest(
            user_id=request.user_id,
            organization_id=request.organization_id,
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            order_id=request.order_id,
            metadata=request.metadata,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        response = await service.create_payment(payment_request, provider)
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment: {e}")


@router.get("/payments/{payment_id}", summary="Get payment details")
async def get_payment(
    payment_id: str,
    service: CryptoPaymentService = Depends(get_service)
):
    """Get details of a crypto payment"""
    payment = await service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return CryptoPaymentDetail(
        payment_id=payment.payment_id,
        user_id=payment.user_id,
        organization_id=payment.organization_id,
        fiat_amount=payment.fiat_amount,
        fiat_currency=payment.fiat_currency,
        crypto_amount=payment.crypto_amount,
        token=payment.token.value if payment.token else None,
        chain=payment.chain.value if payment.chain else None,
        status=payment.status.value,
        provider=payment.provider.value,
        checkout_url=payment.provider_checkout_url,
        wallet_address=payment.wallet_address,
        tx_hash=payment.tx_hash,
        expires_at=payment.expires_at.isoformat() if payment.expires_at else None,
        created_at=payment.created_at.isoformat() if payment.created_at else None,
        completed_at=payment.completed_at.isoformat() if payment.completed_at else None,
    )


@router.get("/payments/{payment_id}/status", summary="Check payment status")
async def check_payment_status(
    payment_id: str,
    service: CryptoPaymentService = Depends(get_service)
):
    """Check and return current payment status"""
    status = await service.check_payment_status(payment_id)
    return {
        "payment_id": payment_id,
        "status": status.value,
    }


@router.post("/payments/{payment_id}/cancel", summary="Cancel payment")
async def cancel_payment(
    payment_id: str,
    service: CryptoPaymentService = Depends(get_service)
):
    """Cancel a pending payment"""
    success = await service.cancel_payment(payment_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel payment - may not exist or not pending"
        )

    return {"payment_id": payment_id, "status": "cancelled"}


@router.get("/users/{user_id}/payments", summary="Get user's crypto payments")
async def get_user_payments(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    service: CryptoPaymentService = Depends(get_service)
):
    """Get crypto payments for a user"""
    # This would query the database
    # For now, return empty list as we need repository integration
    return {
        "user_id": user_id,
        "payments": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }


# ============================================================================
# Refunds
# ============================================================================

@router.post("/refunds", summary="Create refund")
async def create_refund(
    request: CreateRefundRequest,
    service: CryptoPaymentService = Depends(get_service)
):
    """
    Request a refund for a completed crypto payment.

    Note: Crypto refunds typically require manual processing.
    """
    try:
        refund_request = CryptoRefundRequest(
            payment_id=request.payment_id,
            amount=request.amount,
            reason=request.reason,
            wallet_address=request.wallet_address,
            requested_by=request.requested_by,
        )

        refund = await service.create_refund(refund_request)
        if not refund:
            raise HTTPException(
                status_code=400,
                detail="Cannot create refund - payment may not exist or not completed"
            )

        return {
            "refund_id": refund.refund_id,
            "payment_id": refund.payment_id,
            "amount": str(refund.fiat_amount),
            "status": refund.status.value,
            "wallet_address": refund.wallet_address,
            "message": "Refund request created. Manual processing may be required.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create refund: {e}")


# ============================================================================
# Webhooks
# ============================================================================

@router.post("/webhooks/coinbase", summary="Coinbase Commerce webhook")
async def coinbase_webhook(
    request: Request,
    x_cc_webhook_signature: str = Header(None, alias="X-CC-Webhook-Signature"),
    service: CryptoPaymentService = Depends(get_service)
):
    """
    Handle Coinbase Commerce webhook events.

    Configure this URL in Coinbase Commerce dashboard:
    https://your-domain.com/api/v1/payments/crypto/webhooks/coinbase
    """
    try:
        payload = await request.body()
        headers = dict(request.headers)

        event = await service.handle_webhook(
            provider=CryptoProvider.COINBASE_COMMERCE,
            payload=payload,
            signature=x_cc_webhook_signature or "",
            headers=headers,
        )

        if not event:
            raise HTTPException(status_code=400, detail="Invalid webhook")

        return {
            "received": True,
            "event_type": event.event_type,
            "payment_id": event.payment_id,
            "status": event.status.value,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {e}")


# ============================================================================
# Health
# ============================================================================

@router.get("/health", summary="Crypto payment health check")
async def health_check(
    service: CryptoPaymentService = Depends(get_service)
):
    """Check health of crypto payment providers"""
    providers_health = {}

    for provider_enum in service.get_available_providers():
        try:
            provider = service.get_provider(provider_enum)
            healthy = await provider.health_check()
            providers_health[provider_enum.value] = "healthy" if healthy else "unhealthy"
        except Exception as e:
            providers_health[provider_enum.value] = f"error: {e}"

    all_healthy = all(v == "healthy" for v in providers_health.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "providers": providers_health,
    }


__all__ = ["router"]
