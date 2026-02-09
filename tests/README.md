# isA Testing Guide

**The authoritative reference for all testing in the isA microservices platform.**

---

## Quick Navigation

| Section | Purpose |
|---------|---------|
| [Test Pyramid](#test-pyramid) | Which test layer to use |
| [Directory Structure](#directory-structure) | Where files go |
| [Templates](#templates) | How to create new tests |
| [Contracts](#contracts) | CDD data & logic contracts |
| [Running Tests](#running-tests) | How to execute tests |
| [Infrastructure](#infrastructure) | What you need running |

---

## Quick Start

### Prerequisites

根据测试层级需要不同的环境：

| 测试类型 | 环境 | 需要 K8s | 需要 Port-Forward |
|---------|------|:-------:|:----------------:|
| **Unit** | Local (dev) | ❌ | ❌ |
| **Component** | Local (dev) | ❌ | ❌ |
| **Integration** | K8s (test) | ✅ | ✅ 直连服务 |
| **API** | K8s (test) | ✅ | ✅ 直连服务 |
| **Smoke** | K8s (test) | ✅ | ✅ 通过网关 |

### Environment 1: Local Development (Unit + Component)

```bash
# 1. Create and activate virtual environment
uv venv .venv
source .venv/bin/activate

# 2. Install dev dependencies
uv pip install -r deployment/requirements/dev.txt

# 3. Load dev environment (optional, tests don't need it)
source deployment/environments/dev.env

# 4. Run tests - NO infrastructure needed!
pytest tests/unit -v
pytest tests/component -v
```

### Environment 2: K8s Testing (Integration + API + Smoke)

**K8s 环境信息**:
- **Cluster**: `kind-isa-cloud-local`
- **Namespace**: `isa-cloud-staging`
- **Gateway**: APISIX (port 8000)

```bash
# 1. Verify K8s context
kubectl config current-context  # Should be: kind-isa-cloud-local

# 2. Port-forward infrastructure
kubectl port-forward -n isa-cloud-staging svc/isa-postgres-grpc 50061:50061 &
kubectl port-forward -n isa-cloud-staging svc/nats 4222:4222 &
kubectl port-forward -n isa-cloud-staging svc/redis 6379:6379 &

# 3. Port-forward services (for integration/API tests)
kubectl port-forward -n isa-cloud-staging svc/auth 8201:8201 &
kubectl port-forward -n isa-cloud-staging svc/account 8202:8202 &
kubectl port-forward -n isa-cloud-staging svc/location 8224:8224 &
# ... add other services as needed

# 4. Port-forward gateway (for smoke tests)
kubectl port-forward -n isa-cloud-staging svc/apisix-gateway 8000:8000 &

# 5. Load test environment
source deployment/environments/test.env

# 6. Run tests
pytest tests/integration -v       # Direct service access
pytest tests/api -v               # Direct service access
./tests/smoke/{service}/smoke_test.sh  # Via APISIX gateway
```

### Quick Verification

```bash
# Check direct service access (integration/API tests)
curl http://localhost:8224/health

# Check gateway access (smoke tests)
curl http://localhost:8000/api/v1/locations
```

---

## Test Pyramid

```
                    ┌─────────────────┐
                    │   Layer 5       │  ← E2E with real everything
                    │   Smoke Tests   │     Bash scripts
                    │   (15-18 tests) │     tests/smoke/{service}/
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Layer 4       │  ← Real HTTP + JWT Auth
                    │   API Tests     │     tests/api/{service}/
                    │   (25-30 tests) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Layer 3       │  ← Real HTTP + DB (bypass auth)
                    │ Integration     │     tests/integration/{service}/
                    │   (30-35 tests) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Layer 2       │  ← Mocked dependencies via DI
                    │ Component Tests │     tests/component/{service}/
                    │   (75-85 tests) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Layer 1       │  ← Pure functions, no I/O
                    │   Unit Tests    │     tests/unit/{service}/
                    │   (pure logic)  │
                    └─────────────────┘
```

### Decision Tree: Which Layer?

```
What are you testing?

├─ Pure function with no I/O?
│  └─ → Layer 1: UNIT TEST
│
├─ Service method with business logic?
│  └─ → Layer 2: COMPONENT TEST (mock dependencies)
│
├─ Full CRUD lifecycle with real DB?
│  └─ → Layer 3: INTEGRATION TEST (X-Internal-Call header)
│
├─ HTTP API contract validation with auth?
│  └─ → Layer 4: API TEST (JWT authentication)
│
└─ End-to-end user workflow?
   └─ → Layer 5: SMOKE TEST (bash script)
```

---

## Directory Structure

```
tests/
├── README.md                           # THIS FILE - Master Guide
├── conftest.py                         # Global shared configuration
├── pytest.ini                          # Pytest markers and settings
│
├── fixtures/                           # Shared test data generators
│   ├── __init__.py
│   ├── factories.py                    # Factory Boy factories
│   ├── generators.py                   # Random data generators
│   └── common.py                       # Common test patterns
│
├── contracts/                          # CDD: 3-Contract per service
│   ├── README.md                       # Contract documentation
│   └── {service}/
│       ├── data_contract.py            # Layer 4: Pydantic schemas + TestDataFactory
│       ├── logic_contract.md           # Layer 5: Business rules (BR-SVC-001)
│       └── system_contract.md          # Layer 6: Implementation patterns
│
├── unit/                               # Layer 1: Unit Tests
│   ├── conftest.py                     # Minimal config + markers
│   ├── golden/                         # 🔒 Characterization tests (DO NOT MODIFY)
│   │   └── {service}_service/
│   │       ├── __init__.py
│   │       └── test_{service}_models_golden.py
│   └── tdd/                            # 🆕 TDD tests (new features/fixes)
│       └── {service}_service/
│           ├── __init__.py
│           └── test_{service}_{feature}.py
│
├── component/                          # Layer 2: Component Tests
│   ├── conftest.py                     # Common mock fixtures
│   ├── golden/                         # 🔒 Characterization tests
│   │   └── {service}_service/
│   │       ├── __init__.py
│   │       ├── mocks.py                # Service-specific mocks
│   │       └── test_{service}_golden.py
│   └── tdd/                            # 🆕 TDD tests
│       └── {service}_service/
│           ├── __init__.py
│           ├── mocks.py                # Service-specific mocks
│           └── test_{service}_service.py
│
├── integration/                        # Layer 3: Integration Tests
│   ├── conftest.py                     # DB pool, HTTP client fixtures
│   ├── golden/                         # 🔒 Characterization tests
│   │   └── {service}_service/
│   │       ├── __init__.py
│   │       ├── conftest.py             # Service-specific cleanup fixtures
│   │       └── test_{service}_golden.py
│   ├── tdd/                            # 🆕 TDD tests
│   │   └── {service}_service/
│   │       ├── __init__.py
│   │       ├── conftest.py             # Service-specific cleanup fixtures
│   │       └── test_{service}_crud.py
│   └── flows/                          # Cross-service user journey tests
│       └── test_{flow_name}_flow.py
│
├── api/                                # Layer 4: API Tests
│   ├── conftest.py                     # Auth fixtures, API clients
│   ├── golden/                         # 🔒 Characterization tests
│   │   └── {service}_service/
│   │       ├── __init__.py
│   │       └── test_{service}_api_golden.py
│   └── tdd/                            # 🆕 TDD tests
│       └── {service}_service/
│           ├── __init__.py
│           └── test_{service}_api.py
│
└── smoke/                              # Layer 5: E2E Smoke Tests
    ├── test_common.sh                  # Bash test framework (shared)
    ├── run_smoke_tests.sh              # Global runner
    └── {service}_service/              # One folder per service
        ├── smoke_test.sh               # Main smoke test (REQUIRED)
        ├── run_all.sh                  # Runner (optional, for multiple files)
        └── {feature}_test.sh           # Feature tests (optional)
```

### Naming Conventions

| Item | Pattern | Example |
|------|---------|---------|
| **Test file (TDD)** | `test_{service}_{feature}.py` | `test_device_registration.py` |
| **Test file (Golden)** | `test_{service}_{thing}_golden.py` | `test_device_models_golden.py` |
| **Test class (TDD)** | `Test{Service}{Feature}` | `TestDeviceRegistration` |
| **Test class (Golden)** | `Test{Service}{Feature}Char` | `TestDeviceModelsChar` |
| **Test method** | `test_{action}_{expected}` | `test_register_device_success` |
| **Mock class** | `Mock{Dependency}` | `MockDeviceRepository` |
| **Factory class** | `{Service}TestDataFactory` | `DeviceTestDataFactory` |
| **Contract** | `{Operation}RequestContract` | `DeviceRegisterRequestContract` |
| **Smoke folder** | `{service}_service/` | `device_service/` |
| **Smoke script** | `smoke_test.sh` | `smoke_test.sh` |
| **Smoke runner** | `run_all.sh` | `run_all.sh` |

### Golden vs TDD Tests

| Type | Purpose | Location | Modify? |
|------|---------|----------|---------|
| **Golden** | Capture current behavior (characterization) | `{layer}/golden/{service}_service/` | 🔒 Never modify |
| **TDD** | Define expected behavior (new features/fixes) | `{layer}/tdd/{service}_service/` | ✅ Active development |

---

## Templates

### New Service Checklist (TDD)

When adding tests for a **new service**, create files in `tdd/` directories:

1. **Contracts** (CDD - 3 contracts per service)
   - `tests/contracts/{service}/data_contract.py` - Pydantic schemas + TestDataFactory
   - `tests/contracts/{service}/logic_contract.md` - Business rules + state machines
   - `tests/contracts/{service}/system_contract.md` - Implementation patterns (12 patterns)

2. **Unit Tests** (Layer 1)
   - `tests/unit/tdd/{service}_service/__init__.py`
   - `tests/unit/tdd/{service}_service/test_{service}_models.py`

3. **Component Tests** (Layer 2)
   - `tests/component/tdd/{service}_service/__init__.py`
   - `tests/component/tdd/{service}_service/mocks.py`
   - `tests/component/tdd/{service}_service/test_{service}_service.py`

4. **Integration Tests** (Layer 3)
   - `tests/integration/tdd/{service}_service/__init__.py`
   - `tests/integration/tdd/{service}_service/conftest.py`
   - `tests/integration/tdd/{service}_service/test_{service}_crud.py`

5. **API Tests** (Layer 4)
   - `tests/api/tdd/{service}_service/__init__.py`
   - `tests/api/tdd/{service}_service/test_{service}_api.py`

6. **Smoke Tests** (Layer 5)
   - `tests/smoke/{service}_service/smoke_test.sh` (required)
   - `tests/smoke/{service}_service/run_all.sh` (optional)

### Existing Service Checklist (Golden First)

When adding tests for an **existing service** with production code:

1. **Write golden tests** in `golden/` directories to capture current behavior
   - `tests/unit/golden/{service}_service/test_{service}_models_golden.py`
   - `tests/component/golden/{service}_service/test_{service}_golden.py`
   - `tests/integration/golden/{service}_service/test_{service}_golden.py`
   - `tests/api/golden/{service}_service/test_{service}_api_golden.py`

2. **Run golden tests** - they should all PASS (describing current behavior)

3. **If bugs found**, write TDD tests in `tdd/` directories to fix them

4. **Keep both**: golden for regression safety, TDD for fixes/features

---

## Contracts

### The 3-Contract Architecture

Each service has 3 contracts that together define a complete specification:

| Contract | File | Purpose |
|----------|------|---------|
| **Data Contract** | `data_contract.py` | WHAT data structures (Pydantic + TestDataFactory) |
| **Logic Contract** | `logic_contract.md` | WHAT business rules (BR-XXX, state machines, API contracts) |
| **System Contract** | `system_contract.md` | HOW to implement (12 patterns, dependencies, events) |

**Pattern Reference**: `.claude/skills/cdd-system-contract/SKILL.md` (12 implementation patterns)

---

### API-Service Contract (CRITICAL)

**Why This Matters**: Component tests can pass but the service fails at runtime because the **API layer (main.py)** calls the **Service layer** incorrectly.

#### The Contract Chain

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Request Model     │────►│     main.py         │────►│   Service Method    │
│   (Pydantic)        │     │   (API Layer)       │     │   ({service}.py)    │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘

CreateAccountRequest         @app.post("/accounts")      def create_account(
  user_id: str               async def create(...):          self,
  credit_type: str              result = service.???          user_id: str,
                                                              credit_type: str,
                                                          )
```

#### Common Contract Violations

| Violation | Example | Fix |
|-----------|---------|-----|
| **Passing object instead of fields** | `service.create(request)` when service expects `service.create(field1, field2)` | Unpack: `service.create(user_id=request.user_id, ...)` |
| **Missing service method** | API calls `service.get_balance()` but method doesn't exist | Implement the missing method |
| **Request model missing field** | `CreateRequest` lacks `credit_type` but service requires it | Add field to Pydantic model |
| **Type mismatch** | Request has `amount: str` but service expects `amount: int` | Fix type annotation |

#### Validation Pattern

Before deployment, validate this chain manually or via `api-service-contract-validator` agent:

```python
# 1. Check main.py endpoint
@app.post("/api/v1/accounts")
async def create_account(request: CreateAccountRequest, service = Depends(...)):
    # HOW does main.py call the service?
    result = await service.create_account(request)  # ❌ WRONG if service expects individual args
    result = await service.create_account(          # ✅ CORRECT
        user_id=request.user_id,
        credit_type=request.credit_type,
    )

# 2. Check service method signature
class CreditService:
    async def create_account(
        self,
        user_id: str,           # Must match request.user_id
        credit_type: str,       # Must match request.credit_type
    ) -> Dict[str, Any]:
        ...

# 3. Check request model has all fields
class CreateAccountRequest(BaseModel):
    user_id: str                # ✅ Present
    credit_type: str            # ✅ Present
```

#### Component Test Pattern for Contract Validation

```python
# tests/component/{service}/test_{service}_api_contract.py

class TestAPIServiceContract:
    """Verify API layer correctly calls service layer"""

    async def test_create_endpoint_contract(self, service, mock_repo):
        """Test that main.py create endpoint calls service correctly"""
        from microservices.{service}_service.main import CreateEntityRequest

        # Simulate what main.py receives
        request = CreateEntityRequest(name="test", type="standard")

        # Call service the same way main.py should call it
        result = await service.create_entity(
            name=request.name,
            entity_type=request.type,
        )

        # If this fails, the contract is broken
        assert result is not None
```

#### Automated Validation

Run before deployment:
```bash
python agents/cli.py --service {service} --layer api-service-contract-validator
```

---

### Data Contract Template

Location: `tests/contracts/{service}/data_contract.py`

```python
"""
{Service} Service - Data Contract

Pydantic schemas, test data factory, and request builders.
Zero hardcoded data - all test data generated through factory methods.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
import secrets
import uuid


# ============================================================================
# Request Contracts
# ============================================================================

class {Entity}CreateRequestContract(BaseModel):
    """Contract for {entity} creation requests"""
    name: str = Field(..., min_length=1, max_length=100)
    # Add other required fields

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


class {Entity}UpdateRequestContract(BaseModel):
    """Contract for {entity} update requests"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)


# ============================================================================
# Response Contracts
# ============================================================================

class {Entity}ResponseContract(BaseModel):
    """{Entity} response contract"""
    {entity}_id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Test Data Factory - Zero Hardcoded Data
# ============================================================================

class {Service}TestDataFactory:
    """Test data factory for {service}_service"""

    # === Valid Data Generators ===

    @staticmethod
    def make_{entity}_id() -> str:
        """Generate valid {entity} ID"""
        return f"{entity}_{uuid.uuid4().hex}"

    @staticmethod
    def make_name() -> str:
        """Generate valid name"""
        return f"Test {Entity} {secrets.token_hex(4)}"

    @staticmethod
    def make_timestamp() -> datetime:
        """Generate current timestamp"""
        return datetime.now(timezone.utc)

    @staticmethod
    def make_create_request(**overrides) -> {Entity}CreateRequestContract:
        """Generate valid creation request"""
        defaults = {
            "name": {Service}TestDataFactory.make_name(),
        }
        defaults.update(overrides)
        return {Entity}CreateRequestContract(**defaults)

    # === Invalid Data Generators ===

    @staticmethod
    def make_invalid_name() -> str:
        """Generate invalid name (empty)"""
        return ""

    @staticmethod
    def make_invalid_{entity}_id() -> str:
        """Generate invalid {entity} ID"""
        return "invalid_format"


# ============================================================================
# Request Builders
# ============================================================================

class {Entity}CreateRequestBuilder:
    """Builder for {entity} creation requests"""

    def __init__(self):
        self._name = {Service}TestDataFactory.make_name()

    def with_name(self, value: str) -> '{Entity}CreateRequestBuilder':
        self._name = value
        return self

    def build(self) -> {Entity}CreateRequestContract:
        return {Entity}CreateRequestContract(name=self._name)
```

### Logic Contract Template

Location: `tests/contracts/{service}/logic_contract.md`

```markdown
# {Service} Service - Logic Contract

## Business Rules

### BR-{SVC}-001: {Rule Name}
- **Given**: {precondition}
- **When**: {action}
- **Then**: {expected outcome}
- **Error**: {error if violated}

### BR-{SVC}-002: ...

## State Machines

### {Entity} Lifecycle
```
States: CREATED → ACTIVE → SUSPENDED → DELETED

Transitions:
- CREATED → ACTIVE (on activation)
- ACTIVE → SUSPENDED (on suspend)
- SUSPENDED → ACTIVE (on reactivate)
- ACTIVE → DELETED (on delete)
- DELETED → [terminal]
```

## Edge Cases

### EC-001: {Edge Case Name}
- **Input**: {input scenario}
- **Expected**: {expected behavior}

## Error Handling Contracts

| Error | HTTP Code | Message Format |
|-------|-----------|----------------|
| Not Found | 404 | `{"{entity}_id": "...", "error": "not_found"}` |
| Validation | 422 | `{"detail": [...]}` |
| Unauthorized | 401 | `{"error": "unauthorized"}` |
```

---

### System Contract Template

Location: `tests/contracts/{service}/system_contract.md`

```markdown
# {Service} Service System Contract

## Service Identity

| Property | Value |
|----------|-------|
| **Service Name** | `{service}_service` |
| **Port** | `82XX` |
| **Schema** | `{service}` |
| **Version** | `1.0.0` |

## File Structure
(Document actual service file structure)

## DI Protocols
(List protocols defined in protocols.py)

## Events Published

| Event | Subject | Trigger |
|-------|---------|---------|
| `{ENTITY}_CREATED` | `{service}.{entity}.created` | After creation |
| `{ENTITY}_UPDATED` | `{service}.{entity}.updated` | After update |
| `{ENTITY}_DELETED` | `{service}.{entity}.deleted` | After deletion |

## Events Subscribed

| Event | Source | Handler | Action |
|-------|--------|---------|--------|
| `account.user.deleted` | account_service | `handle_user_deleted` | Cleanup user data |

## Sync Dependencies (Clients)

| Client | Target | Purpose |
|--------|--------|---------|
| `AccountClient` | `account_service:8202` | Verify user exists |

## Database Tables

| Table | Schema | Purpose |
|-------|--------|---------|
| `{entities}` | `{service}` | Main entity storage |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `{SERVICE}_SERVICE_PORT` | `82XX` | Service port |

## Compliance Checklist
- [ ] protocols.py with DI interfaces
- [ ] factory.py for service creation
- [ ] routes_registry.py for Consul
- [ ] migrations/ folder with SQL files
- [ ] events/handlers.py for subscriptions
- [ ] events/publishers.py for publishing
```

**Reference**: See `.claude/skills/cdd-system-contract/SKILL.md` for all 12 implementation patterns.

---

## Layer Templates

### Layer 1: Unit Test Template

Location: `tests/unit/{service}/test_{service}_models.py`

```python
"""
{Service} Service - Unit Tests

Tests for pure utility functions and model validation.
No I/O, no mocks, no fixtures needed.
"""
import pytest
from pydantic import ValidationError
from tests.contracts.{service}.data_contract import (
    {Service}TestDataFactory,
    {Entity}CreateRequestContract,
)

pytestmark = [pytest.mark.unit]


class Test{Entity}ModelValidation:
    """Test Pydantic model validation"""

    def test_valid_request_passes_validation(self):
        """Valid request passes Pydantic validation"""
        request = {Service}TestDataFactory.make_create_request()
        assert isinstance(request, {Entity}CreateRequestContract)

    def test_empty_name_raises_validation_error(self):
        """Empty name raises ValidationError"""
        with pytest.raises(ValidationError):
            {Entity}CreateRequestContract(name="")

    def test_whitespace_name_raises_validation_error(self):
        """Whitespace-only name raises ValidationError"""
        with pytest.raises(ValidationError):
            {Entity}CreateRequestContract(name="   ")


class Test{Service}TestDataFactory:
    """Test factory generates valid unique data"""

    def test_make_{entity}_id_uniqueness(self):
        """Factory generates unique IDs"""
        id1 = {Service}TestDataFactory.make_{entity}_id()
        id2 = {Service}TestDataFactory.make_{entity}_id()
        assert id1 != id2

    def test_make_name_non_empty(self):
        """Factory generates non-empty names"""
        name = {Service}TestDataFactory.make_name()
        assert len(name) > 0
```

### Layer 2: Component Test Template

Location: `tests/component/{service}/test_{service}_service.py`

```python
"""
{Service} Service - Component Tests

Tests {Service}Service business logic with mocked dependencies.
No real I/O - all dependencies injected via fixtures.
"""
import pytest
from unittest.mock import AsyncMock
from tests.contracts.{service}.data_contract import {Service}TestDataFactory

pytestmark = [pytest.mark.component, pytest.mark.asyncio]


class Test{Service}Create:
    """Test {entity} creation business logic"""

    async def test_create_{entity}_success(
        self, {service}_service, mock_{entity}_repository, mock_event_bus
    ):
        """Successful creation returns {entity} data and publishes event"""
        # Arrange
        request = {Service}TestDataFactory.make_create_request()
        mock_{entity}_repository.create.return_value = {
            "{entity}_id": "{entity}_123",
            "name": request.name,
            "status": "active"
        }

        # Act
        result = await {service}_service.create_{entity}(request.model_dump())

        # Assert
        assert result["{entity}_id"] == "{entity}_123"
        mock_{entity}_repository.create.assert_called_once()
        mock_event_bus.publish.assert_called_once()

    async def test_create_{entity}_duplicate_raises_error(
        self, {service}_service, mock_{entity}_repository
    ):
        """Duplicate {entity} raises appropriate error"""
        # Arrange
        request = {Service}TestDataFactory.make_create_request()
        mock_{entity}_repository.get_by_name.return_value = {"existing": True}

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await {service}_service.create_{entity}(request.model_dump())
        assert "duplicate" in str(exc_info.value).lower()


class Test{Service}EventPublishing:
    """Test event publishing behavior"""

    async def test_create_publishes_{entity}_created_event(
        self, {service}_service, mock_{entity}_repository, mock_event_bus
    ):
        """Creation publishes {entity}.created event"""
        # Arrange
        request = {Service}TestDataFactory.make_create_request()
        mock_{entity}_repository.create.return_value = {"{entity}_id": "123"}

        # Act
        await {service}_service.create_{entity}(request.model_dump())

        # Assert
        assert mock_event_bus.publish.called
        call_args = mock_event_bus.publish.call_args
        assert "{entity}.created" in str(call_args)
```

**Mocks file**: `tests/component/{service}/mocks.py`

```python
"""
{Service} Service - Mock Dependencies

Mock implementations for component testing.
"""
from unittest.mock import AsyncMock, MagicMock
from typing import Optional, Dict, Any, List
import uuid


class Mock{Entity}Repository:
    """Mock {entity} repository"""

    def __init__(self):
        self._data: Dict[str, Dict] = {}
        self.create = AsyncMock(side_effect=self._create)
        self.get = AsyncMock(side_effect=self._get)
        self.update = AsyncMock(side_effect=self._update)
        self.delete = AsyncMock(side_effect=self._delete)
        self.list = AsyncMock(return_value=[])
        self.get_by_name = AsyncMock(return_value=None)

    async def _create(self, data: Dict) -> Dict:
        {entity}_id = f"{entity}_{uuid.uuid4().hex[:12]}"
        self._data[{entity}_id] = {**data, "{entity}_id": {entity}_id}
        return self._data[{entity}_id]

    async def _get(self, {entity}_id: str) -> Optional[Dict]:
        return self._data.get({entity}_id)

    async def _update(self, {entity}_id: str, data: Dict) -> Optional[Dict]:
        if {entity}_id in self._data:
            self._data[{entity}_id].update(data)
            return self._data[{entity}_id]
        return None

    async def _delete(self, {entity}_id: str) -> bool:
        if {entity}_id in self._data:
            del self._data[{entity}_id]
            return True
        return False


class MockEventBus:
    """Mock NATS event bus"""

    def __init__(self):
        self.published_events: List[Dict] = []
        self.publish = AsyncMock(side_effect=self._publish)
        self.publish_event = AsyncMock(side_effect=self._publish)

    async def _publish(self, event):
        self.published_events.append(event)
```

**Service conftest**: `tests/component/{service}/conftest.py`

```python
"""
{Service} Component Test Configuration

Service-specific fixtures with mocked dependencies.
"""
import pytest
import pytest_asyncio
from .mocks import Mock{Entity}Repository, MockEventBus


@pytest.fixture
def mock_{entity}_repository():
    """Provide Mock{Entity}Repository"""
    return Mock{Entity}Repository()


@pytest.fixture
def mock_event_bus():
    """Provide MockEventBus"""
    return MockEventBus()


@pytest_asyncio.fixture
async def {service}_service(mock_{entity}_repository, mock_event_bus):
    """Create {Service}Service with mocked dependencies"""
    from microservices.{service}_service.{service}_service import {Service}Service

    return {Service}Service(
        repository=mock_{entity}_repository,
        event_bus=mock_event_bus,
    )
```

### Layer 3: Integration Test Template

Location: `tests/integration/{service}/test_{service}_crud.py`

```python
"""
{Service} Service - Integration Tests

Tests full CRUD lifecycle with real database persistence.
Uses X-Internal-Call header to bypass authentication.
"""
import pytest
import httpx
import uuid
from typing import List

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.requires_db]

{SERVICE}_URL = "http://localhost:{PORT}"
API_BASE = f"{{{SERVICE}_URL}}/api/v1/{entities}"


def make_{entity}_request(**overrides):
    """Create {entity} request with unique data"""
    defaults = {
        "name": f"Test {Entity} {uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    return defaults


class Test{Entity}CRUDIntegration:
    """Test {entity} CRUD with real database"""

    async def test_full_{entity}_lifecycle(
        self, http_client, internal_headers, cleanup_{entities}
    ):
        """
        Integration: Full {entity} lifecycle
        1. Create {entity} via API
        2. Read {entity} and verify data
        3. Update {entity} and verify changes
        4. Delete {entity} and verify removal
        """
        # 1. CREATE
        creation = make_{entity}_request(name="Lifecycle Test")

        create_response = await http_client.post(
            API_BASE,
            json=creation,
            headers=internal_headers,
        )
        assert create_response.status_code in [200, 201]

        {entity}_data = create_response.json()
        {entity}_id = {entity}_data["{entity}_id"]
        cleanup_{entities}({entity}_id)

        assert {entity}_data["name"] == "Lifecycle Test"

        # 2. READ
        get_response = await http_client.get(
            f"{API_BASE}/{{{entity}_id}}",
            headers=internal_headers,
        )
        assert get_response.status_code == 200
        read_data = get_response.json()
        assert read_data["{entity}_id"] == {entity}_id

        # 3. UPDATE
        update_response = await http_client.put(
            f"{API_BASE}/{{{entity}_id}}",
            json={"name": "Updated Name"},
            headers=internal_headers,
        )
        assert update_response.status_code == 200

        # Verify update persisted
        verify_response = await http_client.get(
            f"{API_BASE}/{{{entity}_id}}",
            headers=internal_headers,
        )
        assert verify_response.json()["name"] == "Updated Name"

        # 4. DELETE
        delete_response = await http_client.delete(
            f"{API_BASE}/{{{entity}_id}}",
            headers=internal_headers,
        )
        assert delete_response.status_code == 200

        # Verify deleted
        get_deleted = await http_client.get(
            f"{API_BASE}/{{{entity}_id}}",
            headers=internal_headers,
        )
        assert get_deleted.status_code == 404
```

**Service conftest**: `tests/integration/{service}/conftest.py`

```python
"""
{Service} Integration Test Configuration

Service-specific cleanup fixtures.
"""
import pytest
import pytest_asyncio
from typing import List

{SERVICE}_URL = "http://localhost:{PORT}"
API_BASE = f"{{{SERVICE}_URL}}/api/v1/{entities}"


@pytest_asyncio.fixture
async def cleanup_{entities}(http_client, internal_headers):
    """Track and cleanup {entities} created during tests"""
    created_ids: List[str] = []

    def track({entity}_id: str) -> str:
        created_ids.append({entity}_id)
        return {entity}_id

    yield track

    # Cleanup after test
    for {entity}_id in created_ids:
        try:
            await http_client.delete(
                f"{API_BASE}/{{{entity}_id}}",
                headers=internal_headers
            )
        except Exception:
            pass
```

### Layer 4: API Test Template

Location: `tests/api/{service}/test_{service}_api.py`

```python
"""
{Service} Service - API Tests

Tests HTTP API contracts with real authentication.
Uses JWT tokens from auth_service.
"""
import pytest
import uuid

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


class Test{Entity}RegistrationAPI:
    """
    POST /api/v1/{entities}
    """

    async def test_register_{entity}_success(self, {service}_api, api_assert):
        """POST /api/v1/{entities} returns 201 with {entity} data"""
        registration = {
            "name": f"Test {Entity} {uuid.uuid4().hex[:8]}",
        }

        response = await {service}_api.post("", json=registration)

        api_assert.assert_created(response)
        data = response.json()
        api_assert.assert_has_fields(data, [
            "{entity}_id", "name", "status", "created_at"
        ])

    async def test_register_{entity}_validation_error(self, {service}_api, api_assert):
        """POST with invalid data returns 422"""
        response = await {service}_api.post("", json={"name": ""})
        api_assert.assert_validation_error(response)


class Test{Entity}DetailAPI:
    """
    GET/PUT/DELETE /api/v1/{entities}/{{entity}_id}
    """

    async def test_get_{entity}_not_found(self, {service}_api, api_assert):
        """GET non-existent {entity} returns 404"""
        response = await {service}_api.get("/{entity}_nonexistent_12345")
        api_assert.assert_not_found(response)


class Test{Service}AuthAPI:
    """Test API authentication requirements"""

    async def test_unauthenticated_request_returns_401(self, http_client, api_assert):
        """GET without token returns 401"""
        response = await http_client.get(
            "http://localhost:{PORT}/api/v1/{entities}"
        )
        api_assert.assert_unauthorized(response)
```

### Layer 5: Smoke Test Template

Location: `tests/smoke/{service}_service/smoke_test.sh`

**Smoke Tests 访问方式**:
- **API 测试**: 通过 APISIX 网关 (`http://localhost:8000/api/v1/...`)
- **Health 检查**: 直连服务 (`http://localhost:{PORT}/health`)

> **注意**: `/health` 不会同步到网关，需要分开处理

```bash
#!/bin/bash
# {Service} Service - Smoke Tests
#
# 环境变量:
#   GATEWAY_URL - APISIX 网关地址 (默认: http://localhost:8000)
#   SERVICE_URL - 直连服务地址 (默认: http://localhost:{PORT})
#
# Usage:
#   ./smoke_test.sh                     # 使用默认配置
#   GATEWAY_URL=http://gateway:8000 ./smoke_test.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../test_common.sh"

SERVICE_NAME="{service}_service"
SERVICE_PORT={PORT}
API_PATH="/api/v1/{entities}"

# URLs
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
SERVICE_URL="${SERVICE_URL:-http://localhost:${SERVICE_PORT}}"

init_test

# Test Data
TEST_TS="$(date +%s)_$$"
{ENTITY}_ID=""

# ============================================
# Test 1: Health Check (直连服务，不走网关)
# ============================================
print_section "Test 1: Health Check (Direct)"
RESPONSE=$(curl -s "${SERVICE_URL}/health" 2>/dev/null || echo "{}")
if json_has "$RESPONSE" "status"; then
    print_success "Health check passed (direct)"
    test_result 0
else
    print_warning "Health check via direct failed, trying gateway API..."
    # 备选: 通过网关 API 检查服务可用性
    RESPONSE=$(curl -s "${GATEWAY_URL}${API_PATH}" 2>/dev/null || echo "")
    if [ -n "$RESPONSE" ]; then
        print_success "Service accessible via gateway"
        test_result 0
    else
        test_result 1
    fi
fi

# ============================================
# Test 2: Create {Entity} (通过网关)
# ============================================
print_section "Test 2: Create {Entity} (via Gateway)"
CREATE_PAYLOAD='{"name": "Smoke Test '${TEST_TS}'"}'
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
    -d "$CREATE_PAYLOAD" "${GATEWAY_URL}${API_PATH}" 2>/dev/null)
{ENTITY}_ID=$(json_get "$RESPONSE" "{entity}_id")
if [ -n "${ENTITY}_ID" ]; then
    print_success "Created: ${ENTITY}_ID"
    test_result 0
else
    test_result 1
fi

# ============================================
# Test 3-6: Get, List, Update, Delete (通过网关)
# ============================================
# All API calls should go through GATEWAY_URL
# See full template for complete tests

# ============================================
# Summary
# ============================================
print_summary
exit $?
```

**Folder Structure**:
```
tests/smoke/{service}_service/
├── smoke_test.sh      # Main test (REQUIRED)
├── run_all.sh         # Runner (optional)
└── {feature}_test.sh  # Feature tests (optional)
```

**Template Location**: `tests/templates/smoke/README.md`

---

## Running Tests

### By Layer

```bash
# ============================================
# LOCAL ENVIRONMENT (no K8s needed)
# ============================================

# Layer 1: Unit Tests (no infrastructure)
pytest tests/unit -v

# Layer 2: Component Tests (no infrastructure)
pytest tests/component -v

# ============================================
# K8S ENVIRONMENT (requires port-forward)
# ============================================

# Layer 3: Integration Tests (直连服务 via port-forward)
# First: kubectl port-forward -n isa-cloud-staging svc/{service} {port}:{port}
pytest tests/integration -v

# Layer 4: API Tests (直连服务 via port-forward)
pytest tests/api -v

# Layer 5: Smoke Tests (通过 APISIX 网关)
# First: kubectl port-forward -n isa-cloud-staging svc/apisix-gateway 8000:8000
# Also need service port-forward for health check
GATEWAY_URL=http://localhost:8000 \
SERVICE_URL=http://localhost:8224 \
./tests/smoke/location_service/smoke_test.sh

# Run all smoke tests for a service
./tests/smoke/{service}_service/run_all.sh

# Run all smoke tests globally
./tests/smoke/run_smoke_tests.sh
```

### By Golden vs TDD

```bash
# All golden tests (characterization - should always pass)
pytest tests/unit/golden tests/component/golden tests/integration/golden tests/api/golden -v

# All TDD tests (active development)
pytest tests/unit/tdd tests/component/tdd tests/integration/tdd tests/api/tdd -v

# Golden tests for specific layer
pytest tests/unit/golden -v
pytest tests/component/golden -v

# TDD tests for specific layer
pytest tests/unit/tdd -v
pytest tests/component/tdd -v
```

### By Service

```bash
# All tests for device service (both golden and tdd)
pytest tests/unit/golden/device tests/unit/tdd/device \
       tests/component/golden/device tests/component/tdd/device \
       tests/integration/golden/device tests/integration/tdd/device \
       tests/api/golden/device tests/api/tdd/device -v

# Only golden tests for device
pytest tests/*/golden/device -v

# Only TDD tests for device
pytest tests/*/tdd/device -v
```

### By Marker

```bash
# Skip database tests
pytest -m "not requires_db" -v

# Only golden tests (by marker)
pytest -m "golden" -v

# Only TDD tests (by marker)
pytest -m "tdd" -v
```

### Quick Commands

```bash
# Fast local development (unit + component, both golden and tdd)
pytest tests/unit tests/component -v --tb=short

# Pre-commit check (golden should pass, tdd may have red tests)
pytest tests/unit/golden tests/component/golden -v

# Full test suite (excluding smoke)
pytest tests/ --ignore=tests/smoke -v

# Only run passing tests (golden)
pytest tests/*/golden -v
```

---

## Infrastructure

### Requirements by Layer

| Layer | Environment | Access Method | PostgreSQL | NATS | Auth | Target |
|-------|-------------|---------------|:----------:|:----:|:----:|:------:|
| **Unit** | Local | N/A | - | - | - | - |
| **Component** | Local | N/A | - | - | - | - |
| **Integration** | K8s | Port-Forward (直连) | ✅ | Optional | - | ✅ |
| **API** | K8s | Port-Forward (直连) | ✅ | Optional | ✅ | ✅ |
| **Smoke** | K8s | APISIX Gateway | ✅ | ✅ | ✅ | ✅ |

### Access Methods Explained

```
┌─────────────────────────────────────────────────────────────────┐
│                    K8s Cluster (isa-cloud-staging)              │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   APISIX    │───►│   Consul    │───►│    Microservices    │  │
│  │  Gateway    │    │  Discovery  │    │   (8201-8230)       │  │
│  │  :8000      │    │  :8500      │    │                     │  │
│  └──────┬──────┘    └─────────────┘    └──────────┬──────────┘  │
│         │                                         │             │
└─────────┼─────────────────────────────────────────┼─────────────┘
          │                                         │
    Port-Forward                              Port-Forward
     :8000                                    :8201-8230
          │                                         │
          ▼                                         ▼
   ┌──────────────┐                        ┌──────────────┐
   │ Smoke Tests  │                        │ Integration  │
   │ (via gateway)│                        │ API Tests    │
   │              │                        │ (直连服务)   │
   └──────────────┘                        └──────────────┘
```

**为什么 Smoke Tests 通过网关?**
- 验证完整的请求路径（网关 → 路由 → 服务）
- 测试 APISIX 路由配置是否正确
- 验证 Consul 路由同步是否工作
- 测试生产环境的真实访问方式

**为什么 Integration/API Tests 直连服务?**
- 快速测试，减少中间层延迟
- 绕过网关认证，专注测试服务逻辑
- 使用 `X-Internal-Call` header 模拟内部调用

### Health Route 问题

> **重要**: `/health` 端点不会同步到 APISIX 网关！

**原因**: Consul → APISIX 同步脚本只同步有 `api_path` 元数据的路由。`/health` 不在 `api_path` 中。

**解决方案** (Smoke Tests):
```bash
# 方式 1: 直连服务检查 health（推荐）
curl http://localhost:8224/health  # 需要单独 port-forward 服务

# 方式 2: 通过网关检查 API 可用性
curl http://localhost:8000/api/v1/locations  # 检查 API 而非 health
```

### Service Ports

**Authoritative Source**: `deployment/k8s/build-all-images.sh`

```python
# Sequential ports 8201-8230
SERVICES = {
    "auth_service": 8201,
    "account_service": 8202,
    "session_service": 8203,
    "authorization_service": 8204,
    "audit_service": 8205,
    "notification_service": 8206,
    "payment_service": 8207,
    "wallet_service": 8208,
    "storage_service": 8209,
    "order_service": 8210,
    "task_service": 8211,
    "organization_service": 8212,
    "invitation_service": 8213,
    "vault_service": 8214,
    "product_service": 8215,
    "billing_service": 8216,
    "calendar_service": 8217,
    "weather_service": 8218,
    "album_service": 8219,
    "device_service": 8220,
    "ota_service": 8221,
    "media_service": 8222,
    "memory_service": 8223,
    "location_service": 8224,
    "telemetry_service": 8225,
    "compliance_service": 8226,
    "document_service": 8227,
    "subscription_service": 8228,
    "event_service": 8230,
}
```

### Port-Forward Setup (Staging)

```bash
# Infrastructure
kubectl port-forward -n isa-cloud-staging svc/isa-postgres-grpc 50061:50061 &
kubectl port-forward -n isa-cloud-staging svc/nats 4222:4222 &
kubectl port-forward -n isa-cloud-staging svc/redis-grpc 50055:50055 &

# Services
kubectl port-forward -n isa-cloud-staging svc/auth-service 8201:8201 &
kubectl port-forward -n isa-cloud-staging svc/device-service 8220:8220 &
```

---

## Pytest Markers

```ini
# tests/pytest.ini
[pytest]
markers =
    unit: Layer 1 - Pure functions, no I/O
    component: Layer 2 - Mocked dependencies
    integration: Layer 3 - Real DB, bypass auth
    api: Layer 4 - Real auth flow
    golden: Captures current behavior (existing services)
    tdd: Defines expected behavior (new features/fixes)
    requires_db: Test requires PostgreSQL
    requires_nats: Test requires NATS
    requires_auth: Test requires auth_service
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `tests/INFRASTRUCTURE_SETUP.md` | Detailed infrastructure setup guide |
| `docs/CDD_GUIDE.md` | Contract-Driven Development methodology |
| `docs/CDD_TDD_ROADMAP.md` | Service implementation progress |
| `tests/contracts/README.md` | Contract documentation |

---

**Questions?** Open an issue or ask the team.
