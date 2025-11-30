"""
Order Service Business Logic

Business logic layer for order management and microservice communication.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import logging
import httpx
from decimal import Decimal

from .order_repository import OrderRepository, OrderNotFoundException
from .models import (
    OrderCreateRequest, OrderUpdateRequest, OrderCancelRequest,
    OrderCompleteRequest, OrderResponse, OrderListResponse,
    OrderSummaryResponse, OrderStatistics, OrderFilter,
    OrderSearchParams, Order, OrderStatus, OrderType, PaymentStatus,
    PaymentServiceRequest, WalletServiceRequest
)

# Import event publishers
from .events.publishers import (
    publish_order_created,
    publish_order_updated,
    publish_order_canceled,
    publish_order_completed,
    publish_order_expired
)

# Import service clients
from .clients import (
    PaymentClient,
    WalletClient,
    AccountClient,
    StorageClient,
    BillingClient
)

logger = logging.getLogger(__name__)


class OrderServiceError(Exception):
    """Base exception for order service errors"""
    pass


class OrderValidationError(OrderServiceError):
    """Order validation error"""
    pass


class OrderNotFoundError(OrderServiceError):
    """Order not found error"""
    pass


class OrderService:
    """
    Order management business logic service

    Handles order lifecycle, payment integration, and wallet communication.
    """

    def __init__(
        self,
        event_bus=None,
        payment_client: Optional[PaymentClient] = None,
        wallet_client: Optional[WalletClient] = None,
        account_client: Optional[AccountClient] = None,
        storage_client: Optional[StorageClient] = None,
        billing_client: Optional[BillingClient] = None
    ):
        """
        Initialize Order Service

        Args:
            event_bus: NATS event bus instance (optional)
            payment_client: Payment service client (optional, dependency injection)
            wallet_client: Wallet service client (optional, dependency injection)
            account_client: Account service client (optional, dependency injection)
            storage_client: Storage service client (optional, dependency injection)
            billing_client: Billing service client (optional, dependency injection)
        """
        self.order_repo = OrderRepository()
        self.repository = self.order_repo  # Alias for consistency
        self.event_bus = event_bus

        # Service clients (dependency injection)
        self.payment_client = payment_client
        self.wallet_client = wallet_client
        self.account_client = account_client
        self.storage_client = storage_client
        self.billing_client = billing_client

        logger.info("✅ OrderService initialized")
        
    # Order Lifecycle Operations
    
    async def create_order(self, request: OrderCreateRequest) -> OrderResponse:
        """
        Create a new order

        Args:
            request: Order creation request

        Returns:
            Order response with success/failure info
        """
        try:
            # Validate request
            self._validate_order_create_request(request)

            # Validate user exists via Account Service (synchronous dependency)
            # Note: In production, you may want to enforce strict validation
            try:
                async with self.account_client as client:
                    user_account = await client.get_account_profile(request.user_id)
                    if not user_account:
                        logger.warning(f"User {request.user_id} not found in Account Service - proceeding anyway (dev/test mode)")
                    else:
                        logger.info(f"User {request.user_id} validated via Account Service for order creation")
            except Exception as e:
                logger.warning(f"Failed to validate user via Account Service: {e}")
                logger.info(f"Proceeding with order creation despite Account Service validation failure")

            # Calculate expiration time
            expires_at = None
            if request.expires_in_minutes:
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=request.expires_in_minutes)
            
            # Create order in database
            order = await self.order_repo.create_order(
                user_id=request.user_id,
                order_type=request.order_type,
                total_amount=request.total_amount,
                currency=request.currency,
                payment_intent_id=request.payment_intent_id,
                subscription_id=request.subscription_id,
                wallet_id=request.wallet_id,
                items=request.items,
                metadata=request.metadata,
                expires_at=expires_at
            )

            # Publish ORDER_CREATED event
            if self.event_bus:
                try:
                    await publish_order_created(
                        event_bus=self.event_bus,
                        order_id=order.order_id,
                        user_id=request.user_id,
                        order_type=request.order_type.value,
                        total_amount=float(request.total_amount),
                        currency=request.currency,
                        payment_intent_id=request.payment_intent_id,
                        items=request.items
                    )
                    logger.info(f"Published order.created event for order {order.order_id}")
                except Exception as e:
                    logger.error(f"Failed to publish order.created event: {e}")

            logger.info(f"Order created: {order.order_id} for user {request.user_id}")

            return OrderResponse(
                success=True,
                order=order,
                message="Order created successfully"
            )
            
        except OrderValidationError as e:
            return OrderResponse(
                success=False,
                message=str(e),
                error_code="VALIDATION_ERROR"
            )
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return OrderResponse(
                success=False,
                message=f"Failed to create order: {str(e)}",
                error_code="CREATE_ERROR"
            )
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        try:
            return await self.order_repo.get_order(order_id)
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            raise OrderServiceError(f"Failed to get order: {str(e)}")
    
    async def update_order(self, order_id: str, request: OrderUpdateRequest) -> OrderResponse:
        """Update order"""
        try:
            # Get existing order
            existing_order = await self.order_repo.get_order(order_id)
            if not existing_order:
                return OrderResponse(
                    success=False,
                    message=f"Order not found: {order_id}",
                    error_code="ORDER_NOT_FOUND"
                )
            
            # Update order
            updated_order = await self.order_repo.update_order(
                order_id=order_id,
                status=request.status,
                payment_status=request.payment_status,
                payment_intent_id=request.payment_intent_id,
                metadata=request.metadata
            )
            
            if updated_order:
                logger.info(f"Order updated: {order_id}")
                return OrderResponse(
                    success=True,
                    order=updated_order,
                    message="Order updated successfully"
                )
            else:
                return OrderResponse(
                    success=False,
                    message="Failed to update order",
                    error_code="UPDATE_ERROR"
                )
                
        except Exception as e:
            logger.error(f"Failed to update order {order_id}: {e}")
            return OrderResponse(
                success=False,
                message=f"Failed to update order: {str(e)}",
                error_code="UPDATE_ERROR"
            )
    
    async def cancel_order(self, order_id: str, request: OrderCancelRequest) -> OrderResponse:
        """Cancel an order"""
        try:
            # Get existing order
            existing_order = await self.order_repo.get_order(order_id)
            if not existing_order:
                return OrderResponse(
                    success=False,
                    message=f"Order not found: {order_id}",
                    error_code="ORDER_NOT_FOUND"
                )
            
            # Check if order can be cancelled
            if existing_order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.REFUNDED]:
                return OrderResponse(
                    success=False,
                    message=f"Cannot cancel order with status: {existing_order.status.value}",
                    error_code="INVALID_STATUS"
                )
            
            # Cancel the order
            success = await self.order_repo.cancel_order(order_id, request.reason)

            if success:
                # If there's a refund amount, process it through wallet service
                if request.refund_amount and request.refund_amount > 0:
                    await self._process_refund(existing_order, request.refund_amount)

                # Publish ORDER_CANCELED event
                if self.event_bus:
                    try:
                        await publish_order_canceled(
                            event_bus=self.event_bus,
                            order_id=order_id,
                            user_id=existing_order.user_id,
                            order_type=existing_order.order_type.value,
                            total_amount=float(existing_order.total_amount),
                            currency=existing_order.currency,
                            reason=request.reason,
                            refund_amount=float(request.refund_amount) if request.refund_amount else 0
                        )
                        logger.info(f"Published order.canceled event for order {order_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish order.canceled event: {e}")

                logger.info(f"Order cancelled: {order_id}, reason: {request.reason}")
                return OrderResponse(
                    success=True,
                    message="Order cancelled successfully"
                )
            else:
                return OrderResponse(
                    success=False,
                    message="Failed to cancel order",
                    error_code="CANCEL_ERROR"
                )
                
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return OrderResponse(
                success=False,
                message=f"Failed to cancel order: {str(e)}",
                error_code="CANCEL_ERROR"
            )
    
    async def complete_order(self, order_id: str, request: OrderCompleteRequest) -> OrderResponse:
        """Complete an order with payment confirmation"""
        try:
            # Get existing order
            existing_order = await self.order_repo.get_order(order_id)
            if not existing_order:
                return OrderResponse(
                    success=False,
                    message=f"Order not found: {order_id}",
                    error_code="ORDER_NOT_FOUND"
                )
            
            # Check payment confirmation
            if not request.payment_confirmed:
                return OrderResponse(
                    success=False,
                    message="Payment not confirmed",
                    error_code="PAYMENT_NOT_CONFIRMED"
                )
            
            # Complete the order
            success = await self.order_repo.complete_order(
                order_id=order_id,
                payment_intent_id=request.transaction_id
            )

            if success:
                # If this is a credit purchase, add credits to wallet
                if (existing_order.order_type == OrderType.CREDIT_PURCHASE and
                    existing_order.wallet_id and request.credits_added):

                    await self._add_credits_to_wallet(
                        user_id=existing_order.user_id,
                        wallet_id=existing_order.wallet_id,
                        amount=request.credits_added,
                        order_id=order_id
                    )

                # Publish ORDER_COMPLETED event
                if self.event_bus:
                    try:
                        await publish_order_completed(
                            event_bus=self.event_bus,
                            order_id=order_id,
                            user_id=existing_order.user_id,
                            order_type=existing_order.order_type.value,
                            total_amount=float(existing_order.total_amount),
                            currency=existing_order.currency,
                            transaction_id=request.transaction_id,
                            credits_added=request.credits_added if request.credits_added else 0
                        )
                        logger.info(f"Published order.completed event for order {order_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish order.completed event: {e}")

                logger.info(f"Order completed: {order_id}")
                return OrderResponse(
                    success=True,
                    message="Order completed successfully"
                )
            else:
                return OrderResponse(
                    success=False,
                    message="Failed to complete order",
                    error_code="COMPLETE_ERROR"
                )
                
        except Exception as e:
            logger.error(f"Failed to complete order {order_id}: {e}")
            return OrderResponse(
                success=False,
                message=f"Failed to complete order: {str(e)}",
                error_code="COMPLETE_ERROR"
            )
    
    # Order Query Operations
    
    async def list_orders(self, filter_params: OrderFilter) -> OrderListResponse:
        """List orders with filtering"""
        try:
            orders = await self.order_repo.list_orders(
                limit=filter_params.limit,
                offset=filter_params.offset,
                user_id=filter_params.user_id,
                order_type=filter_params.order_type,
                status=filter_params.status,
                payment_status=filter_params.payment_status
            )
            
            # For simplicity, assume we got all available orders
            total_count = len(orders)
            has_next = len(orders) == filter_params.limit
            
            return OrderListResponse(
                orders=orders,
                total_count=total_count,
                page=(filter_params.offset // filter_params.limit) + 1,
                page_size=filter_params.limit,
                has_next=has_next
            )
            
        except Exception as e:
            logger.error(f"Failed to list orders: {e}")
            raise OrderServiceError(f"Failed to list orders: {str(e)}")
    
    async def get_user_orders(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Order]:
        """Get orders for a specific user"""
        try:
            return await self.order_repo.get_user_orders(user_id, limit, offset)
        except Exception as e:
            logger.error(f"Failed to get user orders for {user_id}: {e}")
            raise OrderServiceError(f"Failed to get user orders: {str(e)}")
    
    async def search_orders(self, params: OrderSearchParams) -> List[Order]:
        """Search orders"""
        try:
            return await self.order_repo.search_orders(
                query=params.query,
                limit=params.limit,
                user_id=params.user_id
            )
        except Exception as e:
            logger.error(f"Failed to search orders: {e}")
            raise OrderServiceError(f"Failed to search orders: {str(e)}")
    
    # Service Integration Methods
    
    async def _create_payment_intent(self, order: Order) -> Optional[str]:
        """Create payment intent with payment service"""
        try:
            payment_request = PaymentServiceRequest(
                amount=order.total_amount,
                currency=order.currency,
                description=f"Order {order.order_id}",
                user_id=order.user_id,
                order_id=order.order_id,
                metadata={"order_type": order.order_type.value}
            )
            
            payment_service_url = self._get_service_url("payment_service", 8207)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{payment_service_url}/api/payments/intent",
                    json=payment_request.dict(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("payment_intent_id")
                else:
                    logger.error(f"Payment service error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to create payment intent: {e}")
            return None
    
    async def _add_credits_to_wallet(
        self,
        user_id: str,
        wallet_id: str,
        amount: Decimal,
        order_id: str
    ) -> bool:
        """Add credits to user wallet"""
        try:
            wallet_request = WalletServiceRequest(
                user_id=user_id,
                amount=amount,
                order_id=order_id,
                description=f"Credits from order {order_id}",
                transaction_type="deposit"
            )

            wallet_service_url = self._get_service_url("wallet_service", 8209)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{wallet_service_url}/api/v1/wallets/{wallet_id}/deposit",
                    json=wallet_request.dict(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("success", False)
                else:
                    logger.error(f"Wallet service error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to add credits to wallet: {e}")
            return False
    
    async def _process_refund(self, order: Order, refund_amount: Decimal) -> bool:
        """Process refund through wallet service"""
        try:
            if order.wallet_id:
                # Refund to wallet
                wallet_request = WalletServiceRequest(
                    user_id=order.user_id,
                    amount=refund_amount,
                    order_id=order.order_id,
                    description=f"Refund for order {order.order_id}",
                    transaction_type="refund"
                )

                wallet_service_url = self._get_service_url("wallet_service", 8209)

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{wallet_service_url}/api/v1/wallets/{order.wallet_id}/deposit",
                        json=wallet_request.dict(),
                        timeout=30.0
                    )
                    
                    return response.status_code == 200
            
            return True  # No wallet refund needed
            
        except Exception as e:
            logger.error(f"Failed to process refund: {e}")
            return False
    
    # Service Operations
    
    async def get_order_statistics(self) -> OrderStatistics:
        """Get order service statistics"""
        try:
            stats_data = await self.order_repo.get_order_statistics()
            return OrderStatistics(**stats_data)
        except Exception as e:
            logger.error(f"Failed to get order statistics: {e}")
            raise OrderServiceError(f"Failed to get order statistics: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the service"""
        try:
            # Try to get statistics to test database connectivity
            await self.order_repo.get_order_statistics()
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    # Private Helper Methods
    
    def _validate_order_create_request(self, request: OrderCreateRequest) -> None:
        """Validate order creation request"""
        if not request.user_id or not request.user_id.strip():
            raise OrderValidationError("user_id is required")
        
        if request.total_amount <= 0:
            raise OrderValidationError("total_amount must be positive")
        
        if request.order_type == OrderType.CREDIT_PURCHASE and not request.wallet_id:
            raise OrderValidationError("wallet_id is required for credit purchases")
        
        if request.order_type == OrderType.SUBSCRIPTION and not request.subscription_id:
            raise OrderValidationError("subscription_id is required for subscription orders")