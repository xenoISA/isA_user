# Wallet Service - Design Document

## Design Overview

**Service Name**: wallet_service
**Port**: 8213
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-16

### Design Principles
1. **Financial Integrity First**: All balance changes occur through atomic transactions
2. **Idempotent by Design**: All operations safe for retry (event deduplication)
3. **Event-Driven Synchronization**: Loose coupling via NATS events
4. **Transaction Immutability**: No modification after creation - only refunds
5. **ACID Guarantees**: PostgreSQL transactions for financial consistency
6. **Graceful Degradation**: Event failures don't block operations
7. **Credit-Based Architecture**: 1 Credit = $0.00001 USD (100,000 Credits = $1)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Billing Service, Payment Service, Apps, Admin Dashboard) │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                 Wallet Service (Port 8213)                  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)             │ │
│  │  - Request validation (Pydantic models)               │ │
│  │  - Response formatting                                │ │
│  │  - Error handling & exception handlers                │ │
│  │  - Health checks (/health)                            │ │
│  │  - Lifecycle management (startup/shutdown)            │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                    │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Service Layer (wallet_service.py)                │ │
│  │  - Business logic (balance checks, validation)        │ │
│  │  - Deposit/Withdraw/Consume/Transfer/Refund           │ │
│  │  - Transaction management                             │ │
│  │  - Statistics aggregation                             │ │
│  │  - Event publishing orchestration                     │ │
│  │  - Cross-service client calls (account_service)       │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                    │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Repository Layer (wallet_repository.py)          │ │
│  │  - Database CRUD operations                           │ │
│  │  - PostgreSQL gRPC communication                      │ │
│  │  - Query construction (parameterized)                 │ │
│  │  - Result parsing (proto to Pydantic)                 │ │
│  │  - Atomic balance updates                             │ │
│  │  - No business logic                                  │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                    │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Event Publishing (events/publishers.py)          │ │
│  │  - NATS event bus integration                         │ │
│  │  - Event model construction                           │ │
│  │  - Async non-blocking publishing                      │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐
│  PostgreSQL  │ │    NATS     │ │   Consul   │
│   (gRPC)     │ │  (Events)   │ │ (Discovery)│
│              │ │             │ │            │
│  Schema:     │ │  Subjects:  │ │  Service:  │
│  wallet      │ │  wallet.*   │ │  wallet_   │
│  Tables:     │ │             │ │  service   │
│  - wallets   │ │  Publishers:│ │            │
│  - trans-    │ │  - created  │ │  Health:   │
│    actions   │ │  - deposited│ │  /health   │
│              │ │  - withdrawn│ │            │
│  Indexes:    │ │  - consumed │ │            │
│  - wallet_id │ │  - transfer │ │            │
│  - user_id   │ │  - refunded │ │            │
│  - type      │ │             │ │            │
└──────────────┘ └─────────────┘ └────────────┘

Optional Dependencies:
┌──────────────────┐
│ account_service  │ ← User validation
│ (Port 8201)      │
└──────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Wallet Service                          │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │   Models    │───→│   Service   │───→│ Repository   │   │
│  │  (Pydantic) │    │ (Business)  │    │   (Data)     │   │
│  │             │    │             │    │              │   │
│  │ - Wallet    │    │ - Wallet    │    │ - Wallet     │   │
│  │   Balance   │    │   Service   │    │   Repository │   │
│  │ - Wallet    │    │             │    │              │   │
│  │   Trans-    │    │             │    │              │   │
│  │   action    │    │             │    │              │   │
│  │ - Deposit   │    │             │    │              │   │
│  │   Request   │    │             │    │              │   │
│  │ - Withdraw  │    │             │    │              │   │
│  │   Request   │    │             │    │              │   │
│  │ - Consume   │    │             │    │              │   │
│  │   Request   │    │             │    │              │   │
│  └─────────────┘    └─────────────┘    └──────────────┘   │
│         ↑                  ↑                    ↑          │
│         │                  │                    │          │
│  ┌──────┴──────────────────┴────────────────────┴───────┐ │
│  │              FastAPI Main (main.py)                   │ │
│  │  - Dependency Injection (get_wallet_service)         │ │
│  │  - Route Handlers (17+ endpoints)                    │ │
│  │  - Exception Handlers (custom errors)                │ │
│  └────────────────────────┬──────────────────────────────┘ │
│                           │                                │
│  ┌────────────────────────▼──────────────────────────────┐ │
│  │              Event Publishers                         │ │
│  │  (events/publishers.py, events/models.py)            │ │
│  │  - publish_wallet_created                            │ │
│  │  - publish_wallet_deposited                          │ │
│  │  - publish_wallet_withdrawn                          │ │
│  │  - publish_wallet_consumed                           │ │
│  │  - publish_wallet_transferred                        │ │
│  │  - publish_wallet_refunded                           │ │
│  │  - publish_tokens_deducted                           │ │
│  │  - publish_tokens_insufficient                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                 Factory Pattern                       │ │
│  │              (factory.py, protocols.py)               │ │
│  │  - create_wallet_service (production)                 │ │
│  │  - WalletRepositoryProtocol (interface)               │ │
│  │  - AccountClientProtocol (interface)                  │ │
│  │  - Enables dependency injection for tests             │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (17+ endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup
- Exception handling

**Key Endpoints**:
```python
# Health Checks
GET /health                                  # Basic health check

# Wallet Management
POST /api/v1/wallets                         # Create wallet
GET  /api/v1/wallets/{wallet_id}             # Get wallet by ID
GET  /api/v1/wallets                         # List user wallets (user_id query)
GET  /api/v1/wallets/{wallet_id}/balance     # Get wallet balance

# Transaction Operations
POST /api/v1/wallets/{wallet_id}/deposit     # Deposit funds
POST /api/v1/wallets/{wallet_id}/withdraw    # Withdraw funds
POST /api/v1/wallets/{wallet_id}/consume     # Consume credits
POST /api/v1/wallets/{wallet_id}/transfer    # Transfer between wallets
POST /api/v1/transactions/{id}/refund        # Refund transaction

# Transaction History
GET /api/v1/wallets/{wallet_id}/transactions # Wallet transactions
GET /api/v1/wallets/transactions             # User transactions (user_id query)

# Statistics
GET /api/v1/wallets/{wallet_id}/statistics   # Wallet statistics
GET /api/v1/wallets/statistics               # User statistics (user_id query)

# Backward Compatibility (Credit System)
GET  /api/v1/wallets/credits/balance         # Get user credit balance
POST /api/v1/wallets/credits/consume         # Consume user credits

# Service Statistics
GET /api/v1/wallet/stats                     # Service statistics
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus("wallet_service")
    await wallet_microservice.initialize(event_bus=event_bus)

    # Subscribe to events (handlers from events/handlers.py)
    event_handlers = get_event_handlers(wallet_service, event_bus)
    for pattern, handler in event_handlers.items():
        await event_bus.subscribe_to_events(
            pattern=pattern,
            handler=handler,
            durable=f"wallet-{pattern.split('.')[-1]}-consumer"
        )

    # Consul registration (metadata includes routes)
    if config.consul_enabled:
        consul_registry.register()

    yield  # Service runs

    # Shutdown
    await wallet_microservice.shutdown()
    if event_bus:
        await event_bus.close()
```

### 2. Service Layer (wallet_service.py)

**Class**: `WalletService`

**Responsibilities**:
- Business logic execution
- Balance validation and checks
- Transaction orchestration
- Event publishing coordination
- Input validation
- Error handling and custom exceptions
- Cross-service integration (account_service)

**Key Methods**:
```python
class WalletService:
    def __init__(
        self,
        repository: Optional[WalletRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        account_client: Optional[AccountClientProtocol] = None,
    ):
        self.repository = repository
        self.repo = repository  # Alias for backward compatibility
        self.event_bus = event_bus
        self.account_client = account_client
        self._event_publishers_loaded = False

    # Core Operations
    async def create_wallet(
        self,
        wallet_data: WalletCreate
    ) -> WalletResponse:
        """
        Create a new wallet for user.
        Returns existing wallet if FIAT type already exists.
        """
        # 1. Check if user already has a wallet of this type
        existing_wallets = await self.repository.get_user_wallets(
            wallet_data.user_id, wallet_data.wallet_type
        )

        if existing_wallets and wallet_data.wallet_type == WalletType.FIAT:
            return WalletResponse(
                success=False,
                message="User already has a fiat wallet",
                wallet_id=existing_wallets[0].wallet_id
            )

        # 2. Create wallet in database
        wallet = await self.repository.create_wallet(wallet_data)

        # 3. Publish wallet.created event (non-blocking)
        if wallet and self.event_bus:
            event = Event(
                event_type=EventType.WALLET_CREATED,
                source=ServiceSource.WALLET_SERVICE,
                data={
                    "wallet_id": wallet.wallet_id,
                    "user_id": wallet.user_id,
                    "wallet_type": wallet.wallet_type.value,
                    "currency": wallet.currency,
                    "balance": float(wallet.balance)
                }
            )
            await self.event_bus.publish_event(event)

        return WalletResponse(
            success=True,
            message="Wallet created successfully",
            wallet_id=wallet.wallet_id,
            balance=wallet.balance
        )

    async def deposit(
        self,
        wallet_id: str,
        request: DepositRequest
    ) -> WalletResponse:
        """Deposit funds to wallet"""
        # 1. Execute deposit via repository (atomic)
        transaction = await self.repository.deposit(
            wallet_id=wallet_id,
            amount=request.amount,
            description=request.description,
            reference_id=request.reference_id,
            metadata=request.metadata
        )

        # 2. Publish wallet.deposited event
        if transaction and self.event_bus:
            event = Event(
                event_type=EventType.WALLET_DEPOSITED,
                source=ServiceSource.WALLET_SERVICE,
                data={
                    "wallet_id": wallet_id,
                    "user_id": transaction.user_id,
                    "transaction_id": transaction.transaction_id,
                    "amount": float(request.amount),
                    "balance_before": float(transaction.balance_before),
                    "balance_after": float(transaction.balance_after)
                }
            )
            await self.event_bus.publish_event(event)

        return WalletResponse(
            success=True,
            message=f"Deposited {request.amount} successfully",
            wallet_id=wallet_id,
            balance=transaction.balance_after,
            transaction_id=transaction.transaction_id
        )

    async def withdraw(
        self,
        wallet_id: str,
        request: WithdrawRequest
    ) -> WalletResponse:
        """Withdraw funds from wallet"""
        # 1. Get wallet and verify balance
        wallet = await self.repository.get_wallet(wallet_id)
        if not wallet:
            return WalletResponse(success=False, message="Wallet not found")

        # 2. Execute withdrawal via repository
        transaction = await self.repository.withdraw(
            wallet_id=wallet_id,
            amount=request.amount,
            description=request.description,
            destination=request.destination,
            metadata=request.metadata
        )

        if not transaction:
            return WalletResponse(
                success=False,
                message="Insufficient balance or withdrawal failed"
            )

        # 3. Publish wallet.withdrawn event
        if self.event_bus:
            event = Event(
                event_type=EventType.WALLET_WITHDRAWN,
                source=ServiceSource.WALLET_SERVICE,
                data={
                    "wallet_id": wallet_id,
                    "user_id": transaction.user_id,
                    "amount": float(request.amount),
                    "balance_after": float(transaction.balance_after),
                    "destination": request.destination
                }
            )
            await self.event_bus.publish_event(event)

        return WalletResponse(
            success=True,
            message=f"Withdrew {request.amount} successfully",
            wallet_id=wallet_id,
            balance=transaction.balance_after,
            transaction_id=transaction.transaction_id
        )

    async def consume(
        self,
        wallet_id: str,
        request: ConsumeRequest
    ) -> WalletResponse:
        """Consume credits/tokens from wallet"""
        # 1. Execute consumption via repository
        transaction = await self.repository.consume(
            wallet_id=wallet_id,
            amount=request.amount,
            description=request.description,
            usage_record_id=request.usage_record_id,
            metadata=request.metadata
        )

        if not transaction:
            return WalletResponse(success=False, message="Insufficient balance")

        # 2. Publish wallet.consumed event
        if self.event_bus:
            event = Event(
                event_type=EventType.WALLET_CONSUMED,
                source=ServiceSource.WALLET_SERVICE,
                data={
                    "wallet_id": wallet_id,
                    "user_id": transaction.user_id,
                    "amount": float(request.amount),
                    "balance_after": float(transaction.balance_after),
                    "usage_record_id": request.usage_record_id
                }
            )
            await self.event_bus.publish_event(event)

        return WalletResponse(
            success=True,
            message=f"Consumed {request.amount} successfully",
            wallet_id=wallet_id,
            balance=transaction.balance_after,
            transaction_id=transaction.transaction_id
        )

    async def transfer(
        self,
        from_wallet_id: str,
        request: TransferRequest
    ) -> WalletResponse:
        """Transfer funds between wallets (atomic)"""
        # Repository handles atomic transfer
        result = await self.repository.transfer(
            from_wallet_id=from_wallet_id,
            to_wallet_id=request.to_wallet_id,
            amount=request.amount,
            description=request.description,
            metadata=request.metadata
        )

        if result:
            from_transaction, to_transaction = result

            # Publish wallet.transferred event
            if self.event_bus:
                event = Event(
                    event_type=EventType.WALLET_TRANSFERRED,
                    source=ServiceSource.WALLET_SERVICE,
                    data={
                        "from_wallet_id": from_wallet_id,
                        "to_wallet_id": request.to_wallet_id,
                        "amount": float(request.amount),
                        "from_transaction_id": from_transaction.transaction_id,
                        "to_transaction_id": to_transaction.transaction_id
                    }
                )
                await self.event_bus.publish_event(event)

            return WalletResponse(
                success=True,
                message=f"Transferred {request.amount} successfully",
                wallet_id=from_wallet_id,
                balance=from_transaction.balance_after,
                transaction_id=from_transaction.transaction_id
            )

        return WalletResponse(
            success=False,
            message="Transfer failed - check balance and wallet IDs"
        )

    async def refund(
        self,
        original_transaction_id: str,
        request: RefundRequest
    ) -> WalletResponse:
        """Refund a previous transaction"""
        transaction = await self.repository.refund(
            original_transaction_id=original_transaction_id,
            amount=request.amount,
            reason=request.reason,
            metadata=request.metadata
        )

        if transaction and self.event_bus:
            event = Event(
                event_type=EventType.WALLET_REFUNDED,
                source=ServiceSource.WALLET_SERVICE,
                data={
                    "wallet_id": transaction.wallet_id,
                    "user_id": transaction.user_id,
                    "original_transaction_id": original_transaction_id,
                    "amount": float(transaction.amount),
                    "balance_after": float(transaction.balance_after),
                    "reason": request.reason
                }
            )
            await self.event_bus.publish_event(event)

        return WalletResponse(
            success=True if transaction else False,
            message=f"Refunded successfully" if transaction else "Failed to process refund",
            wallet_id=transaction.wallet_id if transaction else None,
            balance=transaction.balance_after if transaction else None,
            transaction_id=transaction.transaction_id if transaction else None
        )
```

**Custom Exceptions**:
```python
class WalletServiceError(Exception):
    """Base exception for wallet service"""
    pass

class WalletNotFoundError(WalletServiceError):
    """Wallet not found"""
    pass

class InsufficientBalanceError(WalletServiceError):
    """Insufficient balance for operation"""
    pass

class DuplicateWalletError(WalletServiceError):
    """Wallet already exists"""
    pass

class WalletValidationError(WalletServiceError):
    """Validation error"""
    pass
```

### 3. Repository Layer (wallet_repository.py)

**Class**: `WalletRepository`

**Responsibilities**:
- PostgreSQL CRUD operations
- gRPC communication with postgres_grpc_service
- Query construction (parameterized)
- Result parsing (proto JSONB to Python dict)
- Atomic balance updates
- No business logic

**Key Methods**:
```python
class WalletRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        # Discover PostgreSQL gRPC service via Consul
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(host=host, port=port, user_id='wallet_service')
        self.schema = "wallet"
        self.wallets_table = "wallets"
        self.transactions_table = "transactions"

    async def create_wallet(self, wallet_data: WalletCreate) -> Optional[WalletBalance]:
        """Create a new wallet for user"""
        wallet_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        wallet_dict = {
            'wallet_id': wallet_id,
            'user_id': wallet_data.user_id,
            'balance': float(wallet_data.initial_balance),
            'locked_balance': 0.0,
            'currency': wallet_data.currency,
            'wallet_type': wallet_data.wallet_type.value,
            'blockchain_address': wallet_data.blockchain_address,
            'blockchain_network': wallet_data.blockchain_network.value if wallet_data.blockchain_network else None,
            'metadata': wallet_data.metadata or {},
            'is_active': True,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }

        async with self.db:
            count = await self.db.insert_into(
                self.wallets_table, [wallet_dict], schema=self.schema
            )

        if count and count > 0:
            # Create initial transaction if balance > 0
            if wallet_data.initial_balance > 0:
                await self._create_transaction(...)

            return await self.get_wallet(wallet_id)
        return None

    async def deposit(
        self,
        wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[WalletTransaction]:
        """Deposit funds to wallet"""
        # 1. Get current balance
        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            return None

        # 2. Update balance (atomic)
        new_balance = await self.update_balance(wallet_id, amount, "add")
        if new_balance is None:
            return None

        # 3. Create transaction record
        transaction = await self._create_transaction(
            TransactionCreate(
                wallet_id=wallet_id,
                user_id=wallet.user_id,
                transaction_type=TransactionType.DEPOSIT,
                amount=amount,
                description=description or f"Deposit: {amount}",
                reference_id=reference_id,
                metadata=metadata or {}
            ),
            balance_before=wallet.balance,
            balance_after=new_balance
        )

        return transaction

    async def withdraw(
        self,
        wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        destination: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[WalletTransaction]:
        """Withdraw funds from wallet"""
        wallet = await self.get_wallet(wallet_id)
        if not wallet or wallet.available_balance < amount:
            return None

        new_balance = await self.update_balance(wallet_id, amount, "subtract")
        if new_balance is None:
            return None

        tx_metadata = metadata or {}
        if destination:
            tx_metadata["destination"] = destination

        transaction = await self._create_transaction(
            TransactionCreate(
                wallet_id=wallet_id,
                user_id=wallet.user_id,
                transaction_type=TransactionType.WITHDRAW,
                amount=amount,
                description=description or f"Withdrawal: {amount}",
                metadata=tx_metadata
            ),
            balance_before=wallet.balance,
            balance_after=new_balance
        )

        return transaction

    async def consume(
        self,
        wallet_id: str,
        amount: Decimal,
        description: Optional[str] = None,
        usage_record_id: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[WalletTransaction]:
        """Consume credits from wallet"""
        wallet = await self.get_wallet(wallet_id)
        if not wallet or wallet.available_balance < amount:
            return None

        new_balance = await self.update_balance(wallet_id, amount, "subtract")
        if new_balance is None:
            return None

        transaction = await self._create_transaction(
            TransactionCreate(
                wallet_id=wallet_id,
                user_id=wallet.user_id,
                transaction_type=TransactionType.CONSUME,
                amount=amount,
                description=description or f"Consumed: {amount}",
                usage_record_id=usage_record_id,
                metadata=metadata or {}
            ),
            balance_before=wallet.balance,
            balance_after=new_balance
        )

        return transaction

    async def update_balance(
        self,
        wallet_id: str,
        amount: Decimal,
        operation: str = "add"
    ) -> Optional[Decimal]:
        """Update wallet balance atomically"""
        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            return None

        if operation == "add":
            new_balance = wallet.balance + amount
        elif operation == "subtract":
            if wallet.balance < amount:
                return None
            new_balance = wallet.balance - amount
        else:
            raise ValueError(f"Invalid operation: {operation}")

        query = f"""
            UPDATE {self.schema}.{self.wallets_table}
            SET balance = $1, updated_at = $2
            WHERE wallet_id = $3
        """

        async with self.db:
            count = await self.db.execute(
                query,
                [float(new_balance), datetime.now(timezone.utc).isoformat(), wallet_id],
                schema=self.schema
            )

        if count and count > 0:
            return new_balance
        return None

    async def get_transactions(
        self,
        filter_params: TransactionFilter
    ) -> List[WalletTransaction]:
        """Get filtered transaction history"""
        conditions = []
        params = []
        param_count = 0

        if filter_params.wallet_id:
            param_count += 1
            conditions.append(f"wallet_id = ${param_count}")
            params.append(filter_params.wallet_id)

        if filter_params.user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(filter_params.user_id)

        if filter_params.transaction_type:
            param_count += 1
            conditions.append(f"transaction_type = ${param_count}")
            params.append(filter_params.transaction_type.value)

        if filter_params.start_date:
            param_count += 1
            conditions.append(f"created_at >= ${param_count}")
            params.append(filter_params.start_date.isoformat())

        if filter_params.end_date:
            param_count += 1
            conditions.append(f"created_at <= ${param_count}")
            params.append(filter_params.end_date.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        query = f"""
            SELECT * FROM {self.schema}.{self.transactions_table}
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT {filter_params.limit} OFFSET {filter_params.offset}
        """

        async with self.db:
            results = await self.db.query(query, params, schema=self.schema)

        return [self._dict_to_transaction(tx) for tx in results] if results else []
```

---

## Database Schema Design

### PostgreSQL Schema: `wallet`

#### Table: wallet.wallets

```sql
-- Create wallet schema
CREATE SCHEMA IF NOT EXISTS wallet;

-- Create wallets table
CREATE TABLE IF NOT EXISTS wallet.wallets (
    -- Primary Key
    wallet_id VARCHAR(255) PRIMARY KEY,

    -- Owner
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),

    -- Balance (8 decimal places for precision)
    balance DECIMAL(20, 8) NOT NULL DEFAULT 0,
    locked_balance DECIMAL(20, 8) NOT NULL DEFAULT 0,

    -- Currency and Type
    currency VARCHAR(20) NOT NULL DEFAULT 'CREDIT',
    wallet_type VARCHAR(20) NOT NULL DEFAULT 'fiat',

    -- Blockchain Integration
    blockchain_address VARCHAR(255),
    blockchain_network VARCHAR(50),
    on_chain_balance DECIMAL(20, 8),
    sync_status VARCHAR(20),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Metadata (flexible JSONB)
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON wallet.wallets(user_id);
CREATE INDEX IF NOT EXISTS idx_wallets_user_type ON wallet.wallets(user_id, wallet_type);
CREATE INDEX IF NOT EXISTS idx_wallets_is_active ON wallet.wallets(is_active);
CREATE INDEX IF NOT EXISTS idx_wallets_blockchain ON wallet.wallets(blockchain_network, blockchain_address) WHERE blockchain_address IS NOT NULL;

-- Comments
COMMENT ON TABLE wallet.wallets IS 'Digital wallets for users and organizations';
COMMENT ON COLUMN wallet.wallets.wallet_id IS 'Unique wallet identifier (UUID)';
COMMENT ON COLUMN wallet.wallets.user_id IS 'Owner user ID (from account_service)';
COMMENT ON COLUMN wallet.wallets.balance IS 'Current balance (8 decimal precision)';
COMMENT ON COLUMN wallet.wallets.locked_balance IS 'Balance reserved for pending operations';
COMMENT ON COLUMN wallet.wallets.wallet_type IS 'Wallet type: fiat, crypto, hybrid';
COMMENT ON COLUMN wallet.wallets.currency IS 'Currency code: CREDIT, USD, ETH, etc.';
```

#### Table: wallet.transactions

```sql
-- Create transactions table
CREATE TABLE IF NOT EXISTS wallet.transactions (
    -- Primary Key
    transaction_id VARCHAR(255) PRIMARY KEY,

    -- Wallet Reference
    wallet_id VARCHAR(255) NOT NULL REFERENCES wallet.wallets(wallet_id),
    user_id VARCHAR(255) NOT NULL,

    -- Transaction Type
    transaction_type VARCHAR(50) NOT NULL,

    -- Amount and Balance
    amount DECIMAL(20, 8) NOT NULL,
    balance_before DECIMAL(20, 8) NOT NULL,
    balance_after DECIMAL(20, 8) NOT NULL,
    fee_amount DECIMAL(20, 8) DEFAULT 0,

    -- Currency
    currency VARCHAR(20) NOT NULL DEFAULT 'USD',

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'completed',

    -- Description and References
    description TEXT,
    reference_id VARCHAR(255),
    reference_type VARCHAR(50),

    -- Transfer fields
    from_wallet_id VARCHAR(255),
    to_wallet_id VARCHAR(255),

    -- Blockchain fields
    blockchain_txn_hash VARCHAR(255),
    blockchain_confirmation_count INTEGER,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_transactions_wallet_id ON wallet.transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON wallet.transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON wallet.transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON wallet.transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_reference ON wallet.transactions(reference_id) WHERE reference_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_transactions_blockchain ON wallet.transactions(blockchain_txn_hash) WHERE blockchain_txn_hash IS NOT NULL;

-- Comments
COMMENT ON TABLE wallet.transactions IS 'Immutable transaction records for wallet operations';
COMMENT ON COLUMN wallet.transactions.transaction_id IS 'Unique transaction identifier (UUID)';
COMMENT ON COLUMN wallet.transactions.transaction_type IS 'Type: deposit, withdraw, consume, refund, transfer, reward, fee';
COMMENT ON COLUMN wallet.transactions.amount IS 'Transaction amount (always positive)';
COMMENT ON COLUMN wallet.transactions.balance_before IS 'Wallet balance before transaction';
COMMENT ON COLUMN wallet.transactions.balance_after IS 'Wallet balance after transaction';
COMMENT ON COLUMN wallet.transactions.reference_id IS 'External reference (payment_id, billing_record_id)';
```

### Index Strategy

1. **Primary Key** (`wallet_id`, `transaction_id`): Clustered index for fast lookups
2. **User Index** (`idx_wallets_user_id`): B-tree for user wallet queries
3. **User+Type Index** (`idx_wallets_user_type`): Composite for get_user_wallets with type
4. **Transaction Wallet** (`idx_transactions_wallet_id`): Transaction history queries
5. **Transaction Date** (`idx_transactions_created_at DESC`): Recent transactions first
6. **Reference Index** (`idx_transactions_reference`): Lookup by payment/billing ID
7. **Blockchain Index** (`idx_transactions_blockchain`): On-chain transaction lookup

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects**:
```
wallet.created                # New wallet created
wallet.deposited              # Funds deposited
wallet.withdrawn              # Funds withdrawn
wallet.consumed               # Credits consumed
wallet.transferred            # Funds transferred
wallet.refunded               # Transaction refunded
wallet.tokens.deducted        # Token deduction for billing
wallet.tokens.insufficient    # Insufficient tokens alert
wallet.balance.low            # Low balance warning
```

### Event Models (events/models.py)

```python
class WalletCreatedEventData(BaseModel):
    """Event: wallet.created"""
    wallet_id: str
    user_id: str
    wallet_type: str
    currency: str
    balance: float
    timestamp: datetime

class WalletDepositedEventData(BaseModel):
    """Event: wallet.deposited"""
    wallet_id: str
    user_id: str
    transaction_id: str
    amount: float
    balance_before: float
    balance_after: float
    reference_id: Optional[str]
    timestamp: datetime

class WalletConsumedEventData(BaseModel):
    """Event: wallet.consumed"""
    wallet_id: str
    user_id: str
    transaction_id: str
    amount: float
    balance_before: float
    balance_after: float
    usage_record_id: Optional[str]
    timestamp: datetime

class TokensDeductedEventData(BaseModel):
    """Event: wallet.tokens.deducted"""
    user_id: str
    billing_record_id: str
    transaction_id: str
    tokens_deducted: int
    balance_before: Decimal
    balance_after: Decimal
    monthly_quota: Optional[int]
    monthly_used: Optional[int]

class TokensInsufficientEventData(BaseModel):
    """Event: wallet.tokens.insufficient"""
    user_id: str
    billing_record_id: str
    tokens_required: int
    tokens_available: Decimal
    tokens_deficit: int
    suggested_action: str  # "purchase_credits", "upgrade_plan"
```

### Event Subscriptions (events/handlers.py)

```python
def get_event_handlers(wallet_service, event_bus):
    """Get all event handlers for wallet service"""
    return {
        "payment_service.payment.completed": handle_payment_completed,
        "payment_service.payment.refunded": handle_payment_refunded,
        "subscription_service.subscription.created": handle_subscription_created,
        "account_service.user.created": handle_user_created,
        "account_service.user.deleted": handle_user_deleted,
        "billing_service.billing.calculated": handle_billing_calculated,
    }
```

### Event Flow Diagram

```
┌─────────────┐
│   Client    │ (Payment Service)
└──────┬──────┘
       │ POST /payments
       ↓
┌──────────────────┐
│ Payment Service  │
│                  │
│  Process Payment │───→ Stripe/PayPal
│                  │         │
└──────────────────┘         │ Success
       │                     ↓
       │ Event: payment.completed
       ↓
┌─────────────────┐
│   NATS Bus      │
│ Subject:        │
│ payment.        │
│ completed       │
└────────┬────────┘
         │
         ↓
┌────────────────────────────┐
│     Wallet Service         │
│  handle_payment_completed  │
│                            │
│  1. Get user's wallet      │
│  2. Deposit funds          │───→ PostgreSQL (wallet.wallets)
│  3. Create transaction     │         │
│  4. Publish deposited      │         │ Success
└────────────────────────────┘         ↓
         │                      ┌──────────────┐
         │ Event: wallet.       │ Return       │
         │ deposited            │ Success      │
         ↓                      └──────────────┘
┌─────────────────┐
│   NATS Bus      │
│ Subject:        │
│ wallet.deposited│
└────────┬────────┘
         │
         ├──→ Notification Service (email/push)
         ├──→ Audit Service (log transaction)
         └──→ Analytics Service (track revenue)
```

---

## Data Flow Diagrams

### 1. Credit Consumption Flow (Billing Integration)

```
Billing Service calculates usage cost
    │
    ↓
Event: billing.calculated
{user_id, billing_record_id, token_equivalent, is_free_tier}
    │
    ↓
┌───────────────────────────────────────┐
│  WalletService.handle_billing_calculated│
│                                        │
│  Step 1: Check free tier               │
│    if is_free_tier → Skip (no charge)  │
│                                        │
│  Step 2: Get user's primary wallet     │
│    repository.get_primary_wallet()  ───┼──→ PostgreSQL
│                                   ←────┤    Result: Wallet
│                                        │
│  Step 3: Check balance                 │
│    if balance < amount → Insufficient  │
│                                        │
│  Step 4: Consume tokens                │
│    repository.consume()            ────┼──→ PostgreSQL: UPDATE wallet.wallets
│                                   ←────┤         SET balance = balance - amount
│    Success                             │
│                                        │
│  Step 5: Publish event                 │
│    if success:                         │
│      publish_tokens_deducted()     ────┼──→ NATS: wallet.tokens.deducted
│    else:                               │
│      publish_tokens_insufficient() ────┼──→ NATS: wallet.tokens.insufficient
└────────────────────────────────────────┘
```

### 2. Wallet-to-Wallet Transfer Flow

```
User requests transfer: A → B (100 Credits)
    │
    ↓
POST /api/v1/wallets/{wallet_a}/transfer
{to_wallet_id: "wallet_b", amount: 100}
    │
    ↓
┌─────────────────────────────────────────┐
│  WalletService.transfer                  │
│                                          │
│  Step 1: Validate source wallet          │
│    Get wallet A and check balance    ────┼──→ PostgreSQL
│                                     ←────┤    Balance: 500 (OK)
│                                          │
│  Step 2: Validate destination wallet     │
│    Get wallet B exists              ─────┼──→ PostgreSQL
│                                     ←────┤    Found (OK)
│                                          │
│  Step 3: Execute atomic transfer         │
│    BEGIN TRANSACTION                     │
│    - Deduct 100 from A                   │
│    - Add 100 to B                        │
│    - Create transaction A (TRANSFER OUT) │
│    - Create transaction B (TRANSFER IN)  │
│    COMMIT                            ────┼──→ PostgreSQL
│                                     ←────┤    Success
│                                          │
│  Step 4: Publish event                   │
│    publish_wallet_transferred()      ────┼──→ NATS: wallet.transferred
│    Payload:                              │    {from_wallet_id, to_wallet_id,
│      from_wallet: A, balance: 400        │     from_user_id, to_user_id,
│      to_wallet: B, balance: +100         │     amount: 100}
└──────────────────────────────────────────┘
    │
    │ Return success with new balance
    ↓
User sees: balance = 400, transfer complete
    │
    ↓
┌─────────────────────────────────┐
│   Event Subscribers             │
│ - Notification (both users)     │
│ - Audit Service (log transfer)  │
│ - Analytics (track transfers)   │
└─────────────────────────────────┘
```

### 3. User Deletion (GDPR) Flow

```
Account Service deletes user
    │
    ↓
Event: user.deleted {user_id}
    │
    ↓
┌──────────────────────────────────────┐
│  WalletService.handle_user_deleted   │
│                                       │
│  Step 1: Get all user wallets         │
│    repository.get_user_wallets()  ────┼──→ PostgreSQL
│                                  ←────┤    Result: [Wallet1, Wallet2]
│                                       │
│  Step 2: Freeze each wallet           │
│    For each wallet:                   │
│      - Set is_active = FALSE          │
│      - Add deletion metadata          │
│      - Preserve balance for audit ────┼──→ PostgreSQL
│                                  ←────┤    2 wallets frozen
│                                       │
│  Step 3: Anonymize transactions       │
│    - Keep: amounts, types, dates      │
│    - Remove: PII from metadata        │
│    repository.anonymize_user_       ──┼──→ PostgreSQL
│      transactions()             ←────┤    Anonymized 47 transactions
│                                       │
│  (No event published - internal)      │
└───────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+**: Programming language
- **FastAPI 0.104+**: Web framework
- **Pydantic 2.0+**: Data validation
- **asyncio**: Async/await concurrency
- **uvicorn**: ASGI server

### Data Storage
- **PostgreSQL 15+**: Primary database
- **AsyncPostgresClient** (gRPC): Database communication
- **Schema**: `wallet`
- **Tables**: `wallets`, `transactions`

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `wallet.*`
- **Publishers**: Wallet Service (9 event types)
- **Subscribers**: 6 upstream services

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration

### Dependency Injection
- **Protocols (typing.Protocol)**: Interface definitions
- **Factory Pattern**: Production vs test instances
- **ConfigManager**: Environment-based configuration

### Observability
- **Structured Logging**: JSON format
- **core.logger**: Service logger
- **Health Endpoints**: `/health`

---

## Security Considerations

### Input Validation
- **Pydantic Models**: All requests validated
- **Decimal Precision**: 8 decimal places for financial accuracy
- **Amount Validation**: gt=0 for positive amounts
- **SQL Injection**: Parameterized queries via gRPC

### Access Control
- **User Isolation**: All queries filtered by user_id
- **JWT Authentication**: Handled by API Gateway
- **Wallet Ownership**: Operations verify wallet belongs to user
- **Authorization**: Admin endpoints require admin role

### Financial Security
- **Transaction Immutability**: No modification after creation
- **Balance Consistency**: All changes through atomic transactions
- **Audit Trail**: Every operation creates transaction record
- **Refund Limits**: Cannot refund more than original amount

### Data Privacy
- **Soft Delete**: Wallet data preserved for audit
- **GDPR Compliance**: Anonymization on user deletion
- **Encryption in Transit**: TLS for all communication
- **Encryption at Rest**: Database-level encryption (future)

### Rate Limiting (Future)
- **Per User**: 1000 requests/hour
- **Per IP**: 5000 requests/hour
- **Burst**: 100 requests/minute

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New wallet created
- `400 Bad Request`: Validation error, insufficient balance
- `404 Not Found`: Wallet/transaction not found
- `500 Internal Server Error`: Database error, unexpected error
- `503 Service Unavailable`: Database unavailable

### Error Response Format
```json
{
  "detail": "Insufficient balance for withdrawal"
}
```

### Exception Handling
```python
@app.exception_handler(WalletValidationError)
async def validation_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))

@app.exception_handler(WalletNotFoundError)
async def not_found_error_handler(request, exc):
    return HTTPException(status_code=404, detail=str(exc))

@app.exception_handler(InsufficientBalanceError)
async def balance_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))

@app.exception_handler(WalletServiceError)
async def service_error_handler(request, exc):
    return HTTPException(status_code=500, detail=str(exc))
```

---

## Performance Optimization

### Database Optimization
- **Indexes**: Strategic indexes on wallet_id, user_id, transaction dates
- **Connection Pooling**: gRPC client pools connections
- **Parameterized Queries**: Prepared statement efficiency
- **Decimal Precision**: 8 decimal places prevents rounding errors

### API Optimization
- **Async Operations**: All I/O is async
- **Pagination**: Max limit=100 to prevent memory overflow
- **Lazy Loading**: Event publishers loaded on demand
- **Caching**: Future: Redis for frequently accessed balances

### Event Publishing
- **Non-Blocking**: Event failures don't block operations
- **Async Publishing**: Fire-and-forget pattern
- **Idempotency**: Event ID tracking prevents duplicates
- **Error Logging**: Failed publishes logged for retry

### Transaction Processing
- **Atomic Updates**: Single query for balance changes
- **Optimistic Concurrency**: Balance check before update
- **Batch Statistics**: Aggregation in single query

---

## Testing Strategy

### Contract Testing (Layer 4 & 5)
- **Data Contract**: Pydantic schema validation
- **Logic Contract**: Business rule documentation (35 rules)
- **Component Tests**: Factory, builder, validation tests

### Unit Testing
- **Service Layer**: Mock repository, test business logic
- **Repository Layer**: Test query construction
- **Event Handlers**: Test event processing

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **Event Publishing**: Verify events published correctly
- **Event Handling**: Test event subscription handlers

### API Testing
- **Endpoint Contracts**: All 17+ endpoints tested
- **Error Handling**: Validation, not found, insufficient balance
- **Pagination**: Page boundaries, empty results

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation
- **Database Connectivity**: PostgreSQL availability

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Wallet Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/wallet_service.md
- PRD: docs/prd/wallet_service.md
- Data Contract: tests/contracts/wallet/data_contract.py
- Logic Contract: tests/contracts/wallet/logic_contract.md
