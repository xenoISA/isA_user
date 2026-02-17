# Device Service - Known Issues

**Last Updated:** 2025-10-28
**Test Results:** 6/11 tests passing (55%)

## Overview
Device service has auto-schema creation implemented but still experiencing device registration failures.

## Critical Issues

### 1. Device Registration Failing
**Status:** 🔴 Critical
**Severity:** High
**Tests Affected:**
- Test 2: Register Device
- Test 3: Get Device Details (skipped - no device ID)
- Test 4: Update Device (skipped - no device ID)

**Error:**
```
Failed to create device in database
HTTP Status: 500
```

**Root Cause Investigation Needed:**
- Schema and table creation is implemented (`_ensure_schema()`)
- Possible issues:
  1. PostgreSQL gRPC client `insert_into()` method may be failing
  2. Data type mismatch (tags as TEXT[] or JSONB conversion)
  3. Constraint violations (serial_number uniqueness)
  4. Missing indexes or permissions

**Debug Steps:**
1. Check PostgreSQL gRPC service logs
2. Verify table was created successfully
3. Test insert_into() method directly
4. Validate data transformation before insert

**Files to Check:**
- `device_repository.py:96` - Exception handling in `create_device()`
- `device_repository.py:87` - `insert_into()` call
- `device_repository.py:59-84` - Data preparation

**Workaround:**
Currently none - device registration is core functionality

---

### 2. Data Type Conversion Issues
**Status:** ⚠️ Suspected
**Severity:** Medium

**Description:**
PostgreSQL expects specific data types but insert may be failing due to:
- `tags TEXT[]` - Passing Python list vs PostgreSQL array
- `metadata JSONB` - JSON serialization
- `location JSONB` - JSON serialization
- `last_seen TIMESTAMPTZ` - Datetime serialization

**Current Handling:**
```python
location = json.dumps(location) if isinstance(location, dict) else location
metadata = json.dumps(metadata) if isinstance(metadata, dict) else metadata
tags = tags if isinstance(tags, list) else []
```

**Potential Fix:**
Verify that PostgresClient.insert_into() properly handles:
- Python lists → PostgreSQL arrays
- Python dicts → JSONB
- Datetime objects → TIMESTAMPTZ

**Files to Update:**
- `device_repository.py:create_device()` - Enhanced data conversion
- Test with direct PostgreSQL query first

---

### 3. Organization ID Validation
**Status:** ℹ️ Info
**Severity:** Low
**Tests Affected:**
- Test 7: List Devices by Organization

**Description:**
Organization-based device listing may fail if organization_id is null or invalid.

**Current Behavior:**
- Test organization listing without proper organization setup
- May need organization service integration

**Solution:**
- Add organization ID validation
- Create test organization in test data
- Or make organization_id truly optional

---

## Working Features ✅

1. **Health Check** - Working perfectly
2. **List Devices** - Returns empty list correctly
3. **Device Statistics** - Returns correct stats
4. **List Device Groups** - Working
5. **Unauthorized Access Control** - Properly rejecting requests
6. **Service Info** - Returning correct metadata

---

## Recent Improvements

### Schema Auto-Creation ✅
Added automatic schema and table creation on service startup:
```python
def _ensure_schema(self):
    # Creates 'device' schema
    # Creates 'devices' table with all columns and constraints
```

**Status:** Implemented and tested
**Location:** `device_repository.py:46-92`

---

## Environment Requirements

### Database Tables:
- ✅ `device.devices` (auto-created)
- 🔄 `device.device_groups` (pending)
- 🔄 `device.device_commands` (pending)
- 🔄 `device.frame_configs` (pending)

### Required Indexes:
- `idx_devices_user_id`
- `idx_devices_org_id`
- `idx_devices_status`
- `idx_devices_type`
- `idx_devices_serial`
- `idx_devices_tags` (GIN index)

### Service Dependencies:
- ✅ Auth Service (working)
- ✅ PostgreSQL gRPC Service (connected)
- ⚠️ Organization Service (optional)

---

## Debugging Recommendations

### 1. Test PostgreSQL Connection
```python
# Add to device_repository.py __init__
with self.db:
    result = self.db.execute("SELECT 1", schema='device')
    logger.info(f"PostgreSQL connection test: {result}")
```

### 2. Test Table Creation
```bash
# Via PostgreSQL gRPC client
from isa_common.postgres_client import PostgresClient
db = PostgresClient(host='isa-postgres-grpc', port=50061, user_id='test')
tables = db.list_tables(schema='device')
print(f"Tables in device schema: {tables}")
```

### 3. Test Direct Insert
```python
# Minimal test insert
test_device = {
    "device_id": "test_123",
    "user_id": "test_user",
    "device_name": "Test Device",
    "device_type": "smart_frame",
    # ... minimal required fields
}
```

---

## Quick Fix Priority

1. **Critical:** Debug and fix device registration
   - Add detailed error logging in create_device()
   - Test insert_into() with minimal data
   - Verify data type conversions

2. **High:** Add comprehensive error messages
   - Log actual PostgreSQL error
   - Return specific error details to caller

3. **Medium:** Add retry logic for transient failures

4. **Low:** Implement remaining table auto-creation
   - device_groups
   - device_commands
   - frame_configs

---

## Running Tests

```bash
cd microservices/device_service/tests
bash device_test.sh
```

**Expected After Fixes:**
- All 11 tests should pass
- Device registration should succeed
- All CRUD operations should work

---

## Migration Files Available

- `migrations/001_create_devices_table.sql` ✅
- `migrations/002_create_device_groups_table.sql` ✅
- `migrations/003_create_device_commands_table.sql` ✅
- `migrations/004_create_frame_configs_table.sql` ✅

**Note:** Schema auto-creation currently only creates the devices table. Consider adding other tables to `_ensure_schema()`.

---

## Related Files

- `device_service.py` - Business logic
- `device_repository.py:28-92` - Database initialization and schema
- `device_repository.py:96-157` - Device CRUD operations
- `main.py:201-216` - Device registration endpoint
- `models.py` - Data models
- `tests/device_test.sh` - Test suite
