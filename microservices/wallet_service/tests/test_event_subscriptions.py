#!/usr/bin/env python3
"""
Test Wallet Service Event Subscriptions

Tests that wallet service correctly subscribes to and processes events from NATS
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from microservices.wallet_service.wallet_service import WalletService
from microservices.wallet_service.models import (
    WalletCreate, DepositRequest, WalletType, TransactionType
)
from core.nats_client import Event, EventType, ServiceSource


class MockWalletRepository:
    """Mock wallet repository for testing"""

    def __init__(self):
        self.wallets = {}
        self.transactions = []

    async def get_primary_wallet(self, user_id):
        """Mock get primary wallet"""
        return self.wallets.get(user_id)

    async def create_wallet(self, wallet):
        """Mock create wallet"""
        self.wallets[wallet.user_id] = wallet
        return wallet

    async def get_wallet_by_id(self, wallet_id):
        """Mock get wallet by id"""
        for wallet in self.wallets.values():
            if wallet.wallet_id == wallet_id:
                return wallet
        return None

    async def record_transaction(self, transaction):
        """Mock record transaction"""
        self.transactions.append(transaction)
        return transaction

    async def update_wallet_balance(self, wallet_id, new_balance, new_available_balance):
        """Mock update wallet balance"""
        return True

    async def check_connection(self):
        """Mock check connection"""
        return True


class MockWalletService:
    """Mock wallet service for testing"""

    def __init__(self):
        self.repository = MockWalletRepository()
        self.deposits = []
        self.wallets_created = []

    async def deposit(self, wallet_id: str, request: DepositRequest):
        """Mock deposit"""
        # Get user_id from wallet
        wallet = await self.repository.get_wallet_by_id(wallet_id)
        user_id = wallet.user_id if wallet else "unknown"

        self.deposits.append({
            "wallet_id": wallet_id,
            "user_id": user_id,
            "amount": request.amount,
            "description": request.description,
            "reference_id": request.reference_id
        })
        return type('obj', (object,), {
            'success': True,
            'transaction_id': f"txn_{request.reference_id}",
            'balance': Decimal("100.00")
        })

    async def create_wallet(self, request: WalletCreate):
        """Mock create wallet"""
        wallet = type('obj', (object,), {
            'wallet_id': f"wallet_{request.user_id}",
            'user_id': request.user_id,
            'wallet_type': request.wallet_type,
            'currency': request.currency,
            'balance': request.initial_balance
        })
        self.wallets_created.append(wallet)
        return wallet


async def test_payment_completed_event():
    """Test wallet service handles payment.completed events"""
    print("\n" + "="*60)
    print("TEST 1: Payment Completed Event → Wallet Deposit")
    print("="*60)

    # Create mock wallet service
    mock_wallet = MockWalletService()

    # Create a mock wallet for the user
    mock_wallet.repository.wallets["user_456"] = type('obj', (object,), {
        'wallet_id': 'wallet_456',
        'user_id': 'user_456',
        'balance': Decimal("0")
    })

    # Import event handler from main.py
    from microservices.wallet_service import main
    main.wallet_microservice.wallet_service = mock_wallet

    # Create a payment.completed event
    event = Event(
        event_type=EventType.PAYMENT_COMPLETED,
        source=ServiceSource.PAYMENT_SERVICE,
        data={
            "payment_id": "pay_123",
            "user_id": "user_456",
            "amount": 50.00,
            "currency": "USD",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event
    await main.handle_payment_completed(event)

    # Verify deposit was made
    assert len(mock_wallet.deposits) == 1, "Expected 1 deposit"
    deposit = mock_wallet.deposits[0]

    assert deposit["user_id"] == "user_456"
    assert deposit["amount"] == Decimal("50.00")
    assert deposit["reference_id"] == "pay_123"
    assert "Payment received" in deposit["description"]

    print(f"✅ payment.completed event processed successfully")
    print(f"   User ID: {deposit['user_id']}")
    print(f"   Amount: ${deposit['amount']}")
    print(f"   Reference: {deposit['reference_id']}")

    return True


async def test_user_created_event():
    """Test wallet service handles user.created events"""
    print("\n" + "="*60)
    print("TEST 2: User Created Event → Auto-create Wallet")
    print("="*60)

    # Create mock wallet service
    mock_wallet = MockWalletService()

    # Import event handler from main.py
    from microservices.wallet_service import main
    main.wallet_microservice.wallet_service = mock_wallet

    # Create a user.created event
    event = Event(
        event_type=EventType.USER_CREATED,
        source=ServiceSource.ACCOUNT_SERVICE,
        data={
            "user_id": "user_789",
            "email": "test@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Handle the event
    await main.handle_user_created(event)

    # Verify wallet was created
    assert len(mock_wallet.wallets_created) == 1, "Expected 1 wallet created"
    wallet = mock_wallet.wallets_created[0]

    assert wallet.user_id == "user_789"
    assert wallet.wallet_type == WalletType.FIAT
    assert wallet.currency == "USD"
    assert wallet.balance == Decimal("0")

    print(f"✅ user.created event processed successfully")
    print(f"   User ID: {wallet.user_id}")
    print(f"   Wallet ID: {wallet.wallet_id}")
    print(f"   Type: {wallet.wallet_type}")
    print(f"   Initial Balance: ${wallet.balance}")

    return True


async def test_idempotency():
    """Test event idempotency - same event processed twice"""
    print("\n" + "="*60)
    print("TEST 3: Event Idempotency")
    print("="*60)

    # Create mock wallet service
    mock_wallet = MockWalletService()

    # Create a mock wallet for the user
    mock_wallet.repository.wallets["user_123"] = type('obj', (object,), {
        'wallet_id': 'wallet_123',
        'user_id': 'user_123',
        'balance': Decimal("0")
    })

    # Import event handler from main.py
    from microservices.wallet_service import main
    main.wallet_microservice.wallet_service = mock_wallet

    # Create a payment.completed event
    event = Event(
        event_type=EventType.PAYMENT_COMPLETED,
        source=ServiceSource.PAYMENT_SERVICE,
        data={
            "payment_id": "pay_idempotent",
            "user_id": "user_123",
            "amount": 25.00,
            "currency": "USD"
        }
    )

    # Process event first time
    await main.handle_payment_completed(event)
    first_count = len(mock_wallet.deposits)

    # Process same event again (should be skipped)
    await main.handle_payment_completed(event)
    second_count = len(mock_wallet.deposits)

    # Verify event was only processed once
    assert first_count == 1, "Expected 1 deposit after first processing"
    assert second_count == 1, "Expected still 1 deposit after duplicate event"

    print(f"✅ Event idempotency works correctly")
    print(f"   First processing: {first_count} deposits")
    print(f"   Duplicate processing: {second_count} deposits (no change)")

    return True


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("WALLET SERVICE EVENT SUBSCRIPTION TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["payment_completed"] = await test_payment_completed_event()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results["payment_completed"] = False

    try:
        results["user_created"] = await test_user_created_event()
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results["user_created"] = False

    try:
        results["idempotency"] = await test_idempotency()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results["idempotency"] = False

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL WALLET SERVICE EVENT TESTS PASSED!")
        print("\nEvent Subscriptions Verified:")
        print("  ✅ payment.completed → Automatic wallet deposit")
        print("  ✅ user.created → Automatic wallet creation")
        print("  ✅ Event idempotency working correctly")
    else:
        print("\n⚠️  Some tests failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())

    # Exit with appropriate code
    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)
