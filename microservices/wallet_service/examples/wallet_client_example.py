"""
Wallet Service Client Example

Professional client for digital wallet management with transaction operations.
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class WalletInfo:
    """Wallet information"""
    wallet_id: str
    user_id: str
    balance: Decimal
    locked_balance: Decimal
    available_balance: Decimal
    currency: str
    wallet_type: str
    last_updated: str


@dataclass
class TransactionInfo:
    """Transaction information"""
    transaction_id: str
    wallet_id: str
    transaction_type: str
    amount: Decimal
    balance_after: Decimal
    description: str
    created_at: str


class WalletServiceClient:
    """Professional Wallet Service Client"""

    def __init__(
        self,
        base_url: str = "http://localhost:8208",
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self.request_count = 0
        self.error_count = 0

    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=60.0
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={
                "User-Agent": "wallet-client/1.0",
                "Accept": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.request_count += 1
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_exception = e
                if 400 <= e.response.status_code < 500:
                    self.error_count += 1
                    try:
                        error_detail = e.response.json()
                        raise Exception(error_detail.get("detail", str(e)))
                    except:
                        raise Exception(str(e))
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.2 * (2 ** attempt))
            except Exception as e:
                last_exception = e
                self.error_count += 1
                raise
        self.error_count += 1
        raise Exception(f"Request failed after {self.max_retries} attempts: {last_exception}")

    async def create_wallet(
        self,
        user_id: str,
        wallet_type: str = "fiat",
        initial_balance: float = 0.0,
        currency: str = "CREDIT",
        metadata: Optional[Dict[str, Any]] = None
    ) -> WalletInfo:
        """Create new wallet for user"""
        payload = {
            "user_id": user_id,
            "wallet_type": wallet_type,
            "initial_balance": initial_balance,
            "currency": currency
        }
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request("POST", "/api/v1/wallets", json=payload)

        if not result.get("success"):
            raise Exception(result.get("message", "Wallet creation failed"))

        wallet_data = result.get("data", {}).get("wallet", {})
        return WalletInfo(
            wallet_id=wallet_data["wallet_id"],
            user_id=wallet_data["user_id"],
            balance=Decimal(str(wallet_data["balance"])),
            locked_balance=Decimal(str(wallet_data.get("locked_balance", 0))),
            available_balance=Decimal(str(wallet_data["available_balance"])),
            currency=wallet_data["currency"],
            wallet_type=wallet_data["wallet_type"],
            last_updated=wallet_data["last_updated"]
        )

    async def get_wallet(self, wallet_id: str) -> WalletInfo:
        """Get wallet details by ID"""
        result = await self._make_request("GET", f"/api/v1/wallets/{wallet_id}")

        return WalletInfo(
            wallet_id=result["wallet_id"],
            user_id=result["user_id"],
            balance=Decimal(str(result["balance"])),
            locked_balance=Decimal(str(result.get("locked_balance", 0))),
            available_balance=Decimal(str(result["available_balance"])),
            currency=result["currency"],
            wallet_type=result["wallet_type"],
            last_updated=result["last_updated"]
        )

    async def get_user_wallets(self, user_id: str) -> List[WalletInfo]:
        """Get all wallets for user"""
        result = await self._make_request("GET", f"/api/v1/users/{user_id}/wallets")

        wallets = []
        for wallet_data in result.get("wallets", []):
            wallets.append(WalletInfo(
                wallet_id=wallet_data["wallet_id"],
                user_id=wallet_data["user_id"],
                balance=Decimal(str(wallet_data["balance"])),
                locked_balance=Decimal(str(wallet_data.get("locked_balance", 0))),
                available_balance=Decimal(str(wallet_data["available_balance"])),
                currency=wallet_data["currency"],
                wallet_type=wallet_data["wallet_type"],
                last_updated=wallet_data["last_updated"]
            ))
        return wallets

    async def get_balance(self, wallet_id: str) -> Dict[str, Any]:
        """Get wallet balance"""
        result = await self._make_request("GET", f"/api/v1/wallets/{wallet_id}/balance")

        if not result.get("success"):
            raise Exception(result.get("message", "Failed to get balance"))

        return result.get("data", {})

    async def deposit(
        self,
        wallet_id: str,
        amount: float,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransactionInfo:
        """Deposit funds to wallet"""
        payload = {"amount": amount}
        if description:
            payload["description"] = description
        if reference_id:
            payload["reference_id"] = reference_id
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "POST",
            f"/api/v1/wallets/{wallet_id}/deposit",
            json=payload
        )

        if not result.get("success"):
            raise Exception(result.get("message", "Deposit failed"))

        tx_data = result.get("data", {}).get("transaction", {})
        return TransactionInfo(
            transaction_id=tx_data["transaction_id"],
            wallet_id=tx_data["wallet_id"],
            transaction_type=tx_data["transaction_type"],
            amount=Decimal(str(tx_data["amount"])),
            balance_after=Decimal(str(tx_data["balance_after"])),
            description=tx_data.get("description", ""),
            created_at=tx_data["created_at"]
        )

    async def withdraw(
        self,
        wallet_id: str,
        amount: float,
        destination: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransactionInfo:
        """Withdraw funds from wallet"""
        payload = {
            "amount": amount,
            "destination": destination
        }
        if description:
            payload["description"] = description
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "POST",
            f"/api/v1/wallets/{wallet_id}/withdraw",
            json=payload
        )

        if not result.get("success"):
            raise Exception(result.get("message", "Withdrawal failed"))

        tx_data = result.get("data", {}).get("transaction", {})
        return TransactionInfo(
            transaction_id=tx_data["transaction_id"],
            wallet_id=tx_data["wallet_id"],
            transaction_type=tx_data["transaction_type"],
            amount=Decimal(str(tx_data["amount"])),
            balance_after=Decimal(str(tx_data["balance_after"])),
            description=tx_data.get("description", ""),
            created_at=tx_data["created_at"]
        )

    async def consume(
        self,
        wallet_id: str,
        amount: float,
        description: Optional[str] = None,
        usage_record_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransactionInfo:
        """Consume credits from wallet"""
        payload = {"amount": amount}
        if description:
            payload["description"] = description
        if usage_record_id:
            payload["usage_record_id"] = usage_record_id
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "POST",
            f"/api/v1/wallets/{wallet_id}/consume",
            json=payload
        )

        if not result.get("success"):
            raise Exception(result.get("message", "Consumption failed"))

        tx_data = result.get("data", {}).get("transaction", {})
        return TransactionInfo(
            transaction_id=tx_data["transaction_id"],
            wallet_id=tx_data["wallet_id"],
            transaction_type=tx_data["transaction_type"],
            amount=Decimal(str(tx_data["amount"])),
            balance_after=Decimal(str(tx_data["balance_after"])),
            description=tx_data.get("description", ""),
            created_at=tx_data["created_at"]
        )

    async def transfer(
        self,
        from_wallet_id: str,
        to_wallet_id: str,
        amount: float,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, TransactionInfo]:
        """Transfer funds between wallets"""
        payload = {
            "to_wallet_id": to_wallet_id,
            "amount": amount
        }
        if description:
            payload["description"] = description
        if metadata:
            payload["metadata"] = metadata

        result = await self._make_request(
            "POST",
            f"/api/v1/wallets/{from_wallet_id}/transfer",
            json=payload
        )

        if not result.get("success"):
            raise Exception(result.get("message", "Transfer failed"))

        data = result.get("data", {})
        from_tx = data.get("from_transaction", {})
        to_tx = data.get("to_transaction", {})

        return {
            "from_transaction": TransactionInfo(
                transaction_id=from_tx["transaction_id"],
                wallet_id=from_tx["wallet_id"],
                transaction_type=from_tx["transaction_type"],
                amount=Decimal(str(from_tx["amount"])),
                balance_after=Decimal(str(from_tx["balance_after"])),
                description=from_tx.get("description", ""),
                created_at=from_tx["created_at"]
            ),
            "to_transaction": TransactionInfo(
                transaction_id=to_tx["transaction_id"],
                wallet_id=to_tx["wallet_id"],
                transaction_type=to_tx["transaction_type"],
                amount=Decimal(str(to_tx["amount"])),
                balance_after=Decimal(str(to_tx["balance_after"])),
                description=to_tx.get("description", ""),
                created_at=to_tx["created_at"]
            )
        }

    async def get_transactions(
        self,
        wallet_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get wallet transaction history"""
        result = await self._make_request(
            "GET",
            f"/api/v1/wallets/{wallet_id}/transactions",
            params={"limit": limit, "offset": offset}
        )

        return result.get("transactions", [])

    async def get_user_transactions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user transaction history across all wallets"""
        result = await self._make_request(
            "GET",
            f"/api/v1/users/{user_id}/transactions",
            params={"limit": limit, "offset": offset}
        )

        return result.get("transactions", [])

    async def get_statistics(self, wallet_id: str) -> Dict[str, Any]:
        """Get wallet statistics"""
        return await self._make_request("GET", f"/api/v1/wallets/{wallet_id}/statistics")

    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics across all wallets"""
        return await self._make_request("GET", f"/api/v1/users/{user_id}/statistics")

    async def get_credit_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user credit balance (backward compatibility)"""
        return await self._make_request("GET", f"/api/v1/users/{user_id}/credits/balance")

    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        return await self._make_request("GET", "/health")

    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0
        }


# Example Usage
async def main():
    print("=" * 70)
    print("Wallet Service Client Examples")
    print("=" * 70)

    async with WalletServiceClient() as client:
        test_user = f"demo_user_{int(datetime.now().timestamp())}"

        # Example 1: Health Check
        print("\n1. Health Check")
        print("-" * 70)
        health = await client.health_check()
        print(f"✓ Service: {health['service']}")
        print(f"  Status: {health['status']}")
        print(f"  Port: {health['port']}")

        # Example 2: Create Wallet
        print("\n2. Creating Wallet")
        print("-" * 70)
        wallet = await client.create_wallet(
            user_id=test_user,
            wallet_type="fiat",
            initial_balance=1000.0,
            currency="CREDIT",
            metadata={
                "source": "demo",
                "purpose": "testing"
            }
        )
        print(f"✓ Wallet created successfully")
        print(f"  Wallet ID: {wallet.wallet_id}")
        print(f"  Balance: {wallet.balance} {wallet.currency}")
        print(f"  Type: {wallet.wallet_type}")

        # Example 3: Get Wallet Details
        print("\n3. Getting Wallet Details")
        print("-" * 70)
        wallet_info = await client.get_wallet(wallet.wallet_id)
        print(f"✓ Retrieved wallet: {wallet_info.wallet_id}")
        print(f"  Balance: {wallet_info.balance} {wallet_info.currency}")
        print(f"  Available: {wallet_info.available_balance}")
        print(f"  Locked: {wallet_info.locked_balance}")

        # Example 4: Deposit Funds
        print("\n4. Depositing Funds")
        print("-" * 70)
        deposit_tx = await client.deposit(
            wallet.wallet_id,
            amount=500.0,
            description="Demo deposit",
            reference_id="demo_deposit_001",
            metadata={"source": "demo_payment"}
        )
        print(f"✓ Deposit successful")
        print(f"  Transaction ID: {deposit_tx.transaction_id}")
        print(f"  Amount: {deposit_tx.amount}")
        print(f"  New Balance: {deposit_tx.balance_after}")

        # Example 5: Consume Credits
        print("\n5. Consuming Credits")
        print("-" * 70)
        consume_tx = await client.consume(
            wallet.wallet_id,
            amount=150.0,
            description="API usage",
            metadata={"api_calls": 1500, "cost_per_call": 0.10}
        )
        print(f"✓ Credits consumed")
        print(f"  Transaction ID: {consume_tx.transaction_id}")
        print(f"  Consumed: {consume_tx.amount}")
        print(f"  Remaining Balance: {consume_tx.balance_after}")

        # Example 6: Withdraw Funds
        print("\n6. Withdrawing Funds")
        print("-" * 70)
        withdraw_tx = await client.withdraw(
            wallet.wallet_id,
            amount=200.0,
            destination="bank_account_123",
            description="Withdrawal to bank",
            metadata={"bank": "Demo Bank", "account": "****1234"}
        )
        print(f"✓ Withdrawal successful")
        print(f"  Transaction ID: {withdraw_tx.transaction_id}")
        print(f"  Amount: {withdraw_tx.amount}")
        print(f"  New Balance: {withdraw_tx.balance_after}")

        # Example 7: Get Balance
        print("\n7. Getting Current Balance")
        print("-" * 70)
        balance_info = await client.get_balance(wallet.wallet_id)
        print(f"✓ Current balance: {balance_info['balance']} {balance_info['currency']}")
        print(f"  Available: {balance_info['available_balance']}")
        print(f"  Locked: {balance_info['locked_balance']}")

        # Example 8: Get Transaction History
        print("\n8. Getting Transaction History")
        print("-" * 70)
        transactions = await client.get_transactions(wallet.wallet_id, limit=10)
        print(f"✓ Found {len(transactions)} transactions:")
        for tx in transactions[:3]:  # Show first 3
            tx_type_emoji = {
                "deposit": "💰",
                "withdraw": "💸",
                "consume": "🔥",
                "refund": "↩️",
                "transfer": "🔄"
            }
            emoji = tx_type_emoji.get(tx["transaction_type"], "📝")
            print(f"  {emoji} {tx['transaction_type'].upper()}: {tx['amount']} {wallet.currency}")
            print(f"     Balance: {tx['balance_before']} → {tx['balance_after']}")
            print(f"     {tx.get('description', 'No description')}")

        # Example 9: Get User Wallets
        print("\n9. Getting All User Wallets")
        print("-" * 70)
        user_wallets = await client.get_user_wallets(test_user)
        print(f"✓ User has {len(user_wallets)} wallet(s):")
        for w in user_wallets:
            print(f"  • {w.wallet_type.upper()}: {w.balance} {w.currency}")
            print(f"    ID: {w.wallet_id}")

        # Example 10: Get Statistics
        print("\n10. Getting Wallet Statistics")
        print("-" * 70)
        stats = await client.get_statistics(wallet.wallet_id)
        print(f"✓ Wallet statistics:")
        print(f"  Current Balance: {stats['current_balance']}")
        print(f"  Total Deposits: {stats['total_deposits']}")
        print(f"  Total Withdrawals: {stats['total_withdrawals']}")
        print(f"  Total Consumed: {stats['total_consumed']}")
        print(f"  Transaction Count: {stats['transaction_count']}")

        # Example 11: Get Credit Balance (Backward Compatibility)
        print("\n11. Getting Credit Balance")
        print("-" * 70)
        credit_balance = await client.get_credit_balance(test_user)
        print(f"✓ Credit balance: {credit_balance['balance']} {credit_balance['currency']}")
        print(f"  Available: {credit_balance['available_balance']}")
        print(f"  Wallet ID: {credit_balance['wallet_id']}")

        # Show Client Metrics
        print("\n12. Client Performance Metrics")
        print("-" * 70)
        metrics = client.get_metrics()
        print(f"Total requests: {metrics['total_requests']}")
        print(f"Total errors: {metrics['total_errors']}")
        print(f"Error rate: {metrics['error_rate']:.2%}")

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
