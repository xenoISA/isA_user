# Audit Service - Known Issues

**Last Updated:** 2025-10-28
**Test Results:** 5/16 tests passing (31%)

## Overview
Audit service has proper code structure but database connection is not available.

## Critical Issues

### 1. Database Connection Unavailable
**Status:** 🔴 Critical
**Severity:** High
**Tests Affected:**
- Test 4: Get Service Stats (11 tests failing)
- Test 5-15: All audit operations

**Error:**
```
审计服务不可用
HTTP Status: 503
```

**Root Cause:**
The audit service health check shows:
```json
{
  "database_connected": false,
  "status": "degraded"
}
```

**Possible Causes:**
1. PostgreSQL gRPC service not accessible
2. Audit schema not created
3. Network connectivity issues
4. Permissions issues

**Debug Steps:**
```bash
# Check PostgreSQL gRPC service
curl http://localhost:50061/health

# Check if audit schema exists
# Via PostgresClient
from isa_common.postgres_client import PostgresClient
db = PostgresClient(host='isa-postgres-grpc', port=50061, user_id='audit')
result = db.health_check()
```

**Files to Check:**
- `audit_repository.py:36` - `check_connection()` method
- `main.py:57` - Health check in lifespan
- Environment variables for PostgreSQL connection

**Required Fix:**
Ensure PostgreSQL gRPC service is running and audit schema is created.

---

### 2. Missing Auto-Schema Creation
**Status:** ⚠️ Needs Implementation
**Severity:** High

**Description:**
Unlike device_service and telemetry_service, audit_service doesn't automatically create its schema and tables.

**Implementation Needed:**
```python
# Add to audit_repository.py
def _ensure_schema(self):
    """Ensure audit schema and tables exist"""
    try:
        with self.db:
            self.db.execute("CREATE SCHEMA IF NOT EXISTS audit", schema='public')

        # Create audit_events table
        create_audit_events = '''
            CREATE TABLE IF NOT EXISTS audit.audit_events (
                event_id VARCHAR(255) PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                event_category VARCHAR(50) NOT NULL,
                -- ... all other columns from migration
            )
        '''
        with self.db:
            self.db.execute(create_audit_events, schema='audit')
    except Exception as e:
        logger.warning(f"Could not ensure schema: {e}")
```

**Files to Update:**
- `audit_repository.py:__init__()` - Add `self._ensure_schema()` call
- Use migrations/001_*.sql as reference for table schema

**Priority:** High - Required for service to function

---

## Fixed Issues ✅

### Check Connection Method Added
**Previous Error:** `AttributeError: 'AuditRepository' object has no attribute 'check_connection'`

**Fix Applied:**
```python
async def check_connection(self) -> bool:
    """检查数据库连接"""
    try:
        result = self.db.health_check(detailed=False)
        return result is not None and result.get('healthy', False)
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return False
```

**Status:** ✅ Fixed in `audit_repository.py:36-43`

---

## Working Features ✅

When database is connected, these features work:

1. **Health Check** - Returns service status
2. **Detailed Health Check** - Shows database connection status
3. **Service Info** - Returns capabilities and endpoints
4. **Compliance Standards** - Returns supported standards (GDPR, SOX, HIPAA)

**Tests Passing (5/16):**
- ✅ Test 0: Generate test token
- ✅ Test 1: Health check
- ✅ Test 2: Detailed health check
- ✅ Test 3: Get service info
- ✅ Test 13: Get compliance standards

**Tests Failing (11/16):**
All require database connection:
- ❌ Test 4: Get service stats
- ❌ Test 5: Create audit event
- ❌ Test 6: Batch create audit events
- ❌ Test 7: Query audit events
- ❌ Test 8: List audit events
- ❌ Test 9: Get user activities
- ❌ Test 10: Get user activity summary
- ❌ Test 11: Create security alert
- ❌ Test 12: List security events
- ❌ Test 14: Generate compliance report
- ❌ Test 15: Maintenance cleanup

---

## Database Schema Required

### Tables Needed:
```sql
-- From migrations/001_migrate_to_audit_schema.sql
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE audit.audit_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    event_severity VARCHAR(20) NOT NULL,
    event_status VARCHAR(20) NOT NULL,
    user_id VARCHAR(255),
    organization_id VARCHAR(255),
    session_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    action VARCHAR(200) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    resource_name VARCHAR(255),
    status_code INTEGER,
    error_message TEXT,
    changes_made JSONB DEFAULT '{}'::jsonb,
    risk_score INTEGER DEFAULT 0,
    threat_indicators TEXT[] DEFAULT '{}',
    compliance_flags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT '{}',
    event_timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes Required:**
- `idx_audit_events_event_id`
- `idx_audit_events_user_id`
- `idx_audit_events_event_type`
- `idx_audit_events_timestamp`
- And others from migration file

---

## Environment Requirements

### Service Dependencies:
- 🔴 PostgreSQL gRPC Service (not connected)
- ✅ Auth Service (working)

### Required Environment Variables:
```bash
POSTGRES_GRPC_HOST=isa-postgres-grpc
POSTGRES_GRPC_PORT=50061
```

### Network Requirements:
- Access to PostgreSQL gRPC service on port 50061
- Service must be running in same network as PostgreSQL

---

## Quick Fix Priority

1. **Critical:** Verify PostgreSQL gRPC service is running
   ```bash
   docker ps | grep postgres-grpc
   # or
   curl http://isa-postgres-grpc:50061/health
   ```

2. **Critical:** Add auto-schema creation like other services
   - Copy pattern from device_service or telemetry_service
   - Add `_ensure_schema()` method
   - Call in `__init__()`

3. **High:** Run migration scripts if schema exists
   ```bash
   cd microservices/audit_service/migrations
   bash run_migrations.sh
   ```

4. **Medium:** Add better error messages when database unavailable
   - Return more specific error details
   - Suggest troubleshooting steps

---

## Running Tests

```bash
cd microservices/audit_service/tests
bash audit_test.sh
```

**Expected After Fixes:**
- All 16 tests should pass
- Database connection should succeed
- All audit operations should work

---

## Migration Files Available

- `migrations/001_migrate_to_audit_schema.sql` ✅
- `migrations/run_migrations.sh` ✅

**Note:** Migrations are available but need PostgreSQL connection to run.

---

## Troubleshooting Steps

### 1. Check PostgreSQL gRPC Service
```bash
# Check if service is running
docker ps | grep postgres

# Check health
curl http://localhost:50061/health
```

### 2. Check Network Connectivity
```bash
# From audit service container
ping isa-postgres-grpc
telnet isa-postgres-grpc 50061
```

### 3. Check Environment Variables
```bash
# In audit service
echo $POSTGRES_GRPC_HOST
echo $POSTGRES_GRPC_PORT
```

### 4. Test Direct Connection
```python
from isa_common.postgres_client import PostgresClient

db = PostgresClient(
    host='isa-postgres-grpc',
    port=50061,
    user_id='audit_test'
)

result = db.health_check()
print(f"Connection result: {result}")
```

---

## Related Files

- `audit_service.py` - Business logic
- `audit_repository.py:24-43` - Repository initialization
- `audit_repository.py:36` - `check_connection()` method
- `main.py:45-96` - Lifespan management and health checks
- `models.py` - Data models
- `migrations/` - Database schema
- `tests/audit_test.sh` - Test suite

---

## Notes

- ✅ Code structure is correct
- ✅ `check_connection()` method added
- 🔴 Database connection is the blocker
- 📊 5/16 tests passing (31%)
- 🎯 Once database connected, should pass all tests
- ⚠️ Need to add auto-schema creation
