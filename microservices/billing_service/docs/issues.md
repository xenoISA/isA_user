# Billing Service - Known Issues

**Last Updated:** 2025-10-28
**Test Results:** 8/17 tests passing (47%)

## Overview
The billing service has database connectivity but lacks product pricing data and some repository methods.

## Critical Issues

### 1. Product Pricing Not Configured
**Status:** ⚠️ Blocking
**Severity:** High
**Tests Affected:**
- Test 4: Record Usage and Bill
- Test 11: Record Usage - Storage Service
- Test 14: Record Usage - API Gateway

**Error:**
```
Failed to calculate billing cost: Product pricing not found
```

**Root Cause:**
- Product pricing table is empty or doesn't exist
- No seed data for product pricing

**Solution Required:**
1. Create product pricing migration/seed data
2. Add default pricing for common products:
   - storage_service
   - api_gateway
   - agent_execution
   - model_inference

**Files to Update:**
- `migrations/002_seed_product_pricing.sql` (create)
- `billing_repository.py` (add `get_product_pricing()` method)

---

### 2. Missing Billing Record Methods
**Status:** ⚠️ Blocking
**Severity:** High
**Tests Affected:**
- Test 5: Get Billing Record
- Test 6: Get User Billing Records
- Test 9: Get Billing Statistics
- Test 12: Get User Billing Records - Filtered

**Error:**
```
Failed to get user billing records
Failed to get billing statistics
```

**Root Cause:**
- Billing records not being created successfully
- Repository methods may be returning empty results

**Solution Required:**
1. Verify billing_records table schema
2. Debug billing record creation flow
3. Ensure proper error handling and logging

**Files to Check:**
- `billing_repository.py:create_billing_record()`
- `billing_repository.py:get_user_billing_records()`
- `billing_service.py:record_usage_and_bill()`

---

### 3. Subscription Creation Failing
**Status:** ⚠️ Warning
**Severity:** Medium
**Tests Affected:**
- Test 0: Generate Test Token (subscription creation step)

**Error:**
```
Failed to create test subscription
```

**Root Cause:**
- Subscription service dependency unavailable
- Or subscription creation logic has issues

**Solution Required:**
1. Check subscription service availability
2. Add fallback/mock subscription for tests
3. Make subscription optional for billing tests

---

## Test-Only Issues (Non-Blocking)

### 4. Product Service Dependency
**Status:** ℹ️ Expected
**Severity:** Low

**Description:**
Product service is not running in test environment. This is now handled gracefully with fallback logic.

**Current Behavior:**
- Logs warning: "Product service unavailable, continuing with billing without usage record"
- Creates local usage record ID
- Continues with billing operations

**Note:** This is working as designed for resilient service communication.

---

## Environment Requirements

### Database Tables Required:
- ✅ `billing.billing_records`
- ✅ `billing.billing_events`
- ✅ `billing.usage_aggregations`
- ✅ `billing.billing_quotas`
- ⚠️ `billing.product_pricing` (empty/missing)
- ⚠️ `billing.subscriptions` (may be in different service)

### Service Dependencies:
- ✅ Auth Service (running, working)
- ⚠️ Product Service (optional, has fallback)
- ⚠️ Subscription Service (needed for full functionality)

---

## Quick Fix Priority

1. **High Priority:** Create product pricing seed data
2. **High Priority:** Debug billing record creation
3. **Medium Priority:** Fix subscription creation or make it optional
4. **Low Priority:** Add integration tests with mock services

---

## Running Tests

```bash
cd microservices/billing_service/tests
bash billing_test.sh
```

**Expected Results After Fixes:**
- All 17 tests should pass
- No dependency on product_service for basic operations
- Graceful degradation when optional services unavailable

---

## Related Files

- `billing_service.py` - Core business logic
- `billing_repository.py` - Database operations
- `main.py` - API endpoints
- `models.py` - Data models
- `migrations/` - Database schema
- `tests/billing_test.sh` - Test suite
