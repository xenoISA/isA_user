"""
Credit Service Protocols

Defines interfaces for dependency injection and testing.
Following the protocol-based architecture pattern.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ====================
# Repository Protocol
# ====================


@runtime_checkable
class CreditRepositoryProtocol(Protocol):
    """Repository interface for credit operations"""

    async def create_account(self, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new credit account.

        Args:
            account_data: Dictionary containing account fields (user_id, credit_type, etc.)

        Returns:
            Created account record or None if creation failed
        """
        ...

    async def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Get account by ID.

        Args:
            account_id: Unique account identifier

        Returns:
            Account record or None if not found
        """
        ...

    async def get_account_by_user_type(self, user_id: str, credit_type: str) -> Optional[Dict[str, Any]]:
        """
        Get account by user and type.

        Args:
            user_id: User identifier
            credit_type: Type of credit (bonus, subscription, referral, etc.)

        Returns:
            Account record or None if not found
        """
        ...

    async def get_user_accounts(self, user_id: str, filters: Dict) -> List[Dict[str, Any]]:
        """
        Get all accounts for user.

        Args:
            user_id: User identifier
            filters: Optional filters (credit_type, is_active, etc.)

        Returns:
            List of account records
        """
        ...

    async def update_account_balance(self, account_id: str, balance_delta: int) -> bool:
        """
        Update account balance atomically.

        Args:
            account_id: Account identifier
            balance_delta: Amount to add (positive) or subtract (negative)

        Returns:
            True if update successful, False otherwise
        """
        ...

    async def create_transaction(self, txn_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create transaction record.

        Args:
            txn_data: Transaction data (account_id, amount, type, etc.)

        Returns:
            Created transaction record or None if creation failed
        """
        ...

    async def get_user_transactions(self, user_id: str, filters: Dict) -> List[Dict[str, Any]]:
        """
        Get transactions for user.

        Args:
            user_id: User identifier
            filters: Optional filters (transaction_type, date range, etc.)

        Returns:
            List of transaction records
        """
        ...

    async def create_allocation(self, alloc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create allocation record.

        Args:
            alloc_data: Allocation data (campaign_id, user_id, amount, etc.)

        Returns:
            Created allocation record or None if creation failed
        """
        ...

    async def get_expiring_allocations(self, before: datetime) -> List[Dict[str, Any]]:
        """
        Get allocations expiring before date.

        Args:
            before: Datetime threshold for expiration

        Returns:
            List of expiring allocation records
        """
        ...

    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create campaign.

        Args:
            campaign_data: Campaign data (name, credit_type, budget, etc.)

        Returns:
            Created campaign record or None if creation failed
        """
        ...

    async def get_campaign_by_id(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """
        Get campaign by ID.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Campaign record or None if not found
        """
        ...

    async def update_campaign_budget(self, campaign_id: str, amount: int) -> bool:
        """
        Update campaign allocated_amount.

        Args:
            campaign_id: Campaign identifier
            amount: Amount to add to allocated_amount

        Returns:
            True if update successful, False otherwise
        """
        ...

    async def get_aggregated_balance(self, user_id: str) -> Dict[str, int]:
        """
        Get aggregated balance by credit type.

        Args:
            user_id: User identifier

        Returns:
            Dictionary mapping credit_type to balance
        """
        ...

    async def delete_user_data(self, user_id: str) -> int:
        """
        Delete all user data (GDPR).

        Args:
            user_id: User identifier

        Returns:
            Number of records deleted
        """
        ...


# ====================
# Event Bus Protocol
# ====================


@runtime_checkable
class EventBusProtocol(Protocol):
    """Event bus interface for publishing events"""

    async def publish(self, subject: str, data: Dict[str, Any]) -> None:
        """
        Publish event to NATS.

        Args:
            subject: Event subject/topic
            data: Event payload
        """
        ...


# ====================
# Service Client Protocols
# ====================


@runtime_checkable
class AccountClientProtocol(Protocol):
    """Interface for account_service client"""

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user from account_service.

        Args:
            user_id: User identifier

        Returns:
            User record or None if not found
        """
        ...

    async def validate_user(self, user_id: str) -> bool:
        """
        Validate user exists and is active.

        Args:
            user_id: User identifier

        Returns:
            True if user exists and is active, False otherwise
        """
        ...


@runtime_checkable
class SubscriptionClientProtocol(Protocol):
    """Interface for subscription_service client"""

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get active subscription for user.

        Args:
            user_id: User identifier

        Returns:
            Subscription record or None if not found
        """
        ...

    async def get_subscription_credits(self, subscription_id: str) -> Optional[int]:
        """
        Get credits included in subscription.

        Args:
            subscription_id: Subscription identifier

        Returns:
            Number of credits included or None if subscription not found
        """
        ...


# ====================
# Custom Exceptions (no I/O operations)
# ====================


class CreditServiceError(Exception):
    """Base exception for credit service errors"""
    pass


class CreditAccountNotFoundError(CreditServiceError):
    """Raised when credit account is not found"""
    pass


class InsufficientCreditsError(CreditServiceError):
    """Raised when user has insufficient credits"""

    def __init__(
        self,
        message: str,
        available: Optional[int] = None,
        required: Optional[int] = None,
    ):
        super().__init__(message)
        self.available = available
        self.required = required


class CampaignBudgetExhaustedError(CreditServiceError):
    """Raised when campaign budget is exhausted"""

    def __init__(
        self,
        message: str,
        campaign_id: Optional[str] = None,
        total_budget: Optional[int] = None,
        allocated_amount: Optional[int] = None,
    ):
        super().__init__(message)
        self.campaign_id = campaign_id
        self.total_budget = total_budget
        self.allocated_amount = allocated_amount


class CampaignNotFoundError(CreditServiceError):
    """Raised when campaign is not found"""
    pass


class CampaignInactiveError(CreditServiceError):
    """Raised when campaign is inactive or expired"""
    pass


class InvalidCreditTypeError(CreditServiceError):
    """Raised when credit type is invalid"""
    pass


class CreditAllocationFailedError(CreditServiceError):
    """Raised when credit allocation fails"""

    def __init__(self, message: str, reason: Optional[str] = None):
        super().__init__(message)
        self.reason = reason


class CreditConsumptionFailedError(CreditServiceError):
    """Raised when credit consumption fails"""

    def __init__(self, message: str, reason: Optional[str] = None):
        super().__init__(message)
        self.reason = reason


class CreditTransferFailedError(CreditServiceError):
    """Raised when credit transfer fails"""

    def __init__(self, message: str, reason: Optional[str] = None):
        super().__init__(message)
        self.reason = reason


class UserValidationFailedError(CreditServiceError):
    """Raised when user validation fails"""
    pass


__all__ = [
    "CreditRepositoryProtocol",
    "EventBusProtocol",
    "AccountClientProtocol",
    "SubscriptionClientProtocol",
    "CreditServiceError",
    "CreditAccountNotFoundError",
    "InsufficientCreditsError",
    "CampaignBudgetExhaustedError",
    "CampaignNotFoundError",
    "CampaignInactiveError",
    "InvalidCreditTypeError",
    "CreditAllocationFailedError",
    "CreditConsumptionFailedError",
    "CreditTransferFailedError",
    "UserValidationFailedError",
]
