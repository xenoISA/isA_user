# Contract-Driven Development (CDD) Guide

**6-Layer CDD + 5-Layer Test Pyramid Specification**

---

## Core Principles

1. **Contract-First**: Define contracts before implementation
2. **Zero Hardcoded Data**: All test data generated via Factory
3. **Documentation as Code**: Contracts are executable and verifiable
4. **Testability by Design**: Dependency injection, Protocol-based interfaces
5. **Event-Driven**: NATS inter-service communication

---

## 6-Layer CDD Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Documentation Layer (docs/)                                      │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: Domain Context    │ docs/domain/{service}.md           │
│ Layer 2: PRD               │ docs/prd/{service}.md              │
│ Layer 3: Design            │ docs/design/{service}.md           │
├─────────────────────────────────────────────────────────────────┤
│ Contract Layer (tests/contracts/)                                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: Data Contract     │ tests/contracts/{svc}/data_contract.py    │
│ Layer 5: Logic Contract    │ tests/contracts/{svc}/logic_contract.md   │
│ Layer 6: System Contract   │ tests/contracts/{svc}/system_contract.md  │
└─────────────────────────────────────────────────────────────────┘
```

| Layer | File | Content | Template |
|-------|------|---------|----------|
| 1 | `docs/domain/{service}.md` | Business domain, events, rules | `templates/cdd/domain_template.md` |
| 2 | `docs/prd/{service}.md` | Product requirements, user stories, API docs | `templates/cdd/prd_template.md` |
| 3 | `docs/design/{service}.md` | Architecture, DB schema | `templates/cdd/design_template.md` |
| 4 | `data_contract.py` | Pydantic schemas, TestDataFactory | `templates/cdd/contracts/data_contract_template.py` |
| 5 | `logic_contract.md` | Business rules, state machines, edge cases | `templates/cdd/contracts/logic_contract_template.md` |
| 6 | `system_contract.md` | 12 implementation patterns, dependencies, events | `templates/cdd/contracts/system_contract_template.md` |

---

## 5-Layer Test Pyramid

```
                    ┌─────────────────┐
                    │   Layer 5       │  E2E Bash scripts
                    │   Smoke Tests   │  tests/smoke/{service}/
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 4       │  Real HTTP + JWT Auth
                    │   API Tests     │  tests/api/{service}/
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 3       │  Real HTTP + DB
                    │ Integration     │  tests/integration/{service}/
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 2       │  Mocked dependencies
                    │ Component Tests │  tests/component/{service}/
                    └────────┬────────┘
                    ┌────────▼────────┐
                    │   Layer 1       │  Pure functions
                    │   Unit Tests    │  tests/unit/{service}/
                    └─────────────────┘
```

See details at: `tests/README.md`

---

## Naming Conventions

### File Naming

| Type | Location | Format |
|------|----------|--------|
| Domain | `docs/domain/` | `{service}_service.md` |
| PRD | `docs/prd/` | `{service}_service.md` |
| Design | `docs/design/` | `{service}_service.md` |
| Data Contract | `tests/contracts/{svc}/` | `data_contract.py` |
| Logic Contract | `tests/contracts/{svc}/` | `logic_contract.md` |
| System Contract | `tests/contracts/{svc}/` | `system_contract.md` |

### Class Naming

```python
{Service}TestDataFactory        # Test data factory
{Operation}RequestContract      # Request contract
{Operation}ResponseContract     # Response contract
{Operation}RequestBuilder       # Request builder
```

### Business Rule Format

```
BR-{SVC}-001: Rule Name
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `tests/README.md` | Test guide (how to write and run tests) |
| `tests/contracts/README.md` | 3-Contract architecture explanation |
| `templates/cdd/contracts/system_contract_template.md` | Microservice template (DI 12 patterns) |
| `docs/current_status.md` | Progress tracking |
| `.claude/skills/cdd-*/SKILL.md` | Claude generation skills |
| `templates/` | All template files |

---

## Key Rules

### 1. Zero Hardcoded Data
```python
# Wrong
user_id = "user_123"

# Correct
user_id = AccountTestDataFactory.make_user_id()
```

### 2. Dependency Injection
```python
# Wrong - Direct import of implementation
from .account_repository import AccountRepository

# Correct - Import protocol
from .protocols import AccountRepositoryProtocol
```

### 3. No Test Skipping
```python
# Wrong - Hiding unimplemented functionality
pytest.skip("Not implemented")

# Correct - Let tests fail (TDD Red phase)
result = await service.new_feature()
assert result is not None
```

### 4. Event-Driven
```python
# Publish events after successful operations
await self.event_bus.publish_event(UserCreatedEvent(...))
```

---

## Quick Start

### New Service
```bash
# 1. Check CDD status
/check-cdd-status {service}

# 2. Start CDD workflow
/new-cdd-service {service}

# 3. Run tests
/run-service-tests {service}
```

### Generate Contracts
Use Claude skills:
- `cdd-domain-context` -> Layer 1
- `cdd-prd-specification` -> Layer 2
- `cdd-design-document` -> Layer 3
- `cdd-data-contract` -> Layer 4
- `cdd-logic-contract` -> Layer 5
- `cdd-system-contract` -> Layer 6

---

**End of CDD Guide**
