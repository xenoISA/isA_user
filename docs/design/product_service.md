# Product Service - Design Document

## Design Overview

**Service Name**: product_service
**Port**: 8215
**Version**: 1.0.0
**Protocol**: HTTP REST API
**Last Updated**: 2025-12-16

### Design Principles
1. **Product-Centric**: Central catalog for all billable services
2. **Flexible Pricing**: Support multiple pricing models (usage, subscription, hybrid)
3. **Event-Driven Synchronization**: NATS events for billing and wallet integration
4. **Separation of Concerns**: Product/pricing only - no payment or wallet logic
5. **Fail-Open Validation**: Service client failures don't block operations
6. **Credit-Based System**: Platform credits enable micro-transactions

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Clients                        │
│   (Session Service, Billing Service, Admin Dashboard)       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP REST API
                       │ (via API Gateway - JWT validation)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                Product Service (Port 8215)                   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              FastAPI HTTP Layer (main.py)             │ │
│  │  - Request validation (Pydantic models)               │ │
│  │  - Response formatting                                │ │
│  │  - Error handling & exception handlers                │ │
│  │  - Health checks (/health)                            │ │
│  │  - Lifecycle management (startup/shutdown)            │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Service Layer (product_service.py)               │ │
│  │  - Business logic (subscription lifecycle)            │ │
│  │  - Product catalog queries                            │ │
│  │  - Usage recording coordination                       │ │
│  │  - Event publishing orchestration                     │ │
│  │  - Service client calls (account, organization)       │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Repository Layer (product_repository.py)         │ │
│  │  - Database CRUD operations                           │ │
│  │  - PostgreSQL gRPC communication                      │ │
│  │  - Query construction (parameterized)                 │ │
│  │  - Result parsing (proto to Pydantic)                 │ │
│  │  - In-memory subscription cache (temporary)           │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │      Event Publishing (events/publishers.py)          │ │
│  │  - NATS event bus integration                         │ │
│  │  - Event model construction                           │ │
│  │  - Async non-blocking publishing                      │ │
│  └───────────────────────────────────────────────────────┘ │
└───────────────────────┼──────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        │               │               │               │
        ↓               ↓               ↓               ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────┐
│  PostgreSQL  │ │    NATS     │ │   Consul   │ │  Clients   │
│   (gRPC)     │ │  (Events)   │ │ (Discovery)│ │            │
│              │ │             │ │            │ │ - Account  │
│  Schema:     │ │  Subjects:  │ │  Service:  │ │ - Org      │
│  product     │ │subscription.│ │  product_  │ │            │
│  Tables:     │ │  created    │ │  service   │ │            │
│  - products  │ │subscription.│ │            │ │            │
│  - pricing   │ │  status     │ │  Health:   │ │            │
│              │ │  changed    │ │  /health   │ │            │
│  Indexes:    │ │product.     │ │            │ │            │
│  - product_id│ │  usage      │ │            │ │            │
│  - category  │ │  recorded   │ │            │ │            │
│  - is_active │ │             │ │            │ │            │
└──────────────┘ └─────────────┘ └────────────┘ └────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Product Service                         │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │   Models    │───→│   Service   │───→│ Repository   │   │
│  │  (Pydantic) │    │ (Business)  │    │   (Data)     │   │
│  │             │    │             │    │              │   │
│  │ - Product   │    │ - Product   │    │ - Product    │   │
│  │ - Category  │    │   Service   │    │   Repository │   │
│  │ - Pricing   │    │             │    │              │   │
│  │ - Plan      │    │             │    │              │   │
│  │ - Sub       │    │             │    │              │   │
│  │ - Usage     │    │             │    │              │   │
│  └─────────────┘    └─────────────┘    └──────────────┘   │
│         ↑                  ↑                    ↑           │
│         │                  │                    │           │
│  ┌──────┴──────────────────┴────────────────────┴───────┐  │
│  │              FastAPI Main (main.py)                   │  │
│  │  - Dependency Injection (get_product_service)        │  │
│  │  - Route Handlers (16 endpoints)                     │  │
│  │  - Exception Handlers (HTTPException)                │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Event Publishers                         │  │
│  │  (events/publishers.py, events/models.py)            │  │
│  │  - publish_subscription_created                      │  │
│  │  - publish_subscription_status_changed              │  │
│  │  - publish_product_usage_recorded                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Service Clients                       │  │
│  │              (clients/__init__.py)                    │  │
│  │  - AccountClient (user validation)                   │  │
│  │  - OrganizationClient (org validation)               │  │
│  │  - Fail-open for testing environments                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. FastAPI HTTP Layer (main.py)

**Responsibilities**:
- HTTP request/response handling
- Request validation via Pydantic models
- Route definitions (16 endpoints)
- Health checks
- Service initialization (lifespan management)
- Consul registration
- NATS event bus setup
- Exception handling

**Key Endpoints**:
```python
# Health Checks
GET /health                                    # Basic health check
GET /api/v1/product/info                       # Service info

# Product Catalog
GET /api/v1/product/categories                 # List categories
GET /api/v1/product/products                   # List products (filtered)
GET /api/v1/product/products/{product_id}      # Get product details
GET /api/v1/product/products/{id}/pricing      # Get product pricing
GET /api/v1/product/products/{id}/availability # Check availability

# Subscription Management
GET  /api/v1/product/subscriptions/user/{user_id}  # User subscriptions
GET  /api/v1/product/subscriptions/{id}            # Get subscription
POST /api/v1/product/subscriptions                 # Create subscription
PUT  /api/v1/product/subscriptions/{id}/status     # Update status

# Usage Tracking
POST /api/v1/product/usage/record              # Record usage
GET  /api/v1/product/usage/records             # Query usage

# Statistics
GET /api/v1/product/statistics/usage           # Usage stats
GET /api/v1/product/statistics/service         # Service stats
```

**Lifecycle Management**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global product_service, repository, event_bus, account_client, organization_client

    # Startup
    # 1. Initialize repository
    repository = ProductRepository(config=config_manager)
    await repository.initialize()

    # 2. Initialize service clients (fail-open)
    try:
        account_client = AccountClient()
        organization_client = OrganizationClient()
    except Exception as e:
        logger.warning(f"Failed to initialize service clients: {e}")
        account_client = None
        organization_client = None

    # 3. Initialize NATS event bus
    try:
        event_bus = await get_event_bus("product_service")
    except Exception as e:
        logger.warning(f"Failed to initialize event bus: {e}")
        event_bus = None

    # 4. Create service with dependencies
    product_service = ProductService(
        repository,
        event_bus=event_bus,
        account_client=account_client,
        organization_client=organization_client
    )

    # 5. Subscribe to events
    if event_bus:
        handler_map = get_event_handlers(product_service)
        for event_pattern, handler_func in handler_map.items():
            await event_bus.subscribe_to_events(
                pattern=event_pattern,
                handler=handler_func
            )

    # 6. Consul registration
    if config.consul_enabled:
        consul_registry.register()

    yield  # Service runs

    # Shutdown
    if consul_registry:
        consul_registry.deregister()
    if account_client:
        await account_client.close()
    if organization_client:
        await organization_client.close()
    if event_bus:
        await event_bus.close()
    if repository:
        await repository.close()
```

### 2. Service Layer (product_service.py)

**Class**: `ProductService`

**Responsibilities**:
- Business logic execution
- Subscription lifecycle management
- Usage recording coordination
- Event publishing orchestration
- Service client integration (validation)

**Key Methods**:
```python
class ProductService:
    def __init__(
        self,
        repository: ProductRepository,
        event_bus=None,
        account_client: Optional[AccountClient] = None,
        organization_client: Optional[OrganizationClient] = None
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.account_client = account_client
        self.organization_client = organization_client

    # ==================== Product Catalog ====================

    async def get_product_categories(self) -> List[ProductCategory]:
        """Get all product categories"""
        return await self.repository.get_categories()

    async def get_products(
        self,
        category_id: Optional[str] = None,
        product_type: Optional[ProductType] = None,
        is_active: bool = True
    ) -> List[Product]:
        """Get filtered product list"""
        return await self.repository.get_products(
            category=category_id,
            product_type=product_type,
            is_active=is_active
        )

    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get single product by ID"""
        return await self.repository.get_product(product_id)

    async def get_product_pricing(
        self,
        product_id: str,
        user_id: Optional[str] = None,
        subscription_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get product pricing with optional personalization"""
        return await self.repository.get_product_pricing(
            product_id=product_id,
            user_id=user_id,
            subscription_id=subscription_id
        )

    async def check_product_availability(
        self,
        product_id: str,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if product is available for user"""
        product = await self.repository.get_product(product_id)
        if not product:
            return {"available": False, "reason": "Product not found"}

        if not product.is_active:
            return {"available": False, "reason": "Product is not active"}

        return {"available": True, "product": product.model_dump()}

    # ==================== Subscription Management ====================

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        organization_id: Optional[str] = None,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserSubscription:
        """Create new subscription"""
        # 1. Validate user (fail-open)
        if self.account_client:
            try:
                user_exists = await self.account_client.get_user(user_id)
                if not user_exists:
                    logger.warning(f"User {user_id} not found, proceeding anyway")
            except Exception as e:
                logger.warning(f"User validation error: {e}, proceeding")

        # 2. Validate organization (fail-open)
        if organization_id and self.organization_client:
            try:
                org_exists = await self.organization_client.get_organization(organization_id)
                if not org_exists:
                    logger.warning(f"Organization {organization_id} not found, proceeding")
            except Exception as e:
                logger.warning(f"Organization validation error: {e}, proceeding")

        # 3. Get service plan
        service_plan = await self.repository.get_service_plan(plan_id)
        if not service_plan:
            raise ValueError(f"Service plan {plan_id} not found")

        # 4. Create subscription
        subscription = UserSubscription(
            subscription_id=str(uuid.uuid4()),
            user_id=user_id,
            organization_id=organization_id,
            plan_id=plan_id,
            plan_tier=service_plan.get("plan_tier", "basic"),
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.utcnow(),
            current_period_end=self._calculate_period_end(billing_cycle),
            billing_cycle=billing_cycle,
            metadata=metadata or {}
        )

        # 5. Save to repository
        created_subscription = await self.repository.create_subscription(subscription)

        # 6. Publish event
        await publish_subscription_created(
            event_bus=self.event_bus,
            subscription_id=created_subscription.subscription_id,
            user_id=created_subscription.user_id,
            organization_id=created_subscription.organization_id,
            plan_id=created_subscription.plan_id,
            plan_tier=created_subscription.plan_tier,
            billing_cycle=created_subscription.billing_cycle.value,
            status=created_subscription.status.value,
            current_period_start=created_subscription.current_period_start,
            current_period_end=created_subscription.current_period_end,
            metadata=metadata
        )

        return created_subscription

    def _calculate_period_end(self, billing_cycle: BillingCycle) -> datetime:
        """Calculate billing period end date"""
        now = datetime.utcnow()
        if billing_cycle == BillingCycle.MONTHLY:
            return now + timedelta(days=30)
        elif billing_cycle == BillingCycle.QUARTERLY:
            return now + timedelta(days=90)
        elif billing_cycle == BillingCycle.YEARLY:
            return now + timedelta(days=365)
        else:
            return now + timedelta(days=30)

    async def update_subscription_status(
        self,
        subscription_id: str,
        status: SubscriptionStatus
    ) -> bool:
        """Update subscription status"""
        # 1. Get current subscription
        subscription = await self.repository.get_subscription(subscription_id)
        if not subscription:
            return False

        old_status = subscription.status.value

        # 2. Update status
        success = await self.repository.update_subscription_status(
            subscription_id=subscription_id,
            new_status=status.value
        )

        if not success:
            return False

        # 3. Publish event
        await publish_subscription_status_changed(
            event_bus=self.event_bus,
            subscription_id=subscription_id,
            user_id=subscription.user_id,
            organization_id=subscription.organization_id,
            plan_id=subscription.plan_id,
            old_status=old_status,
            new_status=status.value
        )

        return True

    # ==================== Usage Tracking ====================

    async def record_product_usage(
        self,
        user_id: str,
        organization_id: Optional[str],
        subscription_id: Optional[str],
        product_id: str,
        usage_amount: Decimal,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        usage_details: Optional[Dict[str, Any]] = None,
        usage_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Record product usage"""
        # 1. Validate user (fail-open)
        if self.account_client:
            try:
                user_valid = await self.account_client.validate_user(user_id)
                if not user_valid:
                    logger.warning(f"User {user_id} validation failed, proceeding")
            except Exception as e:
                logger.warning(f"User validation error: {e}, proceeding")

        # 2. Validate product
        product = await self.repository.get_product(product_id)
        if not product:
            return {
                "success": False,
                "message": f"Product {product_id} not found",
                "usage_record_id": None
            }

        # 3. Validate subscription if provided
        if subscription_id:
            subscription = await self.repository.get_subscription(subscription_id)
            if not subscription:
                return {
                    "success": False,
                    "message": f"Subscription {subscription_id} not found",
                    "usage_record_id": None
                }
            if subscription.status != SubscriptionStatus.ACTIVE:
                return {
                    "success": False,
                    "message": f"Subscription {subscription_id} is not active",
                    "usage_record_id": None
                }

        # 4. Record usage
        usage_record_id = await self.repository.record_product_usage(
            user_id=user_id,
            organization_id=organization_id,
            subscription_id=subscription_id,
            product_id=product_id,
            usage_amount=usage_amount,
            session_id=session_id,
            request_id=request_id,
            usage_details=usage_details,
            usage_timestamp=usage_timestamp
        )

        # 5. Publish event
        await publish_product_usage_recorded(
            event_bus=self.event_bus,
            usage_record_id=usage_record_id,
            user_id=user_id,
            organization_id=organization_id,
            subscription_id=subscription_id,
            product_id=product_id,
            usage_amount=float(usage_amount),
            session_id=session_id,
            request_id=request_id,
            usage_details=usage_details,
            timestamp=usage_timestamp
        )

        return {
            "success": True,
            "message": "Usage recorded successfully",
            "usage_record_id": usage_record_id,
            "product": product.model_dump(),
            "recorded_amount": float(usage_amount),
            "timestamp": usage_timestamp or datetime.utcnow()
        }
```

### 3. Repository Layer (product_repository.py)

**Class**: `ProductRepository`

**Responsibilities**:
- PostgreSQL CRUD operations
- gRPC communication with postgres_grpc_service
- Query construction (parameterized)
- Result parsing (proto JSONB to Python dict)
- Temporary in-memory cache for subscriptions

**Key Methods**:
```python
class ProductRepository:
    def __init__(self, config: Optional[ConfigManager] = None):
        # Discover PostgreSQL service
        postgres_host, postgres_port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061
        )
        self.db = AsyncPostgresClient(
            host=postgres_host,
            port=postgres_port,
            user_id="product_service"
        )
        self.schema = "product"
        self.products_table = "products"
        self._subscriptions_cache = {}  # Temporary

    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        query = f'''
            SELECT * FROM {self.schema}.{self.products_table}
            WHERE product_id = $1
        '''
        async with self.db:
            result = await self.db.query_row(query, params=[product_id])
        if result:
            return self._row_to_product(result)
        return None

    async def get_products(
        self,
        category: Optional[str] = None,
        product_type: Optional[ProductType] = None,
        is_active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Product]:
        """Get products with filters"""
        conditions = []
        params = []
        param_count = 0

        if category:
            param_count += 1
            conditions.append(f"category = ${param_count}")
            params.append(category)

        if product_type:
            param_count += 1
            conditions.append(f"product_type = ${param_count}")
            params.append(product_type.value)

        if is_active is not None:
            param_count += 1
            conditions.append(f"is_active = ${param_count}")
            params.append(is_active)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f'''
            SELECT * FROM {self.schema}.{self.products_table}
            {where_clause}
            ORDER BY display_order ASC, created_at DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        '''
        params.extend([limit, offset])

        async with self.db:
            results = await self.db.query(query, params=params)

        return [self._row_to_product(row) for row in results] if results else []

    async def get_categories(self) -> List[ProductCategory]:
        """Get distinct categories from products"""
        query = f'''
            SELECT DISTINCT category
            FROM {self.schema}.{self.products_table}
            WHERE is_active = true
            ORDER BY category
        '''
        async with self.db:
            results = await self.db.query(query, params=[])

        if results:
            categories = []
            for idx, row in enumerate(results):
                category_name = row.get("category")
                categories.append(ProductCategory(
                    category_id=category_name,
                    name=category_name.replace("_", " ").title(),
                    display_order=idx,
                    is_active=True
                ))
            return categories
        return []

    async def get_product_pricing(
        self,
        product_id: str,
        user_id: Optional[str] = None,
        subscription_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get pricing with tiered structure"""
        query = f'''
            SELECT product_id, product_name, product_type,
                   base_price, currency, billing_interval,
                   features, quota_limits
            FROM {self.schema}.{self.products_table}
            WHERE product_id = $1 AND is_active = true
        '''
        async with self.db:
            result = await self.db.query_row(query, params=[product_id])

        if not result:
            return None

        base_price = float(result.get("base_price", 0.0))
        return {
            "product_id": result.get("product_id"),
            "product_name": result.get("product_name"),
            "base_price": base_price,
            "currency": result.get("currency", "USD"),
            "pricing_type": "usage_based",
            "tiers": [
                {"tier_name": "Base", "min_units": 0, "max_units": 1000, "price_per_unit": base_price},
                {"tier_name": "Standard", "min_units": 1001, "max_units": 10000, "price_per_unit": round(base_price * 0.9, 4)},
                {"tier_name": "Premium", "min_units": 10001, "max_units": None, "price_per_unit": round(base_price * 0.8, 4)}
            ]
        }

    def _row_to_product(self, row: Dict[str, Any]) -> Product:
        """Convert database row to Product model"""
        return Product(
            id=int(row.get("id")) if row.get("id") else None,
            product_id=row.get("product_id"),
            category_id=row.get("category", ""),
            name=row.get("product_name", ""),
            description=row.get("description"),
            product_type=ProductType(row.get("product_type")),
            provider=row.get("provider"),
            is_active=row.get("is_active", True),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )
```

---

## Database Schema Design

### PostgreSQL Schema: `product`

#### Table: product.products

```sql
-- Create product schema
CREATE SCHEMA IF NOT EXISTS product;

-- Create products table
CREATE TABLE IF NOT EXISTS product.products (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) UNIQUE NOT NULL,

    -- Product Info
    product_name VARCHAR(255) NOT NULL,
    product_code VARCHAR(100),
    description TEXT,
    category VARCHAR(100),

    -- Product Classification
    product_type VARCHAR(50) NOT NULL,
    provider VARCHAR(100),

    -- Pricing
    base_price DECIMAL(12, 4) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'USD',
    billing_interval VARCHAR(50) DEFAULT 'per_unit',

    -- Features and Limits
    features JSONB DEFAULT '[]'::jsonb,
    quota_limits JSONB DEFAULT '{}'::jsonb,
    specifications JSONB DEFAULT '{}'::jsonb,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_category ON product.products(category);
CREATE INDEX IF NOT EXISTS idx_products_type ON product.products(product_type);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON product.products(is_active);
CREATE INDEX IF NOT EXISTS idx_products_provider ON product.products(provider);
CREATE INDEX IF NOT EXISTS idx_products_features ON product.products USING GIN(features);
```

#### Future Tables (TODO)

```sql
-- Service Plans
CREATE TABLE IF NOT EXISTS product.service_plans (
    id SERIAL PRIMARY KEY,
    plan_id VARCHAR(255) UNIQUE NOT NULL,
    plan_name VARCHAR(255) NOT NULL,
    plan_tier VARCHAR(50) NOT NULL,
    monthly_price DECIMAL(12, 2) DEFAULT 0,
    yearly_price DECIMAL(12, 2) DEFAULT 0,
    included_credits INTEGER DEFAULT 0,
    features JSONB DEFAULT '[]'::jsonb,
    usage_limits JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Subscriptions
CREATE TABLE IF NOT EXISTS product.user_subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    plan_id VARCHAR(255) NOT NULL,
    plan_tier VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    billing_cycle VARCHAR(50),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage Records
CREATE TABLE IF NOT EXISTS product.product_usage_records (
    id SERIAL PRIMARY KEY,
    usage_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    organization_id VARCHAR(255),
    subscription_id VARCHAR(255),
    product_id VARCHAR(255) NOT NULL,
    usage_amount DECIMAL(18, 6) NOT NULL,
    unit_type VARCHAR(50),
    total_cost DECIMAL(12, 4),
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    usage_details JSONB DEFAULT '{}'::jsonb,
    usage_timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Event-Driven Architecture

### Event Publishing (events/publishers.py)

**NATS Subjects**:
```
product_service.subscription.created       # New subscription created
product_service.subscription.status_changed # Subscription status updated
product_service.product.usage.recorded     # Usage event recorded
```

### Event Models (events/models.py)

```python
class SubscriptionCreatedEventData(BaseModel):
    """Event: subscription.created"""
    subscription_id: str
    user_id: str
    organization_id: Optional[str]
    plan_id: str
    plan_tier: str
    billing_cycle: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    metadata: Optional[Dict[str, Any]]
    created_at: datetime

class SubscriptionStatusChangedEventData(BaseModel):
    """Event: subscription.status_changed"""
    subscription_id: str
    user_id: str
    organization_id: Optional[str]
    plan_id: str
    old_status: str
    new_status: str
    changed_at: datetime

class ProductUsageRecordedEventData(BaseModel):
    """Event: product.usage.recorded"""
    usage_record_id: str
    user_id: str
    organization_id: Optional[str]
    subscription_id: Optional[str]
    product_id: str
    usage_amount: float
    session_id: Optional[str]
    request_id: Optional[str]
    usage_details: Optional[Dict[str, Any]]
    timestamp: datetime
```

### Event Handlers (events/handlers.py)

**Subscribed Events**:
```python
def get_event_handlers(product_service: ProductService) -> Dict[str, Callable]:
    return {
        "payment_service.payment.completed": handle_payment_completed,
        "wallet_service.wallet.insufficient_funds": handle_wallet_insufficient_funds,
        "account_service.user.deleted": handle_user_deleted,
    }

async def handle_payment_completed(message: Dict[str, Any]):
    """Handle payment completion - update subscription if needed"""
    user_id = message.get("user_id")
    payment_status = message.get("payment_status")
    if payment_status == "failed":
        # Update subscription to PAST_DUE
        pass

async def handle_user_deleted(message: Dict[str, Any]):
    """Handle user deletion - cancel subscriptions"""
    user_id = message.get("user_id")
    # Cancel all user subscriptions
```

### Event Flow Diagram

```
┌─────────────┐
│   Client    │ (Session Service)
└──────┬──────┘
       │ POST /api/v1/product/subscriptions
       ↓
┌──────────────────┐
│  Product Service │
│                  │
│  1. Validate     │──→ Account Service (optional)
│  2. Get Plan     │──→ Repository: get_service_plan
│  3. Create Sub   │──→ Repository: create_subscription
│  4. Publish      │
└──────────────────┘
       │ Event: subscription.created
       ↓
┌─────────────────┐
│   NATS Bus      │
└────────┬────────┘
         │
         ├──→ Billing Service (create invoice)
         ├──→ Wallet Service (allocate credits)
         ├──→ Notification Service (welcome email)
         └──→ Audit Service (log event)
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
- **Schema**: `product`
- **Tables**: `products` (+ future: `service_plans`, `user_subscriptions`, `product_usage_records`)

### Event-Driven
- **NATS 2.9+**: Event bus
- **Subjects**: `product_service.*`
- **Publishers**: Subscription, usage events
- **Subscribers**: Payment, wallet, account events

### Service Discovery
- **Consul 1.15+**: Service registry
- **Health Checks**: HTTP `/health`
- **Metadata**: Route registration

### Service Clients
- **AccountClient**: User validation (fail-open)
- **OrganizationClient**: Organization validation (fail-open)
- **HTTP-based**: REST calls to other services

---

## Security Considerations

### Input Validation
- **Pydantic Models**: All requests validated
- **Enum Validation**: ProductType, SubscriptionStatus, BillingCycle
- **SQL Injection**: Parameterized queries via gRPC
- **Amount Validation**: Decimal for precise pricing

### Access Control
- **User Isolation**: Subscriptions filtered by user_id
- **JWT Authentication**: Handled by API Gateway
- **Service Validation**: Client calls verify ownership
- **Rate Limiting**: Future enhancement

### Data Privacy
- **Usage Tracking**: Session/request IDs for tracing
- **Soft Delete**: Subscriptions preserved for audit
- **Encryption in Transit**: TLS for all communication

---

## Performance Optimization

### Database Optimization
- **Indexes**: Strategic indexes on product_id, category, is_active
- **Connection Pooling**: gRPC client pools connections
- **Query Optimization**: LIMIT/OFFSET for pagination
- **In-Memory Cache**: Temporary subscription cache

### API Optimization
- **Async Operations**: All I/O is async
- **Fail-Open Clients**: Validation failures don't block
- **Event Publishing**: Non-blocking async

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful operation
- `201 Created`: New subscription created
- `400 Bad Request`: Invalid enum, missing required field
- `404 Not Found`: Product/subscription not found
- `500 Internal Server Error`: Database error
- `503 Service Unavailable`: Database unavailable

### Error Response Format
```json
{
  "detail": "Invalid billing_cycle: invalid_value"
}
```

---

## Testing Strategy

### Unit Testing
- **Pure Functions**: Pricing calculations, period calculations
- **Model Validation**: Pydantic schema tests
- **Factory Methods**: Test data generation

### Component Testing
- **Service Layer**: Business logic with mocked repository
- **Repository Layer**: Database operations with test DB
- **Event Publishing**: Mock event bus

### Integration Testing
- **HTTP + Database**: Full request/response cycle
- **Event Publishing**: Verify events published
- **Cross-Service**: Client mock testing

### API Testing
- **Endpoint Contracts**: All 16 endpoints tested
- **Error Handling**: Validation, not found, server errors

### Smoke Testing
- **E2E Scripts**: Bash scripts for critical paths
- **Health Checks**: Service startup validation

---

**Document Version**: 1.0
**Last Updated**: 2025-12-16
**Maintained By**: Product Service Engineering Team
**Related Documents**:
- Domain Context: docs/domain/product_service.md
- PRD: docs/prd/product_service.md
- Data Contract: tests/contracts/product/data_contract.py
- Logic Contract: tests/contracts/product/logic_contract.md
