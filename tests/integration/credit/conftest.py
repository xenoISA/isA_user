"""
Credit Service Integration Test Fixtures

Provides database fixtures and test data for credit repository integration tests.
"""

import os
import sys
import pytest
import pytest_asyncio
import asyncpg
from typing import AsyncGenerator, Dict, Any

# Add paths for imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_current_dir, "../../..")
sys.path.insert(0, _project_root)

from tests.contracts.credit.data_contract import CreditTestDataFactory


@pytest_asyncio.fixture(scope="function")
async def credit_db_pool(config) -> AsyncGenerator[asyncpg.Pool, None]:
    """
    PostgreSQL connection pool for credit_db

    Creates a dedicated connection pool for credit service database.
    Automatically creates the credit schema if it doesn't exist.
    """
    pool = None
    try:
        # Create connection pool
        pool = await asyncpg.create_pool(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            database="credit_db",
            min_size=1,
            max_size=5,
            timeout=30
        )

        # Ensure schema exists
        async with pool.acquire() as conn:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS credit")

        yield pool

    except Exception as e:
        print(f"Warning: Could not connect to credit_db: {e}")
        yield None
    finally:
        if pool:
            await pool.close()


@pytest_asyncio.fixture(scope="function")
async def credit_db_conn(credit_db_pool) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    PostgreSQL connection for credit_db

    Provides a single connection from the pool for test operations.
    Automatically rolls back after each test to maintain isolation.
    """
    if not credit_db_pool:
        yield None
        return

    async with credit_db_pool.acquire() as conn:
        # Start transaction for test isolation
        transaction = conn.transaction()
        await transaction.start()

        try:
            yield conn
        finally:
            # Rollback to clean up test data
            await transaction.rollback()


@pytest.fixture(scope="session")
def credit_factory():
    """
    Credit test data factory

    Provides CreditTestDataFactory instance for generating test data.
    """
    return CreditTestDataFactory()


@pytest_asyncio.fixture(scope="function")
async def clean_credit_tables(credit_db_conn):
    """
    Clean credit tables before each test

    Ensures a clean state by truncating all credit tables.
    Use this fixture when you need a completely clean database state.
    """
    if not credit_db_conn:
        return

    try:
        # Truncate tables in reverse dependency order
        await credit_db_conn.execute("TRUNCATE TABLE credit.credit_allocations CASCADE")
        await credit_db_conn.execute("TRUNCATE TABLE credit.credit_transactions CASCADE")
        await credit_db_conn.execute("TRUNCATE TABLE credit.credit_campaigns CASCADE")
        await credit_db_conn.execute("TRUNCATE TABLE credit.credit_accounts CASCADE")
    except Exception as e:
        print(f"Warning: Could not clean credit tables: {e}")


@pytest_asyncio.fixture(scope="function")
async def test_account(credit_db_conn, credit_factory) -> Dict[str, Any]:
    """
    Create a test credit account

    Returns:
        Dict with account_id, user_id, credit_type, and balance
    """
    if not credit_db_conn:
        return None

    user_id = credit_factory.make_user_id()
    account_id = credit_factory.make_account_id()
    credit_type = "bonus"

    query = """
        INSERT INTO credit.credit_accounts (
            account_id, user_id, credit_type, balance,
            total_allocated, total_consumed, total_expired,
            expiration_policy, expiration_days, is_active,
            created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
        RETURNING *
    """

    row = await credit_db_conn.fetchrow(
        query,
        account_id, user_id, credit_type, 1000,
        1000, 0, 0,
        "fixed_days", 90, True
    )

    return {
        "account_id": row["account_id"],
        "user_id": row["user_id"],
        "credit_type": row["credit_type"],
        "balance": row["balance"]
    }


@pytest_asyncio.fixture(scope="function")
async def test_campaign(credit_db_conn, credit_factory) -> Dict[str, Any]:
    """
    Create a test credit campaign

    Returns:
        Dict with campaign_id, name, credit_type, and budget info
    """
    if not credit_db_conn:
        return None

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
        credit_factory.make_past_timestamp(1), credit_factory.make_future_timestamp(30), 90,
        1, True
    )

    return {
        "campaign_id": row["campaign_id"],
        "name": row["name"],
        "credit_type": row["credit_type"],
        "total_budget": row["total_budget"],
        "allocated_amount": row["allocated_amount"]
    }


@pytest_asyncio.fixture(scope="function")
async def test_allocation(credit_db_conn, credit_factory, test_account) -> Dict[str, Any]:
    """
    Create a test credit allocation

    Returns:
        Dict with allocation_id, user_id, amount, and expires_at
    """
    if not credit_db_conn or not test_account:
        return None

    allocation_id = credit_factory.make_allocation_id()

    query = """
        INSERT INTO credit.credit_allocations (
            allocation_id, user_id, account_id, amount,
            status, expires_at, created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
        RETURNING *
    """

    row = await credit_db_conn.fetchrow(
        query,
        allocation_id, test_account["user_id"], test_account["account_id"], 1000,
        "completed", credit_factory.make_future_timestamp(90)
    )

    return {
        "allocation_id": row["allocation_id"],
        "user_id": row["user_id"],
        "account_id": row["account_id"],
        "amount": row["amount"],
        "expires_at": row["expires_at"]
    }


# Helper functions for assertions

async def get_account_balance(conn: asyncpg.Connection, account_id: str) -> int:
    """Get current account balance"""
    row = await conn.fetchrow(
        "SELECT balance FROM credit.credit_accounts WHERE account_id = $1",
        account_id
    )
    return row["balance"] if row else 0


async def get_transaction_count(conn: asyncpg.Connection, account_id: str) -> int:
    """Get transaction count for account"""
    row = await conn.fetchrow(
        "SELECT COUNT(*) as cnt FROM credit.credit_transactions WHERE account_id = $1",
        account_id
    )
    return row["cnt"] if row else 0


async def get_user_total_balance(conn: asyncpg.Connection, user_id: str) -> int:
    """Get total balance across all user accounts"""
    row = await conn.fetchrow(
        "SELECT COALESCE(SUM(balance), 0) as total FROM credit.credit_accounts WHERE user_id = $1",
        user_id
    )
    return row["total"] if row else 0
