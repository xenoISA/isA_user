# Memory Service - Logic Contract

## Overview

This document defines the **business logic rules, validation requirements, state machines, and edge cases** for the Memory Service. Every rule is testable and forms the contract that the implementation must satisfy.

**Purpose**: Ensure consistent behavior across all memory operations with validated business rules.

**Related Documents**:
- Domain Context: `docs/domain/memory_service.md`
- PRD: `docs/prd/memory_service.md`
- Design: `docs/design/memory_service.md`
- Data Contract: `tests/contracts/memory/data_contract.py`

---

## Business Rules

### General Memory Rules

#### BR-MEM-001: Unique Memory IDs
**Rule**: All memories MUST have globally unique IDs in UUID format.

**Validation**:
```python
assert memory_id matches pattern: ^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$
OR matches pattern: ^(fact|epis|proc|sem|work|sess)_[0-9]{4}$  # Test format
```

**Test Cases**:
- ✅ Valid: `"550e8400-e29b-41d4-a716-446655440000"`
- ✅ Valid: `"fact_0001"` (test format)
- ❌ Invalid: `"invalid-id"`
- ❌ Invalid: `""` (empty)

**Test Marker**: `@pytest.mark.logic_rule("BR-MEM-001")`

---

#### BR-MEM-002: User ID Required
**Rule**: All memory operations MUST include a non-empty user_id.

**Validation**:
```python
assert user_id is not None
assert len(user_id.strip()) > 0
```

**Test Cases**:
- ✅ Valid: `"usr_123"`
- ❌ Invalid: `None`
- ❌ Invalid: `""` (empty string)
- ❌ Invalid: `"   "` (whitespace only)

**Test Marker**: `@pytest.mark.logic_rule("BR-MEM-002")`

---

#### BR-MEM-003: Valid Memory Type
**Rule**: memory_type MUST be one of six valid types.

**Validation**:
```python
VALID_MEMORY_TYPES = ["factual", "episodic", "procedural", "semantic", "working", "session"]
assert memory_type in VALID_MEMORY_TYPES
```

**Test Cases**:
- ✅ Valid: All 6 types
- ❌ Invalid: `"invalid_type"`
- ❌ Invalid: `"FACTUAL"` (case-sensitive)

**Test Marker**: `@pytest.mark.logic_rule("BR-MEM-003")`

---

#### BR-MEM-004: Content Required
**Rule**: Content field MUST be non-empty string.

**Validation**:
```python
assert content is not None
assert isinstance(content, str)
assert len(content.strip()) > 0
```

**Test Cases**:
- ✅ Valid: `"John lives in Tokyo"`
- ❌ Invalid: `None`
- ❌ Invalid: `""`
- ❌ Invalid: `"   "`

**Test Marker**: `@pytest.mark.logic_rule("BR-MEM-004")`

---

#### BR-MEM-005: Importance Score Range
**Rule**: importance_score MUST be between 0.0 and 1.0 (inclusive).

**Validation**:
```python
assert 0.0 <= importance_score <= 1.0
```

**Test Cases**:
- ✅ Valid: `0.0`, `0.5`, `1.0`
- ❌ Invalid: `-0.1`, `1.1`, `None`

**Test Marker**: `@pytest.mark.logic_rule("BR-MEM-005")`

---

#### BR-MEM-006: Confidence Range
**Rule**: confidence MUST be between 0.0 and 1.0 (inclusive).

**Validation**:
```python
assert 0.0 <= confidence <= 1.0
```

**Test Cases**:
- ✅ Valid: `0.0`, `0.8`, `1.0`
- ❌ Invalid: `-0.5`, `2.0`

**Test Marker**: `@pytest.mark.logic_rule("BR-MEM-006")`

---

#### BR-MEM-007: Access Count Non-Negative
**Rule**: access_count MUST be non-negative integer, defaults to 0.

**Validation**:
```python
assert isinstance(access_count, int)
assert access_count >= 0
```

**Test Cases**:
- ✅ Valid: `0`, `5`, `1000`
- ❌ Invalid: `-1`, `1.5` (float)

**Test Marker**: `@pytest.mark.logic_rule("BR-MEM-007")`

---

### Factual Memory Rules

#### BR-FACT-001: Subject-Predicate-Object Required
**Rule**: Factual memory MUST have non-empty subject, predicate, and object_value.

**Validation**:
```python
assert subject is not None and len(subject.strip()) > 0
assert predicate is not None and len(predicate.strip()) > 0
assert object_value is not None and len(object_value.strip()) > 0
```

**Test Cases**:
- ✅ Valid: subject="John", predicate="lives in", object_value="Tokyo"
- ❌ Invalid: subject="" (empty)
- ❌ Invalid: predicate=None

**Test Marker**: `@pytest.mark.logic_rule("BR-FACT-001")`

---

#### BR-FACT-002: Duplicate Prevention
**Rule**: Duplicate facts (same user_id + subject + predicate) SHOULD be prevented or merged.

**Validation**:
```python
existing = db.query(user_id=user_id, subject=subject, predicate=predicate)
if existing:
    # Handle: merge, update, or reject
    pass
```

**Test Cases**:
- ✅ Create first fact: user="usr_1", subject="John", predicate="lives in"
- ⚠️  Create duplicate: Same user/subject/predicate → should update or reject
- ✅ Different user: user="usr_2" with same subject/predicate → allow (different user)

**Test Marker**: `@pytest.mark.logic_rule("BR-FACT-002")`

---

#### BR-FACT-003: Content Auto-Generation
**Rule**: If content is empty, auto-generate from subject-predicate-object.

**Validation**:
```python
if not content or len(content.strip()) == 0:
    content = f"{subject} {predicate} {object_value}"
```

**Test Cases**:
- ✅ Provided content: Use as-is
- ✅ Empty content: Auto-generate "John lives in Tokyo"
- ✅ Whitespace content: Auto-generate

**Test Marker**: `@pytest.mark.logic_rule("BR-FACT-003")`

---

#### BR-FACT-004: Verification Status Default
**Rule**: verification_status MUST default to "unverified" if not provided.

**Validation**:
```python
if verification_status is None:
    verification_status = "unverified"
assert verification_status in ["unverified", "verified", "disputed", "outdated"]
```

**Test Cases**:
- ✅ Not provided → defaults to "unverified"
- ✅ Provided "verified" → use as-is
- ❌ Invalid value "invalid_status"

**Test Marker**: `@pytest.mark.logic_rule("BR-FACT-004")`

---

### Episodic Memory Rules

#### BR-EPIS-001: Emotional Valence Range
**Rule**: emotional_valence MUST be between -1.0 (negative) and 1.0 (positive).

**Validation**:
```python
assert -1.0 <= emotional_valence <= 1.0
```

**Test Cases**:
- ✅ Valid: `-1.0` (very negative), `0.0` (neutral), `1.0` (very positive)
- ❌ Invalid: `-1.5`, `2.0`

**Test Marker**: `@pytest.mark.logic_rule("BR-EPIS-001")`

---

#### BR-EPIS-002: Vividness Range
**Rule**: vividness MUST be between 0.0 (vague) and 1.0 (vivid).

**Validation**:
```python
assert 0.0 <= vividness <= 1.0
```

**Test Cases**:
- ✅ Valid: `0.0`, `0.5`, `1.0`
- ❌ Invalid: `-0.1`, `1.1`

**Test Marker**: `@pytest.mark.logic_rule("BR-EPIS-002")`

---

#### BR-EPIS-003: Episode Date Constraint
**Rule**: episode_date CAN be in the past or present, but NOT in the future.

**Validation**:
```python
if episode_date:
    assert episode_date <= datetime.now(timezone.utc)
```

**Test Cases**:
- ✅ Valid: Yesterday's date
- ✅ Valid: Current timestamp
- ❌ Invalid: Tomorrow's date

**Test Marker**: `@pytest.mark.logic_rule("BR-EPIS-003")`

---

### Procedural Memory Rules

#### BR-PROC-001: Steps Non-Empty
**Rule**: steps array MUST be non-empty with at least one step.

**Validation**:
```python
assert steps is not None
assert isinstance(steps, list)
assert len(steps) > 0
```

**Test Cases**:
- ✅ Valid: `[{"step": 1, "action": "run tests"}]`
- ❌ Invalid: `[]` (empty list)
- ❌ Invalid: `None`

**Test Marker**: `@pytest.mark.logic_rule("BR-PROC-001")`

---

#### BR-PROC-002: Success Rate Range
**Rule**: success_rate MUST be between 0.0 and 1.0.

**Validation**:
```python
assert 0.0 <= success_rate <= 1.0
```

**Test Cases**:
- ✅ Valid: `0.0`, `0.75`, `1.0`
- ❌ Invalid: `-0.1`, `1.5`

**Test Marker**: `@pytest.mark.logic_rule("BR-PROC-002")`

---

#### BR-PROC-003: Valid Difficulty Level
**Rule**: difficulty_level MUST be one of: easy, medium, hard.

**Validation**:
```python
VALID_DIFFICULTIES = ["easy", "medium", "hard"]
assert difficulty_level in VALID_DIFFICULTIES
```

**Test Cases**:
- ✅ Valid: "easy", "medium", "hard"
- ❌ Invalid: "trivial", "HARD" (case-sensitive)

**Test Marker**: `@pytest.mark.logic_rule("BR-PROC-003")`

---

### Working Memory Rules

#### BR-WORK-001: Positive TTL
**Rule**: ttl_seconds MUST be positive integer (greater than 0).

**Validation**:
```python
assert isinstance(ttl_seconds, int)
assert ttl_seconds > 0
```

**Test Cases**:
- ✅ Valid: `1`, `3600`, `86400`
- ❌ Invalid: `0`, `-100`, `1.5` (float)

**Test Marker**: `@pytest.mark.logic_rule("BR-WORK-001")`

---

#### BR-WORK-002: Expiry Calculation
**Rule**: expires_at MUST be auto-calculated as created_at + ttl_seconds.

**Validation**:
```python
expected_expires_at = created_at + timedelta(seconds=ttl_seconds)
assert abs((expires_at - expected_expires_at).total_seconds()) < 1  # Allow 1s tolerance
```

**Test Cases**:
- ✅ TTL=3600, created_at=now → expires_at=now+1hour
- ✅ TTL=60, created_at=now → expires_at=now+1min

**Test Marker**: `@pytest.mark.logic_rule("BR-WORK-002")`

---

#### BR-WORK-003: Priority Range
**Rule**: priority MUST be between 1 and 10 (inclusive).

**Validation**:
```python
assert 1 <= priority <= 10
```

**Test Cases**:
- ✅ Valid: `1`, `5`, `10`
- ❌ Invalid: `0`, `11`, `-5`

**Test Marker**: `@pytest.mark.logic_rule("BR-WORK-003")`

---

#### BR-WORK-004: Expired Memory Cleanup
**Rule**: Expired memories (expires_at <= NOW) SHOULD be automatically cleaned up.

**Validation**:
```python
expired_memories = db.query(expires_at <= datetime.now(timezone.utc))
# Cleanup process removes these
```

**Test Cases**:
- ✅ Create memory with TTL=1 second
- ⏱️  Wait 2 seconds
- ✅ Cleanup removes expired memory
- ✅ Active memories remain

**Test Marker**: `@pytest.mark.logic_rule("BR-WORK-004")`

---

#### BR-WORK-005: Task Context Required
**Rule**: task_id and task_context are required for working memory.

**Validation**:
```python
assert task_id is not None and len(task_id.strip()) > 0
assert task_context is not None
assert isinstance(task_context, dict)
```

**Test Cases**:
- ✅ Valid: task_id="task_001", task_context={"key": "value"}
- ❌ Invalid: task_id="" (empty)
- ❌ Invalid: task_context=None

**Test Marker**: `@pytest.mark.logic_rule("BR-WORK-005")`

---

### Session Memory Rules

#### BR-SESS-001: Session ID Required
**Rule**: session_id MUST be non-empty string.

**Validation**:
```python
assert session_id is not None
assert len(session_id.strip()) > 0
```

**Test Cases**:
- ✅ Valid: "session_abc123"
- ❌ Invalid: "" (empty)
- ❌ Invalid: None

**Test Marker**: `@pytest.mark.logic_rule("BR-SESS-001")`

---

#### BR-SESS-002: Positive Interaction Sequence
**Rule**: interaction_sequence MUST be positive integer (>= 1).

**Validation**:
```python
assert isinstance(interaction_sequence, int)
assert interaction_sequence >= 1
```

**Test Cases**:
- ✅ Valid: `1`, `5`, `100`
- ❌ Invalid: `0`, `-1`

**Test Marker**: `@pytest.mark.logic_rule("BR-SESS-002")`

---

#### BR-SESS-003: Sequence Auto-Increment
**Rule**: New messages in a session MUST auto-increment interaction_sequence.

**Validation**:
```python
existing_max = db.query(session_id=session_id).max(interaction_sequence)
new_sequence = existing_max + 1 if existing_max else 1
```

**Test Cases**:
- ✅ First message: sequence=1
- ✅ Second message: sequence=2
- ✅ Third message: sequence=3

**Test Marker**: `@pytest.mark.logic_rule("BR-SESS-003")`

---

#### BR-SESS-004: Session Deactivation
**Rule**: Sessions can be deactivated (active=False) but NOT deleted.

**Validation**:
```python
# Deactivate operation
assert update(session_id, active=False) == True
# Session still exists
assert db.query(session_id=session_id) is not None
```

**Test Cases**:
- ✅ Deactivate session: active changes to False
- ✅ Session data remains queryable
- ❌ Delete session: not allowed (only deactivate)

**Test Marker**: `@pytest.mark.logic_rule("BR-SESS-004")`

---

#### BR-SESS-005: Conversation State is Dictionary
**Rule**: conversation_state MUST be a JSON-serializable dictionary.

**Validation**:
```python
assert isinstance(conversation_state, dict)
import json
json.dumps(conversation_state)  # Must not raise
```

**Test Cases**:
- ✅ Valid: `{"message_type": "human", "role": "user"}`
- ❌ Invalid: `"not a dict"` (string)
- ❌ Invalid: `None`

**Test Marker**: `@pytest.mark.logic_rule("BR-SESS-005")`

---

## State Machines

### Working Memory Lifecycle State Machine

```
States:
- ACTIVE: expires_at > NOW
- EXPIRED: expires_at <= NOW
- DELETED: Removed from database

Transitions:
┌────────┐
│ CREATE │
└───┬────┘
    │
    ↓
┌────────┐      (expires_at <= NOW)      ┌─────────┐
│ ACTIVE │ ───────────────────────────→  │ EXPIRED │
└────────┘                                └────┬────┘
    │                                          │
    │ (manual delete)                          │ (cleanup job)
    ↓                                          ↓
┌─────────┐                              ┌─────────┐
│ DELETED │  ←───────────────────────────│ DELETED │
└─────────┘                              └─────────┘
```

**State Rules**:
- `ACTIVE`: Can be retrieved, updated, or deleted
- `EXPIRED`: Should not appear in active queries, eligible for cleanup
- `DELETED`: Permanently removed

---

### Session Memory State Machine

```
States:
- ACTIVE: active=True
- INACTIVE: active=False

Transitions:
┌────────┐
│ CREATE │ (active=True by default)
└───┬────┘
    │
    ↓
┌────────┐    (deactivate_session)    ┌──────────┐
│ ACTIVE │ ─────────────────────────→ │ INACTIVE │
└────────┘                             └──────────┘
    ↑                                       │
    │                                       │
    └───────────────────────────────────────┘
         (reactivate - future feature)
```

**State Rules**:
- `ACTIVE`: Session ongoing, new messages can be added
- `INACTIVE`: Session ended, no new messages (read-only)

---

## Validation Logic

### Input Validation Order

1. **Schema Validation** (Pydantic): Type checking, required fields
2. **Business Rule Validation**: Range checks, format validation
3. **State Validation**: Check current state allows operation
4. **Authorization**: Verify user_id ownership
5. **Database Constraint**: Unique constraints, foreign keys

### Validation Error Responses

```json
{
  "success": false,
  "operation": "create_memory",
  "message": "Validation error: importance_score must be between 0.0 and 1.0",
  "error": {
    "code": "VALIDATION_ERROR",
    "field": "importance_score",
    "value": 1.5,
    "constraint": "0.0 <= value <= 1.0"
  }
}
```

---

## Edge Cases

### Edge Case 1: Empty Dialog Content for Extraction
**Scenario**: User submits extraction request with empty dialog_content.

**Expected Behavior**:
- ❌ Reject with validation error
- Return error: "dialog_content is required and cannot be empty"
- Status code: 400

**Test**:
```python
request = ExtractFactualMemoryRequest(user_id="usr_1", dialog_content="", importance_score=0.5)
# Should raise ValidationError
```

---

### Edge Case 2: Working Memory Expires Before Access
**Scenario**: Working memory created with TTL=1 second, accessed after 2 seconds.

**Expected Behavior**:
- Memory is EXPIRED
- GET request returns 404 or empty
- Cleanup job removes it

**Test**:
```python
create_working_memory(ttl_seconds=1)
time.sleep(2)
result = get_memory(memory_id)
assert result is None or result["status"] == "expired"
```

---

### Edge Case 3: Session with Single Message
**Scenario**: Session created with only one message.

**Expected Behavior**:
- ✅ Valid session
- interaction_sequence=1
- Can be deactivated
- Statistics show total_messages=1

**Test**:
```python
store_session_message(session_id="sess_1", message_content="Hello", interaction_sequence=1)
context = get_session_context("sess_1")
assert context["total_messages"] == 1
```

---

### Edge Case 4: Factual Memory with Same Subject but Different Predicate
**Scenario**: Create two facts: "John lives in Tokyo" and "John works at Apple".

**Expected Behavior**:
- ✅ Both allowed (different predicates)
- No duplicate constraint violation
- Both retrievable by subject="John"

**Test**:
```python
create_fact(subject="John", predicate="lives in", object="Tokyo")
create_fact(subject="John", predicate="works at", object="Apple")
facts = search_by_subject("John")
assert len(facts) == 2
```

---

### Edge Case 5: Update Memory Type (Not Allowed)
**Scenario**: Attempt to change memory_type via update.

**Expected Behavior**:
- ❌ Reject update
- memory_type is immutable after creation
- Return error: "memory_type cannot be changed"

**Test**:
```python
memory = create_memory(memory_type="factual", ...)
update_request = UpdateMemoryRequest(memory_type="episodic")  # Should not have this field
# memory_type should not be in UpdateMemoryRequest schema
```

---

### Edge Case 6: Extremely High Access Count
**Scenario**: Memory accessed 1 million times.

**Expected Behavior**:
- ✅ access_count increments correctly
- No integer overflow
- Performance remains acceptable

**Test**:
```python
for i in range(1000000):
    get_memory(memory_id)  # Increments access_count
memory = get_memory(memory_id)
assert memory["access_count"] == 1000000
```

---

### Edge Case 7: Unicode Content
**Scenario**: Memory content contains emojis, CJK characters, special symbols.

**Expected Behavior**:
- ✅ Stored correctly
- ✅ Retrieved without corruption
- ✅ Searchable

**Test**:
```python
content = "今天天气很好 🌞 Très bien! 日本語テスト"
create_memory(content=content)
retrieved = get_memory(memory_id)
assert retrieved["content"] == content
```

---

### Edge Case 8: Bulk Memory Creation
**Scenario**: Create 1000 memories in rapid succession.

**Expected Behavior**:
- ✅ All created successfully
- ✅ Unique IDs for each
- ✅ Correct statistics (total_memories += 1000)

**Test**:
```python
for i in range(1000):
    create_memory(content=f"Memory {i}")
stats = get_statistics(user_id)
assert stats["total_memories"] >= 1000
```

---

### Edge Case 9: Session Messages Out of Order
**Scenario**: Messages stored with non-sequential interaction_sequence.

**Expected Behavior**:
- ✅ Allowed (client may have retry logic)
- Retrieval sorts by interaction_sequence
- No gaps in sequence flagged as warning

**Test**:
```python
store_session_message(session_id="sess_1", interaction_sequence=1)
store_session_message(session_id="sess_1", interaction_sequence=3)  # Skip 2
store_session_message(session_id="sess_1", interaction_sequence=2)  # Out of order
context = get_session_context("sess_1")
assert context["recent_messages"][0]["interaction_sequence"] == 1
assert context["recent_messages"][1]["interaction_sequence"] == 2
assert context["recent_messages"][2]["interaction_sequence"] == 3
```

---

### Edge Case 10: Procedural Memory with Circular Prerequisites
**Scenario**: Procedure A requires B, which requires A (circular dependency).

**Expected Behavior**:
- ⚠️ Allowed at creation (no validation)
- Application logic should detect cycles
- Future: Add cycle detection

**Test**:
```python
create_procedure(id="proc_A", prerequisites=["proc_B"])
create_procedure(id="proc_B", prerequisites=["proc_A"])
# Both created, but circular dependency exists
# Detection is application-level responsibility
```

---

## Testing Strategy

### Test Markers

Use pytest markers to tag tests by business rule:

```python
@pytest.mark.logic_rule("BR-MEM-001")
def test_unique_memory_ids():
    """Test BR-MEM-001: All memories have unique IDs"""
    factory = MemoryTestDataFactory()
    memory1 = factory.factual_memory_response()
    memory2 = factory.factual_memory_response()
    assert memory1.id != memory2.id

@pytest.mark.logic_rule("BR-FACT-001")
def test_factual_memory_requires_spo():
    """Test BR-FACT-001: Subject-Predicate-Object required"""
    with pytest.raises(ValidationError):
        CreateMemoryRequest(
            user_id="usr_1",
            memory_type="factual",
            content="test",
            subject="",  # Empty - should fail
            predicate="lives in",
            object_value="Tokyo"
        )
```

### Test Coverage Requirements

- **100% Business Rule Coverage**: Every BR-XXX-NNN must have at least one test
- **Positive Tests**: Valid inputs produce expected outputs
- **Negative Tests**: Invalid inputs produce validation errors
- **Edge Case Tests**: All documented edge cases tested
- **State Machine Tests**: All state transitions validated

---

## Contract Validation

### Validation Checklist

- [ ] All data contracts (request/response schemas) have Pydantic validation
- [ ] All business rules (BR-XXX-NNN) have corresponding tests
- [ ] State machines have tests for all transitions
- [ ] Edge cases have explicit test coverage
- [ ] Validation error messages are clear and actionable
- [ ] Test data factory generates valid data for all scenarios

---

**Document Version**: 1.0
**Last Updated**: 2025-12-11
**Maintained By**: Memory Service QA Team
**Related Documents**:
- Domain Context: `docs/domain/memory_service.md`
- PRD: `docs/prd/memory_service.md`
- Design: `docs/design/memory_service.md`
- Data Contract: `tests/contracts/memory/data_contract.py`
- Proof Tests: `tests/component/golden/test_memory_contracts_proof.py` (next)
