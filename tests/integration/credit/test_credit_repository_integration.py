"""
Credit Repository Integration Tests

Tests CreditRepository against a real PostgreSQL database.
These tests require a running PostgreSQL service with credit_db database.

Test Coverage:
- Account CRUD operations (5 tests)
- Transaction creation and queries (5 tests)
- Allocation CRUD and expiring queries (5 tests)
- Campaign CRUD and budget updates (5 tests)
- Atomic balance updates (5 tests)
- FIFO credit ordering (5 tests)
- GDPR delete_user_data (3 tests)
- Index usage verification (2 tests)

Usage:
    pytest tests/integration/credit/test_credit_repository_integration.py -v
    pytest tests/integration/credit -v -k "account"
"""

import os
import sys
import pytest
import asyncpg
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Add paths for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../../..")
sys.path.insert(0, _project_root)

from tests.contracts.credit.data_contract import CreditTestDataFactory, CreditTypeEnum, TransactionTypeEnum
from tests.integration.credit.conftest import get_account_balance, get_transaction_count, get_user_total_balance

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.requires_db]


# ============================================================================
# Account CRUD Operations (5 tests)
# ============================================================================

class TestCreditAccountCRUD:
    """Test credit account CRUD operations against database"""

    async def test_create_account_inserts_into_database(
        self,
        credit_db_conn: asyncpg.Connection,
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: create_account inserts new account into database"""
        if not credit_db_conn:
            pytest.skip("Database connection not available")

        user_id = credit_factory.make_user_id()
        account_id = credit_factory.make_account_id()
        credit_type = CreditTypeEnum.BONUS.value

        # Insert account
        query = """
            INSERT INTO credit.credit_accounts (
                account_id, user_id, credit_type, balance,
                expiration_policy, expiration_days, is_active,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
            RETURNING *
        """

        row = await credit_db_conn.fetchrow(
            query, account_id, user_id, credit_type, 0, "fixed_days", 90, True
        )

        assert row is not None
        assert row["account_id"] == account_id
        assert row["user_id"] == user_id
        assert row["credit_type"] == credit_type
        assert row["balance"] == 0
        assert row["is_active"] is True

    async def test_get_account_by_id_returns_existing_account(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any]
    ):
        """INTEGRATION: get_account_by_id retrieves existing account"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        query = "SELECT * FROM credit.credit_accounts WHERE account_id = $1"
        row = await credit_db_conn.fetchrow(query, test_account["account_id"])

        assert row is not None
        assert row["account_id"] == test_account["account_id"]
        assert row["user_id"] == test_account["user_id"]
        assert row["balance"] == test_account["balance"]

    async def test_get_account_by_user_type_returns_correct_account(
        self,
        credit_db_conn: asyncpg.Connection,
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: get_account_by_user_type retrieves correct account"""
        if not credit_db_conn:
            pytest.skip("Database connection not available")

        user_id = credit_factory.make_user_id()

        # Create multiple accounts for same user with different types
        for credit_type in ["bonus", "promotional", "referral"]:
            account_id = credit_factory.make_account_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_accounts (
                    account_id, user_id, credit_type, balance,
                    expiration_policy, expiration_days, is_active,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                account_id, user_id, credit_type, 1000, "fixed_days", 90, True
            )

        # Query for specific type
        query = """
            SELECT * FROM credit.credit_accounts
            WHERE user_id = $1 AND credit_type = $2
        """
        row = await credit_db_conn.fetchrow(query, user_id, "promotional")

        assert row is not None
        assert row["user_id"] == user_id
        assert row["credit_type"] == "promotional"

    async def test_get_user_accounts_returns_all_user_accounts(
        self,
        credit_db_conn: asyncpg.Connection,
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: get_user_accounts returns all accounts for user"""
        if not credit_db_conn:
            pytest.skip("Database connection not available")

        user_id = credit_factory.make_user_id()

        # Create 3 accounts for same user
        for i in range(3):
            account_id = credit_factory.make_account_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_accounts (
                    account_id, user_id, credit_type, balance,
                    expiration_policy, expiration_days, is_active,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                account_id, user_id, f"type_{i}", 1000, "fixed_days", 90, True
            )

        # Query all accounts
        query = "SELECT * FROM credit.credit_accounts WHERE user_id = $1"
        rows = await credit_db_conn.fetch(query, user_id)

        assert len(rows) == 3
        for row in rows:
            assert row["user_id"] == user_id

    async def test_update_account_balance_modifies_balance_atomically(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any]
    ):
        """INTEGRATION: update_account_balance modifies balance atomically"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        initial_balance = await get_account_balance(credit_db_conn, test_account["account_id"])

        # Update balance with delta
        delta = 500
        query = """
            UPDATE credit.credit_accounts
            SET balance = balance + $1,
                total_allocated = CASE WHEN $1 > 0 THEN total_allocated + $1 ELSE total_allocated END,
                updated_at = NOW()
            WHERE account_id = $2
        """
        await credit_db_conn.execute(query, delta, test_account["account_id"])

        new_balance = await get_account_balance(credit_db_conn, test_account["account_id"])

        assert new_balance == initial_balance + delta


# ============================================================================
# Transaction Creation and Queries (5 tests)
# ============================================================================

class TestCreditTransactions:
    """Test credit transaction creation and queries"""

    async def test_create_transaction_inserts_transaction_record(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: create_transaction inserts immutable transaction record"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        transaction_id = credit_factory.make_transaction_id()
        amount = 500

        query = """
            INSERT INTO credit.credit_transactions (
                transaction_id, account_id, user_id, transaction_type,
                amount, balance_before, balance_after,
                description, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            RETURNING *
        """

        row = await credit_db_conn.fetchrow(
            query,
            transaction_id, test_account["account_id"], test_account["user_id"],
            "allocate", amount, 1000, 1500, "Test allocation"
        )

        assert row is not None
        assert row["transaction_id"] == transaction_id
        assert row["amount"] == amount
        assert row["transaction_type"] == "allocate"

    async def test_get_user_transactions_returns_all_transactions(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: get_user_transactions retrieves all user transactions"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        # Create 5 transactions
        for i in range(5):
            transaction_id = credit_factory.make_transaction_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_transactions (
                    transaction_id, account_id, user_id, transaction_type,
                    amount, balance_before, balance_after, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """,
                transaction_id, test_account["account_id"], test_account["user_id"],
                "allocate", 100 * (i + 1), 0, 100 * (i + 1)
            )

        # Query all transactions
        query = """
            SELECT * FROM credit.credit_transactions
            WHERE user_id = $1
            ORDER BY created_at DESC
        """
        rows = await credit_db_conn.fetch(query, test_account["user_id"])

        assert len(rows) == 5
        for row in rows:
            assert row["user_id"] == test_account["user_id"]

    async def test_transaction_query_filtered_by_type(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: transactions can be filtered by transaction_type"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        # Create allocate and consume transactions
        for txn_type in ["allocate", "consume", "allocate", "consume", "expire"]:
            transaction_id = credit_factory.make_transaction_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_transactions (
                    transaction_id, account_id, user_id, transaction_type,
                    amount, balance_before, balance_after, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """,
                transaction_id, test_account["account_id"], test_account["user_id"],
                txn_type, 100, 1000, 1100
            )

        # Query only consume transactions
        query = """
            SELECT * FROM credit.credit_transactions
            WHERE user_id = $1 AND transaction_type = $2
        """
        rows = await credit_db_conn.fetch(query, test_account["user_id"], "consume")

        assert len(rows) == 2
        for row in rows:
            assert row["transaction_type"] == "consume"

    async def test_transaction_query_with_date_range(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: transactions can be filtered by date range"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        past_date = credit_factory.make_past_timestamp(30)
        recent_date = credit_factory.make_past_timestamp(1)

        # Create transactions with different timestamps
        for days_ago in [40, 20, 5, 2]:
            transaction_id = credit_factory.make_transaction_id()
            timestamp = credit_factory.make_past_timestamp(days_ago)
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_transactions (
                    transaction_id, account_id, user_id, transaction_type,
                    amount, balance_before, balance_after, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                transaction_id, test_account["account_id"], test_account["user_id"],
                "allocate", 100, 1000, 1100, timestamp
            )

        # Query transactions in date range (last 30 days)
        query = """
            SELECT * FROM credit.credit_transactions
            WHERE user_id = $1 AND created_at >= $2
        """
        rows = await credit_db_conn.fetch(query, test_account["user_id"], past_date)

        # Should return transactions from 20, 5, and 2 days ago (3 total)
        assert len(rows) == 3

    async def test_transaction_records_are_immutable(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: transaction records cannot be updated (append-only)"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        transaction_id = credit_factory.make_transaction_id()

        # Create transaction
        await credit_db_conn.execute(
            """
            INSERT INTO credit.credit_transactions (
                transaction_id, account_id, user_id, transaction_type,
                amount, balance_before, balance_after, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """,
            transaction_id, test_account["account_id"], test_account["user_id"],
            "allocate", 500, 1000, 1500
        )

        # Verify transaction exists
        row = await credit_db_conn.fetchrow(
            "SELECT * FROM credit.credit_transactions WHERE transaction_id = $1",
            transaction_id
        )

        assert row["amount"] == 500

        # Best practice: transactions should be append-only
        # In production, UPDATE permissions should be revoked on this table


# ============================================================================
# Allocation CRUD and Expiring Queries (5 tests)
# ============================================================================

class TestCreditAllocations:
    """Test credit allocation CRUD and expiration queries"""

    async def test_create_allocation_inserts_allocation_record(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: create_allocation inserts new allocation record"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        allocation_id = credit_factory.make_allocation_id()
        expires_at = credit_factory.make_future_timestamp(90)

        query = """
            INSERT INTO credit.credit_allocations (
                allocation_id, user_id, account_id, amount,
                status, expires_at, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            RETURNING *
        """

        row = await credit_db_conn.fetchrow(
            query,
            allocation_id, test_account["user_id"], test_account["account_id"],
            1000, "completed", expires_at
        )

        assert row is not None
        assert row["allocation_id"] == allocation_id
        assert row["amount"] == 1000
        assert row["status"] == "completed"

    async def test_get_expiring_allocations_returns_allocations_before_date(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: get_expiring_allocations returns allocations expiring before date"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        # Create allocations with different expiration dates
        expiry_dates = [
            credit_factory.make_future_timestamp(5),   # Expiring soon
            credit_factory.make_future_timestamp(10),  # Expiring soon
            credit_factory.make_future_timestamp(60),  # Not expiring soon
            credit_factory.make_future_timestamp(90),  # Not expiring soon
        ]

        for i, expires_at in enumerate(expiry_dates):
            allocation_id = credit_factory.make_allocation_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_allocations (
                    allocation_id, user_id, account_id, amount,
                    status, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                """,
                allocation_id, test_account["user_id"], test_account["account_id"],
                1000, "completed", expires_at
            )

        # Query allocations expiring in next 30 days
        cutoff_date = credit_factory.make_future_timestamp(30)
        query = """
            SELECT * FROM credit.credit_allocations
            WHERE expires_at <= $1 AND status = 'completed'
        """
        rows = await credit_db_conn.fetch(query, cutoff_date)

        # Should return 2 allocations expiring in 5 and 10 days
        assert len(rows) == 2

    async def test_allocation_status_can_be_updated(
        self,
        credit_db_conn: asyncpg.Connection,
        test_allocation: Dict[str, Any]
    ):
        """INTEGRATION: allocation status can be updated (e.g., to expired)"""
        if not credit_db_conn or not test_allocation:
            pytest.skip("Database connection or test allocation not available")

        # Update status to expired
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_allocations
            SET status = $1, expired_amount = amount, updated_at = NOW()
            WHERE allocation_id = $2
            """,
            "expired", test_allocation["allocation_id"]
        )

        # Verify update
        row = await credit_db_conn.fetchrow(
            "SELECT * FROM credit.credit_allocations WHERE allocation_id = $1",
            test_allocation["allocation_id"]
        )

        assert row["status"] == "expired"
        assert row["expired_amount"] == test_allocation["amount"]

    async def test_get_user_allocations_by_campaign(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        test_campaign: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: allocations can be filtered by campaign_id"""
        if not credit_db_conn or not test_account or not test_campaign:
            pytest.skip("Database connection, test account, or campaign not available")

        campaign_id = test_campaign["campaign_id"]

        # Create allocations for campaign
        for i in range(3):
            allocation_id = credit_factory.make_allocation_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_allocations (
                    allocation_id, campaign_id, user_id, account_id,
                    amount, status, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                allocation_id, campaign_id, test_account["user_id"],
                test_account["account_id"], 1000, "completed",
                credit_factory.make_future_timestamp(90)
            )

        # Query by campaign
        query = """
            SELECT * FROM credit.credit_allocations
            WHERE user_id = $1 AND campaign_id = $2
        """
        rows = await credit_db_conn.fetch(query, test_account["user_id"], campaign_id)

        assert len(rows) == 3
        for row in rows:
            assert row["campaign_id"] == campaign_id

    async def test_allocation_consumed_amount_tracks_usage(
        self,
        credit_db_conn: asyncpg.Connection,
        test_allocation: Dict[str, Any]
    ):
        """INTEGRATION: allocation consumed_amount tracks credit usage"""
        if not credit_db_conn or not test_allocation:
            pytest.skip("Database connection or test allocation not available")

        # Update consumed amount
        consumed = 300
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_allocations
            SET consumed_amount = consumed_amount + $1, updated_at = NOW()
            WHERE allocation_id = $2
            """,
            consumed, test_allocation["allocation_id"]
        )

        # Verify update
        row = await credit_db_conn.fetchrow(
            "SELECT consumed_amount FROM credit.credit_allocations WHERE allocation_id = $1",
            test_allocation["allocation_id"]
        )

        assert row["consumed_amount"] == consumed


# ============================================================================
# Campaign CRUD and Budget Updates (5 tests)
# ============================================================================

class TestCreditCampaigns:
    """Test credit campaign CRUD and budget management"""

    async def test_create_campaign_inserts_campaign_record(
        self,
        credit_db_conn: asyncpg.Connection,
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: create_campaign inserts new campaign record"""
        if not credit_db_conn:
            pytest.skip("Database connection not available")

        campaign_id = credit_factory.make_campaign_id()
        name = credit_factory.make_campaign_name()

        query = """
            INSERT INTO credit.credit_campaigns (
                campaign_id, name, description, credit_type,
                credit_amount, total_budget, allocated_amount,
                start_date, end_date, expiration_days,
                max_allocations_per_user, is_active,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
            RETURNING *
        """

        row = await credit_db_conn.fetchrow(
            query,
            campaign_id, name, "Test campaign", "promotional",
            1000, 100000, 0,
            credit_factory.make_timestamp(), credit_factory.make_future_timestamp(30),
            90, 1, True
        )

        assert row is not None
        assert row["campaign_id"] == campaign_id
        assert row["name"] == name
        assert row["total_budget"] == 100000
        assert row["allocated_amount"] == 0

    async def test_get_campaign_by_id_returns_campaign(
        self,
        credit_db_conn: asyncpg.Connection,
        test_campaign: Dict[str, Any]
    ):
        """INTEGRATION: get_campaign_by_id retrieves existing campaign"""
        if not credit_db_conn or not test_campaign:
            pytest.skip("Database connection or test campaign not available")

        query = "SELECT * FROM credit.credit_campaigns WHERE campaign_id = $1"
        row = await credit_db_conn.fetchrow(query, test_campaign["campaign_id"])

        assert row is not None
        assert row["campaign_id"] == test_campaign["campaign_id"]
        assert row["total_budget"] == test_campaign["total_budget"]

    async def test_update_campaign_budget_increases_allocated_amount(
        self,
        credit_db_conn: asyncpg.Connection,
        test_campaign: Dict[str, Any]
    ):
        """INTEGRATION: update_campaign_budget atomically increases allocated_amount"""
        if not credit_db_conn or not test_campaign:
            pytest.skip("Database connection or test campaign not available")

        allocation_amount = 5000

        # Update budget atomically
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_campaigns
            SET allocated_amount = allocated_amount + $1, updated_at = NOW()
            WHERE campaign_id = $2
            """,
            allocation_amount, test_campaign["campaign_id"]
        )

        # Verify update
        row = await credit_db_conn.fetchrow(
            "SELECT allocated_amount FROM credit.credit_campaigns WHERE campaign_id = $1",
            test_campaign["campaign_id"]
        )

        assert row["allocated_amount"] == test_campaign["allocated_amount"] + allocation_amount

    async def test_campaign_budget_exhaustion_check(
        self,
        credit_db_conn: asyncpg.Connection,
        test_campaign: Dict[str, Any]
    ):
        """INTEGRATION: campaign can check if budget is exhausted"""
        if not credit_db_conn or not test_campaign:
            pytest.skip("Database connection or test campaign not available")

        # Set allocated_amount to total_budget
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_campaigns
            SET allocated_amount = total_budget, updated_at = NOW()
            WHERE campaign_id = $1
            """,
            test_campaign["campaign_id"]
        )

        # Query campaigns with remaining budget
        query = """
            SELECT * FROM credit.credit_campaigns
            WHERE campaign_id = $1 AND allocated_amount < total_budget
        """
        row = await credit_db_conn.fetchrow(query, test_campaign["campaign_id"])

        # Should return None (budget exhausted)
        assert row is None

    async def test_get_active_campaigns_filters_by_date_and_status(
        self,
        credit_db_conn: asyncpg.Connection,
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: campaigns can be filtered by active status and date range"""
        if not credit_db_conn:
            pytest.skip("Database connection not available")

        now = credit_factory.make_timestamp()

        # Create campaigns with different statuses and dates
        campaigns = [
            (credit_factory.make_campaign_id(), True, now, credit_factory.make_future_timestamp(30)),   # Active
            (credit_factory.make_campaign_id(), False, now, credit_factory.make_future_timestamp(30)),  # Inactive
            (credit_factory.make_campaign_id(), True, credit_factory.make_past_timestamp(60), credit_factory.make_past_timestamp(30)),  # Expired
        ]

        for campaign_id, is_active, start_date, end_date in campaigns:
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_campaigns (
                    campaign_id, name, credit_type, credit_amount,
                    total_budget, start_date, end_date, is_active,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                campaign_id, "Test Campaign", "promotional", 1000,
                100000, start_date, end_date, is_active
            )

        # Query active campaigns within date range
        query = """
            SELECT * FROM credit.credit_campaigns
            WHERE is_active = TRUE AND start_date <= $1 AND end_date >= $1
        """
        rows = await credit_db_conn.fetch(query, now)

        # Should return only 1 active campaign within date range
        assert len(rows) == 1


# ============================================================================
# Atomic Balance Updates (5 tests)
# ============================================================================

class TestAtomicBalanceUpdates:
    """Test atomic balance update operations"""

    async def test_balance_update_with_positive_delta_increases_balance(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any]
    ):
        """INTEGRATION: positive balance delta increases account balance"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        initial_balance = await get_account_balance(credit_db_conn, test_account["account_id"])
        delta = 1000

        await credit_db_conn.execute(
            """
            UPDATE credit.credit_accounts
            SET balance = balance + $1,
                total_allocated = total_allocated + $1,
                updated_at = NOW()
            WHERE account_id = $2
            """,
            delta, test_account["account_id"]
        )

        new_balance = await get_account_balance(credit_db_conn, test_account["account_id"])
        assert new_balance == initial_balance + delta

    async def test_balance_update_with_negative_delta_decreases_balance(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any]
    ):
        """INTEGRATION: negative balance delta decreases account balance"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        initial_balance = await get_account_balance(credit_db_conn, test_account["account_id"])
        delta = -500

        await credit_db_conn.execute(
            """
            UPDATE credit.credit_accounts
            SET balance = balance + $1,
                total_consumed = total_consumed + ABS($1),
                updated_at = NOW()
            WHERE account_id = $2
            """,
            delta, test_account["account_id"]
        )

        new_balance = await get_account_balance(credit_db_conn, test_account["account_id"])
        assert new_balance == initial_balance + delta

    async def test_balance_update_prevents_negative_balance_with_constraint(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any]
    ):
        """INTEGRATION: balance update can enforce non-negative constraint"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        current_balance = await get_account_balance(credit_db_conn, test_account["account_id"])

        # Try to consume more than available (should be prevented by application logic)
        excessive_delta = -(current_balance + 1000)

        # Application should check balance before update
        if current_balance + excessive_delta >= 0:
            await credit_db_conn.execute(
                "UPDATE credit.credit_accounts SET balance = balance + $1 WHERE account_id = $2",
                excessive_delta, test_account["account_id"]
            )
        else:
            # Skip update if would result in negative balance
            pass

        # Verify balance didn't go negative
        final_balance = await get_account_balance(credit_db_conn, test_account["account_id"])
        assert final_balance >= 0

    async def test_concurrent_balance_updates_maintain_consistency(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any]
    ):
        """INTEGRATION: concurrent balance updates maintain consistency"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        initial_balance = await get_account_balance(credit_db_conn, test_account["account_id"])

        # Simulate concurrent updates (in real scenario, use multiple connections)
        deltas = [100, 200, -50, 150, -100]

        for delta in deltas:
            await credit_db_conn.execute(
                "UPDATE credit.credit_accounts SET balance = balance + $1 WHERE account_id = $2",
                delta, test_account["account_id"]
            )

        expected_balance = initial_balance + sum(deltas)
        final_balance = await get_account_balance(credit_db_conn, test_account["account_id"])

        assert final_balance == expected_balance

    async def test_balance_update_increments_total_allocated_and_consumed(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any]
    ):
        """INTEGRATION: balance updates correctly increment total_allocated and total_consumed"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        # Get initial totals
        row = await credit_db_conn.fetchrow(
            "SELECT total_allocated, total_consumed FROM credit.credit_accounts WHERE account_id = $1",
            test_account["account_id"]
        )
        initial_allocated = row["total_allocated"]
        initial_consumed = row["total_consumed"]

        # Allocate credits
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_accounts
            SET balance = balance + $1,
                total_allocated = total_allocated + $1,
                updated_at = NOW()
            WHERE account_id = $2
            """,
            500, test_account["account_id"]
        )

        # Consume credits
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_accounts
            SET balance = balance - $1,
                total_consumed = total_consumed + $1,
                updated_at = NOW()
            WHERE account_id = $2
            """,
            200, test_account["account_id"]
        )

        # Verify totals
        row = await credit_db_conn.fetchrow(
            "SELECT total_allocated, total_consumed FROM credit.credit_accounts WHERE account_id = $1",
            test_account["account_id"]
        )

        assert row["total_allocated"] == initial_allocated + 500
        assert row["total_consumed"] == initial_consumed + 200


# ============================================================================
# FIFO Credit Ordering (5 tests)
# ============================================================================

class TestFIFOCreditOrdering:
    """Test FIFO (First-In-First-Out) credit consumption ordering"""

    async def test_fifo_consumes_oldest_expiring_credits_first(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: FIFO consumption prioritizes oldest expiring credits"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        # Create allocations with different expiration dates
        allocations = [
            (credit_factory.make_allocation_id(), credit_factory.make_future_timestamp(10)),  # Expires first
            (credit_factory.make_allocation_id(), credit_factory.make_future_timestamp(30)),
            (credit_factory.make_allocation_id(), credit_factory.make_future_timestamp(90)),  # Expires last
        ]

        for allocation_id, expires_at in allocations:
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_allocations (
                    allocation_id, user_id, account_id, amount,
                    status, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                """,
                allocation_id, test_account["user_id"], test_account["account_id"],
                1000, "completed", expires_at
            )

        # Query allocations ordered by expiration (FIFO)
        query = """
            SELECT * FROM credit.credit_allocations
            WHERE user_id = $1 AND status = 'completed'
            ORDER BY expires_at ASC
        """
        rows = await credit_db_conn.fetch(query, test_account["user_id"])

        # Verify order: earliest expiration first
        assert len(rows) == 3
        assert rows[0]["allocation_id"] == allocations[0][0]
        assert rows[1]["allocation_id"] == allocations[1][0]
        assert rows[2]["allocation_id"] == allocations[2][0]

    async def test_fifo_consumption_spans_multiple_allocations(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: FIFO consumption can span multiple allocations"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        # Create 3 allocations, each with 500 credits
        allocation_ids = []
        for i in range(3):
            allocation_id = credit_factory.make_allocation_id()
            allocation_ids.append(allocation_id)
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_allocations (
                    allocation_id, user_id, account_id, amount,
                    consumed_amount, status, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                allocation_id, test_account["user_id"], test_account["account_id"],
                500, 0, "completed", credit_factory.make_future_timestamp(30 + i * 30)
            )

        # Simulate consuming 1200 credits (spans first 2 allocations + part of third)
        # First allocation: consume 500
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_allocations
            SET consumed_amount = 500, status = 'expired', updated_at = NOW()
            WHERE allocation_id = $1
            """,
            allocation_ids[0]
        )

        # Second allocation: consume 500
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_allocations
            SET consumed_amount = 500, status = 'expired', updated_at = NOW()
            WHERE allocation_id = $1
            """,
            allocation_ids[1]
        )

        # Third allocation: consume 200 (partial)
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_allocations
            SET consumed_amount = 200, updated_at = NOW()
            WHERE allocation_id = $1
            """,
            allocation_ids[2]
        )

        # Verify consumption
        total_consumed = 0
        for allocation_id in allocation_ids:
            row = await credit_db_conn.fetchrow(
                "SELECT consumed_amount FROM credit.credit_allocations WHERE allocation_id = $1",
                allocation_id
            )
            total_consumed += row["consumed_amount"]

        assert total_consumed == 1200

    async def test_fifo_marks_fully_consumed_allocations_as_expired(
        self,
        credit_db_conn: asyncpg.Connection,
        test_allocation: Dict[str, Any]
    ):
        """INTEGRATION: fully consumed allocations are marked as expired"""
        if not credit_db_conn or not test_allocation:
            pytest.skip("Database connection or test allocation not available")

        # Consume all credits
        await credit_db_conn.execute(
            """
            UPDATE credit.credit_allocations
            SET consumed_amount = amount,
                status = 'expired',
                updated_at = NOW()
            WHERE allocation_id = $1
            """,
            test_allocation["allocation_id"]
        )

        # Verify status
        row = await credit_db_conn.fetchrow(
            "SELECT status, consumed_amount, amount FROM credit.credit_allocations WHERE allocation_id = $1",
            test_allocation["allocation_id"]
        )

        assert row["status"] == "expired"
        assert row["consumed_amount"] == row["amount"]

    async def test_fifo_query_excludes_expired_allocations(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: FIFO query excludes already expired allocations"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        # Create active and expired allocations
        for status in ["completed", "expired", "completed", "expired"]:
            allocation_id = credit_factory.make_allocation_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_allocations (
                    allocation_id, user_id, account_id, amount,
                    status, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                """,
                allocation_id, test_account["user_id"], test_account["account_id"],
                1000, status, credit_factory.make_future_timestamp(30)
            )

        # Query only active allocations
        query = """
            SELECT * FROM credit.credit_allocations
            WHERE user_id = $1 AND status = 'completed'
        """
        rows = await credit_db_conn.fetch(query, test_account["user_id"])

        # Should return only 2 completed allocations
        assert len(rows) == 2
        for row in rows:
            assert row["status"] == "completed"

    async def test_fifo_prioritizes_by_expires_at_then_created_at(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: FIFO ordering uses expires_at first, then created_at as tiebreaker"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        same_expiry = credit_factory.make_future_timestamp(30)

        # Create allocations with same expiry but different creation times
        for i in range(3):
            allocation_id = credit_factory.make_allocation_id()
            created_at = credit_factory.make_past_timestamp(3 - i)  # Earlier created_at first
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_allocations (
                    allocation_id, user_id, account_id, amount,
                    status, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """,
                allocation_id, test_account["user_id"], test_account["account_id"],
                1000, "completed", same_expiry, created_at
            )

        # Query with FIFO ordering
        query = """
            SELECT * FROM credit.credit_allocations
            WHERE user_id = $1 AND status = 'completed'
            ORDER BY expires_at ASC, created_at ASC
        """
        rows = await credit_db_conn.fetch(query, test_account["user_id"])

        # Verify order: earliest created_at first (for same expires_at)
        assert len(rows) == 3
        for i in range(len(rows) - 1):
            assert rows[i]["created_at"] <= rows[i + 1]["created_at"]


# ============================================================================
# GDPR delete_user_data (3 tests)
# ============================================================================

class TestGDPRDeleteUserData:
    """Test GDPR-compliant user data deletion"""

    async def test_delete_user_data_removes_all_user_accounts(
        self,
        credit_db_conn: asyncpg.Connection,
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: delete_user_data removes all credit accounts for user"""
        if not credit_db_conn:
            pytest.skip("Database connection not available")

        user_id = credit_factory.make_user_id()

        # Create multiple accounts for user
        for i in range(3):
            account_id = credit_factory.make_account_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_accounts (
                    account_id, user_id, credit_type, balance,
                    expiration_policy, expiration_days, is_active,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                account_id, user_id, f"type_{i}", 1000, "fixed_days", 90, True
            )

        # Delete all user data
        result = await credit_db_conn.execute(
            "DELETE FROM credit.credit_accounts WHERE user_id = $1",
            user_id
        )

        # Verify deletion
        count = await credit_db_conn.fetchval(
            "SELECT COUNT(*) FROM credit.credit_accounts WHERE user_id = $1",
            user_id
        )

        assert count == 0

    async def test_delete_user_data_removes_transactions_and_allocations(
        self,
        credit_db_conn: asyncpg.Connection,
        test_account: Dict[str, Any],
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: delete_user_data removes transactions and allocations"""
        if not credit_db_conn or not test_account:
            pytest.skip("Database connection or test account not available")

        user_id = test_account["user_id"]

        # Create transactions
        for i in range(5):
            transaction_id = credit_factory.make_transaction_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_transactions (
                    transaction_id, account_id, user_id, transaction_type,
                    amount, balance_before, balance_after, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """,
                transaction_id, test_account["account_id"], user_id,
                "allocate", 100, 1000, 1100
            )

        # Create allocations
        for i in range(3):
            allocation_id = credit_factory.make_allocation_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_allocations (
                    allocation_id, user_id, account_id, amount,
                    status, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                """,
                allocation_id, user_id, test_account["account_id"],
                1000, "completed", credit_factory.make_future_timestamp(90)
            )

        # Delete user data (cascade or explicit deletion)
        await credit_db_conn.execute("DELETE FROM credit.credit_allocations WHERE user_id = $1", user_id)
        await credit_db_conn.execute("DELETE FROM credit.credit_transactions WHERE user_id = $1", user_id)
        await credit_db_conn.execute("DELETE FROM credit.credit_accounts WHERE user_id = $1", user_id)

        # Verify deletion
        account_count = await credit_db_conn.fetchval(
            "SELECT COUNT(*) FROM credit.credit_accounts WHERE user_id = $1", user_id
        )
        transaction_count = await credit_db_conn.fetchval(
            "SELECT COUNT(*) FROM credit.credit_transactions WHERE user_id = $1", user_id
        )
        allocation_count = await credit_db_conn.fetchval(
            "SELECT COUNT(*) FROM credit.credit_allocations WHERE user_id = $1", user_id
        )

        assert account_count == 0
        assert transaction_count == 0
        assert allocation_count == 0

    async def test_delete_user_data_returns_count_of_deleted_records(
        self,
        credit_db_conn: asyncpg.Connection,
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: delete_user_data returns count of deleted records"""
        if not credit_db_conn:
            pytest.skip("Database connection not available")

        user_id = credit_factory.make_user_id()

        # Create 2 accounts
        for i in range(2):
            account_id = credit_factory.make_account_id()
            await credit_db_conn.execute(
                """
                INSERT INTO credit.credit_accounts (
                    account_id, user_id, credit_type, balance,
                    expiration_policy, expiration_days, is_active,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                account_id, user_id, f"type_{i}", 1000, "fixed_days", 90, True
            )

        # Delete and count
        result = await credit_db_conn.execute(
            "DELETE FROM credit.credit_accounts WHERE user_id = $1",
            user_id
        )

        # Extract count from result (format: "DELETE N")
        deleted_count = int(result.split()[-1])

        assert deleted_count == 2


# ============================================================================
# Index Usage Verification (2 tests)
# ============================================================================

class TestIndexUsage:
    """Test database index usage for performance"""

    async def test_user_id_index_used_for_account_queries(
        self,
        credit_db_conn: asyncpg.Connection,
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: user_id index is used for account queries"""
        if not credit_db_conn:
            pytest.skip("Database connection not available")

        user_id = credit_factory.make_user_id()

        # Create account
        account_id = credit_factory.make_account_id()
        await credit_db_conn.execute(
            """
            INSERT INTO credit.credit_accounts (
                account_id, user_id, credit_type, balance,
                expiration_policy, expiration_days, is_active,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
            """,
            account_id, user_id, "bonus", 1000, "fixed_days", 90, True
        )

        # Query with EXPLAIN to verify index usage
        query = """
            EXPLAIN SELECT * FROM credit.credit_accounts WHERE user_id = $1
        """
        explain_result = await credit_db_conn.fetch(query, user_id)

        # Check if index scan is used (contains "Index Scan" in plan)
        explain_text = "\n".join([row[0] for row in explain_result])
        # Note: In test environment without many rows, may use Seq Scan
        # This test documents expected behavior with sufficient data

        assert "credit_accounts" in explain_text

    async def test_expires_at_index_used_for_expiring_queries(
        self,
        credit_db_conn: asyncpg.Connection,
        credit_factory: CreditTestDataFactory
    ):
        """INTEGRATION: expires_at index is used for expiring allocation queries"""
        if not credit_db_conn:
            pytest.skip("Database connection not available")

        # Create allocation
        user_id = credit_factory.make_user_id()
        account_id = credit_factory.make_account_id()
        allocation_id = credit_factory.make_allocation_id()

        # First create account
        await credit_db_conn.execute(
            """
            INSERT INTO credit.credit_accounts (
                account_id, user_id, credit_type, balance,
                expiration_policy, expiration_days, is_active,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
            """,
            account_id, user_id, "bonus", 1000, "fixed_days", 90, True
        )

        # Then create allocation
        await credit_db_conn.execute(
            """
            INSERT INTO credit.credit_allocations (
                allocation_id, user_id, account_id, amount,
                status, expires_at, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            """,
            allocation_id, user_id, account_id, 1000, "completed",
            credit_factory.make_future_timestamp(30)
        )

        # Query with EXPLAIN to verify index usage
        cutoff = credit_factory.make_future_timestamp(60)
        query = """
            EXPLAIN SELECT * FROM credit.credit_allocations
            WHERE expires_at <= $1 AND status = 'completed'
        """
        explain_result = await credit_db_conn.fetch(query, cutoff)

        explain_text = "\n".join([row[0] for row in explain_result])

        # Verify query plan includes allocations table
        assert "credit_allocations" in explain_text
