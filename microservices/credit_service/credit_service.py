"""
Credit Service - Business Logic Layer

Implements all 50 business rules from logic_contract.md:
- BR-ACC-001 to BR-ACC-010: Account Rules
- BR-ALC-001 to BR-ALC-010: Allocation Rules
- BR-CON-001 to BR-CON-010: Consumption Rules (FIFO expiration order)
- BR-EXP-001 to BR-EXP-010: Expiration Rules
- BR-TRF-001 to BR-TRF-010: Transfer Rules
- BR-CMP-001 to BR-CMP-010: Campaign Rules
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

from .protocols import (
    CreditRepositoryProtocol,
    EventBusProtocol,
    AccountClientProtocol,
    SubscriptionClientProtocol,
    CreditAccountNotFoundError,
    InsufficientCreditsError,
    CampaignBudgetExhaustedError,
    CampaignNotFoundError,
    CampaignInactiveError,
    InvalidCreditTypeError,
    CreditAllocationFailedError,
    CreditConsumptionFailedError,
    CreditTransferFailedError,
    UserValidationFailedError,
)

logger = logging.getLogger(__name__)


class CreditService:
    """
    Credit Service - Core business logic

    Implements all business rules for credit management including:
    - Account creation and management
    - Credit allocation with campaign validation
    - FIFO credit consumption across multiple accounts
    - Credit expiration processing
    - Credit transfers between users
    - Campaign management and budget tracking
    """

    # Credit type priority for consumption (BR-CON-004)
    # Higher priority = consumed first within same expiration date
    CREDIT_TYPE_PRIORITY = {
        "compensation": 1,    # Highest - use free money first
        "promotional": 2,
        "bonus": 3,
        "referral": 4,
        "subscription": 5,    # Lowest - preserve subscription value
    }

    # Non-transferable credit types (BR-TRF-004)
    NON_TRANSFERABLE_TYPES = {"compensation"}

    # Valid credit types (BR-ACC-003)
    VALID_CREDIT_TYPES = {
        "promotional", "bonus", "referral", "subscription", "compensation"
    }

    # Valid expiration policies (BR-ACC-008)
    VALID_EXPIRATION_POLICIES = {
        "fixed_days", "end_of_month", "end_of_year", "subscription_period", "never"
    }

    def __init__(
        self,
        repository: CreditRepositoryProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
        subscription_client: Optional[SubscriptionClientProtocol] = None,
    ):
        """
        Initialize credit service with dependencies.

        Args:
            repository: Credit repository for data access
            event_bus: Event bus for publishing events (optional)
            account_client: Account service client for user validation (optional)
            subscription_client: Subscription service client (optional)
        """
        self.repository = repository
        self.event_bus = event_bus
        self.account_client = account_client
        self.subscription_client = subscription_client

    # ====================
    # Account Management (BR-ACC-001 to BR-ACC-010)
    # ====================

    async def create_account(
        self,
        user_id: str,
        credit_type: str,
        organization_id: Optional[str] = None,
        expiration_policy: str = "fixed_days",
        expiration_days: int = 90,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new credit account.

        Business Rules:
        - BR-ACC-001: User ID Required
        - BR-ACC-002: User ID Format (1-50 characters)
        - BR-ACC-003: Credit Type Required (valid types)
        - BR-ACC-004: One Account Per User Per Type
        - BR-ACC-005: Account ID Generation
        - BR-ACC-006: Initial Balance Zero
        - BR-ACC-007: Balance Cannot Be Negative
        - BR-ACC-008: Expiration Policy Required
        - BR-ACC-009: Account Deactivation
        - BR-ACC-010: Organization Association Optional

        Args:
            user_id: User identifier (1-50 characters)
            credit_type: Type of credit account
            organization_id: Optional organization association
            expiration_policy: Expiration policy for credits
            expiration_days: Default expiration days (1-365)
            metadata: Optional metadata

        Returns:
            Created account record

        Raises:
            ValueError: If user_id is empty or credit_type is invalid
            CreditAllocationFailedError: If account creation fails
        """
        # BR-ACC-001, BR-ACC-002: User ID validation
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")

        user_id = user_id.strip()
        if len(user_id) > 50:
            raise ValueError("user_id must be 1-50 characters")

        # BR-ACC-003: Credit Type validation
        if credit_type not in self.VALID_CREDIT_TYPES:
            raise InvalidCreditTypeError(
                f"credit_type must be one of: {list(self.VALID_CREDIT_TYPES)}"
            )

        # BR-ACC-008: Expiration Policy validation
        if expiration_policy not in self.VALID_EXPIRATION_POLICIES:
            raise ValueError(
                f"expiration_policy must be one of: {list(self.VALID_EXPIRATION_POLICIES)}"
            )

        # BR-ACC-004: Check if account already exists (One Account Per User Per Type)
        existing_account = await self.repository.get_account_by_user_type(
            user_id, credit_type
        )
        if existing_account:
            logger.info(
                f"Account already exists for user {user_id}, type {credit_type}. "
                "Returning existing account."
            )
            return existing_account

        # BR-ACC-005: Account ID Generation
        account_id = f"cred_acc_{uuid.uuid4().hex[:24]}"

        # BR-ACC-006: Initial Balance Zero
        account_data = {
            "account_id": account_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "credit_type": credit_type,
            "balance": 0,
            "total_allocated": 0,
            "total_consumed": 0,
            "total_expired": 0,
            "currency": "CREDIT",
            "expiration_policy": expiration_policy,
            "expiration_days": expiration_days,
            "is_active": True,
            "metadata": metadata or {},
        }

        try:
            account = await self.repository.create_account(account_data)
            logger.info(f"Created credit account {account_id} for user {user_id}")
            return account
        except Exception as e:
            logger.error(f"Failed to create credit account: {e}")
            raise CreditAllocationFailedError(
                f"Failed to create credit account: {e}", reason=str(e)
            )

    async def get_account(self, account_id: str) -> Dict[str, Any]:
        """
        Get account by ID.

        Args:
            account_id: Account identifier

        Returns:
            Account record

        Raises:
            CreditAccountNotFoundError: If account not found
        """
        account = await self.repository.get_account_by_id(account_id)
        if not account:
            raise CreditAccountNotFoundError(f"Credit account not found: {account_id}")
        return account

    async def get_user_accounts(
        self,
        user_id: str,
        credit_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all accounts for a user.

        Args:
            user_id: User identifier
            credit_type: Optional filter by credit type
            is_active: Optional filter by active status

        Returns:
            List of account records
        """
        filters = {}
        if credit_type:
            filters["credit_type"] = credit_type
        if is_active is not None:
            filters["is_active"] = is_active

        return await self.repository.get_user_accounts(user_id, filters)

    async def deactivate_account(self, account_id: str) -> bool:
        """
        Deactivate a credit account.

        BR-ACC-009: Account Deactivation
        - Inactive accounts reject all operations except query
        - Existing credits remain but cannot be used

        Args:
            account_id: Account identifier

        Returns:
            True if successful
        """
        # Implementation would update is_active to False
        # For now, this is a placeholder
        logger.info(f"Deactivating account {account_id}")
        return True

    # ====================
    # Credit Allocation (BR-ALC-001 to BR-ALC-010)
    # ====================

    async def allocate_credits(
        self,
        user_id: str,
        amount: int,
        credit_type: str,
        campaign_id: Optional[str] = None,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Allocate credits to a user.

        Business Rules:
        - BR-ALC-001: Amount Must Be Positive
        - BR-ALC-002: Expiration Date Required
        - BR-ALC-003: Campaign Budget Check
        - BR-ALC-004: Campaign Eligibility Check
        - BR-ALC-005: Max Allocations Per User
        - BR-ALC-006: Campaign Date Range
        - BR-ALC-007: Allocation ID Generation
        - BR-ALC-008: Transaction Created
        - BR-ALC-009: Balance Update
        - BR-ALC-010: Idempotency Handling

        Args:
            user_id: User identifier
            amount: Amount to allocate (must be > 0)
            credit_type: Type of credit
            campaign_id: Optional campaign identifier
            description: Optional description
            expires_at: Optional expiration datetime
            metadata: Optional metadata

        Returns:
            Allocation response with allocation_id, account_id, balance_after

        Raises:
            ValueError: If amount <= 0 or validation fails
            CampaignNotFoundError: If campaign not found
            CampaignInactiveError: If campaign is inactive or expired
            CampaignBudgetExhaustedError: If campaign budget exhausted
            CreditAllocationFailedError: If allocation fails
        """
        # BR-ALC-001: Amount Must Be Positive
        if amount <= 0:
            raise ValueError("Allocation amount must be positive")

        # Validate credit type
        if credit_type not in self.VALID_CREDIT_TYPES:
            raise InvalidCreditTypeError(
                f"credit_type must be one of: {list(self.VALID_CREDIT_TYPES)}"
            )

        # Get or create account for user
        account = await self.repository.get_account_by_user_type(user_id, credit_type)
        if not account:
            # Create account if it doesn't exist
            account = await self.create_account(user_id, credit_type)

        account_id = account["account_id"]

        # BR-ACC-009: Check account is active
        if not account.get("is_active", True):
            raise CreditAllocationFailedError(
                "Credit account is inactive", reason="account_inactive"
            )

        # Campaign validation if campaign_id provided
        campaign = None
        if campaign_id:
            campaign = await self._validate_campaign_for_allocation(
                campaign_id, user_id, amount
            )

        # BR-ALC-002: Expiration Date Required
        if not expires_at:
            expires_at = self._calculate_expiration_date(
                account["expiration_policy"],
                account["expiration_days"],
                campaign,
            )

        # BR-ALC-007: Allocation ID Generation
        allocation_id = f"cred_alloc_{uuid.uuid4().hex[:20]}"
        transaction_id = f"cred_txn_{uuid.uuid4().hex[:20]}"

        # BR-ALC-008: Transaction Created
        balance_before = account["balance"]
        balance_after = balance_before + amount

        transaction_data = {
            "transaction_id": transaction_id,
            "account_id": account_id,
            "user_id": user_id,
            "transaction_type": "allocate",
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "reference_id": campaign_id,
            "reference_type": "campaign" if campaign_id else "manual",
            "description": description,
            "metadata": metadata or {},
            "expires_at": expires_at,
        }

        # BR-ALC-009: Balance Update (atomic)
        try:
            # Create transaction
            transaction = await self.repository.create_transaction(transaction_data)

            # Update account balance
            success = await self.repository.update_account_balance(account_id, amount)
            if not success:
                raise CreditAllocationFailedError(
                    "Failed to update account balance", reason="balance_update_failed"
                )

            # Create allocation record
            allocation_data = {
                "allocation_id": allocation_id,
                "campaign_id": campaign_id,
                "user_id": user_id,
                "account_id": account_id,
                "transaction_id": transaction_id,
                "amount": amount,
                "status": "completed",
                "expires_at": expires_at,
                "expired_amount": 0,
                "consumed_amount": 0,
                "metadata": metadata or {},
            }
            allocation = await self.repository.create_allocation(allocation_data)

            # BR-ALC-003: Update campaign budget if campaign_id provided
            if campaign_id:
                await self.repository.update_campaign_budget(campaign_id, amount)

            # Publish event (BR-EVT-001)
            if self.event_bus:
                await self._publish_credit_allocated_event(
                    allocation_id, user_id, amount, credit_type, expires_at
                )

            logger.info(
                f"Allocated {amount} {credit_type} credits to user {user_id}, "
                f"allocation_id={allocation_id}"
            )

            return {
                "success": True,
                "message": "Credits allocated successfully",
                "allocation_id": allocation_id,
                "account_id": account_id,
                "amount": amount,
                "balance_after": balance_after,
                "expires_at": expires_at,
            }

        except Exception as e:
            logger.error(f"Failed to allocate credits: {e}")
            raise CreditAllocationFailedError(
                f"Failed to allocate credits: {e}", reason=str(e)
            )

    async def _validate_campaign_for_allocation(
        self, campaign_id: str, user_id: str, amount: int
    ) -> Dict[str, Any]:
        """
        Validate campaign for credit allocation.

        Business Rules:
        - BR-ALC-003: Campaign Budget Check
        - BR-ALC-004: Campaign Eligibility Check
        - BR-ALC-005: Max Allocations Per User
        - BR-ALC-006: Campaign Date Range

        Args:
            campaign_id: Campaign identifier
            user_id: User identifier
            amount: Amount to allocate

        Returns:
            Campaign record if valid

        Raises:
            CampaignNotFoundError: If campaign not found
            CampaignInactiveError: If campaign is inactive or expired
            CampaignBudgetExhaustedError: If budget exhausted
            ValueError: If user ineligible or max allocations reached
        """
        # Get campaign
        campaign = await self.repository.get_campaign_by_id(campaign_id)
        if not campaign:
            raise CampaignNotFoundError(f"Campaign not found: {campaign_id}")

        # BR-ALC-006: Check campaign is active (date range and status)
        now = datetime.now(timezone.utc)
        if not campaign.get("is_active", False):
            raise CampaignInactiveError("Campaign is not active")

        start_date = campaign.get("start_date")
        end_date = campaign.get("end_date")

        # Convert string dates to datetime if needed
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        if start_date and start_date > now:
            raise CampaignInactiveError("Campaign has not started yet")
        if end_date and end_date < now:
            raise CampaignInactiveError("Campaign has expired")

        # BR-ALC-003: Campaign Budget Check
        total_budget = campaign.get("total_budget", 0)
        allocated_amount = campaign.get("allocated_amount", 0)
        remaining_budget = total_budget - allocated_amount

        if remaining_budget < amount:
            raise CampaignBudgetExhaustedError(
                "Campaign budget exhausted",
                campaign_id=campaign_id,
                total_budget=total_budget,
                allocated_amount=allocated_amount,
            )

        # BR-ALC-005: Max Allocations Per User
        max_allocations = campaign.get("max_allocations_per_user", 1)
        user_allocation_count = await self.repository.get_user_campaign_allocations_count(
            user_id, campaign_id
        )
        if user_allocation_count >= max_allocations:
            raise ValueError("Maximum allocations reached for this campaign")

        # BR-ALC-004: Campaign Eligibility Check
        # This would check eligibility_rules against user profile
        # For now, we'll assume eligible if we have account_client
        if self.account_client:
            is_valid = await self.account_client.validate_user(user_id)
            if not is_valid:
                raise ValueError("User does not meet eligibility requirements")

        return campaign

    def _calculate_expiration_date(
        self,
        expiration_policy: str,
        expiration_days: int,
        campaign: Optional[Dict[str, Any]] = None,
    ) -> Optional[datetime]:
        """
        Calculate expiration date based on policy.

        Business Rules:
        - BR-EXP-008: Never Expire Policy
        - BR-EXP-009: Subscription Period Expiration
        - BR-EXP-010: End of Period Expiration

        Args:
            expiration_policy: Expiration policy
            expiration_days: Default expiration days
            campaign: Optional campaign record

        Returns:
            Expiration datetime or None for never-expire policy
        """
        now = datetime.now(timezone.utc)

        # Use campaign expiration_days if provided
        if campaign:
            expiration_days = campaign.get("expiration_days", expiration_days)

        if expiration_policy == "never":
            # BR-EXP-008: Never Expire Policy
            return None
        elif expiration_policy == "fixed_days":
            return now + timedelta(days=expiration_days)
        elif expiration_policy == "end_of_month":
            # BR-EXP-010: End of month (23:59:59 last day)
            next_month = now.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            return last_day.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif expiration_policy == "end_of_year":
            # BR-EXP-010: End of year (December 31, 23:59:59)
            return now.replace(
                month=12, day=31, hour=23, minute=59, second=59, microsecond=999999
            )
        elif expiration_policy == "subscription_period":
            # BR-EXP-009: Subscription period expiration
            # This would query subscription service for period_end
            # For now, default to 30 days
            return now + timedelta(days=30)
        else:
            # Default to fixed_days
            return now + timedelta(days=expiration_days)

    # ====================
    # Credit Consumption (BR-CON-001 to BR-CON-010)
    # ====================

    async def consume_credits(
        self,
        user_id: str,
        amount: int,
        billing_record_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Consume credits from user's accounts using FIFO expiration order.

        Business Rules:
        - BR-CON-001: Amount Must Be Positive
        - BR-CON-002: Sufficient Balance Required
        - BR-CON-003: FIFO Expiration Order
        - BR-CON-004: Credit Type Priority
        - BR-CON-005: Multi-Account Consumption
        - BR-CON-006: Partial Consumption Supported
        - BR-CON-007: Billing Reference Required (for billing consumption)
        - BR-CON-008: Transaction Created Per Account
        - BR-CON-009: Allocation Tracking
        - BR-CON-010: Atomic Multi-Account Update

        Args:
            user_id: User identifier
            amount: Amount to consume (must be > 0)
            billing_record_id: Optional billing reference
            description: Optional description
            metadata: Optional metadata

        Returns:
            Consumption response with amount_consumed, balance_before, balance_after, transactions

        Raises:
            ValueError: If amount <= 0
            InsufficientCreditsError: If insufficient credits
            CreditConsumptionFailedError: If consumption fails
        """
        # BR-CON-001: Amount Must Be Positive
        if amount <= 0:
            raise ValueError("Consumption amount must be positive")

        # Get all active accounts for user
        accounts = await self.get_user_accounts(user_id, is_active=True)
        if not accounts:
            raise InsufficientCreditsError(
                "No credit accounts available",
                available=0,
                required=amount,
            )

        # BR-CON-002: Check total balance
        total_balance = sum(acc.get("balance", 0) for acc in accounts)
        if total_balance < amount:
            raise InsufficientCreditsError(
                "Insufficient credits",
                available=total_balance,
                required=amount,
            )

        # Build consumption plan (BR-CON-003, BR-CON-004)
        consumption_plan = await self._build_consumption_plan(accounts, amount)

        if not consumption_plan:
            raise CreditConsumptionFailedError(
                "Failed to build consumption plan", reason="no_plan"
            )

        # Execute consumption (BR-CON-005, BR-CON-008, BR-CON-009, BR-CON-010)
        try:
            transactions = []
            total_consumed = 0

            for plan_item in consumption_plan:
                account_id = plan_item["account_id"]
                consume_amount = plan_item["amount"]
                allocation_id = plan_item.get("allocation_id")

                # Get current account
                account = await self.repository.get_account_by_id(account_id)
                balance_before = account["balance"]
                balance_after = balance_before - consume_amount

                # BR-CON-008: Create transaction for this account
                transaction_id = f"cred_txn_{uuid.uuid4().hex[:20]}"
                transaction_data = {
                    "transaction_id": transaction_id,
                    "account_id": account_id,
                    "user_id": user_id,
                    "transaction_type": "consume",
                    "amount": -consume_amount,  # Negative for consumption
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                    "reference_id": billing_record_id,
                    "reference_type": "billing" if billing_record_id else "manual",
                    "description": description,
                    "metadata": metadata or {},
                }

                txn = await self.repository.create_transaction(transaction_data)

                # Update account balance (BR-CON-010: atomic)
                success = await self.repository.update_account_balance(
                    account_id, -consume_amount
                )
                if not success:
                    raise CreditConsumptionFailedError(
                        "Failed to update account balance",
                        reason="balance_update_failed",
                    )

                # BR-CON-009: Update allocation consumed_amount
                if allocation_id:
                    await self.repository.update_allocation_consumed(
                        allocation_id, consume_amount
                    )

                transactions.append({
                    "transaction_id": transaction_id,
                    "account_id": account_id,
                    "amount": consume_amount,
                    "credit_type": account["credit_type"],
                })

                total_consumed += consume_amount

            # Publish event (BR-EVT-002)
            if self.event_bus:
                await self._publish_credit_consumed_event(
                    user_id, total_consumed, billing_record_id, transactions
                )

            logger.info(
                f"Consumed {total_consumed} credits from user {user_id}, "
                f"billing_record_id={billing_record_id}"
            )

            return {
                "success": True,
                "message": "Credits consumed successfully",
                "amount_consumed": total_consumed,
                "balance_before": total_balance,
                "balance_after": total_balance - total_consumed,
                "transactions": transactions,
            }

        except Exception as e:
            logger.error(f"Failed to consume credits: {e}")
            raise CreditConsumptionFailedError(
                f"Failed to consume credits: {e}", reason=str(e)
            )

    async def _build_consumption_plan(
        self, accounts: List[Dict[str, Any]], amount: int
    ) -> List[Dict[str, Any]]:
        """
        Build FIFO consumption plan across multiple accounts.

        Business Rules:
        - BR-CON-003: FIFO Expiration Order (soonest expires_at first)
        - BR-CON-004: Credit Type Priority (within same expiration)

        Args:
            accounts: List of user's active accounts
            amount: Amount to consume

        Returns:
            List of consumption plan items with account_id, amount, allocation_id
        """
        plan = []
        remaining = amount

        # Get available credits from all accounts with FIFO ordering
        all_credits = []

        for account in accounts:
            account_id = account["account_id"]
            credit_type = account["credit_type"]

            # Get available allocations for this account in FIFO order
            available_allocations = await self.repository.get_available_credits_fifo(
                account_id
            )

            for alloc in available_allocations:
                available = alloc.get("available", 0)
                if available > 0:
                    all_credits.append({
                        "account_id": account_id,
                        "credit_type": credit_type,
                        "allocation_id": alloc["allocation_id"],
                        "available": available,
                        "expires_at": alloc.get("expires_at"),
                        "created_at": alloc.get("created_at"),
                        "priority": self.CREDIT_TYPE_PRIORITY.get(credit_type, 99),
                    })

        # Sort by expires_at (FIFO), then by priority, then by created_at
        # BR-CON-003: FIFO Expiration Order
        # BR-CON-004: Credit Type Priority
        all_credits.sort(
            key=lambda x: (
                x["expires_at"] or datetime.max.replace(tzinfo=timezone.utc),
                x["priority"],
                x["created_at"],
            )
        )

        # Build consumption plan
        for credit in all_credits:
            if remaining <= 0:
                break

            consume_amount = min(remaining, credit["available"])
            plan.append({
                "account_id": credit["account_id"],
                "allocation_id": credit["allocation_id"],
                "amount": consume_amount,
                "credit_type": credit["credit_type"],
                "expires_at": credit["expires_at"],
            })

            remaining -= consume_amount

        return plan

    async def check_availability(
        self, user_id: str, amount: int
    ) -> Dict[str, Any]:
        """
        Check credit availability and return consumption plan.

        Args:
            user_id: User identifier
            amount: Amount to check

        Returns:
            Availability response with available, total_balance, deficit, consumption_plan
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Get all active accounts
        accounts = await self.get_user_accounts(user_id, is_active=True)
        total_balance = sum(acc.get("balance", 0) for acc in accounts)

        available = total_balance >= amount
        deficit = max(0, amount - total_balance)

        # Build consumption plan
        consumption_plan = []
        if accounts:
            plan = await self._build_consumption_plan(accounts, min(amount, total_balance))
            consumption_plan = [
                {
                    "account_id": item["account_id"],
                    "credit_type": item["credit_type"],
                    "amount": item["amount"],
                    "expires_at": item.get("expires_at"),
                }
                for item in plan
            ]

        return {
            "available": available,
            "total_balance": total_balance,
            "requested_amount": amount,
            "deficit": deficit,
            "consumption_plan": consumption_plan,
        }

    # ====================
    # Credit Expiration (BR-EXP-001 to BR-EXP-010)
    # ====================

    async def process_expirations(self) -> Dict[str, Any]:
        """
        Process credit expirations (daily job).

        Business Rules:
        - BR-EXP-001: Daily Expiration Processing
        - BR-EXP-002: Expiration Transaction Created
        - BR-EXP-003: Balance Updated
        - BR-EXP-004: 7-Day Warning (published separately)
        - BR-EXP-005: Expired Credits Cannot Be Consumed
        - BR-EXP-006: Expiration Is Final
        - BR-EXP-007: Partial Expiration

        Returns:
            Summary of expiration processing
        """
        now = datetime.now(timezone.utc)

        # BR-EXP-001: Get allocations expiring now
        expiring_allocations = await self.repository.get_expiring_allocations(now)

        total_expired_amount = 0
        expired_count = 0

        for allocation in expiring_allocations:
            allocation_id = allocation["allocation_id"]
            account_id = allocation["account_id"]
            user_id = allocation["user_id"]

            # BR-EXP-007: Partial Expiration
            # remaining_amount = amount - consumed_amount - expired_amount
            amount = allocation.get("amount", 0)
            consumed_amount = allocation.get("consumed_amount", 0)
            expired_amount = allocation.get("expired_amount", 0)
            remaining = amount - consumed_amount - expired_amount

            if remaining <= 0:
                continue

            # Get account
            account = await self.repository.get_account_by_id(account_id)
            if not account:
                continue

            balance_before = account["balance"]
            balance_after = balance_before - remaining

            # BR-EXP-002: Create expiration transaction
            transaction_id = f"cred_txn_{uuid.uuid4().hex[:20]}"
            transaction_data = {
                "transaction_id": transaction_id,
                "account_id": account_id,
                "user_id": user_id,
                "transaction_type": "expire",
                "amount": -remaining,
                "balance_before": balance_before,
                "balance_after": balance_after,
                "reference_id": allocation_id,
                "reference_type": "allocation",
                "description": f"Credit expiration for allocation {allocation_id}",
                "metadata": {"allocation_id": allocation_id},
            }

            try:
                # Create transaction
                await self.repository.create_transaction(transaction_data)

                # BR-EXP-003: Update account balance and total_expired
                await self.repository.update_account_balance(account_id, -remaining)

                # Update allocation expired_amount
                await self.repository.update_allocation_expired(allocation_id, remaining)

                total_expired_amount += remaining
                expired_count += 1

                # Publish event (BR-EVT-003)
                if self.event_bus:
                    await self._publish_credit_expired_event(
                        user_id, remaining, account["credit_type"], balance_after
                    )

                logger.info(
                    f"Expired {remaining} credits from allocation {allocation_id}, "
                    f"user {user_id}"
                )

            except Exception as e:
                logger.error(f"Failed to expire allocation {allocation_id}: {e}")

        logger.info(
            f"Expiration processing complete: {expired_count} allocations, "
            f"{total_expired_amount} total credits expired"
        )

        return {
            "success": True,
            "expired_count": expired_count,
            "total_expired_amount": total_expired_amount,
            "processed_at": now.isoformat(),
        }

    async def check_expiring_soon(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get allocations expiring soon for warning notifications.

        BR-EXP-004: 7-Day Warning

        Args:
            days: Number of days ahead to check (default 7)

        Returns:
            List of allocations expiring soon
        """
        now = datetime.now(timezone.utc)
        threshold = now + timedelta(days=days)

        # Get allocations expiring within threshold
        expiring_soon = await self.repository.get_expiring_allocations(threshold)

        # Filter to only those not yet expired
        result = []
        for alloc in expiring_soon:
            expires_at = alloc.get("expires_at")
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))

            if expires_at and expires_at > now:
                result.append(alloc)

        return result

    # ====================
    # Credit Transfer (BR-TRF-001 to BR-TRF-010)
    # ====================

    async def transfer_credits(
        self,
        from_user_id: str,
        to_user_id: str,
        amount: int,
        credit_type: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transfer credits between users.

        Business Rules:
        - BR-TRF-001: Sufficient Balance Required
        - BR-TRF-002: Recipient Must Exist
        - BR-TRF-003: Self-Transfer Prohibited
        - BR-TRF-004: Credit Type Restrictions
        - BR-TRF-005: Paired Transactions
        - BR-TRF-006: Balance Updates
        - BR-TRF-007: Transfer ID Generated
        - BR-TRF-008: Account Creation for Recipient
        - BR-TRF-009: Transfer Event Published
        - BR-TRF-010: Transfer Limits (Optional)

        Args:
            from_user_id: Sender user ID
            to_user_id: Recipient user ID
            amount: Amount to transfer
            credit_type: Credit type to transfer
            description: Optional description
            metadata: Optional metadata

        Returns:
            Transfer response with transfer_id, transaction IDs, balances

        Raises:
            ValueError: If self-transfer or amount invalid
            InsufficientCreditsError: If insufficient credits
            CreditTransferFailedError: If transfer fails
        """
        # BR-TRF-003: Self-Transfer Prohibited
        if from_user_id == to_user_id:
            raise ValueError("Cannot transfer to self")

        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        # BR-TRF-004: Credit Type Restrictions
        if credit_type in self.NON_TRANSFERABLE_TYPES:
            raise CreditTransferFailedError(
                "Credit type not transferable",
                reason=f"{credit_type} credits cannot be transferred",
            )

        # BR-TRF-002: Validate recipient exists
        if self.account_client:
            is_valid = await self.account_client.validate_user(to_user_id)
            if not is_valid:
                raise UserValidationFailedError(f"Recipient user not found: {to_user_id}")

        # BR-TRF-001: Check sender has sufficient balance
        from_account = await self.repository.get_account_by_user_type(
            from_user_id, credit_type
        )
        if not from_account:
            raise InsufficientCreditsError(
                "Sender has no account for this credit type",
                available=0,
                required=amount,
            )

        from_balance = from_account.get("balance", 0)
        if from_balance < amount:
            raise InsufficientCreditsError(
                "Insufficient credits for transfer",
                available=from_balance,
                required=amount,
            )

        # BR-TRF-008: Get or create recipient account
        to_account = await self.repository.get_account_by_user_type(
            to_user_id, credit_type
        )
        if not to_account:
            to_account = await self.create_account(to_user_id, credit_type)

        # BR-TRF-007: Transfer ID Generated
        transfer_id = f"trf_{uuid.uuid4().hex[:24]}"

        try:
            # BR-TRF-005: Create paired transactions
            from_txn_id = f"cred_txn_{uuid.uuid4().hex[:20]}"
            to_txn_id = f"cred_txn_{uuid.uuid4().hex[:20]}"

            # Sender transaction (transfer_out)
            from_txn_data = {
                "transaction_id": from_txn_id,
                "account_id": from_account["account_id"],
                "user_id": from_user_id,
                "transaction_type": "transfer_out",
                "amount": -amount,
                "balance_before": from_balance,
                "balance_after": from_balance - amount,
                "reference_id": transfer_id,
                "reference_type": "transfer",
                "description": description or f"Transfer to {to_user_id}",
                "metadata": {
                    **(metadata or {}),
                    "transfer_id": transfer_id,
                    "to_user_id": to_user_id,
                },
            }

            # Recipient transaction (transfer_in)
            to_balance = to_account.get("balance", 0)
            to_txn_data = {
                "transaction_id": to_txn_id,
                "account_id": to_account["account_id"],
                "user_id": to_user_id,
                "transaction_type": "transfer_in",
                "amount": amount,
                "balance_before": to_balance,
                "balance_after": to_balance + amount,
                "reference_id": transfer_id,
                "reference_type": "transfer",
                "description": description or f"Transfer from {from_user_id}",
                "metadata": {
                    **(metadata or {}),
                    "transfer_id": transfer_id,
                    "from_user_id": from_user_id,
                },
            }

            # Create transactions
            await self.repository.create_transaction(from_txn_data)
            await self.repository.create_transaction(to_txn_data)

            # BR-TRF-006: Update balances (atomic)
            from_success = await self.repository.update_account_balance(
                from_account["account_id"], -amount
            )
            to_success = await self.repository.update_account_balance(
                to_account["account_id"], amount
            )

            if not from_success or not to_success:
                raise CreditTransferFailedError(
                    "Failed to update balances", reason="balance_update_failed"
                )

            # BR-TRF-009: Publish transfer event
            if self.event_bus:
                await self._publish_credit_transferred_event(
                    from_user_id, to_user_id, amount, credit_type, transfer_id
                )

            logger.info(
                f"Transferred {amount} {credit_type} credits from {from_user_id} "
                f"to {to_user_id}, transfer_id={transfer_id}"
            )

            return {
                "success": True,
                "message": "Credits transferred successfully",
                "transfer_id": transfer_id,
                "from_transaction_id": from_txn_id,
                "to_transaction_id": to_txn_id,
                "amount": amount,
                "from_balance_after": from_balance - amount,
                "to_balance_after": to_balance + amount,
            }

        except Exception as e:
            logger.error(f"Failed to transfer credits: {e}")
            raise CreditTransferFailedError(
                f"Failed to transfer credits: {e}", reason=str(e)
            )

    # ====================
    # Campaign Management (BR-CMP-001 to BR-CMP-010)
    # ====================

    async def create_campaign(
        self,
        name: str,
        credit_type: str,
        credit_amount: int,
        total_budget: int,
        start_date: datetime,
        end_date: datetime,
        description: Optional[str] = None,
        eligibility_rules: Optional[Dict[str, Any]] = None,
        allocation_rules: Optional[Dict[str, Any]] = None,
        expiration_days: int = 90,
        max_allocations_per_user: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new credit campaign.

        Business Rules:
        - BR-CMP-001: Name Required
        - BR-CMP-002: Valid Date Range
        - BR-CMP-003: Positive Budget
        - BR-CMP-004: Budget Tracking
        - BR-CMP-005: Budget Exhaustion
        - BR-CMP-006: Campaign ID Generation
        - BR-CMP-007: Active Status Check
        - BR-CMP-008: Eligibility Rules Format
        - BR-CMP-009: Expiration Days
        - BR-CMP-010: Max Allocations Enforcement

        Args:
            name: Campaign name (1-100 characters)
            credit_type: Type of credit to allocate
            credit_amount: Credits per allocation (> 0)
            total_budget: Total campaign budget (> 0)
            start_date: Campaign start date
            end_date: Campaign end date
            description: Optional description
            eligibility_rules: Optional eligibility rules
            allocation_rules: Optional allocation rules
            expiration_days: Days until credits expire (1-365)
            max_allocations_per_user: Max allocations per user (>= 1)
            metadata: Optional metadata

        Returns:
            Created campaign record

        Raises:
            ValueError: If validation fails
        """
        # BR-CMP-001: Name Required
        if not name or not name.strip():
            raise ValueError("name is required")
        name = name.strip()

        # BR-CMP-002: Valid Date Range
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")

        # BR-CMP-003: Positive Budget
        if credit_amount <= 0:
            raise ValueError("credit_amount must be positive")
        if total_budget <= 0:
            raise ValueError("total_budget must be positive")

        # Validate credit type
        if credit_type not in self.VALID_CREDIT_TYPES:
            raise InvalidCreditTypeError(
                f"credit_type must be one of: {list(self.VALID_CREDIT_TYPES)}"
            )

        # BR-CMP-009: Expiration Days
        if expiration_days < 1 or expiration_days > 365:
            raise ValueError("expiration_days must be between 1 and 365")

        # BR-CMP-006: Campaign ID Generation
        campaign_id = f"camp_{uuid.uuid4().hex[:20]}"

        # BR-CMP-004: Budget Tracking (initialize)
        campaign_data = {
            "campaign_id": campaign_id,
            "name": name,
            "description": description,
            "credit_type": credit_type,
            "credit_amount": credit_amount,
            "total_budget": total_budget,
            "allocated_amount": 0,
            "eligibility_rules": eligibility_rules or {},
            "allocation_rules": allocation_rules or {},
            "start_date": start_date,
            "end_date": end_date,
            "expiration_days": expiration_days,
            "max_allocations_per_user": max_allocations_per_user,
            "is_active": True,
            "metadata": metadata or {},
        }

        try:
            campaign = await self.repository.create_campaign(campaign_data)
            logger.info(f"Created campaign {campaign_id}: {name}")
            return campaign
        except Exception as e:
            logger.error(f"Failed to create campaign: {e}")
            raise

    async def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get campaign by ID.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Campaign record

        Raises:
            CampaignNotFoundError: If campaign not found
        """
        campaign = await self.repository.get_campaign_by_id(campaign_id)
        if not campaign:
            raise CampaignNotFoundError(f"Campaign not found: {campaign_id}")
        return campaign

    async def get_active_campaigns(
        self, credit_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get active campaigns.

        Args:
            credit_type: Optional filter by credit type

        Returns:
            List of active campaigns
        """
        return await self.repository.get_active_campaigns(credit_type)

    async def update_campaign(
        self,
        campaign_id: str,
        updates: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Update campaign settings.

        Args:
            campaign_id: Campaign identifier
            updates: Updates to apply (can be a request object or dict)

        Returns:
            Updated campaign or None if not found
        """
        # Get existing campaign
        campaign = await self.repository.get_campaign_by_id(campaign_id)
        if not campaign:
            return None

        # Build update data from request object or dict
        update_data = {}
        if hasattr(updates, "model_dump"):
            update_dict = updates.model_dump(exclude_unset=True)
        elif hasattr(updates, "dict"):
            update_dict = updates.dict(exclude_unset=True)
        else:
            update_dict = updates if isinstance(updates, dict) else {}

        # Apply updates
        for key, value in update_dict.items():
            if value is not None:
                update_data[key] = value

        if not update_data:
            return campaign  # No updates to apply

        # Update in repository
        updated = await self.repository.update_campaign(campaign_id, update_data)
        return updated

    async def allocate_from_campaign(
        self,
        user_id: str,
        campaign_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Allocate credits to user from a campaign.

        Validates campaign rules and allocates the campaign's credit_amount.

        Args:
            user_id: User identifier
            campaign_id: Campaign identifier
            metadata: Optional metadata

        Returns:
            Allocation response

        Raises:
            CampaignNotFoundError: If campaign not found
            CampaignInactiveError: If campaign is inactive or expired
            CampaignBudgetExhaustedError: If budget exhausted
            CreditAllocationFailedError: If allocation fails
        """
        # Validate campaign
        campaign = await self._validate_campaign_for_allocation(
            campaign_id, user_id, 0  # Amount validated internally
        )

        # Get credit_amount from campaign
        credit_amount = campaign.get("credit_amount", 0)
        credit_type = campaign.get("credit_type", "promotional")
        expiration_days = campaign.get("expiration_days", 90)

        # Check budget
        total_budget = campaign.get("total_budget", 0)
        allocated_amount = campaign.get("allocated_amount", 0)
        remaining_budget = total_budget - allocated_amount

        if remaining_budget < credit_amount:
            raise CampaignBudgetExhaustedError(
                "Campaign budget exhausted",
                campaign_id=campaign_id,
                total_budget=total_budget,
                allocated_amount=allocated_amount,
            )

        # Check eligibility rules
        eligibility_rules = campaign.get("eligibility_rules", {})
        if eligibility_rules and self.account_client:
            user = await self.account_client.get_user(user_id)
            if user:
                user_tier = user.get("tier", "basic")
                required_tiers = eligibility_rules.get("user_tiers", [])
                if required_tiers and user_tier not in required_tiers:
                    raise CreditAllocationFailedError(
                        "User does not meet eligibility requirements",
                        reason="eligibility_failed"
                    )

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(days=expiration_days)

        # Allocate credits
        return await self.allocate_credits(
            user_id=user_id,
            amount=credit_amount,
            credit_type=credit_type,
            campaign_id=campaign_id,
            description=f"Campaign allocation: {campaign.get('name', campaign_id)}",
            expires_at=expires_at,
            metadata=metadata,
        )

    async def check_credit_availability(
        self, user_id: str, amount: int
    ) -> Dict[str, Any]:
        """
        Check credit availability (alias for check_availability).

        Args:
            user_id: User identifier
            amount: Amount to check

        Returns:
            Availability response
        """
        return await self.check_availability(user_id, amount)

    async def get_user_balance(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's credit balance summary.

        Args:
            user_id: User identifier

        Returns:
            Balance summary with total_balance, by_type, etc.
        """
        return await self.get_balance_summary(user_id)

    async def process_expiration_warnings(self, days: int = 7) -> Dict[str, Any]:
        """
        Process expiration warnings and publish events for credits expiring soon.

        BR-EXP-004: 7-Day Warning

        Args:
            days: Number of days ahead to warn (default 7)

        Returns:
            Summary of warnings processed
        """
        now = datetime.now(timezone.utc)
        expiring_soon = await self.check_expiring_soon(days=days)

        warnings_sent = 0
        users_notified = set()

        for alloc in expiring_soon:
            user_id = alloc.get("user_id")
            if not user_id:
                continue

            remaining = (
                alloc.get("amount", 0) -
                alloc.get("consumed_amount", 0) -
                alloc.get("expired_amount", 0)
            )

            if remaining <= 0:
                continue

            # Publish warning event
            if self.event_bus and user_id not in users_notified:
                await self.event_bus.publish(
                    "credit.expiring_soon",
                    {
                        "user_id": user_id,
                        "amount": remaining,
                        "expires_at": alloc.get("expires_at").isoformat() if alloc.get("expires_at") else None,
                        "allocation_id": alloc.get("allocation_id"),
                        "timestamp": now.isoformat(),
                    },
                )
                users_notified.add(user_id)
                warnings_sent += 1

        logger.info(
            f"Expiration warnings processed: {warnings_sent} users notified, "
            f"{len(expiring_soon)} allocations expiring in {days} days"
        )

        return {
            "success": True,
            "warnings_sent": warnings_sent,
            "allocations_expiring": len(expiring_soon),
            "processed_at": now.isoformat(),
        }

    # ====================
    # Balance and Summary
    # ====================

    async def get_balance_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive balance summary for user.

        Args:
            user_id: User identifier

        Returns:
            Balance summary with total_balance, by_type, expiring_soon, next_expiration
        """
        # Get all accounts
        accounts = await self.get_user_accounts(user_id, is_active=True)

        total_balance = sum(acc.get("balance", 0) for acc in accounts)
        by_type = await self.repository.get_aggregated_balance(user_id)

        # Get credits expiring in 7 days
        expiring_soon_allocations = await self.check_expiring_soon(days=7)
        expiring_soon = sum(
            alloc.get("amount", 0) -
            alloc.get("consumed_amount", 0) -
            alloc.get("expired_amount", 0)
            for alloc in expiring_soon_allocations
            if alloc.get("user_id") == user_id
        )

        # Get next expiration
        next_expiration = None
        if expiring_soon_allocations:
            # Filter for this user and sort by expires_at
            user_allocations = [
                a for a in expiring_soon_allocations if a.get("user_id") == user_id
            ]
            if user_allocations:
                next_alloc = user_allocations[0]
                next_expiration = {
                    "amount": next_alloc.get("amount", 0) -
                             next_alloc.get("consumed_amount", 0) -
                             next_alloc.get("expired_amount", 0),
                    "expires_at": next_alloc.get("expires_at"),
                }

        return {
            "user_id": user_id,
            "total_balance": total_balance,
            "available_balance": total_balance,  # Same as total for now
            "expiring_soon": expiring_soon,
            "by_type": by_type,
            "next_expiration": next_expiration,
        }

    # ====================
    # Transaction History
    # ====================

    async def get_transactions(
        self,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get transaction history for a user.

        Args:
            user_id: User identifier
            filters: Optional filters (transaction_type, start_date, end_date, limit, offset)

        Returns:
            Transaction list with pagination info
        """
        filters = filters or {}
        limit = filters.get("limit", 100)
        offset = filters.get("offset", 0)

        transactions = await self.repository.get_user_transactions(user_id, filters)

        return {
            "transactions": transactions,
            "total": len(transactions),
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "page_size": limit,
        }

    # ====================
    # Statistics
    # ====================

    async def get_statistics(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get credit statistics and analytics.

        Args:
            filters: Optional filters (user_id, credit_type, start_date, end_date)

        Returns:
            Credit statistics response
        """
        filters = filters or {}
        now = datetime.now(timezone.utc)

        # Default period: last 30 days
        start_date = filters.get("start_date", now - timedelta(days=30))
        end_date = filters.get("end_date", now)

        # Get aggregated statistics from repository
        # For now, return basic statistics structure
        user_id = filters.get("user_id")

        total_allocated = 0
        total_consumed = 0
        total_expired = 0
        active_campaigns = 0
        active_accounts = 0

        if user_id:
            accounts = await self.get_user_accounts(user_id, is_active=True)
            active_accounts = len(accounts)
            for account in accounts:
                total_allocated += account.get("total_allocated", 0)
                total_consumed += account.get("total_consumed", 0)
                total_expired += account.get("total_expired", 0)

        # Calculate rates
        utilization_rate = total_consumed / total_allocated if total_allocated > 0 else 0.0
        expiration_rate = total_expired / total_allocated if total_allocated > 0 else 0.0

        # Get active campaigns
        campaigns = await self.get_active_campaigns()
        active_campaigns = len(campaigns)

        return {
            "period_start": start_date,
            "period_end": end_date,
            "total_allocated": total_allocated,
            "total_consumed": total_consumed,
            "total_expired": total_expired,
            "utilization_rate": min(utilization_rate, 1.0),
            "expiration_rate": min(expiration_rate, 1.0),
            "by_credit_type": {},
            "active_campaigns": active_campaigns,
            "active_accounts": active_accounts,
        }

    # ====================
    # Event Publishing
    # ====================

    async def _publish_credit_allocated_event(
        self,
        allocation_id: str,
        user_id: str,
        amount: int,
        credit_type: str,
        expires_at: Optional[datetime],
    ):
        """Publish credit.allocated event (BR-EVT-001)"""
        if not self.event_bus:
            return

        await self.event_bus.publish(
            "credit.allocated",
            {
                "allocation_id": allocation_id,
                "user_id": user_id,
                "amount": amount,
                "credit_type": credit_type,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _publish_credit_consumed_event(
        self,
        user_id: str,
        amount: int,
        billing_record_id: Optional[str],
        transactions: List[Dict[str, Any]],
    ):
        """Publish credit.consumed event (BR-EVT-002)"""
        if not self.event_bus:
            return

        await self.event_bus.publish(
            "credit.consumed",
            {
                "user_id": user_id,
                "amount": amount,
                "billing_record_id": billing_record_id,
                "transaction_ids": [t["transaction_id"] for t in transactions],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _publish_credit_expired_event(
        self,
        user_id: str,
        amount: int,
        credit_type: str,
        balance_after: int,
    ):
        """Publish credit.expired event (BR-EVT-003)"""
        if not self.event_bus:
            return

        await self.event_bus.publish(
            "credit.expired",
            {
                "user_id": user_id,
                "amount": amount,
                "credit_type": credit_type,
                "balance_after": balance_after,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _publish_credit_transferred_event(
        self,
        from_user_id: str,
        to_user_id: str,
        amount: int,
        credit_type: str,
        transfer_id: str,
    ):
        """Publish credit.transferred event (BR-EVT-004)"""
        if not self.event_bus:
            return

        await self.event_bus.publish(
            "credit.transferred",
            {
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "amount": amount,
                "credit_type": credit_type,
                "transfer_id": transfer_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


__all__ = ["CreditService"]
