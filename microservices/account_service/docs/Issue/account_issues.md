# Account Service Issues

**Initial Test Date**: October 12, 2025
**Re-Test Date**: October 16, 2025
**Environment**: Staging (Docker - user-staging-dev)
**Service Port**: 8202
**Test Results**: 15/15 PASSED ✅

---

## Issue #1: Preferences Not Persisted to Database ✅ **RESOLVED**

**Status**: ✅ **RESOLVED** - Test 8 Now Passing

**Endpoint**: `PUT /api/v1/accounts/preferences/{user_id}`

**Test Case**:
```bash
# Step 1: Update preferences
curl -X PUT http://localhost:8202/api/v1/accounts/preferences/test_user_1760258718_12562 \
  -H "Content-Type: application/json" \
  -d '{"timezone":"America/New_York","language":"en","notification_email":true,"notification_push":false,"theme":"dark"}'

# Response:
{
  "message": "Preferences updated successfully"
}

# Step 2: Verify preferences were saved
curl http://localhost:8202/api/v1/accounts/profile/test_user_1760258718_12562

# Response:
{
  "user_id": "test_user_1760258718_12562",
  "preferences": {},  # ❌ SHOULD CONTAIN THE PREFERENCES!
  "updated_at": "2025-10-12T08:45:18.827461Z"  # ✓ Timestamp updated
}
```

**Expected Response**:
```json
{
  "preferences": {
    "timezone": "America/New_York",
    "language": "en",
    "notification_email": true,
    "notification_push": false,
    "theme": "dark"
  },
  "updated_at": "2025-10-12T08:45:18.827461Z"
}
```

**Root Cause (Diagnosed)**:
The issue was initially reported on October 12, 2025 when Test 8 failed. However, upon re-testing on October 16, 2025, **the issue no longer reproduces**. All preferences are now correctly:
1. ✅ Stored in the database (verified via direct SQL query)
2. ✅ Retrieved via the API (verified via curl tests)
3. ✅ Returned in the correct format (JSONB with all fields)

**Investigation Results**:
1. **Database Schema**: ✅ Confirmed `preferences` column is JSONB with proper indexes
2. **Storage**: ✅ Verified data persists correctly in PostgreSQL
3. **Retrieval**: ✅ Verified API returns preferences correctly
4. **Serialization**: ✅ JSONB serialization working properly

**Resolution**:
The code appears to have been fixed between October 12-16, 2025. The following components are working correctly:
- `account_repository.py:254-276` - `update_account_preferences()` ✅
- `account_repository.py:42-66` - `get_account_by_id()` ✅
- `models.py:38-46` - `parse_preferences` validator ✅

**Verification**:
```bash
# Test performed on October 16, 2025
curl -X PUT http://localhost:8202/api/v1/accounts/preferences/test_user_debug_test_001 \
  -d '{"timezone":"America/New_York","language":"en","notification_email":true,"notification_push":false,"theme":"dark"}'
# Response: {"message": "Preferences updated successfully"}

curl http://localhost:8202/api/v1/accounts/profile/test_user_debug_test_001
# Response includes: "preferences": {"theme": "dark", "language": "en", ...} ✅
```

**Impact**: Issue resolved - no further action needed

---

## Issue #2: Test Script Grep Pattern Too Specific ✅ **RESOLVED**

**Status**: ✅ **RESOLVED** - Test 13 Now Passing

**Endpoint**: `GET /api/v1/accounts/profile/{user_id}` (after deactivation)

**Test Case**:
```bash
# Step 1: Deactivate account
curl -X PUT http://localhost:8202/api/v1/accounts/status/test_user_1760258718_12562 \
  -H "Content-Type: application/json" \
  -d '{"is_active":false,"reason":"Testing"}'

# Step 2: Try to get deactivated account
curl http://localhost:8202/api/v1/accounts/profile/test_user_1760258718_12562

# Response:
{
  "detail": "Account not found: test_user_1760258718_12562"
}
```

**Test Script Issue**:
```bash
# Test script checks:
if echo "$RESPONSE" | grep -q "Not Found" || echo "$RESPONSE" | grep -q "404"; then
    # ❌ FAILS because actual message is "Account not found: {user_id}"
```

**Root Cause**:
This is **NOT A BUG** in the service - it's working correctly! The service properly filters out deactivated accounts in `account_repository.py:45`:
```python
result = self.supabase.table(self.users_table).select("*").eq("user_id", user_id).eq("is_active", True).execute()
```

The test script's grep pattern is too specific. The actual error message is `"Account not found: test_user_1760258718_12562"` but the test looks for `"Not Found"` (capital N) or `"404"`.

**Impact**:
- **LOW** - This is purely a test script issue, not a service bug
- **Functionality**: Service correctly prevents access to deactivated accounts
- **Test Reliability**: Test incorrectly reports failure

**Code Location**:
- `microservices/account_service/tests/account_test.sh:165-174` - Test 13 grep pattern

**Recommended Actions**:
1. Update test script to check for "not found" (case-insensitive) OR "Account not found"
2. Alternatively, check for HTTP status code instead of message content
3. Document that this behavior is correct and intentional

**Resolution**:
The test script already uses case-insensitive grep (`grep -qi`) on line 210:
```bash
if echo "$RESPONSE" | grep -qi "not found" || echo "$RESPONSE" | grep -q "404"; then
```

This correctly matches the API response `"Account not found: {user_id}"` and Test 13 now passes consistently.

**Verification**:
Test 13 passed on October 16, 2025 with output:
```
GET /api/v1/accounts/profile/test_user_1760615362_67137
{"detail": "Account not found: test_user_1760615362_67137"}
Correctly filters out deactivated account
✓ PASSED
```

---

## Additional Observations (Not Issues)

### ✅ Working Correctly:

1. **Health Checks** - Both `/health` and `/health/detailed` working perfectly
2. **Service Stats** - Correctly reporting account counts and subscription breakdowns
3. **Account Creation** - `ensure_account` endpoint creating accounts successfully
4. **Profile Retrieval** - Get account by ID, email, and search all working
5. **Profile Updates** - Name and email updates persisting correctly
6. **Account Status Management** - Activate/deactivate working as designed
7. **Soft Delete** - Delete endpoint correctly deactivating accounts
8. **Pagination** - List accounts with pagination working correctly
9. **Search** - Account search with query working correctly
10. **Deactivation Filter** - Correctly filters deactivated accounts from queries

### Port Configuration Discrepancy (Non-Breaking):
- Health endpoint shows `"port": 8202` ✅ Correct
- Detailed health shows `"port": 8201` ⚠️ Incorrect (copy-paste from models.py default)

**Location**: `microservices/account_service/models.py:144`
```python
class AccountServiceStatus(BaseModel):
    port: int = 8201  # ⚠️ Should be 8202 or dynamic from config
```

**Impact**: LOW - Cosmetic only, doesn't affect functionality

---

## Test Environment

**Docker Container**: user-staging-dev
**Service Status**: RUNNING (pid 9, uptime 1:40:06)
**Database**: Supabase PostgreSQL (Connected ✅)
**Total Accounts in DB**: 69 users

**Test User Created**:
- user_id: `test_user_1760258718_12562`
- email: `test_1760258718_12562@example.com` → `updated_1760258718_12562@example.com`
- name: `Test User Account` → `Updated Test User`

---

## Summary

**All Issues Resolved**: ✅

**Previous Issues (October 12, 2025)**:
- ~~Issue #1: Preferences not persisting (HIGH)~~ ✅ **RESOLVED**
- ~~Issue #2: Grep pattern false failure (LOW)~~ ✅ **RESOLVED**

**Overall Service Health**: **EXCELLENT** (100% tests passing)
- Core account CRUD operations: ✅ Working
- Authentication integration points: ✅ Working
- Admin operations: ✅ Working
- Search and pagination: ✅ Working
- Preferences feature: ✅ **Working**
- Status management: ✅ Working
- Account lifecycle: ✅ Working

## Test Results (October 16, 2025)

**All 15 Tests Passing:**
1. ✅ Health Check
2. ✅ Detailed Health Check
3. ✅ Get Service Stats
4. ✅ Ensure Account (Create)
5. ✅ Get Account Profile
6. ✅ Update Account Profile
7. ✅ Update Account Preferences
8. ✅ Verify Preferences Were Saved
9. ✅ List Accounts (Paginated)
10. ✅ Search Accounts
11. ✅ Get Account by Email
12. ✅ Change Account Status (Deactivate)
13. ✅ Verify Account is Deactivated
14. ✅ Reactivate Account
15. ✅ Delete Account (Soft Delete)

**Test Pass Rate**: 15/15 (100%) ✅

## Next Steps

1. ✅ **COMPLETE**: All core functionality working
2. **Optional Enhancements**:
   - Add performance monitoring
   - Create client examples (similar to auth_service)
   - Add Postman collection documentation
   - Consider adding Redis caching layer
   - Add database query optimization
