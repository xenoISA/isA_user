"""
Wallet Service Event Publishing Tests

Tests that Wallet Service correctly publishes events for all wallet operations
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.nats_client import Event, EventType, ServiceSource
from microservices.wallet_service.wallet_service import WalletService
from microservices.wallet_service.models import (
    WalletCreate, DepositRequest, WithdrawRequest, ConsumeRequest,
    TransferRequest, RefundRequest, WalletType, WalletBalance, WalletTransaction,
    TransactionType
)


class MockEventBus:
    """Mock event bus for testing"""

    def __init__(self):
        self.published_events = []

    async def publish_event(self, event: Event):
        """Mock publish event"""
        self.published_events.append(event)
        print(f"✅ Event captured: {event.type}")
        print(f"   Data: {event.data}")


class MockWalletRepository:
    """Mock Wallet Repository for testing"""

    def __init__(self):
        self.wallets = {}
        self.transactions = []

    async def get_user_wallets(self, user_id: str, wallet_type=None):
        """Mock get user wallets"""
        return []

    async def create_wallet(self, wallet_data):
        """Mock create wallet"""
        wallet = WalletBalance(
            wallet_id="wallet_123",
            user_id=wallet_data.user_id,
            wallet_type=wallet_data.wallet_type,
            currency=wallet_data.currency or "USD",
            balance=Decimal("0"),
            locked_balance=Decimal("0"),
            available_balance=Decimal("0"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc)
        )
        self.wallets[wallet.wallet_id] = wallet
        return wallet

    async def deposit(self, wallet_id, amount, description, reference_id=None, metadata=None):
        """Mock deposit"""
        transaction = WalletTransaction(
            transaction_id="txn_deposit_123",
            wallet_id=wallet_id,
            user_id="user_456",
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            balance_before=Decimal("100"),
            balance_after=Decimal("100") + amount,
            description=description,
            reference_id=reference_id,
            metadata=metadata,
            created_at=datetime.now(timezone.utc)
        )
        self.transactions.append(transaction)
        return transaction

    async def withdraw(self, wallet_id, amount, description, destination=None, metadata=None):
        """Mock withdraw"""
        transaction = WalletTransaction(
            transaction_id="txn_withdraw_123",
            wallet_id=wallet_id,
            user_id="user_456",
            transaction_type=TransactionType.WITHDRAW,
            amount=amount,
            balance_before=Decimal("100"),
            balance_after=Decimal("100") - amount,
            description=description,
            metadata=metadata,
            created_at=datetime.now(timezone.utc)
        )
        self.transactions.append(transaction)
        return transaction

    async def consume(self, wallet_id, amount, description, usage_record_id=None, metadata=None):
        """Mock consume"""
        transaction = WalletTransaction(
            transaction_id="txn_consume_123",
            wallet_id=wallet_id,
            user_id="user_456",
            transaction_type=TransactionType.CONSUME,
            amount=amount,
            balance_before=Decimal("100"),
            balance_after=Decimal("100") - amount,
            description=description,
            metadata=metadata,
            created_at=datetime.now(timezone.utc)
        )
        self.transactions.append(transaction)
        return transaction

    async def transfer(self, from_wallet_id, to_wallet_id, amount, description, metadata=None):
        """Mock transfer"""
        from_txn = WalletTransaction(
            transaction_id="txn_transfer_from_123",
            wallet_id=from_wallet_id,
            user_id="user_from",
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            balance_before=Decimal("100"),
            balance_after=Decimal("100") - amount,
            description=description,
            metadata=metadata,
            created_at=datetime.now(timezone.utc)
        )
        to_txn = WalletTransaction(
            transaction_id="txn_transfer_to_123",
            wallet_id=to_wallet_id,
            user_id="user_to",
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            balance_before=Decimal("50"),
            balance_after=Decimal("50") + amount,
            description=description,
            metadata=metadata,
            created_at=datetime.now(timezone.utc)
        )
        self.transactions.extend([from_txn, to_txn])
        return (from_txn, to_txn)

    async def refund(self, original_transaction_id, amount=None, reason=None, metadata=None):
        """Mock refund"""
        transaction = WalletTransaction(
            transaction_id="txn_refund_123",
            wallet_id="wallet_123",
            user_id="user_456",
            transaction_type=TransactionType.REFUND,
            amount=Decimal("50"),
            balance_before=Decimal("100"),
            balance_after=Decimal("150"),
            description=f"Refund for {original_transaction_id}",
            metadata=metadata,
            created_at=datetime.now(timezone.utc)
        )
        self.transactions.append(transaction)
        return transaction

    async def get_wallet(self, wallet_id):
        """Mock get wallet"""
        return self.wallets.get(wallet_id)


async def test_wallet_created_event():
    """Test that wallet.created event is published"""
    print("\n" + "="*60)
    print("TEST 1: Wallet Created Event Publishing")
    print("="*60)

    mock_event_bus = MockEventBus()
    wallet_service = WalletService(event_bus=mock_event_bus)
    wallet_service.repository = MockWalletRepository()

    # Create wallet
    wallet_data = WalletCreate(
        user_id="user_456",
        wallet_type=WalletType.FIAT,
        currency="USD"
    )

    response = await wallet_service.create_wallet(wallet_data)

    # Verify response
    assert response.success, "Wallet creation should succeed"
    assert response.wallet_id is not None, "Wallet ID should be returned"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Should publish 1 event"
    event = mock_event_bus.published_events[0]

    assert event.type == "wallet.created", f"Event type should be wallet.created, got {event.type}"
    assert event.source == "wallet_service", f"Event source should be wallet_service, got {event.source}"
    assert event.data["user_id"] == "user_456"
    assert event.data["wallet_type"] == "fiat"
    assert event.data["currency"] == "USD"

    print("✅ wallet.created event published correctly")
    print(f"   Wallet ID: {response.wallet_id}")
    print(f"   User: {event.data['user_id']}")

    return True


async def test_wallet_deposited_event():
    """Test that wallet.deposited event is published"""
    print("\n" + "="*60)
    print("TEST 2: Wallet Deposited Event Publishing")
    print("="*60)

    mock_event_bus = MockEventBus()
    wallet_service = WalletService(event_bus=mock_event_bus)
    wallet_service.repository = MockWalletRepository()

    # Deposit funds
    request = DepositRequest(
        amount=Decimal("100.50"),
        description="Test deposit",
        reference_id="ref_123"
    )

    response = await wallet_service.deposit("wallet_123", request)

    # Verify response
    assert response.success, "Deposit should succeed"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Should publish 1 event"
    event = mock_event_bus.published_events[0]

    assert event.type == "wallet.deposited"
    assert event.data["wallet_id"] == "wallet_123"
    assert event.data["amount"] == 100.50
    assert event.data["description"] == "Test deposit"
    assert event.data["reference_id"] == "ref_123"

    print("✅ wallet.deposited event published correctly")
    print(f"   Amount: ${event.data['amount']}")
    print(f"   Balance after: ${event.data['balance_after']}")

    return True


async def test_wallet_withdrawn_event():
    """Test that wallet.withdrawn event is published"""
    print("\n" + "="*60)
    print("TEST 3: Wallet Withdrawn Event Publishing")
    print("="*60)

    mock_event_bus = MockEventBus()
    wallet_service = WalletService(event_bus=mock_event_bus)
    mock_repo = MockWalletRepository()
    wallet_service.repository = mock_repo

    # Create a mock wallet first (needed by withdraw method)
    mock_wallet = WalletBalance(
        wallet_id="wallet_123",
        user_id="user_456",
        wallet_type=WalletType.FIAT,
        currency="USD",
        balance=Decimal("100"),
        locked_balance=Decimal("0"),
        available_balance=Decimal("100"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc)
    )
    mock_repo.wallets["wallet_123"] = mock_wallet

    # Withdraw funds
    request = WithdrawRequest(
        amount=Decimal("25.00"),
        description="Test withdrawal",
        destination="bank_account_123"
    )

    response = await wallet_service.withdraw("wallet_123", request)

    # Verify response
    assert response.success, f"Withdrawal should succeed, got: {response.message}"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Should publish 1 event"
    event = mock_event_bus.published_events[0]

    assert event.type == "wallet.withdrawn"
    assert event.data["wallet_id"] == "wallet_123"
    assert event.data["amount"] == 25.00
    assert event.data["destination"] == "bank_account_123"

    print("✅ wallet.withdrawn event published correctly")
    print(f"   Amount: ${event.data['amount']}")
    print(f"   Destination: {event.data['destination']}")

    return True


async def test_wallet_consumed_event():
    """Test that wallet.consumed event is published"""
    print("\n" + "="*60)
    print("TEST 4: Wallet Consumed Event Publishing")
    print("="*60)

    mock_event_bus = MockEventBus()
    wallet_service = WalletService(event_bus=mock_event_bus)
    wallet_service.repository = MockWalletRepository()

    # Consume credits
    request = ConsumeRequest(
        amount=Decimal("10.00"),
        description="AI tokens consumed",
        usage_record_id=12345  # Integer, not string
    )

    response = await wallet_service.consume("wallet_123", request)

    # Verify response
    assert response.success, "Consumption should succeed"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Should publish 1 event"
    event = mock_event_bus.published_events[0]

    assert event.type == "wallet.consumed"
    assert event.data["wallet_id"] == "wallet_123"
    assert event.data["amount"] == 10.00
    assert event.data["usage_record_id"] == 12345

    print("✅ wallet.consumed event published correctly")
    print(f"   Amount: ${event.data['amount']}")
    print(f"   Usage record: {event.data['usage_record_id']}")

    return True


async def test_wallet_transferred_event():
    """Test that wallet.transferred event is published"""
    print("\n" + "="*60)
    print("TEST 5: Wallet Transferred Event Publishing")
    print("="*60)

    mock_event_bus = MockEventBus()
    wallet_service = WalletService(event_bus=mock_event_bus)
    wallet_service.repository = MockWalletRepository()

    # Transfer funds
    request = TransferRequest(
        to_wallet_id="wallet_456",
        amount=Decimal("75.00"),
        description="Transfer to friend"
    )

    response = await wallet_service.transfer("wallet_123", request)

    # Verify response
    assert response.success, "Transfer should succeed"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Should publish 1 event"
    event = mock_event_bus.published_events[0]

    assert event.type == "wallet.transferred"
    assert event.data["from_wallet_id"] == "wallet_123"
    assert event.data["to_wallet_id"] == "wallet_456"
    assert event.data["amount"] == 75.00

    print("✅ wallet.transferred event published correctly")
    print(f"   From: {event.data['from_wallet_id']}")
    print(f"   To: {event.data['to_wallet_id']}")
    print(f"   Amount: ${event.data['amount']}")

    return True


async def test_wallet_refunded_event():
    """Test that wallet.refunded event is published"""
    print("\n" + "="*60)
    print("TEST 6: Wallet Refunded Event Publishing")
    print("="*60)

    mock_event_bus = MockEventBus()
    wallet_service = WalletService(event_bus=mock_event_bus)
    wallet_service.repository = MockWalletRepository()

    # Refund transaction
    request = RefundRequest(
        original_transaction_id="original_txn_123",
        amount=Decimal("50.00"),
        reason="Customer request"
    )

    response = await wallet_service.refund("original_txn_123", request)

    # Verify response
    assert response.success, "Refund should succeed"

    # Verify event was published
    assert len(mock_event_bus.published_events) == 1, "Should publish 1 event"
    event = mock_event_bus.published_events[0]

    assert event.type == "wallet.refunded"
    assert event.data["original_transaction_id"] == "original_txn_123"
    assert event.data["amount"] == 50.0
    assert event.data["reason"] == "Customer request"

    print("✅ wallet.refunded event published correctly")
    print(f"   Amount: ${event.data['amount']}")
    print(f"   Reason: {event.data['reason']}")

    return True


async def run_all_tests():
    """Run all wallet event publishing tests"""
    print("\n" + "="*80)
    print("WALLET SERVICE EVENT PUBLISHING TEST SUITE")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Run tests
    try:
        results["wallet_created"] = await test_wallet_created_event()
    except AssertionError as e:
        print(f"❌ TEST 1 FAILED: {e}")
        results["wallet_created"] = False
    except Exception as e:
        print(f"❌ TEST 1 ERROR: {e}")
        import traceback
        traceback.print_exc()
        results["wallet_created"] = False

    try:
        results["wallet_deposited"] = await test_wallet_deposited_event()
    except AssertionError as e:
        print(f"❌ TEST 2 FAILED: {e}")
        results["wallet_deposited"] = False
    except Exception as e:
        print(f"❌ TEST 2 ERROR: {e}")
        import traceback
        traceback.print_exc()
        results["wallet_deposited"] = False

    try:
        results["wallet_withdrawn"] = await test_wallet_withdrawn_event()
    except AssertionError as e:
        print(f"❌ TEST 3 FAILED: {e}")
        results["wallet_withdrawn"] = False
    except Exception as e:
        print(f"❌ TEST 3 ERROR: {e}")
        import traceback
        traceback.print_exc()
        results["wallet_withdrawn"] = False

    try:
        results["wallet_consumed"] = await test_wallet_consumed_event()
    except AssertionError as e:
        print(f"❌ TEST 4 FAILED: {e}")
        results["wallet_consumed"] = False
    except Exception as e:
        print(f"❌ TEST 4 ERROR: {e}")
        import traceback
        traceback.print_exc()
        results["wallet_consumed"] = False

    try:
        results["wallet_transferred"] = await test_wallet_transferred_event()
    except AssertionError as e:
        print(f"❌ TEST 5 FAILED: {e}")
        results["wallet_transferred"] = False
    except Exception as e:
        print(f"❌ TEST 5 ERROR: {e}")
        import traceback
        traceback.print_exc()
        results["wallet_transferred"] = False

    try:
        results["wallet_refunded"] = await test_wallet_refunded_event()
    except AssertionError as e:
        print(f"❌ TEST 6 FAILED: {e}")
        results["wallet_refunded"] = False
    except Exception as e:
        print(f"❌ TEST 6 ERROR: {e}")
        import traceback
        traceback.print_exc()
        results["wallet_refunded"] = False

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
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_all_tests())
    sys.exit(0 if passed == total else 1)
