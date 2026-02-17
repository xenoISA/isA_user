"""
Order Microservice

Responsibilities:
- Order management and lifecycle
- Transaction recording and tracking
- Payment service integration
- Wallet service integration
- Order analytics and reporting
"""

from fastapi import FastAPI, HTTPException, Depends, status, Query, Path, Body
import uvicorn
import logging
from contextlib import asynccontextmanager
import sys
import os
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import local components
from .order_service import OrderService
from .protocols import OrderServiceError, OrderValidationError, OrderNotFoundError
from .factory import create_order_service
from core.config_manager import ConfigManager
from core.logger import setup_service_logger
from core.nats_client import get_event_bus, Event
from isa_common.consul_client import ConsulRegistry
from .models import (
    OrderCreateRequest, OrderUpdateRequest, OrderCancelRequest,
    OrderCompleteRequest, OrderResponse, OrderListResponse,
    OrderSummaryResponse, OrderStatistics, OrderFilter,
    OrderSearchParams, Order, OrderStatus, OrderType, PaymentStatus,
    OrderServiceStatus
)
from .routes_registry import get_routes_for_consul, SERVICE_METADATA

# Initialize configuration
config_manager = ConfigManager("order_service")
config = config_manager.get_service_config()

# Setup loggers (use actual service name)
app_logger = setup_service_logger("order_service")
logger = app_logger  # for backward compatibility

# Global client instances
payment_client = None
wallet_client = None
account_client = None
storage_client = None
billing_client = None
inventory_client = None
tax_client = None
fulfillment_client = None


class OrderMicroservice:
    """Order microservice core class"""

    def __init__(self):
        self.order_service = None
        self.event_bus = None

    async def initialize(
        self,
        event_bus=None,
        payment_client=None,
        wallet_client=None,
        account_client=None,
        storage_client=None,
        billing_client=None,
        inventory_client=None,
        tax_client=None,
        fulfillment_client=None,
    ):
        """Initialize the microservice"""
        try:
            self.event_bus = event_bus
            # Use factory to create service with real dependencies
            self.order_service = create_order_service(
                config=config_manager,
                event_bus=event_bus,
                payment_client=payment_client,
                wallet_client=wallet_client,
                account_client=account_client,
                storage_client=storage_client,
                billing_client=billing_client,
                inventory_client=inventory_client,
                tax_client=tax_client,
                fulfillment_client=fulfillment_client,
            )
            logger.info("Order microservice initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize order microservice: {e}")
            raise

    async def shutdown(self):
        """Shutdown the microservice"""
        try:
            if self.event_bus:
                await self.event_bus.close()
                logger.info("Event bus closed")
            logger.info("Order microservice shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global microservice instance
order_microservice = OrderMicroservice()
consul_registry: Optional[ConsulRegistry] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global consul_registry, payment_client, wallet_client, account_client, storage_client, billing_client
    global inventory_client, tax_client, fulfillment_client

    # Initialize event bus
    event_bus = None
    try:
        event_bus = await get_event_bus("order_service")
        logger.info("✅ Event bus initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize event bus: {e}. Continuing without event publishing.")
        event_bus = None

    # Initialize service clients
    try:
        from .clients import (
            PaymentClient,
            WalletClient,
            AccountClient,
            StorageClient,
            BillingClient,
            InventoryClient,
            TaxClient,
            FulfillmentClient,
        )

        payment_client = PaymentClient(config=config_manager)
        wallet_client = WalletClient(config=config_manager)
        account_client = AccountClient(config=config_manager)
        storage_client = StorageClient(config=config_manager)
        billing_client = BillingClient(config=config_manager)
        inventory_client = InventoryClient(config=config_manager)
        tax_client = TaxClient(config=config_manager)
        fulfillment_client = FulfillmentClient(config=config_manager)

        logger.info("✅ Service clients initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Failed to initialize service clients: {e}")
        payment_client = None
        wallet_client = None
        account_client = None
        storage_client = None
        billing_client = None
        inventory_client = None
        tax_client = None
        fulfillment_client = None

    # Initialize microservice with event bus and clients
    await order_microservice.initialize(
        event_bus=event_bus,
        payment_client=payment_client,
        wallet_client=wallet_client,
        account_client=account_client,
        storage_client=storage_client,
        billing_client=billing_client,
        inventory_client=inventory_client,
        tax_client=tax_client,
        fulfillment_client=fulfillment_client,
    )

    # Register event handlers
    if event_bus:
        try:
            from .events.handlers import get_event_handlers

            # Get event handlers (function-based, not class-based)
            handler_map = get_event_handlers(order_microservice.order_service)

            # Subscribe to events
            for event_pattern, handler_func in handler_map.items():
                # Subscribe to each event pattern (already includes service prefix)
                await event_bus.subscribe_to_events(
                    pattern=event_pattern, handler=handler_func
                )
                logger.info(f"Subscribed to {event_pattern} events")

            logger.info(f"✅ Event handlers registered successfully - Subscribed to {len(handler_map)} event types")
        except Exception as e:
            logger.warning(f"⚠️  Failed to register event handlers: {e}")

    # Consul 服务注册
    if config.consul_enabled:
        try:
            # 获取路由元数据
            route_meta = get_routes_for_consul()

            # 合并服务元数据
            consul_meta = {
                'version': SERVICE_METADATA['version'],
                'capabilities': ','.join(SERVICE_METADATA['capabilities']),
                **route_meta
            }

            consul_registry = ConsulRegistry(
                service_name=SERVICE_METADATA['service_name'],
                service_port=config.service_port,
                consul_host=config.consul_host,
                consul_port=config.consul_port,
                tags=SERVICE_METADATA['tags'],
                meta=consul_meta,
                health_check_type='ttl'  # Use TTL for reliable health checks
            )
            consul_registry.register()
            consul_registry.start_maintenance()  # Start TTL heartbeat
            logger.info(f"✅ Service registered with Consul: {route_meta.get('route_count')} routes")
        except Exception as e:
            logger.warning(f"⚠️  Failed to register with Consul: {e}")
            consul_registry = None

    yield

    # Cleanup
    try:
        # Consul 注销
        if consul_registry:
            try:
                consul_registry.deregister()
                logger.info("✅ Service deregistered from Consul")
            except Exception as e:
                logger.error(f"❌ Failed to deregister from Consul: {e}")

        # Close service clients
        if payment_client:
            try:
                await payment_client.close()
                logger.info("✅ Payment client closed")
            except Exception as e:
                logger.error(f"❌ Failed to close payment client: {e}")

        if wallet_client:
            try:
                await wallet_client.close()
                logger.info("✅ Wallet client closed")
            except Exception as e:
                logger.error(f"❌ Failed to close wallet client: {e}")

        if account_client:
            try:
                await account_client.close()
                logger.info("✅ Account client closed")
            except Exception as e:
                logger.error(f"❌ Failed to close account client: {e}")

        if storage_client:
            try:
                await storage_client.close()
                logger.info("✅ Storage client closed")
            except Exception as e:
                logger.error(f"❌ Failed to close storage client: {e}")

        if billing_client:
            try:
                await billing_client.close()
                logger.info("✅ Billing client closed")
            except Exception as e:
                logger.error(f"❌ Failed to close billing client: {e}")

        await order_microservice.shutdown()

    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")


# Create FastAPI application
app = FastAPI(
    title="Order Service",
    description="Order management and transaction recording microservice",
    version="1.0.0",
    lifespan=lifespan
)

# CORS handled by Gateway


# Dependency injection
def get_order_service() -> OrderService:
    """Get order service instance"""
    if not order_microservice.order_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order service not initialized"
        )
    return order_microservice.order_service


# Health check endpoints
@app.get("/api/v1/orders/health")
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


@app.get("/health/detailed")
async def detailed_health_check(
    order_service: OrderService = Depends(get_order_service)
):
    """Detailed health check with database connectivity"""
    try:
        health_data = await order_service.health_check()
        return OrderServiceStatus(
            database_connected=health_data["status"] == "healthy",
            timestamp=health_data["timestamp"]
        )
    except Exception as e:
        return OrderServiceStatus(
            database_connected=False,
            timestamp=datetime.utcnow()
        )


# Core order management endpoints

@app.post("/api/v1/orders", response_model=OrderResponse)
async def create_order(
    request: OrderCreateRequest,
    order_service: OrderService = Depends(get_order_service)
):
    """Create a new order"""
    try:
        return await order_service.create_order(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/orders/search")
async def search_orders(
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    include_cancelled: bool = Query(False, description="Include cancelled orders"),
    order_service: OrderService = Depends(get_order_service)
):
    """Search orders"""
    try:
        search_params = OrderSearchParams(
            query=query,
            user_id=user_id,
            limit=limit,
            include_cancelled=include_cancelled
        )
        orders = await order_service.search_orders(search_params)
        return {
            "orders": orders,
            "count": len(orders),
            "query": query
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/orders/statistics")
async def get_order_statistics(
    order_service: OrderService = Depends(get_order_service)
):
    """Get order service statistics"""
    try:
        logger.info("Getting order statistics...")
        result = await order_service.get_order_statistics()
        logger.info(f"Statistics result: {result}")
        # Convert to dict for JSON response
        return result.dict() if hasattr(result, 'dict') else result
    except OrderServiceError as e:
        logger.error(f"OrderServiceError in get_order_statistics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_order_statistics: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error: {str(e)}")


@app.get("/api/v1/orders/{order_id}")
async def get_order(
    order_id: str = Path(..., description="Order ID"),
    order_service: OrderService = Depends(get_order_service)
):
    """Get order details"""
    try:
        order = await order_service.get_order(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/api/v1/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str = Path(..., description="Order ID"),
    request: OrderUpdateRequest = Body(...),
    order_service: OrderService = Depends(get_order_service)
):
    """Update order"""
    try:
        return await order_service.update_order(order_id, request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str = Path(..., description="Order ID"),
    request: OrderCancelRequest = Body(...),
    order_service: OrderService = Depends(get_order_service)
):
    """Cancel an order"""
    try:
        return await order_service.cancel_order(order_id, request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/v1/orders/{order_id}/complete", response_model=OrderResponse)
async def complete_order(
    order_id: str = Path(..., description="Order ID"),
    request: OrderCompleteRequest = Body(...),
    order_service: OrderService = Depends(get_order_service)
):
    """Complete an order"""
    try:
        return await order_service.complete_order(order_id, request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Order query endpoints

@app.get("/api/v1/orders", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    order_type: Optional[OrderType] = Query(None, description="Filter by order type"),
    status: Optional[OrderStatus] = Query(None, description="Filter by status"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    order_service: OrderService = Depends(get_order_service)
):
    """List orders with filtering and pagination"""
    try:
        filter_params = OrderFilter(
            user_id=user_id,
            order_type=order_type,
            status=status,
            payment_status=payment_status,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=(page - 1) * page_size
        )
        return await order_service.list_orders(filter_params)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Note: User orders can be retrieved using GET /api/v1/orders?user_id={user_id}
# The dedicated /api/v1/users/{user_id}/orders endpoint has been removed to avoid
# routing conflicts with APISIX base_path pattern


# Integration endpoints

@app.get("/api/v1/payments/{payment_intent_id}/orders")
async def get_orders_by_payment(
    payment_intent_id: str = Path(..., description="Payment intent ID"),
    order_service: OrderService = Depends(get_order_service)
):
    """Get orders associated with a payment intent"""
    try:
        # This would be implemented in the repository layer
        orders = await order_service.order_repo.get_orders_by_payment_intent(payment_intent_id)
        return {
            "orders": orders,
            "payment_intent_id": payment_intent_id,
            "count": len(orders)
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/api/v1/subscriptions/{subscription_id}/orders")
async def get_orders_by_subscription(
    subscription_id: str = Path(..., description="Subscription ID"),
    order_service: OrderService = Depends(get_order_service)
):
    """Get orders associated with a subscription"""
    try:
        orders = await order_service.order_repo.get_orders_by_subscription(subscription_id)
        return {
            "orders": orders,
            "subscription_id": subscription_id,
            "count": len(orders)
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Service info endpoints

@app.get("/api/v1/order/info")
async def get_service_info():
    """Get order service information"""
    return {
        "service": "order_service",
        "version": "1.0.0",
        "port": 8210,
        "status": "operational",
        "capabilities": {
            "order_management": True,
            "payment_integration": True,
            "wallet_integration": True,
            "transaction_recording": True,
            "order_analytics": True
        },
        "integrations": {
            "payment_service": "http://localhost:8207",
            "wallet_service": "http://localhost:8209"
        }
    }


# Error handlers
@app.exception_handler(OrderValidationError)
async def validation_error_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(OrderNotFoundError)
async def not_found_error_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)}
    )


@app.exception_handler(OrderServiceError)
async def service_error_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)}
    )


if __name__ == "__main__":
    # Print configuration summary for debugging
    config_manager.print_config_summary()
    
    uvicorn.run(
        "microservices.order_service.main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )
