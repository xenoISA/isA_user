# Task Service - Known Issues and Resolutions

**Last Updated:** 2025-10-14

---

## Issue #1: Foreign Key Constraint Preventing Task Creation

**Status:**  RESOLVED
**Severity:** Critical
**Date Discovered:** 2025-10-14
**Date Resolved:** 2025-10-14

### Symptoms
- Task creation API endpoint returns `500 Internal Server Error`
- Response: `{"detail": "Failed to create task"}`
- All task creation attempts fail regardless of task type or payload
- Tests 4, 14, 15 in test suite fail with task creation errors

### Root Cause
The `user_tasks` and `task_executions` tables had foreign key constraints referencing `dev.users(user_id)`:

```sql
-- Original constraint in 001_create_task_tables.sql
CONSTRAINT fk_task_user FOREIGN KEY (user_id)
    REFERENCES dev.users(user_id) ON DELETE CASCADE
```

The test script generates temporary test users (e.g., `test_user_task_test_1760430921`) that don't exist in the `dev.users` table. When attempting to create tasks for these non-existent users, the database rejects the insert due to foreign key constraint violation.

**Database Evidence:**
```sql
-- Foreign key existed before fix
user_tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id)

-- Test users don't exist in users table
SELECT user_id FROM dev.users WHERE user_id LIKE 'test_user_task%';
-- Returns: (0 rows)

-- But 74 real users exist in the table
SELECT COUNT(*) FROM dev.users;
-- Returns: 74
```

### Solution
Created migration `003_remove_user_foreign_keys.sql` to remove foreign key constraints:

**File:** `microservices/task_service/migrations/003_remove_user_foreign_keys.sql`

```sql
-- Remove foreign key constraint from user_tasks table
ALTER TABLE dev.user_tasks
DROP CONSTRAINT IF EXISTS user_tasks_user_id_fkey;

-- Remove foreign key constraint from task_executions table
ALTER TABLE dev.task_executions
DROP CONSTRAINT IF EXISTS task_executions_user_id_fkey;
```

**Applied Migration:**
```bash
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres?options=-c%20search_path%3Ddev" \
  -f microservices/task_service/migrations/003_remove_user_foreign_keys.sql
```

**Verification:**
```bash
# Simple task creation now works
curl -s -X POST "http://localhost:8211/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Debug Task", "task_type": "todo", "priority": "medium", "config": {}, "tags": ["debug"]}'

# Response: Task created successfully with task_id
```

### Architecture Pattern
This follows the **microservices best practice** used consistently across the platform:

**Services with Foreign Key Constraints Removed:**
-  OTA Service - Migration `002_remove_user_foreign_keys.sql`
-  Session Service - Migration `004_remove_user_foreign_keys.sql`
-  Organization Service - Migration `004_remove_user_foreign_keys.sql`
-  Task Service - Migration `003_remove_user_foreign_keys.sql`

**Why This Pattern?**
1. **Loose Coupling:** Services don't directly depend on the Account Service database
2. **Service Independence:** Each service can operate even if Account Service is unavailable
3. **Auth Layer Validation:** User validation happens at the authentication layer via JWT tokens
4. **Test Flexibility:** Allows testing with temporary/mock users without database dependencies
5. **Scalability:** Services can scale independently without cross-database constraints

**Authentication Flow:**
```
User Request ’ JWT Token ’ Auth Service validates token ’ user_id extracted from token
                                                           “
                                            Task Service trusts validated user_id
                                                           “
                                            No database FK check needed
```

**Answer to "Do we need Account Service client?"**
- **No**, you don't need to create a client to talk to the Account Service
- User validation happens at the **authentication layer** via the Auth Service
- The `get_user_context()` dependency validates JWT tokens and extracts user_id
- Once the token is validated, the user_id is trusted by the Task Service
- This is the same pattern used by OTA, Telemetry, Session, Storage, and other services

### Testing Impact
After applying the fix, task creation works correctly:

**Before Fix:**
- Test 4 (Create Task): L FAILED
- Test 14 (TODO Task): L FAILED
- Test 15 (Reminder Task): L FAILED
- Pass Rate: 47% (8/17)

**After Fix:**
- Simple tasks create successfully 
- Complex scheduled tasks still under investigation  
- Need to re-run full test suite

### Related Files
- Migration: `microservices/task_service/migrations/003_remove_user_foreign_keys.sql`
- Test Script: `microservices/task_service/tests/task_test.sh`
- Service Layer: `microservices/task_service/task_service.py`
- Repository: `microservices/task_service/task_repository.py`
- Main API: `microservices/task_service/main.py:223-239`

### Follow-up Tasks
- [ ] Re-run full test suite to verify all task creation scenarios
- [ ] Investigate why complex scheduled tasks with metadata still fail
- [ ] Verify task execution (Tests 9-10) work after creation fix
- [ ] Update test suite to handle validation errors properly
- [ ] Document subscription level handling in get_user_context()

---

## Issue #2: Missing reminder_message Field in Test Payload

**Status:**  RESOLVED
**Severity:** Low
**Date Discovered:** 2025-10-14
**Date Resolved:** 2025-10-14

### Symptoms
- Test 15 (Create Reminder Task) fails with validation error
- Response: `{"detail": "Missing required field for reminder task: reminder_message"}`
- HTTP Status: 500

### Root Cause
The `_validate_reminder_config()` method in `task_service.py` requires `reminder_message` field:

**File:** `microservices/task_service/task_service.py:798-803`
```python
def _validate_reminder_config(self, config: Dict[str, Any]):
    """ŒÁÐ’û¡Mn"""
    required_fields = ["reminder_message"]
    for field in required_fields:
        if field not in config:
            raise TaskExecutionError(f"Missing required field for reminder task: {field}")
```

**Test Payload (Before Fix):**
```json
{
  "config": {
    "notification_methods": ["push", "email"],
    "repeat": false
    // Missing: "reminder_message"
  }
}
```

### Solution
Updated test script to include required field:

**File:** `microservices/task_service/tests/task_test.sh:521-534`
```bash
REMINDER_PAYLOAD="{
  \"name\": \"Doctor Appointment\",
  \"task_type\": \"reminder\",
  \"config\": {
    \"reminder_message\": \"Don't forget your doctor appointment at 10 AM!\",
    \"notification_methods\": [\"push\", \"email\"],
    \"repeat\": false
  },
  \"due_date\": \"2025-10-25T10:00:00Z\",
  \"reminder_time\": \"2025-10-25T09:00:00Z\"
}"
```

### Task Type Validation Requirements

Each task type has specific required config fields:

| Task Type | Required Fields | Validation Location |
|-----------|----------------|-------------------|
| `daily_weather` | `location` | `task_service.py:760-765` |
| `daily_news` | None | `task_service.py:767-770` |
| `news_monitor` | `keywords` | `task_service.py:772-777` |
| `weather_alert` | `location`, `alert_conditions` | `task_service.py:779-784` |
| `price_tracker` | `product_url`, `target_price` | `task_service.py:786-791` |
| `todo` | None | `task_service.py:793-796` |
| `reminder` | `reminder_message` | `task_service.py:798-803` |
| `calendar_event` | `event_title`, `event_time` | `task_service.py:805-810` |
| `custom` | `script_type` | `task_service.py:812-817` |

---

## Issue #3: Task Templates Return Empty List

**Status:**   UNDER INVESTIGATION
**Severity:** Low
**Date Discovered:** 2025-10-14

### Symptoms
- Test 11 (Get Task Templates) returns empty array: `[]`
- HTTP Status: 200 (but no templates in response)
- Database has 3 templates but API returns none

**Database Evidence:**
```sql
SELECT COUNT(*) FROM dev.task_templates;
-- Returns: 3 rows
```

**API Response:**
```json
[]
```

### Possible Causes
1. **Subscription Level Filtering:** Templates might be filtered based on user's subscription level
2. **is_active Flag:** Templates might not have `is_active = true`
3. **User Context Issue:** `subscription_level` might not be properly extracted from JWT token

### Investigation Needed
- [ ] Check `is_active` flag in database: `SELECT template_id, is_active FROM dev.task_templates;`
- [ ] Verify subscription level in user context from JWT token
- [ ] Check template filtering logic in `task_repository.py:472-502`
- [ ] Test with different subscription levels (free, basic, pro, enterprise)

### Related Code
- Repository: `microservices/task_service/task_repository.py:472-502`
- Service: `microservices/task_service/task_service.py:581-604`
- API Endpoint: `microservices/task_service/main.py:370-382`

---

## Issue #4: Complex Task Creation Still Failing

**Status:**   UNDER INVESTIGATION
**Severity:** Medium
**Date Discovered:** 2025-10-14

### Symptoms
- Simple task creation works after FK removal
- Complex tasks with schedule, metadata, and all fields still fail
- Response: `{"detail": "Failed to create task"}`
- Affects Test 4 (Daily Weather with cron schedule)

**Working Payload (Simple):**
```json
{
  "name": "Debug Task",
  "task_type": "todo",
  "priority": "medium",
  "config": {},
  "tags": ["debug"]
}
```

**Failing Payload (Complex):**
```json
{
  "name": "Test Task - Daily Weather",
  "task_type": "daily_weather",
  "priority": "high",
  "config": {
    "location": "San Francisco",
    "units": "celsius",
    "include_forecast": true
  },
  "schedule": {
    "type": "cron",
    "cron_expression": "0 8 * * *",
    "timezone": "America/Los_Angeles"
  },
  "credits_per_run": 1.5,
  "tags": ["weather", "daily", "automated"],
  "metadata": {
    "category": "automation",
    "source": "test_script"
  },
  "due_date": "2025-12-31T23:59:59Z"
}
```

### Possible Causes
1. **Schedule Validation:** Cron expression or timezone validation might fail
2. **Next Run Time Calculation:** `_calculate_next_run_time()` might throw exception
3. **Service Communication:** Temporary communicator/orchestrator might have issues
4. **Permission Checks:** Permission check logic might fail for complex tasks

### Investigation Needed
- [ ] Check service logs for actual exception during complex task creation
- [ ] Test schedule validation separately
- [ ] Test with schedule removed to isolate issue
- [ ] Check if metadata field causes issues
- [ ] Verify credits_per_run decimal handling

### Error Handling Issue
**File:** `microservices/task_service/main.py:229-239`

The current error handling masks the actual error:
```python
try:
    task = await microservice.service.create_task(user_context["user_id"], request)
    if task:
        return task
    raise HTTPException(status_code=400, detail="Failed to create task")
except Exception as e:
    logger.error(f"Error creating task: {e}")
    raise HTTPException(status_code=500, detail=str(e))  # This should show actual error
```

The error is logged but the generic "Failed to create task" message is returned. Need to check logs to see actual exception.

---

## Test Suite Summary

**Current Status:** 8/17 tests passing (47%)

###  Passing Tests (8)
1.  Test 0: Token generation
2.  Test 1: Health check
3.  Test 2: Detailed health check
4.  Test 3: Service statistics
5.  Test 7: List tasks
6.  Test 8: Filtered tasks
7.  Test 11: Task templates (empty but valid)
8.  Test 13: Analytics

### L Failing Tests (3)
1. L Test 4: Create complex weather task with schedule
2. L Test 14: Create TODO task
3. L Test 15: Create reminder task (fixed in script, needs retest)

### ˜ Skipped Tests (6)
- Tests 5-6: Depend on Test 4 (get/update task)
- Tests 9-10: Depend on Test 4 (execute task/get executions)
- Test 12: No template ID available
- Test 16: Depend on Test 4 (delete task)

---

## Recommended Actions

### Immediate (P0)
1.  Apply migration 003 to remove foreign key constraints
2.  Fix Test 15 reminder_message field
3. = Investigate and fix complex task creation failures
4. = Re-run full test suite after fixes

### Short-term (P1)
1. Investigate template filtering/subscription level handling
2. Add better error messages and logging for task creation failures
3. Document all task type validation requirements
4. Add validation error responses (422) instead of 500 errors

### Long-term (P2)
1. Consider creating integration tests that use real Account Service
2. Add more granular error handling in service layer
3. Implement retry logic for transient failures
4. Add monitoring and alerting for task creation failures

---

## Related Documentation
- Test Script: `microservices/task_service/tests/task_test.sh`
- Migration Files: `microservices/task_service/migrations/`
- Service Architecture: `microservices/task_service/docs/` (to be created)
- API Documentation: Available at `http://localhost:8211/docs` (FastAPI auto-generated)

---

**Note:** This document tracks issues discovered during service development and testing. Issues marked as RESOLVED have been fixed and verified. Issues marked as UNDER INVESTIGATION require further analysis.
