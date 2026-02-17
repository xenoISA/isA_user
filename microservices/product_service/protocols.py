"""
Product Service Protocols (Interfaces)

These interfaces define contracts for dependency injection.
NO import-time I/O dependencies - safe to import anywhere.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime
from decimal import Decimal

# Import only models (no I/O dependencies)
from .models import (
    Product,
    ProductCategory,
    PricingModel,
    ServicePlan,
    UserSubscription,
    ProductUsageRecord,
    ProductType,
    SubscriptionStatus,
    BillingCycle,
)


class ProductNotFoundError(Exception):
    """Product not found error"""
    pass


class SubscriptionNotFoundError(Exception):
    """Subscription not found error"""
    pass


class PlanNotFoundError(Exception):
    """Service plan not found error"""
    pass


class UsageRecordingError(Exception):
    """Usage recording error"""
    pass


@runtime_checkable
class ProductRepositoryProtocol(Protocol):
    """
    Interface for Product Repository.

    Implementations must provide these methods.
    Used for dependency injection to enable testing.
    """

    # ==================== Product Operations ====================

    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        ...

    async def get_products(
        self,
        category: Optional[str] = None,
        product_type: Optional[ProductType] = None,
        is_active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Product]:
        """Get products with filters"""
        ...

    async def create_product(self, product: Product) -> Optional[Product]:
        """Create new product"""
        ...

    async def update_product(
        self, product_id: str, updates: Dict[str, Any]
    ) -> Optional[Product]:
        """Update product"""
        ...

    async def delete_product(self, product_id: str) -> bool:
        """Delete product"""
        ...

    # ==================== Category Operations ====================

    async def get_categories(self) -> List[ProductCategory]:
        """Get all product categories"""
        ...

    # ==================== Pricing Operations ====================

    async def get_product_pricing(
        self,
        product_id: str,
        user_id: Optional[str] = None,
        subscription_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get product pricing information"""
        ...

    # ==================== Service Plan Operations ====================

    async def get_service_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get service plan by ID"""
        ...

    # ==================== Subscription Operations ====================

    async def create_subscription(
        self, subscription: UserSubscription
    ) -> UserSubscription:
        """Create new subscription"""
        ...

    async def get_subscription(
        self, subscription_id: str
    ) -> Optional[UserSubscription]:
        """Get subscription by ID"""
        ...

    async def update_subscription_status(
        self, subscription_id: str, new_status: str
    ) -> bool:
        """Update subscription status"""
        ...

    async def get_user_subscriptions(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get subscriptions for user"""
        ...

    # ==================== Usage Records Operations ====================

    async def record_product_usage(
        self,
        user_id: str,
        organization_id: Optional[str],
        subscription_id: Optional[str],
        product_id: str,
        usage_amount: Any,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        usage_details: Optional[Dict[str, Any]] = None,
        usage_timestamp: Optional[datetime] = None
    ) -> str:
        """Record product usage, returns usage_record_id"""
        ...

    async def get_usage_records(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get usage records with filters"""
        ...

    # ==================== Statistics Operations ====================

    async def get_usage_statistics(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        product_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get usage statistics"""
        ...

    # ==================== Lifecycle Operations ====================

    async def initialize(self) -> None:
        """Initialize repository"""
        ...

    async def close(self) -> None:
        """Close repository connections"""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus - no I/O imports"""

    async def publish_event(self, event: Any) -> None:
        """Publish an event"""
        ...

    async def subscribe_to_events(
        self, pattern: str, handler: Any
    ) -> None:
        """Subscribe to events matching pattern"""
        ...

    async def close(self) -> None:
        """Close event bus connection"""
        ...


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for Account Service Client"""

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        ...

    async def validate_user(self, user_id: str) -> bool:
        """Validate user exists"""
        ...

    async def close(self) -> None:
        """Close client connection"""
        ...


@runtime_checkable
class OrganizationClientProtocol(Protocol):
    """Interface for Organization Service Client"""

    async def get_organization(
        self, organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get organization by ID"""
        ...

    async def validate_organization(self, organization_id: str) -> bool:
        """Validate organization exists"""
        ...

    async def close(self) -> None:
        """Close client connection"""
        ...
