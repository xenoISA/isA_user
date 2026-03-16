# Wallet Service - System Contract (Layer 6)

## Overview

This document defines HOW wallet_service implements the 12 standard system patterns.

**Service**: wallet_service
**Port**: 8208
**Category**: User Microservice
**Version**: 1.0.0

---

## 1. Architecture Pattern

### Service Layer Structure

```
microservices/wallet_service/
├── __init__.py
├── main.py                          # FastAPI app, routes, DI setup, lifespan
├── wallet_service.py                # Business logic layer
├── wallet_repository.py             # Data access layer
├── models.py                        # Pydantic models (Wallet, Transaction, etc.)
├── protocols.py                     # DI interfaces
├── factory.py                       # DI factory
├── routes_registry.py               # Consul route metadata
├── client.py                        # Service client
├── clients/
│   ├── __init__.py
│   └── account_client.py
├── events/
│   ├── __init__.py
│   ├── models.py                    # Event models (BillingCalculated, TokensDeducted, etc.)
│   ├── handlers.py                  # NATS handlers (billing, payment, user lifecycle)
│   └── publishers.py                # Event publishers
└── migrations/
    ├── 001_create_wallet_schema.sql
    └── 002_add_credit_accounts.sql
```

### External Dependencies

| Dependency | Type | Purpose | Endpoint |
|------------|------|---------|----------|
| PostgreSQL | AsyncPostgresClient | Primary data store | postgres:5432 |
| NATS | Native | Event pub/sub | nats:4222 |
| Consul | HTTP | Service registration | consul:8500 |
| Account Service | HTTP | User validation | localhost:8202 |

---

## 2. Dependency Injection Pattern

### Protocol Definition (`protocols.py`)

```python
@runtime_checkable
class WalletRepositoryProtocol(Protocol):
    async def create_wallet(self, wallet_data: WalletCreate) -> Optional[WalletBalance]: ...
    async def get_wallet(self, wallet_id: str) -> Optional[WalletBalance]: ...
    async def get_user_wallets(self, user_id: str, wallet_type=None) -> List[WalletBalance]: ...
    async def get_primary_wallet(self, user_id: str) -> Optional[WalletBalance]: ...
    async def update_balance(self, wallet_id: str, amount: Decimal, operation="add") -> Optional[Decimal]: ...
    async def deactivate_wallet(self, wallet_id: str) -> bool: ...
    async def deposit(self, wallet_id: str, amount: Decimal, ...) -> Optional[WalletTransaction]: ...
    async def withdraw(self, wallet_id: str, amount: Decimal, ...) -> Optional[WalletTransaction]: ...
    async def consume(self, wallet_id: str, amount: Decimal, ...) -> Optional[WalletTransaction]: ...
    async def refund(self, original_transaction_id: str, ...) -> Optional[WalletTransaction]: ...
    async def transfer(self, from_wallet_id: str, to_wallet_id: str, amount: Decimal, ...) -> Optional[Tuple[WalletTransaction, WalletTransaction]]: ...
    async def get_transactions(self, filter_params: TransactionFilter) -> List[WalletTransaction]: ...
    async def get_statistics(self, wallet_id: str, ...) -> Optional[WalletStatistics]: ...
    async def anonymize_user_transactions(self, user_id: str) -> int: ...

class EventBusProtocol(Protocol):
    async def publish_event(self, event: Any) -> bool: ...
    async def subscribe_to_events(self, pattern: str, handler: Any, durable=None) -> None: ...

class AccountClientProtocol(Protocol):
    async def get_account(self, user_id: str) -> Optional[Dict]: ...
    async def validate_user_exists(self, user_id: str) -> bool: ...
```

### Custom Exceptions

| Exception | Description |
|-----------|-------------|
| WalletNotFoundError | Wallet not found |
| InsufficientBalanceError | Not enough balance |
| DuplicateWalletError | Wallet already exists |
| TransactionNotFoundError | Transaction not found |
| InvalidTransactionError | Invalid transaction |
| WalletFrozenError | Wallet is frozen |

---

## 3. Factory Implementation

```python
def create_wallet_service(config=None, event_bus=None, account_client=None) -> WalletService:
    from .wallet_repository import WalletRepository
    repository = WalletRepository(config=config)
    if account_client is None:
        from .clients.account_client import AccountClient
        account_client = AccountClient()
    return WalletService(repository=repository, event_bus=event_bus, account_client=account_client)
```

---

## 4. Singleton Management

Global variable pattern (in main.py). Service created via factory in lifespan.

---

## 5. Service Registration (Consul)

- **Route count**: 17 routes
- **Base path**: `/api/v1/wallets`
- **Tags**: `["v1", "user-microservice", "wallet", "payment"]`
- **Capabilities**: wallet_management, balance_management, deposit_withdraw, credit_system, transaction_history, wallet_transfer, transaction_refund, event_driven
- **Health check type**: TTL

---

## 6. Health Check Contract

| Endpoint | Auth | Response |
|----------|------|----------|
| `/health` | No | `{status, service, port, version}` |
| `/api/v1/wallets/health` | No | Same |

---

## 7. Event System Contract (NATS)

### Published Events

| Event | Subject | Trigger |
|-------|---------|---------|
| `wallet.created` | `wallet.created` | Wallet created |
| `wallet.deposited` | `wallet.deposited` | Funds deposited |
| `wallet.withdrawn` | `wallet.withdrawn` | Funds withdrawn |
| `wallet.consumed` | `wallet.consumed` | Credits consumed |
| `wallet.transferred` | `wallet.transferred` | Transfer completed |
| `wallet.refunded` | `wallet.refunded` | Refund processed |
| `wallet.tokens.deducted` | `wallet.tokens.deducted` | Token deduction from billing |
| `wallet.tokens.insufficient` | `wallet.tokens.insufficient` | Insufficient tokens |

### Subscribed Events

| Pattern | Source | Handler |
|---------|--------|---------|
| `payment_service.payment.completed` | payment_service | Deposit funds into wallet |
| `payment_service.payment.refunded` | payment_service | Deposit refund back to wallet |
| `subscription_service.subscription.created` | subscription_service | Allocate subscription credits |
| `account_service.user.created` | account_service | Auto-create wallet for new user |
| `account_service.user.deleted` | account_service | Freeze wallets, anonymize transactions |
| `billing_service.billing.calculated` | billing_service | Execute token deduction |

### Idempotency

Event handlers maintain a `_processed_event_ids` set (max 10,000 entries, prunes oldest half at limit).

---

## 8. Configuration Contract

| Variable | Description | Default |
|----------|-------------|---------|
| `WALLET_SERVICE_PORT` | HTTP port | 8208 |

---

## 9. Error Handling Contract

Standard try/except in routes with HTTP status mapping.

---

## 10. Logging Contract

```python
app_logger = setup_service_logger("wallet_service")
```

---

## 11. Testing Contract

```python
mock_repo = AsyncMock(spec=WalletRepositoryProtocol)
mock_account = AsyncMock(spec=AccountClientProtocol)
service = WalletService(repository=mock_repo, event_bus=AsyncMock(), account_client=mock_account)
```

---

## 12. Deployment Contract

### Lifecycle

1. Install signal handlers
2. Initialize event bus
3. Create WalletService via factory
4. Register event handlers (6 patterns)
5. Consul TTL registration
6. **yield**
7. Graceful shutdown
8. Consul deregistration
9. Event bus close

### Special: Billing Integration

Wallet service is the primary consumer of `billing.calculated` events, executing token deductions and publishing success/failure events back to the event bus.

---

## Reference Files

| File | Purpose |
|------|---------|
| `microservices/wallet_service/main.py` | FastAPI app, routes, lifespan |
| `microservices/wallet_service/wallet_service.py` | Business logic |
| `microservices/wallet_service/wallet_repository.py` | Data access |
| `microservices/wallet_service/protocols.py` | DI interfaces |
| `microservices/wallet_service/factory.py` | DI factory |
| `microservices/wallet_service/models.py` | Pydantic schemas |
| `microservices/wallet_service/routes_registry.py` | Consul metadata |
| `microservices/wallet_service/events/handlers.py` | NATS handlers (6 event types) |
| `microservices/wallet_service/events/models.py` | Event schemas |
| `microservices/wallet_service/events/publishers.py` | Event publishers |
