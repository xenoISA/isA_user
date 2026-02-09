# Test Contracts Architecture

**3-Contract Driven Development for isA Microservices**

This directory contains the **Data Contracts**, **Logic Contracts**, and **System Contracts** for all microservices.

---

## 🎯 The 3-Contract Architecture

Each service has **3 contracts** in `tests/contracts/{service}/`:

```
tests/contracts/{service}/
├── data_contract.py      # Layer 4: WHAT data structures
├── logic_contract.md     # Layer 5: WHAT business rules
└── system_contract.md    # Layer 6: HOW to implement
```

---

### 1. **Data Contract** (Per Service) - `data_contract.py`
**Defines WHAT data structures to test**
- Request/Response Pydantic schemas
- Test data factories (builders)
- Valid/invalid data generators
- Field validation rules

**Example:**
```python
from tests.contracts.storage.data_contract import (
    StorageTestDataFactory,
    FileUploadRequestContract,
    FileUploadResponseContract,
)

# Use in tests
request = StorageTestDataFactory.make_upload_request(
    file_name="test.jpg",
    user_id="user_123",
)

# Validate response
response = FileUploadResponseContract(**api_response.json())
assert response.file_id is not None
```

---

### 2. **Logic Contract** (Per Service) - `logic_contract.md`
**Defines WHAT business rules to test**
- Business rules (BR-001, BR-002, ...)
- State machines and transitions
- Authorization matrix
- API contracts (status codes, error handling)
- Event contracts (published events)
- Performance SLAs

**Example:**
```markdown
### BR-001: File Upload
**Given**: Valid file upload request
**When**: User uploads file
**Then**:
- File ID generated (format: `file_[0-9a-f]{32}`)
- File persisted to MinIO
- Database record created
- Event `file.uploaded` published
- Quota updated

**Edge Cases**:
- Quota exceeded → 400 Bad Request
- Invalid file type → 400 Bad Request
- File size > 500MB → 400 Bad Request
```

---

### 3. **System Contract** (Per Service) - `system_contract.md`
**Defines HOW this service implements the 12 standard patterns**

Combines information from:
- `docs/domain/{service}.md` (Domain Context)
- `docs/prd/{service}.md` (PRD)
- `docs/design/{service}.md` (Design)
- Pattern reference: `.claude/skills/cdd-system-contract/SKILL.md`

**Contents:**
- Service identity (port, schema, version)
- File structure
- DI protocols & factory
- Events published/subscribed
- Sync clients (HTTP dependencies)
- Database tables & migrations
- Consul registration
- Configuration & environment variables
- Lifecycle (startup/shutdown)

**Example:**
```markdown
## Service Identity
| Property | Value |
|----------|-------|
| Service Name | storage_service |
| Port | 8209 |
| Schema | storage |

## Events Published
| Event | Subject | Trigger |
|-------|---------|---------|
| FILE_UPLOADED | storage.file.uploaded | After upload |

## Sync Dependencies
| Client | Target | Purpose |
|--------|--------|---------|
| AccountClient | account_service:8202 | Verify user |
```

---

## 📁 Directory Structure

```
tests/
├── README.md                          # Master testing guide
│
├── contracts/                         # 3-Contract per service
│   ├── README.md                      # ← You are here
│   │
│   ├── storage/                       # Storage service
│   │   ├── __init__.py
│   │   ├── data_contract.py           # Layer 4: Data structures
│   │   ├── logic_contract.md          # Layer 5: Business rules
│   │   └── system_contract.md         # Layer 6: Implementation
│   │
│   ├── device/                        # Device service
│   │   ├── __init__.py
│   │   ├── data_contract.py
│   │   ├── logic_contract.md
│   │   └── system_contract.md
│   │
│   └── {service}/                     # Each service follows same pattern
│       ├── __init__.py
│       ├── data_contract.py
│       ├── logic_contract.md
│       └── system_contract.md
│
├── component/                         # Tests import from contracts/
├── integration/
├── api/
└── smoke/
```

---

## 🚀 Usage Workflow

### For Developers

#### 1. Creating Tests for EXISTING Service

```bash
# Step 1: Read contracts
cat tests/contracts/storage/logic_contract.md  # Understand business rules
vim tests/contracts/storage/data_contract.py   # See available test data

# Step 2: Write golden tests (capture current behavior)
# Component golden
pytest tests/component/golden/test_storage_service_golden.py

# Integration golden
pytest tests/integration/golden/test_storage_crud_golden.py

# API golden
pytest tests/api/golden/test_storage_api_golden.py

# Step 3: Find bugs → Write TDD tests → Fix → GREEN
```

#### 2. Creating Tests for NEW Service

```bash
# Step 1: Define contracts FIRST (before implementation)
vim tests/contracts/myservice/logic_contract.md    # Define business rules
vim tests/contracts/myservice/data_contract.py      # Define schemas

# Step 2: Write TDD tests based on contracts
pytest tests/component/services/myservice/test_myservice_service_tdd.py

# Step 3: Implement service to satisfy contracts

# Step 4: Tests turn GREEN
```

### For AI Assistants

When generating tests, AI should:

1. **Read System Contract** (`tests/TDD_CONTRACT.md`)
   - Understand test layer structure
   - Know which markers to use
   - Follow naming conventions

2. **Read Data Contract** (`tests/contracts/{service}/data_contract.py`)
   - Use factories to generate test data
   - Validate responses against contracts
   - Never hardcode schemas

3. **Read Logic Contract** (`tests/contracts/{service}/logic_contract.md`)
   - Verify all business rules (BR-XXX)
   - Test state transitions
   - Validate API contracts (status codes)
   - Check event publishing

---

## ✅ Benefits

### 1. **Single Source of Truth**
- All tests use same schemas → Consistency
- All tests verify same rules → Completeness
- Contract changes propagate to all tests

### 2. **Discoverability**
- Contracts in one place (`tests/contracts/`)
- Easy to find specifications
- Clear service boundaries

### 3. **Maintainability**
- Update contract once → All tests benefit
- Refactor schemas without touching tests
- Business rules documented and versioned

### 4. **Cross-Service Validation**
- Easy to compare service contracts
- Detect contract mismatches
- Validate integration contracts

### 5. **AI-Friendly**
- Structured, parseable contracts
- Clear separation of concerns
- Self-documenting specifications

---

## 📋 Contract Checklist

Before writing tests for a service, ensure all 3 contracts are complete:

### Data Contract Checklist (`data_contract.py`)
- [ ] All request schemas defined with Pydantic
- [ ] All response schemas defined with Pydantic
- [ ] Test data factories for valid data
- [ ] Test data factories for invalid data
- [ ] Builders for complex request construction
- [ ] Field validation rules documented

### Logic Contract Checklist (`logic_contract.md`)
- [ ] All business rules documented (BR-XXX format)
- [ ] State machines defined with transitions
- [ ] Authorization matrix specified
- [ ] API contracts defined (status codes)
- [ ] Event contracts defined (published events)
- [ ] Performance SLAs specified
- [ ] Edge cases documented

### System Contract Checklist (`system_contract.md`)
- [ ] Service identity (name, port, schema, version)
- [ ] File structure documented
- [ ] DI protocols defined
- [ ] Factory implementation documented
- [ ] Events published listed
- [ ] Events subscribed listed
- [ ] Sync client dependencies listed
- [ ] Database tables/migrations listed
- [ ] Consul registration documented
- [ ] Environment variables listed
- [ ] Startup/shutdown sequence documented

---

## 🔄 Contract Versioning

Contracts evolve with the service:

1. **Breaking Changes**
   - Update contract version
   - Update all affected tests
   - Document migration path

2. **Non-Breaking Changes**
   - Add new fields as optional
   - Add new business rules
   - Keep backward compatibility

3. **Contract Review**
   - Review contracts in PR process
   - Validate against production behavior
   - Update documentation

---

## 📖 Reference Implementation

**Storage Service** is the reference implementation for 3-contract architecture:

- **Data Contract**: `tests/contracts/storage/data_contract.py`
- **Logic Contract**: `tests/contracts/storage/logic_contract.md`
- **Tests using contracts**:
  - Component: `tests/component/services/storage/test_storage_service_tdd.py`
  - Integration: `tests/integration/services/storage/test_storage_crud_integration.py`
  - API: `tests/api/services/storage/test_storage_api.py`

Study this implementation as the canonical example!

---

## 🤝 Contributing

When adding a new service:

1. Create `tests/contracts/{service}/` directory
2. Write `data_contract.py` - Pydantic schemas + TestDataFactory
3. Write `logic_contract.md` - Business rules + state machines
4. Write `system_contract.md` - Implementation patterns (use skill as reference)
5. Write tests importing from contracts
6. Submit PR with all three contracts

### Reference Documents
- **Pattern Reference**: `.claude/skills/cdd-system-contract/SKILL.md` (12 patterns)
- **Testing Guide**: `tests/README.md`
- **CDD Guide**: `docs/CDD_GUIDE.md`

**Questions?** Open an issue or ask the team.
