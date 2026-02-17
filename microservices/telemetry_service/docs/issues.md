# Telemetry Service - Known Issues

**Last Updated:** 2025-10-28
**Test Results:** 15/18 tests passing (83%)

## Overview
Telemetry service has auto-schema creation but metric definitions and alert rules are failing to create.

## Critical Issues

### 1. Metric Definition Creation Failing
**Status:** 🔴 Critical
**Severity:** High
**Tests Affected:**
- Test 4: Create Metric Definition

**Error:**
```
400: Failed to create metric definition
HTTP Status: 500
```

**Root Cause Investigation Needed:**
Schema and metric_definitions table are auto-created, but insert is failing.

**Possible Causes:**
1. Data type mismatch in `create_metric_definition()`
2. Constraint violation (name uniqueness)
3. JSONB conversion issues for metadata/tags
4. TEXT[] array conversion for tags
5. DOUBLE PRECISION values for min/max

**Debug Steps:**
```python
# Check in telemetry_repository.py:226-269
# Verify data being passed to insert:
logger.info(f"Creating metric with params: {params}")
```

**Files to Check:**
- `telemetry_repository.py:226` - `create_metric_definition()`
- `telemetry_service.py:79` - Calling code
- `main.py:282` - API endpoint

**Workaround:** None - metrics are core functionality

---

### 2. Alert Rule Creation Failing
**Status:** 🔴 Critical
**Severity:** High
**Tests Affected:**
- Test 5: Create Alert Rule

**Error:**
```
400: Failed to create alert rule
HTTP Status: 500
```

**Root Cause Investigation Needed:**
Similar to metric definitions, the alert_rules table is created but inserts are failing.

**Possible Causes:**
1. Data type issues with arrays (device_ids, notification_channels, tags)
2. JSONB conversion for device_filters
3. Constraint violations
4. Missing required fields in request

**Debug Steps:**
```python
# Add to telemetry_repository.py alert rule creation
logger.error(f"Alert rule creation failed: {e}")
logger.info(f"Alert rule data: {alert_rule_data}")
```

**Files to Check:**
- `telemetry_repository.py:~300-400` - Alert rule creation
- `telemetry_service.py:129` - `create_alert_rule()`
- `main.py:~400` - Alert rule endpoint

---

### 3. List Alert Rules Returns 500 Error
**Status:** 🔴 Critical
**Severity:** High
**Tests Affected:**
- Test 6: List Alert Rules

**Error:**
```
jq: parse error: Invalid numeric literal at line 1, column 9
HTTP Status: 500
```

**Root Cause:**
Likely returning invalid JSON or HTML error page instead of JSON response.

**Possible Causes:**
1. Exception in list_alert_rules() not handled properly
2. Response not being serialized correctly
3. Database query returning unexpected format

**Debug Steps:**
```python
# Check telemetry_repository.py list methods
# Verify return format matches expected model
```

**Files to Check:**
- `telemetry_repository.py` - List alert rules method
- `main.py` - Alert rules list endpoint
- Error handling in repository methods

---

## Recent Improvements ✅

### Schema Auto-Creation Implemented
Added automatic schema and table creation:
```python
def _ensure_schema(self):
    # Creates 'telemetry' schema
    # Creates 'metric_definitions' table
    # Creates 'alert_rules' table
```

**Status:** ✅ Implemented
**Location:** `telemetry_repository.py:49-119`

**Tables Created:**
- ✅ `telemetry.metric_definitions`
- ✅ `telemetry.alert_rules`

**Tables Still Needed:**
- 🔄 `telemetry.telemetry_data`
- 🔄 `telemetry.aggregated_data`
- 🔄 `telemetry.alerts`
- 🔄 `telemetry.real_time_subscriptions`
- 🔄 `telemetry.telemetry_stats`

---

## Working Features ✅

1. **Health Checks** - Working perfectly
2. **Service Info** - Returning correct metadata
3. **Telemetry Data Recording** - Working
4. **Data Query** - Working
5. **Statistics** - Working
6. **Real-time Subscriptions** - Working (15 tests passing)

---

## Data Type Analysis

### PostgreSQL Schema (from migration):
```sql
-- metric_definitions
min_value DOUBLE PRECISION,
max_value DOUBLE PRECISION,
tags TEXT[],
metadata JSONB DEFAULT '{}',

-- alert_rules
device_ids TEXT[],
device_groups TEXT[],
notification_channels TEXT[],
tags TEXT[],
device_filters JSONB DEFAULT '{}',
```

### Python Code (current):
```python
# In create_metric_definition():
params = [
    metric_id,
    metric_def["name"],
    metric_def.get("description"),
    metric_def["data_type"],
    metric_def.get("metric_type", "gauge"),
    metric_def.get("unit"),
    metric_def.get("min_value"),  # Should be float/None
    metric_def.get("max_value"),  # Should be float/None
    metric_def.get("retention_days", 90),
    metric_def.get("aggregation_interval", 60),
    metric_def.get("tags", []),  # Should be list
    metric_def.get("metadata", {}),  # Should be dict
    metric_def.get("created_by", "system"),
    now,
    now
]
```

**Potential Issue:** PostgresClient may not be converting Python types properly to PostgreSQL types.

---

## Debugging Recommendations

### 1. Test Direct Insert
```python
# Minimal test with telemetry_repository
from telemetry_repository import TelemetryRepository

repo = TelemetryRepository()
test_metric = {
    "name": "test_metric",
    "data_type": "numeric",
    "metric_type": "gauge",
    "tags": [],
    "metadata": {},
    "created_by": "test"
}

result = await repo.create_metric_definition(test_metric)
print(f"Result: {result}")
```

### 2. Check PostgresClient Behavior
```python
# Test how PostgresClient handles arrays and JSONB
with self.db:
    result = self.db.execute(
        "INSERT INTO telemetry.metric_definitions (metric_id, name, ...) VALUES ($1, $2, ...)",
        [uuid, "test", ...],
        schema='telemetry'
    )
```

### 3. Verify Table Schema
```python
# Check if table was created correctly
tables = self.db.list_tables(schema='telemetry')
logger.info(f"Telemetry tables: {tables}")
```

---

## Quick Fix Priority

1. **Critical:** Debug metric definition creation
   - Add detailed error logging
   - Test with minimal required fields only
   - Verify data type conversions

2. **Critical:** Debug alert rule creation
   - Similar approach as metrics
   - Test with minimal required fields

3. **High:** Fix list alert rules error
   - Add proper error handling
   - Ensure JSON serialization

4. **Medium:** Add remaining table creation to `_ensure_schema()`

---

## Environment Requirements

### Database Tables:
- ✅ `telemetry.metric_definitions` (auto-created)
- ✅ `telemetry.alert_rules` (auto-created)
- 🔄 `telemetry.telemetry_data` (needed)
- 🔄 `telemetry.aggregated_data` (needed)
- 🔄 `telemetry.alerts` (needed)
- 🔄 `telemetry.real_time_subscriptions` (needed)

### Service Dependencies:
- ✅ Auth Service (working)
- ✅ PostgreSQL gRPC Service (connected)
- ⚠️ Device Service (optional for FK validation)

---

## Running Tests

```bash
cd microservices/telemetry_service/tests
bash telemetry_test.sh
```

**Expected After Fixes:**
- All 18 tests should pass
- Metric definitions should create successfully
- Alert rules should create successfully
- All list operations should return valid JSON

---

## Migration Files Available

- `migrations/001_create_telemetry_tables.sql` ✅
- `migrations/002_migrate_to_telemetry_schema.sql` ✅ (Used for auto-creation)

---

## Related Files

- `telemetry_service.py` - Business logic
- `telemetry_repository.py:32-119` - Schema creation
- `telemetry_repository.py:226-269` - Metric definition CRUD
- `telemetry_repository.py:~300-400` - Alert rule CRUD
- `main.py:282-298` - Metric definition endpoint
- `main.py:~400-450` - Alert rule endpoints
- `models.py` - Data models
- `tests/telemetry_test.sh` - Test suite

---

## Notes

- ✅ Schema auto-creation working
- 🔴 Insert operations failing (likely data type conversion)
- 📊 15/18 tests passing (83%)
- 🎯 Service functional for read operations
- ⚠️ Write operations need debugging
