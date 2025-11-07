"""
Wallet Microservice

Responsibilities:
- Digital wallet management (CRUD operations)
- Transaction management (deposit, withdraw, consume, transfer)
- Credit/token balance management
- Transaction history and analytics
"""

from fastapi import FastAPI, HTTPException, Depends, status, Query, Path, Body
import uvicorn
import logging
from contextlib import asynccontextmanager
import sys
import os
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import local components
from .wallet_service import WalletService
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus, Event, EventType, ServiceSource
from isa_common.consul_client import ConsulRegistry
from .routes_registry import get_routes_for_consul, SERVICE_METADATA
from .models import (
    WalletCreate, WalletUpdate, WalletBalance, WalletResponse,
    DepositRequest, WithdrawRequest, ConsumeRequest, TransferRequest,
    RefundRequest, TransactionFilter, WalletTransaction,
    TransactionType, WalletType, WalletStatistics
)

# Initialize configuration
config_manager = ConfigManager("wallet_service")
config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("wallet_service")
logger = app_logger  # for backward compatibility

# Track processed event IDs for idempotency
processed_event_ids = set()


def is_event_processed(event_id: str) -> bool:
    """Check if event has already been processed (idempotency)"""
    return event_id in processed_event_ids


def mark_event_processed(event_id: str):
    """Mark event as processed"""
    global processed_event_ids
    processed_event_ids.add(event_id)
    if len(processed_event_ids) > 10000:
        # Remove oldest half to prevent memory bloat
        processed_event_ids = set(list(processed_event_ids)[5000:])


# ==================== Event Handlers ====================

async def handle_payment_completed(event: Event):
    """
    Handle payment.completed event
    Deposit funds into wallet after successful payment
    """
    try:
        if is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        user_id = event.data.get("user_id")
        amount = event.data.get("amount")
        currency = event.data.get("currency", "USD")
        payment_id = event.data.get("payment_id")

        if not user_id or not amount:
            logger.warning(f"payment.completed event missing required fields: {event.id}")
            return

        # Get user's primary wallet
        wallet = await wallet_microservice.wallet_service.repository.get_primary_wallet(user_id)
        if not wallet:
            logger.warning(f"No wallet found for user {user_id}, skipping deposit")
            mark_event_processed(event.id)
            return

        # Deposit into wallet
        deposit_request = DepositRequest(
            amount=Decimal(str(amount)),
            description=f"Payment received (payment_id: {payment_id})",
            reference_id=payment_id,
            metadata={
                "event_id": event.id,
                "event_type": event.type,
                "payment_id": payment_id,
                "timestamp": event.timestamp,
                "currency": currency
            }
        )

        result = await wallet_microservice.wallet_service.deposit(wallet.wallet_id, deposit_request)

        mark_event_processed(event.id)
        logger.info(f"✅ Deposited {amount} {currency} to wallet for user {user_id} (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle payment.completed event {event.id}: {e}")


async def handle_user_created(event: Event):
    """
    Handle user.created event
    Automatically create wallet for new user
    """
    try:
        if is_event_processed(event.id):
            logger.debug(f"Event {event.id} already processed, skipping")
            return

        user_id = event.data.get("user_id")

        if not user_id:
            logger.warning(f"user.created event missing user_id: {event.id}")
            return

        # Create wallet for user
        wallet_request = WalletCreate(
            user_id=user_id,
            wallet_type=WalletType.FIAT,
            currency="USD",
            initial_balance=Decimal("0"),
            metadata={
                "auto_created": True,
                "event_id": event.id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )

        wallet = await wallet_microservice.wallet_service.create_wallet(wallet_request)

        mark_event_processed(event.id)
        logger.info(f"✅ Auto-created wallet {wallet.wallet_id} for user {user_id} (event: {event.id})")

    except Exception as e:
        logger.error(f"Failed to handle user.created event {event.id}: {e}")


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
            self.wallet_service = WalletService(event_bus=event_bus, config=config_manager)
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
    # Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("wallet_service")
        logger.info("✅ Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

    # Initialize microservice
    await wallet_microservice.initialize(event_bus=event_bus)

    # Subscribe to events
    if event_bus:
        try:
            # Subscribe to payment.completed from payment_service
            await event_bus.subscribe_to_events(
                pattern="payment_service.payment.completed",
                handler=handle_payment_completed,
                durable="wallet-payment-consumer"
            )
            logger.info("✅ Subscribed to payment.completed events")

            # Subscribe to user.created from account_service
            await event_bus.subscribe_to_events(
                pattern="account_service.user.created",
                handler=handle_user_created,
                durable="wallet-user-consumer"
            )
            logger.info("✅ Subscribed to user.created events")

        except Exception as e:
            logger.warning(f"⚠️  Failed to subscribe to events: {e}")

    # Consul service registration
    if config.consul_enabled:
        try:
            # Get route metadata
            route_meta = get_routes_for_consul()

            # Merge service metadata
            consul_meta = {
                'version': SERVICE_METADATA['version'],
                'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                **route_meta
            }

            wallet_microservice.consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA['service_name'],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA['tags'],
                meta=consul_meta,
                health_check_type='http'
            )
            wallet_microservice.consul_registry.register()
            logger.info(f"✅ Service registered with Consul: {route_meta.get('route_count')} routes")
        except Exception as e:
            logger.warning(f"⚠️  Failed to register with Consul: {e}")
            wallet_microservice.consul_registry = None

    yield

    # Cleanup
    if event_bus:
        await event_bus.close()
        logger.info("Event bus closed")

    await wallet_microservice.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Wallet Service",
    description="Digital wallet management microservice",
    version="1.0.0",
    lifespan=lifespan
)

# CORS handled by Gateway


# Dependency injection
def get_wallet_service() -> WalletService:
    """Get wallet service instance"""
    if not wallet_microservice.wallet_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wallet service not initialized"
        )
    return wallet_microservice.wallet_service


# Health check endpoints
@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": config.service_name,
        "port": config.service_port,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# Core wallet management endpoints

@app.post("/api/v1/wallets", response_model=WalletResponse)
async def create_wallet(
    wallet_data: WalletCreate,
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Create a new wallet for user"""
    try:
        result = await wallet_service.create_wallet(wallet_data)
        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/wallets/{wallet_id}")
async def get_wallet(
    wallet_id: str = Path(..., description="Wallet ID"),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get wallet details"""
    try:
        wallet = await wallet_service.get_wallet(wallet_id)
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
        return wallet
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/users/{user_id}/wallets")
async def get_user_wallets(
    user_id: str = Path(..., description="User ID"),
    wallet_type: Optional[WalletType] = Query(None, description="Filter by wallet type"),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get all wallets for a user"""
    try:
        wallets = await wallet_service.get_user_wallets(user_id)
        
        # Filter by type if specified
        if wallet_type:
            wallets = [w for w in wallets if w.wallet_type == wallet_type]
            
        return {"wallets": wallets, "count": len(wallets)}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/wallets/{wallet_id}/balance", response_model=WalletResponse)
async def get_balance(
    wallet_id: str = Path(..., description="Wallet ID"),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get wallet balance"""
    try:
        result = await wallet_service.get_balance(wallet_id)
        if not result.success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Transaction endpoints

@app.post("/api/v1/wallets/{wallet_id}/deposit", response_model=WalletResponse)
async def deposit(
    wallet_id: str = Path(..., description="Wallet ID"),
    request: DepositRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Deposit funds to wallet"""
    try:
        result = await wallet_service.deposit(wallet_id, request)
        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/wallets/{wallet_id}/withdraw", response_model=WalletResponse)
async def withdraw(
    wallet_id: str = Path(..., description="Wallet ID"),
    request: WithdrawRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Withdraw funds from wallet"""
    try:
        result = await wallet_service.withdraw(wallet_id, request)
        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/wallets/{wallet_id}/consume", response_model=WalletResponse)
async def consume(
    wallet_id: str = Path(..., description="Wallet ID"),
    request: ConsumeRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Consume credits/tokens from wallet"""
    try:
        result = await wallet_service.consume(wallet_id, request)
        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Backward compatibility endpoint for credit consumption
@app.post("/api/v1/users/{user_id}/credits/consume", response_model=WalletResponse)
async def consume_user_credits(
    user_id: str = Path(..., description="User ID"),
    request: ConsumeRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Consume credits from user's primary wallet (backward compatibility)"""
    try:
        result = await wallet_service.consume_by_user(user_id, request)
        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/wallets/{wallet_id}/transfer", response_model=WalletResponse)
async def transfer(
    wallet_id: str = Path(..., description="Source wallet ID"),
    request: TransferRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Transfer funds between wallets"""
    try:
        result = await wallet_service.transfer(wallet_id, request)
        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/transactions/{transaction_id}/refund", response_model=WalletResponse)
async def refund_transaction(
    transaction_id: str = Path(..., description="Original transaction ID"),
    request: RefundRequest = Body(...),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Refund a previous transaction"""
    try:
        result = await wallet_service.refund(transaction_id, request)
        if not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Transaction history endpoints

@app.get("/api/v1/wallets/{wallet_id}/transactions")
async def get_wallet_transactions(
    wallet_id: str = Path(..., description="Wallet ID"),
    transaction_type: Optional[TransactionType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get wallet transaction history"""
    try:
        filter_params = TransactionFilter(
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        transactions = await wallet_service.get_transactions(filter_params)
        return {
            "transactions": transactions,
            "count": len(transactions),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/users/{user_id}/transactions")
async def get_user_transactions(
    user_id: str = Path(..., description="User ID"),
    transaction_type: Optional[TransactionType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get user transaction history across all wallets"""
    try:
        transactions = await wallet_service.get_user_transactions(
            user_id=user_id,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "transactions": transactions,
            "count": len(transactions),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Statistics endpoints

@app.get("/api/v1/wallets/{wallet_id}/statistics")
async def get_wallet_statistics(
    wallet_id: str = Path(..., description="Wallet ID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get wallet statistics"""
    try:
        stats = await wallet_service.get_statistics(wallet_id, start_date, end_date)
        if not stats:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/users/{user_id}/statistics")
async def get_user_statistics(
    user_id: str = Path(..., description="User ID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Get aggregated statistics for all user wallets"""
    try:
        stats = await wallet_service.get_user_statistics(user_id, start_date, end_date)
        return stats
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Backward compatibility for credit balance
@app.get("/api/v1/users/{user_id}/credits/balance")
async def get_user_credit_balance(
    user_id: str = Path(..., description="User ID"),
    wallet_service: WalletService = Depends(get_wallet_service)
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
                    currency="CREDIT"
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
                    "wallet_id": create_result.wallet_id
                }
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create wallet")
        
        wallet = fiat_wallets[0]
        return {
            "success": True,
            "balance": float(wallet.balance),
            "available_balance": float(wallet.available_balance) if hasattr(wallet, 'available_balance') else float(wallet.balance - wallet.locked_balance),
            "locked_balance": float(wallet.locked_balance) if hasattr(wallet, 'locked_balance') else 0.0,
            "currency": wallet.currency,
            "wallet_id": wallet.wallet_id
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Service statistics
@app.get("/api/v1/wallet/stats")
async def get_wallet_service_stats(
    wallet_service: WalletService = Depends(get_wallet_service)
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
                "blockchain_ready": True
            }
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


if __name__ == "__main__":
    # Print configuration summary for debugging
    config_manager.print_config_summary()
    
    uvicorn.run(
        "microservices.wallet_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )