"""
Wallet Microservice

Responsibilities:
- Digital wallet management (CRUD operations)
- Transaction management (deposit, withdraw, consume, transfer)
- Credit/token balance management
- Transaction history and analytics
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, Path, Query, Request, status

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Import local components
from isa_common.consul_client import ConsulRegistry

from core.admin_audit import publish_admin_action
from core.config_manager import ConfigManager
from core.graceful_shutdown import GracefulShutdown, shutdown_middleware
from core.metrics import setup_metrics
from core.logger import setup_service_logger
from core.nats_client import Event, get_event_bus
from core.health import HealthCheck

from .models import (
    ConsumeRequest,
    DepositRequest,
    RefundRequest,
    TransactionFilter,
    TransactionType,
    TransferRequest,
    WalletBalance,
    WalletCreate,
    WalletResponse,
    WalletStatistics,
    WalletTransaction,
    WalletType,
    WalletUpdate,
    WithdrawRequest,
)
from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .wallet_service import WalletService
from .factory import create_wallet_service

# Initialize configuration
config_manager = ConfigManager("wallet_service")
config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("wallet_service")
logger = app_logger  # for backward compatibility

shutdown_manager = GracefulShutdown("wallet_service")

# =============================================================================
# NEW: Import standardized event handlers and clients
# =============================================================================
from .clients import AccountClient
from .events import get_event_handlers

# =============================================================================
# OLD: Legacy event handlers (KEPT FOR BACKWARD COMPATIBILITY - DO NOT USE)
# These are now in events/handlers.py
# =============================================================================

# Track processed event IDs for idempotency (DEPRECATED - moved to events/handlers.py)
processed_event_ids = set()


def is_event_processed(event_id: str) -> bool:
    """Check if event has already been processed (idempotency) - DEPRECATED"""
    return event_id in processed_event_ids


def mark_event_processed(event_id: str):
    """Mark event as processed - DEPRECATED"""
    global processed_event_ids
    processed_event_ids.add(event_id)
    if len(processed_event_ids) > 10000:
        # Remove oldest half to prevent memory bloat
        processed_event_ids = set(list(processed_event_ids)[5000:])


# ==================== Event Handlers (DEPRECATED - moved to events/handlers.py) ====================

"""
# DEPRECATED: These handlers have been moved to events/handlers.py
# Keeping commented code for reference during migration
#
# - handle_payment_completed() -> events/handlers.py
# - handle_user_created() -> events/handlers.py
#
# All event handlers are now registered via get_event_handlers() in lifespan()
"""


class WalletMicroservice:
    """Wallet microservice core class"""

    def __init__(self):
        self.wallet_service = None
        self.event_bus = None
        self.consul_registry = None

    async def initialize(self, event_bus=None):
        """Initialize the microservice"""
        try:
            self.event_bus = event_bus
            self.wallet_service = create_wallet_service(
                config=config_manager,
                event_bus=event_bus
            )
            logger.info("Wallet microservice initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize wallet microservice: {e}")
            raise

    async def shutdown(self):
        """Shutdown the microservice"""
        try:
            # Consul deregistration
            if self.consul_registry:
                try:
                    self.consul_registry.deregister()
                    logger.info("✅ Wallet service deregistered from Consul")
                except Exception as e:
                    logger.error(f"❌ Failed to deregister from Consul: {e}")

            logger.info("Wallet microservice shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global microservice instance
wallet_microservice = WalletMicroservice()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    shutdown_manager.install_signal_handlers()
    # Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("wallet_service")
        logger.info("✅ Event bus initialized successfully")
    except Exception as e:
        logger.warning(
            f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing."
        )
        event_bus = None

    # Initialize microservice
    await wallet_microservice.initialize(event_bus=event_bus)

    # =============================================================================
    # NEW: Subscribe to events using standardized event handlers
    # =============================================================================
    if event_bus:
        try:
            # Get all event handlers from events/handlers.py
            event_handlers = get_event_handlers(
                wallet_service=wallet_microservice.wallet_service, event_bus=event_bus
            )

            # Subscribe to each event pattern
            for pattern, handler in event_handlers.items():
                await event_bus.subscribe_to_events(
                    pattern=pattern,
                    handler=handler,
                    durable=f"wallet-{pattern.split('.')[-1]}-consumer",
                )
                logger.info(f"✅ Subscribed to {pattern}")

            logger.info(
                f"✅ Wallet service subscribed to {len(event_handlers)} event types"
            )

        except Exception as e:
            logger.warning(f"⚠️  Failed to subscribe to events: {e}")

    # =============================================================================
    # OLD: Legacy event subscription (COMMENTED OUT - replaced by standardized approach)
    # =============================================================================
    """
    # OLD CODE - DO NOT USE
    if event_bus:
        try:
            await event_bus.subscribe_to_events(
                pattern="payment_service.payment.completed",
                handler=handle_payment_completed,  # This function no longer exists in main.py
                durable="wallet-payment-consumer",
            )
            await event_bus.subscribe_to_events(
                pattern="account_service.user.created",
                handler=handle_user_created,  # This function no longer exists in main.py
                durable="wallet-user-consumer",
            )
        except Exception as e:
            logger.warning(f"Failed to subscribe to events: {e}")
    """

    # Consul service registration
    if config.consul_enabled:
        try:
            # Get route metadata
            route_meta = get_routes_for_consul()

            # Merge service metadata
            consul_meta = {
                "version": SERVICE_METADATA["version"],
                "capabilities": ",".join(SERVICE_METADATA["capabilities"]),
                **route_meta,
            }

            wallet_microservice.consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA["service_name"],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA["tags"],
                meta=consul_meta,
                health_check_type="ttl"  # Use TTL for reliable health checks,
            )
            wallet_microservice.consul_registry.register()
            wallet_microservice.consul_registry.start_maintenance()  # Start TTL heartbeat
            # Start TTL heartbeat - added for consistency with isA_Model
            logger.info(
                f"✅ Service registered with Consul: {route_meta.get('route_count')} routes"
            )
        except Exception as e:
            logger.warning(f"⚠️  Failed to register with Consul: {e}")
            wallet_microservice.consul_registry = None

    yield

    # Cleanup
    shutdown_manager.initiate_shutdown()
    await shutdown_manager.wait_for_drain()
    if event_bus:
        await event_bus.close()
        logger.info("Event bus closed")

    await wallet_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Wallet Service",
    description="Digital wallet management microservice",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(shutdown_middleware, shutdown_manager=shutdown_manager)
setup_metrics(app, "wallet_service")

# CORS handled by Gateway


# Dependency injection
def get_wallet_service() -> WalletService:
    """Get wallet service instance"""
    if not wallet_microservice.wallet_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wallet service not initialized",
        )
    return wallet_microservice.wallet_service


# Health check endpoints
health = HealthCheck("wallet_service", version="1.0.0", shutdown_manager=shutdown_manager)
health.add_postgres(lambda: wallet_microservice.wallet_service.repository.db if wallet_microservice.wallet_service and hasattr(wallet_microservice.wallet_service, 'repository') and wallet_microservice.wallet_service.repository else None)


@app.get("/api/v1/wallet/health")
@app.get("/health")
async def health_check():
    """Service health check"""
    return await health.check()

@app.post("/api/v1/wallets", response_model=WalletResponse)
async def create_wallet(
    wallet_data: WalletCreate,
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Create a new wallet for user"""
    try:
        result = await wallet_service.create_wallet(wallet_data)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Backward compatibility for credit balance (must be before {wallet_id} routes)
@app.get("/api/v1/wallets/credits/balance")
async def get_user_credit_balance(
    user_id: str = Query(..., description="User ID"),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Get user's credit balance (backward compatibility)"""
    try:
        wallets = await wallet_service.get_user_wallets(user_id)

        # Get primary fiat wallet
        fiat_wallets = [w for w in wallets if w.wallet_type == WalletType.FIAT]
        if not fiat_wallets:
            # Create default wallet if doesn't exist
            create_result = await wallet_service.create_wallet(
                WalletCreate(
                    user_id=user_id,
                    wallet_type=WalletType.FIAT,
                    initial_balance=Decimal(0),
                    currency="CREDIT",
                )
            )
            if create_result.success:
                balance = float(create_result.balance or 0)
                return {
                    "success": True,
                    "balance": balance,
                    "available_balance": balance,
                    "locked_balance": 0.0,
                    "currency": "CREDIT",
                    "wallet_id": create_result.wallet_id,
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create wallet",
                )

        wallet = fiat_wallets[0]
        return {
            "success": True,
            "balance": float(wallet.balance),
            "available_balance": float(wallet.available_balance)
            if hasattr(wallet, "available_balance")
            else float(wallet.balance - wallet.locked_balance),
            "locked_balance": float(wallet.locked_balance)
            if hasattr(wallet, "locked_balance")
            else 0.0,
            "currency": wallet.currency,
            "wallet_id": wallet.wallet_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/wallets/{wallet_id}")
async def get_wallet(
    wallet_id: str = Path(..., description="Wallet ID"),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Get wallet details"""
    try:
        wallet = await wallet_service.get_wallet(wallet_id)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found"
            )
        return wallet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/wallets")
async def get_user_wallets(
    user_id: str = Query(..., description="User ID"),
    wallet_type: Optional[WalletType] = Query(
        None, description="Filter by wallet type"
    ),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Get all wallets for a user (filtered by user_id query parameter)"""
    try:
        wallets = await wallet_service.get_user_wallets(user_id)

        # Filter by type if specified
        if wallet_type:
            wallets = [w for w in wallets if w.wallet_type == wallet_type]

        return {"wallets": wallets, "count": len(wallets)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/wallets/{wallet_id}/balance", response_model=WalletResponse)
async def get_balance(
    wallet_id: str = Path(..., description="Wallet ID"),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Get wallet balance"""
    try:
        result = await wallet_service.get_balance(wallet_id)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result.message
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Transaction endpoints


@app.post("/api/v1/wallets/{wallet_id}/deposit", response_model=WalletResponse)
async def deposit(
    wallet_id: str = Path(..., description="Wallet ID"),
    request: DepositRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Deposit funds to wallet"""
    try:
        result = await wallet_service.deposit(wallet_id, request)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/wallets/{wallet_id}/withdraw", response_model=WalletResponse)
async def withdraw(
    wallet_id: str = Path(..., description="Wallet ID"),
    request: WithdrawRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Withdraw funds from wallet"""
    try:
        result = await wallet_service.withdraw(wallet_id, request)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/wallets/{wallet_id}/consume", response_model=WalletResponse)
async def consume(
    wallet_id: str = Path(..., description="Wallet ID"),
    request: ConsumeRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Consume credits/tokens from wallet"""
    try:
        result = await wallet_service.consume(wallet_id, request)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Backward compatibility endpoint for credit consumption
@app.post("/api/v1/wallets/credits/consume", response_model=WalletResponse)
async def consume_user_credits(
    user_id: str = Query(..., description="User ID"),
    request: ConsumeRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Consume credits from user's primary wallet (backward compatibility)"""
    try:
        result = await wallet_service.consume_by_user(user_id, request)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/wallets/{wallet_id}/transfer", response_model=WalletResponse)
async def transfer(
    wallet_id: str = Path(..., description="Source wallet ID"),
    request: TransferRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Transfer funds between wallets"""
    try:
        result = await wallet_service.transfer(wallet_id, request)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/transactions/{transaction_id}/refund", response_model=WalletResponse)
async def refund_transaction(
    transaction_id: str = Path(..., description="Original transaction ID"),
    request: RefundRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Refund a previous transaction"""
    try:
        result = await wallet_service.refund(transaction_id, request)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.message
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Transaction history endpoints


@app.get("/api/v1/wallets/{wallet_id}/transactions")
async def get_wallet_transactions(
    wallet_id: str = Path(..., description="Wallet ID"),
    transaction_type: Optional[TransactionType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Get wallet transaction history"""
    try:
        filter_params = TransactionFilter(
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        transactions = await wallet_service.get_transactions(filter_params)
        return {
            "transactions": transactions,
            "count": len(transactions),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/wallets/transactions")
async def get_user_transactions(
    user_id: str = Query(..., description="User ID"),
    transaction_type: Optional[TransactionType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Get user transaction history across all wallets (filtered by user_id query parameter)"""
    try:
        transactions = await wallet_service.get_user_transactions(
            user_id=user_id,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "transactions": transactions,
            "count": len(transactions),
            "limit": limit,
            "offset": offset,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Statistics endpoints


@app.get("/api/v1/wallets/{wallet_id}/statistics")
async def get_wallet_statistics(
    wallet_id: str = Path(..., description="Wallet ID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Get wallet statistics"""
    try:
        stats = await wallet_service.get_statistics(wallet_id, start_date, end_date)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found"
            )
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/wallets/statistics")
async def get_user_statistics(
    user_id: str = Query(..., description="User ID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Get aggregated statistics for all user wallets (filtered by user_id query parameter)"""
    try:
        stats = await wallet_service.get_user_statistics(user_id, start_date, end_date)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Service statistics
@app.get("/api/v1/wallet/stats")
async def get_wallet_service_stats(
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """Get wallet service statistics"""
    try:
        # Return basic service info
        return {
            "service": "wallet_service",
            "version": "1.0.0",
            "status": "operational",
            "capabilities": {
                "wallet_management": True,
                "transaction_management": True,
                "blockchain_ready": True,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ====================
# Admin Endpoints
# ====================

async def require_admin(request: Request):
    """Check for admin role header"""
    if request.headers.get("X-Admin-Role") != "true":
        raise HTTPException(status_code=403, detail="Admin access required")


def _extract_admin_context(request: Request) -> dict:
    """Extract admin identity and request context from headers for audit logging."""
    return {
        "admin_user_id": request.headers.get("X-Admin-User-Id", "unknown_admin"),
        "admin_email": request.headers.get("X-Admin-Email"),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
    }


async def _audit_admin_action(
    request: Request,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    changes: Optional[dict] = None,
    metadata: Optional[dict] = None,
):
    """Fire-and-forget admin audit event. Never raises."""
    try:
        ctx = _extract_admin_context(request)
        await publish_admin_action(
            event_bus=wallet_microservice.event_bus,
            admin_user_id=ctx["admin_user_id"],
            admin_email=ctx["admin_email"],
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ctx["ip_address"],
            user_agent=ctx["user_agent"],
            metadata=metadata,
        )
    except Exception as e:
        logger.warning(f"Admin audit publish failed (non-blocking): {e}")


@app.get("/api/v1/wallet/admin/{user_id}")
async def admin_get_wallet_details(
    user_id: str,
    request: Request,
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """[Admin] Get wallet details for a specific user"""
    await require_admin(request)
    try:
        wallets = await wallet_service.get_user_wallets(user_id)

        wallet_summaries = []
        for w in wallets:
            summary = {
                "wallet_id": w.wallet_id,
                "wallet_type": w.wallet_type.value if hasattr(w.wallet_type, "value") else str(w.wallet_type),
                "balance": float(w.balance),
                "locked_balance": float(w.locked_balance) if hasattr(w, "locked_balance") else 0.0,
                "available_balance": float(w.available_balance) if hasattr(w, "available_balance") else float(w.balance),
                "currency": w.currency,
                "last_updated": w.last_updated.isoformat() if hasattr(w, "last_updated") and w.last_updated else None,
            }
            wallet_summaries.append(summary)

        return {
            "success": True,
            "user_id": user_id,
            "wallets": wallet_summaries,
            "wallet_count": len(wallet_summaries),
            "total_balance": sum(float(w.balance) for w in wallets),
        }

    except Exception as e:
        logger.error(f"Error getting wallet details (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/wallet/admin/{user_id}/adjust")
async def admin_adjust_wallet_balance(
    user_id: str,
    request: Request,
    amount: Decimal = Query(..., description="Adjustment amount (positive to add, negative to subtract)"),
    reason: str = Query(..., description="Reason for balance adjustment"),
    wallet_id: Optional[str] = Query(None, description="Target wallet ID (defaults to primary fiat wallet)"),
    wallet_service: WalletService = Depends(get_wallet_service),
):
    """[Admin] Adjust wallet balance for a user with reason"""
    await require_admin(request)
    try:
        # Find the target wallet
        if wallet_id:
            wallet = await wallet_service.get_wallet(wallet_id)
            if not wallet:
                raise HTTPException(status_code=404, detail=f"Wallet {wallet_id} not found")
            # Verify it belongs to the user
            if hasattr(wallet, "user_id") and wallet.user_id != user_id:
                raise HTTPException(status_code=400, detail="Wallet does not belong to specified user")
            target_wallet_id = wallet_id
        else:
            # Get user's primary fiat wallet
            wallets = await wallet_service.get_user_wallets(user_id)
            fiat_wallets = [w for w in wallets if w.wallet_type == WalletType.FIAT]
            if not fiat_wallets:
                raise HTTPException(status_code=404, detail=f"No fiat wallet found for user {user_id}")
            target_wallet_id = fiat_wallets[0].wallet_id

        # Perform the adjustment as a deposit (positive) or withdraw (negative)
        if amount > 0:
            result = await wallet_service.deposit(
                target_wallet_id,
                DepositRequest(
                    amount=abs(amount),
                    description=f"Admin adjustment: {reason}",
                    metadata={"admin_adjustment": True, "reason": reason},
                ),
            )
        elif amount < 0:
            result = await wallet_service.withdraw(
                target_wallet_id,
                WithdrawRequest(
                    amount=abs(amount),
                    description=f"Admin adjustment: {reason}",
                    metadata={"admin_adjustment": True, "reason": reason},
                ),
            )
        else:
            raise HTTPException(status_code=400, detail="Adjustment amount must be non-zero")

        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)

        # Audit
        await _audit_admin_action(
            request, action="balance_adjustment", resource_type="wallet",
            resource_id=target_wallet_id,
            changes={"adjustment": str(amount), "new_balance": str(result.balance)},
            metadata={"user_id": user_id, "reason": reason},
        )

        return {
            "success": True,
            "message": f"Balance adjusted by {amount}",
            "user_id": user_id,
            "wallet_id": target_wallet_id,
            "adjustment": str(amount),
            "new_balance": str(result.balance),
            "transaction_id": result.transaction_id,
            "reason": reason,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adjusting wallet balance (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


if __name__ == "__main__":
    # Print configuration summary for debugging
    config_manager.print_config_summary()

    uvicorn.run(
        "microservices.wallet_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower(),
    )
