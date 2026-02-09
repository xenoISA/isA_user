"""
Credit Service Component Test Fixtures

Provides mocks for credit service component testing:
- MockCreditRepository: Mock implementation of CreditRepositoryProtocol
- MockEventBus: Mock event publishing
- MockAccountClient: Mock account service client
- MockSubscriptionClient: Mock subscription service client
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock

from tests.contracts.credit.data_contract import CreditTestDataFactory


# =============================================================================
# Mock Repository Implementation
# =============================================================================


class MockCreditRepository:
    """
    Mock implementation of CreditRepositoryProtocol for testing.

    Provides in-memory storage for accounts, transactions, allocations, and campaigns.
    """

    def __init__(self):
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.transactions: List[Dict[str, Any]] = []
        self.allocations: List[Dict[str, Any]] = []
        self.campaigns: Dict[str, Dict[str, Any]] = {}

        # Track method calls for verification
        self.method_calls = []

    def reset(self):
        """Reset all stored data"""
        self.accounts.clear()
        self.transactions.clear()
        self.allocations.clear()
        self.campaigns.clear()
        self.method_calls.clear()

    async def create_account(self, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a credit account"""
        self.method_calls.append(("create_account", account_data))

        account_id = account_data.get("account_id")
        if not account_id:
            account_id = CreditTestDataFactory.make_account_id()
            account_data["account_id"] = account_id

        # Set defaults
        account_data.setdefault("balance", 0)
        account_data.setdefault("total_allocated", 0)
        account_data.setdefault("total_consumed", 0)
        account_data.setdefault("total_expired", 0)
        account_data.setdefault("is_active", True)
        account_data.setdefault("created_at", datetime.now(timezone.utc))
        account_data.setdefault("updated_at", datetime.now(timezone.utc))

        self.accounts[account_id] = account_data.copy()
        return account_data

    async def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account by ID"""
        self.method_calls.append(("get_account_by_id", account_id))
        return self.accounts.get(account_id)

    async def get_account_by_user_type(self, user_id: str, credit_type: str) -> Optional[Dict[str, Any]]:
        """Get account by user ID and credit type"""
        self.method_calls.append(("get_account_by_user_type", user_id, credit_type))

        for account in self.accounts.values():
            if account["user_id"] == user_id and account["credit_type"] == credit_type:
                return account
        return None

    async def get_user_accounts(self, user_id: str, filters: Dict) -> List[Dict[str, Any]]:
        """Get all accounts for user"""
        self.method_calls.append(("get_user_accounts", user_id, filters))

        result = []
        for account in self.accounts.values():
            if account["user_id"] != user_id:
                continue

            # Apply filters
            if "credit_type" in filters and account["credit_type"] != filters["credit_type"]:
                continue
            if "is_active" in filters and account["is_active"] != filters["is_active"]:
                continue

            result.append(account)

        return result

    async def update_account_balance(self, account_id: str, balance_delta: int, transaction_type: str = None) -> bool:
        """Update account balance atomically"""
        self.method_calls.append(("update_account_balance", account_id, balance_delta))

        account = self.accounts.get(account_id)
        if not account:
            return False

        account["balance"] += balance_delta
        account["updated_at"] = datetime.now(timezone.utc)

        # Update totals based on delta direction
        if balance_delta > 0:
            account["total_allocated"] += balance_delta
        elif balance_delta < 0:
            # Check if this is an expiration (look at recent transactions)
            is_expiration = False
            if self.transactions:
                # Check the last transaction for this account
                for txn in reversed(self.transactions):
                    if txn.get("account_id") == account_id:
                        if txn.get("transaction_type") == "expire":
                            is_expiration = True
                        break

            if is_expiration:
                account["total_expired"] += abs(balance_delta)
            else:
                account["total_consumed"] += abs(balance_delta)

        return True

    async def create_transaction(self, txn_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create transaction record"""
        self.method_calls.append(("create_transaction", txn_data))

        if "transaction_id" not in txn_data:
            txn_data["transaction_id"] = CreditTestDataFactory.make_transaction_id()

        txn_data.setdefault("created_at", datetime.now(timezone.utc))

        self.transactions.append(txn_data.copy())
        return txn_data

    async def get_user_transactions(self, user_id: str, filters: Dict) -> List[Dict[str, Any]]:
        """Get transactions for user"""
        self.method_calls.append(("get_user_transactions", user_id, filters))

        result = []
        for txn in self.transactions:
            if txn["user_id"] != user_id:
                continue

            # Apply filters
            if "transaction_type" in filters and txn["transaction_type"] != filters["transaction_type"]:
                continue
            if "start_date" in filters and txn["created_at"] < filters["start_date"]:
                continue
            if "end_date" in filters and txn["created_at"] > filters["end_date"]:
                continue

            result.append(txn)

        return result

    async def create_allocation(self, alloc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create allocation record"""
        self.method_calls.append(("create_allocation", alloc_data))

        if "allocation_id" not in alloc_data:
            alloc_data["allocation_id"] = CreditTestDataFactory.make_allocation_id()

        alloc_data.setdefault("status", "completed")
        alloc_data.setdefault("consumed_amount", 0)
        alloc_data.setdefault("expired_amount", 0)
        alloc_data.setdefault("created_at", datetime.now(timezone.utc))
        alloc_data.setdefault("updated_at", datetime.now(timezone.utc))

        self.allocations.append(alloc_data.copy())
        return alloc_data

    async def get_expiring_allocations(self, before: datetime) -> List[Dict[str, Any]]:
        """Get allocations expiring before date"""
        self.method_calls.append(("get_expiring_allocations", before))

        result = []
        for alloc in self.allocations:
            expires_at = alloc.get("expires_at")
            if expires_at and expires_at <= before:
                remaining = alloc["amount"] - alloc.get("consumed_amount", 0) - alloc.get("expired_amount", 0)
                if remaining > 0:
                    result.append(alloc)

        return result

    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create campaign"""
        self.method_calls.append(("create_campaign", campaign_data))

        campaign_id = campaign_data.get("campaign_id")
        if not campaign_id:
            campaign_id = CreditTestDataFactory.make_campaign_id()
            campaign_data["campaign_id"] = campaign_id

        campaign_data.setdefault("allocated_amount", 0)
        campaign_data.setdefault("is_active", True)
        campaign_data.setdefault("created_at", datetime.now(timezone.utc))
        campaign_data.setdefault("updated_at", datetime.now(timezone.utc))

        self.campaigns[campaign_id] = campaign_data.copy()
        return campaign_data

    async def get_campaign_by_id(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign by ID"""
        self.method_calls.append(("get_campaign_by_id", campaign_id))
        return self.campaigns.get(campaign_id)

    async def update_campaign_budget(self, campaign_id: str, amount: int) -> bool:
        """Update campaign allocated_amount"""
        self.method_calls.append(("update_campaign_budget", campaign_id, amount))

        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False

        campaign["allocated_amount"] += amount
        campaign["updated_at"] = datetime.now(timezone.utc)
        return True

    async def get_aggregated_balance(self, user_id: str) -> Dict[str, int]:
        """Get aggregated balance by credit type"""
        self.method_calls.append(("get_aggregated_balance", user_id))

        result = {}
        for account in self.accounts.values():
            if account["user_id"] == user_id and account["is_active"]:
                credit_type = account["credit_type"]
                result[credit_type] = result.get(credit_type, 0) + account["balance"]

        return result

    async def delete_user_data(self, user_id: str) -> int:
        """Delete all user data (GDPR)"""
        self.method_calls.append(("delete_user_data", user_id))

        count = 0

        # Delete accounts
        accounts_to_delete = [aid for aid, acc in self.accounts.items() if acc["user_id"] == user_id]
        for aid in accounts_to_delete:
            del self.accounts[aid]
            count += 1

        # Delete transactions
        self.transactions = [txn for txn in self.transactions if txn["user_id"] != user_id]
        count += len([txn for txn in self.transactions if txn["user_id"] == user_id])

        # Delete allocations
        allocations_to_keep = [alloc for alloc in self.allocations if alloc["user_id"] != user_id]
        count += len(self.allocations) - len(allocations_to_keep)
        self.allocations = allocations_to_keep

        return count

    async def get_available_credits_fifo(self, account_id: str) -> List[Dict[str, Any]]:
        """Get available credits for account in FIFO order (by expires_at)"""
        self.method_calls.append(("get_available_credits_fifo", account_id))

        result = []
        now = datetime.now(timezone.utc)

        for alloc in self.allocations:
            if alloc.get("account_id") != account_id:
                continue

            # Skip expired allocations
            expires_at = alloc.get("expires_at")
            if expires_at and expires_at <= now:
                continue

            # Calculate available amount
            available = alloc["amount"] - alloc.get("consumed_amount", 0) - alloc.get("expired_amount", 0)
            if available > 0:
                result.append({
                    "allocation_id": alloc["allocation_id"],
                    "available": available,
                    "expires_at": expires_at,
                    "created_at": alloc.get("created_at"),
                })

        # Sort by expires_at (FIFO) - None expires_at goes last
        result.sort(key=lambda x: (
            x["expires_at"] or datetime.max.replace(tzinfo=timezone.utc),
            x["created_at"]
        ))

        return result

    async def update_allocation_consumed(self, allocation_id: str, amount: int) -> bool:
        """Update allocation consumed_amount"""
        self.method_calls.append(("update_allocation_consumed", allocation_id, amount))

        for alloc in self.allocations:
            if alloc["allocation_id"] == allocation_id:
                alloc["consumed_amount"] = alloc.get("consumed_amount", 0) + amount
                alloc["updated_at"] = datetime.now(timezone.utc)
                return True
        return False

    async def update_allocation_expired(self, allocation_id: str, amount: int) -> bool:
        """Update allocation expired_amount"""
        self.method_calls.append(("update_allocation_expired", allocation_id, amount))

        for alloc in self.allocations:
            if alloc["allocation_id"] == allocation_id:
                alloc["expired_amount"] = alloc.get("expired_amount", 0) + amount
                alloc["updated_at"] = datetime.now(timezone.utc)
                return True
        return False

    async def get_user_campaign_allocations_count(self, user_id: str, campaign_id: str) -> int:
        """Get count of allocations for user from campaign"""
        self.method_calls.append(("get_user_campaign_allocations_count", user_id, campaign_id))

        count = 0
        for alloc in self.allocations:
            if alloc.get("user_id") == user_id and alloc.get("campaign_id") == campaign_id:
                count += 1
        return count

    async def get_active_campaigns(self, credit_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active campaigns"""
        self.method_calls.append(("get_active_campaigns", credit_type))

        now = datetime.now(timezone.utc)
        result = []

        for campaign in self.campaigns.values():
            if not campaign.get("is_active", False):
                continue

            start_date = campaign.get("start_date")
            end_date = campaign.get("end_date")

            if start_date and start_date > now:
                continue
            if end_date and end_date < now:
                continue

            if credit_type and campaign.get("credit_type") != credit_type:
                continue

            result.append(campaign)

        return result


# =============================================================================
# Mock Event Bus
# =============================================================================


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    def reset(self):
        """Reset published events"""
        self.published_events.clear()

    async def publish(self, subject: str, data: Dict[str, Any]) -> None:
        """Publish event"""
        self.published_events.append({"subject": subject, "data": data})

    def get_events_by_subject(self, subject: str) -> List[Dict[str, Any]]:
        """Get all events for a subject"""
        return [event for event in self.published_events if event["subject"] == subject]

    def event_published(self, subject: str) -> bool:
        """Check if event was published"""
        return any(event["subject"] == subject for event in self.published_events)


# =============================================================================
# Mock Service Clients
# =============================================================================


class MockAccountClient:
    """Mock account service client"""

    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.method_calls = []

    def reset(self):
        """Reset mock state"""
        self.users.clear()
        self.method_calls.clear()

    def add_user(self, user_id: str, is_active: bool = True, **kwargs):
        """Add a user to the mock"""
        self.users[user_id] = {
            "user_id": user_id,
            "is_active": is_active,
            **kwargs
        }

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from account_service"""
        self.method_calls.append(("get_user", user_id))
        return self.users.get(user_id)

    async def validate_user(self, user_id: str) -> bool:
        """Validate user exists and is active"""
        self.method_calls.append(("validate_user", user_id))
        user = self.users.get(user_id)
        return user is not None and user.get("is_active", False)


class MockSubscriptionClient:
    """Mock subscription service client"""

    def __init__(self):
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.method_calls = []

    def reset(self):
        """Reset mock state"""
        self.subscriptions.clear()
        self.method_calls.clear()

    def add_subscription(self, user_id: str, subscription_id: str, credits_included: int = 1000, **kwargs):
        """Add a subscription to the mock"""
        self.subscriptions[user_id] = {
            "subscription_id": subscription_id,
            "user_id": user_id,
            "credits_included": credits_included,
            **kwargs
        }

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active subscription for user"""
        self.method_calls.append(("get_user_subscription", user_id))
        return self.subscriptions.get(user_id)

    async def get_subscription_credits(self, subscription_id: str) -> Optional[int]:
        """Get credits included in subscription"""
        self.method_calls.append(("get_subscription_credits", subscription_id))
        for sub in self.subscriptions.values():
            if sub["subscription_id"] == subscription_id:
                return sub.get("credits_included", 0)
        return None


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def mock_repository():
    """Create mock credit repository"""
    return MockCreditRepository()


@pytest.fixture
def mock_event_bus():
    """Create mock event bus"""
    return MockEventBus()


@pytest.fixture
def mock_account_client():
    """Create mock account client"""
    return MockAccountClient()


@pytest.fixture
def mock_subscription_client():
    """Create mock subscription client"""
    return MockSubscriptionClient()


@pytest.fixture
def credit_service(mock_repository, mock_event_bus, mock_account_client, mock_subscription_client):
    """Create credit service with mocked dependencies"""
    from microservices.credit_service.credit_service import CreditService

    return CreditService(
        repository=mock_repository,
        event_bus=mock_event_bus,
        account_client=mock_account_client,
        subscription_client=mock_subscription_client,
    )


@pytest.fixture
def data_factory():
    """Provide data factory for test data generation"""
    return CreditTestDataFactory
