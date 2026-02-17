#!/bin/bash
# Account Service Validation & Edge Case Tests
# Tests input validation, error handling, and edge cases
# Usage:
#   ./account_validation_test.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./account_validation_test.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Helper function for HTTP response parsing (macOS compatible)
# ============================================================================
parse_response() {
    local response="$1"
    # Extract HTTP code (last line)
    HTTP_CODE=$(echo "$response" | tail -1)
    # Extract body (all lines except last)
    BODY=$(echo "$response" | sed '$d')
}

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="account_service"
API_PATH="/api/v1/accounts"

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"

print_info "Test Timestamp: $TEST_TS"
echo ""

# ============================================================================
# VALIDATION TESTS - Input Validation
# ============================================================================

print_section "VALIDATION TESTS"

# Test V1: Invalid email format
print_section "Test V1: Invalid Email Format"
echo "POST ${API_PATH}/ensure with invalid email"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/ensure" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_invalid_email","email":"not-a-valid-email","name":"Test User"}')
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -10

if [ "$HTTP_CODE" = "422" ]; then
    print_success "Correctly rejected invalid email (HTTP 422)"
    test_result 0
else
    print_error "Expected HTTP 422, got $HTTP_CODE"
    test_result 1
fi
echo ""

# Test V2: Empty user_id
print_section "Test V2: Empty user_id"
echo "POST ${API_PATH}/ensure with empty user_id"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/ensure" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"","email":"test@example.com","name":"Test User"}')
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -5

if [ "$HTTP_CODE" = "400" ] && echo "$BODY" | grep -q "user_id is required"; then
    print_success "Correctly rejected empty user_id (HTTP 400)"
    test_result 0
else
    print_error "Expected HTTP 400 with user_id validation error, got HTTP $HTTP_CODE"
    test_result 1
fi
echo ""

# Test V3: Empty name
print_section "Test V3: Empty name"
echo "POST ${API_PATH}/ensure with empty name"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/ensure" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"test_empty_name_${TEST_TS}\",\"email\":\"test@example.com\",\"name\":\"\"}")
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -5

if [ "$HTTP_CODE" = "400" ] && echo "$BODY" | grep -q "name is required"; then
    print_success "Correctly rejected empty name (HTTP 400)"
    test_result 0
else
    print_error "Expected HTTP 400 with name validation error, got HTTP $HTTP_CODE"
    test_result 1
fi
echo ""

# Test V4: Missing required field (email)
print_section "Test V4: Missing Required Field (email)"
echo "POST ${API_PATH}/ensure without email"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/ensure" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"test_no_email_${TEST_TS}\",\"name\":\"Test User\"}")
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -5

if [ "$HTTP_CODE" = "422" ] && echo "$BODY" | grep -q "Field required"; then
    print_success "Correctly rejected missing email (HTTP 422)"
    test_result 0
else
    print_error "Expected HTTP 422 for missing email"
    test_result 1
fi
echo ""

# Test V5: Duplicate email for different user
print_section "Test V5: Duplicate Email for Different User"
# First create a user
DUP_EMAIL="dup_test_${TEST_TS}@example.com"
echo "Step 1: Create first user with email $DUP_EMAIL"
curl -s -X POST "${API_BASE}/ensure" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"dup_user_1_${TEST_TS}\",\"email\":\"${DUP_EMAIL}\",\"name\":\"First User\"}" > /dev/null

echo "Step 2: Try to create second user with same email"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/ensure" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"dup_user_2_${TEST_TS}\",\"email\":\"${DUP_EMAIL}\",\"name\":\"Second User\"}")
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -5

if [ "$HTTP_CODE" = "400" ] && echo "$BODY" | grep -qi "already exists"; then
    print_success "Correctly rejected duplicate email (HTTP 400)"
    test_result 0
else
    print_error "Expected HTTP 400 with 'already exists' message, got HTTP $HTTP_CODE"
    test_result 1
fi
echo ""

# Test V6: Invalid theme preference
print_section "Test V6: Invalid Theme Preference"
echo "PUT ${API_PATH}/preferences with invalid theme"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/preferences/some_user_id" \
  -H "Content-Type: application/json" \
  -d '{"theme":"invalid_theme"}')
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -5

if [ "$HTTP_CODE" = "422" ] && echo "$BODY" | grep -q "pattern"; then
    print_success "Correctly rejected invalid theme (HTTP 422)"
    test_result 0
else
    print_error "Expected HTTP 422 for invalid theme"
    test_result 1
fi
echo ""

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

print_section "ERROR HANDLING TESTS"

# Test E1: Get non-existent profile
print_section "Test E1: Get Non-existent Profile"
echo "GET ${API_PATH}/profile/non_existent_user_xyz123"
RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/profile/non_existent_user_xyz123")
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -5

if [ "$HTTP_CODE" = "404" ] && echo "$BODY" | grep -q "not found"; then
    print_success "Correctly returned 404 for non-existent user"
    test_result 0
else
    print_error "Expected HTTP 404 for non-existent user"
    test_result 1
fi
echo ""

# Test E2: Get non-existent email
print_section "Test E2: Get Account by Non-existent Email"
echo "GET ${API_PATH}/by-email/nonexistent@nowhere.com"
RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/by-email/nonexistent@nowhere.com")
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -5

if [ "$HTTP_CODE" = "404" ] && echo "$BODY" | grep -q "not found"; then
    print_success "Correctly returned 404 for non-existent email"
    test_result 0
else
    print_error "Expected HTTP 404 for non-existent email"
    test_result 1
fi
echo ""

# Test E3: Update non-existent profile
print_section "Test E3: Update Non-existent Profile"
echo "PUT ${API_PATH}/profile/non_existent_user_xyz123"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/profile/non_existent_user_xyz123" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name"}')
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -5

if [ "$HTTP_CODE" = "404" ] && echo "$BODY" | grep -q "not found"; then
    print_success "Correctly returned 404 for non-existent user update"
    test_result 0
else
    print_error "Expected HTTP 404 for non-existent user update"
    test_result 1
fi
echo ""

# ============================================================================
# EDGE CASE TESTS
# ============================================================================

print_section "EDGE CASE TESTS"

# Test EC1: Pagination max boundary
print_section "Test EC1: Pagination Max Boundary (page_size=100)"
echo "GET ${API_PATH}?page=1&page_size=100"
RESPONSE=$(curl -s "${API_BASE}?page=1&page_size=100")
ACCOUNT_COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('accounts',[])))" 2>/dev/null)
TOTAL_COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_count',0))" 2>/dev/null)
echo "Returned: $ACCOUNT_COUNT accounts (max 100), Total: $TOTAL_COUNT"

if [ "$ACCOUNT_COUNT" -le 100 ]; then
    print_success "Pagination respects max limit"
    test_result 0
else
    print_error "Pagination exceeded max limit"
    test_result 1
fi
echo ""

# Test EC2: Pagination over max
print_section "Test EC2: Pagination Over Max (page_size=200)"
echo "GET ${API_PATH}?page=1&page_size=200"
RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}?page=1&page_size=200")
parse_response "$RESPONSE"
echo "$BODY" | json_pretty | head -5

if [ "$HTTP_CODE" = "422" ] && echo "$BODY" | grep -q "less than or equal to 100"; then
    print_success "Correctly rejected page_size > 100 (HTTP 422)"
    test_result 0
else
    print_error "Expected HTTP 422 for page_size > 100"
    test_result 1
fi
echo ""

# Test EC3: Search with include_inactive=true
print_section "Test EC3: Search with include_inactive=true"
echo "GET ${API_PATH}/search?query=test&include_inactive=true"
RESPONSE=$(curl -s "${API_BASE}/search?query=test&limit=50&include_inactive=true")
TOTAL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
echo "Found $TOTAL accounts with include_inactive=true"

if [ "$TOTAL" -ge 0 ]; then
    print_success "Search with include_inactive works"
    test_result 0
else
    print_error "Search with include_inactive failed"
    test_result 1
fi
echo ""

# Test EC4: Search with include_inactive=false (should exclude inactive)
print_section "Test EC4: Search with include_inactive=false"
echo "GET ${API_PATH}/search?query=test&include_inactive=false"
RESPONSE=$(curl -s "${API_BASE}/search?query=test&limit=50&include_inactive=false")
INACTIVE_COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(sum(1 for a in data if not a.get('is_active',True)))" 2>/dev/null)
echo "Inactive accounts in results: $INACTIVE_COUNT (should be 0)"

if [ "$INACTIVE_COUNT" = "0" ]; then
    print_success "Search correctly excludes inactive accounts"
    test_result 0
else
    print_error "Search should exclude inactive accounts when include_inactive=false"
    test_result 1
fi
echo ""

# Test EC5: List with is_active filter
print_section "Test EC5: List with is_active=false Filter"
echo "GET ${API_PATH}?is_active=false&page_size=5"
RESPONSE=$(curl -s "${API_BASE}?is_active=false&page_size=5")
ACTIVE_COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(sum(1 for a in data.get('accounts',[]) if a.get('is_active',True)))" 2>/dev/null)
echo "Active accounts in results: $ACTIVE_COUNT (should be 0)"

if [ "$ACTIVE_COUNT" = "0" ]; then
    print_success "List correctly filters by is_active=false"
    test_result 0
else
    print_error "List should only return inactive accounts when is_active=false"
    test_result 1
fi
echo ""

# Test EC6: Preferences merge behavior
print_section "Test EC6: Preferences Merge Behavior"
# Create a test user
PREF_USER="pref_test_${TEST_TS}"
PREF_EMAIL="pref_${TEST_TS}@example.com"
echo "Step 1: Create test user"
curl -s -X POST "${API_BASE}/ensure" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"${PREF_USER}\",\"email\":\"${PREF_EMAIL}\",\"name\":\"Pref Test User\"}" > /dev/null

echo "Step 2: Set initial preferences (language, theme)"
curl -s -X PUT "${API_BASE}/preferences/${PREF_USER}" \
  -H "Content-Type: application/json" \
  -d '{"language":"en","theme":"dark"}' > /dev/null

echo "Step 3: Update only timezone (should preserve language and theme)"
curl -s -X PUT "${API_BASE}/preferences/${PREF_USER}" \
  -H "Content-Type: application/json" \
  -d '{"timezone":"UTC"}' > /dev/null

echo "Step 4: Verify all preferences preserved"
RESPONSE=$(curl -s "${API_BASE}/profile/${PREF_USER}")
PREFS=$(echo "$RESPONSE" | python3 -c "import sys,json; prefs=json.load(sys.stdin).get('preferences',{}); print(f'language={prefs.get(\"language\",\"MISSING\")}, theme={prefs.get(\"theme\",\"MISSING\")}, timezone={prefs.get(\"timezone\",\"MISSING\")}')" 2>/dev/null)
echo "Preferences: $PREFS"

if echo "$PREFS" | grep -q "language=en" && echo "$PREFS" | grep -q "theme=dark" && echo "$PREFS" | grep -q "timezone=UTC"; then
    print_success "Preferences are correctly merged (not replaced)"
    test_result 0
else
    print_error "Preferences should be merged, not replaced"
    test_result 1
fi
echo ""

# Test EC7: Update with empty payload
print_section "Test EC7: Update with Empty Payload"
echo "PUT ${API_PATH}/profile/${PREF_USER} with {}"
RESPONSE=$(curl -s "${API_BASE}/profile/${PREF_USER}")
ORIGINAL_NAME=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null)

RESPONSE=$(curl -s -X PUT "${API_BASE}/profile/${PREF_USER}" \
  -H "Content-Type: application/json" \
  -d '{}')
UPDATED_NAME=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null)

echo "Original name: $ORIGINAL_NAME, After empty update: $UPDATED_NAME"

if [ "$ORIGINAL_NAME" = "$UPDATED_NAME" ]; then
    print_success "Empty update preserves existing data"
    test_result 0
else
    print_error "Empty update should preserve existing data"
    test_result 1
fi
echo ""

# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

print_section "HEALTH CHECK TESTS"

# Test H1: Basic health check
print_section "Test H1: Basic Health Check"
echo "GET /health"
RESPONSE=$(curl -s "${BASE_URL}/health")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q '"status".*"healthy"'; then
    print_success "Health check returns healthy"
    test_result 0
else
    print_error "Health check should return healthy"
    test_result 1
fi
echo ""

# Test H2: Detailed health check
print_section "Test H2: Detailed Health Check"
echo "GET /health/detailed"
RESPONSE=$(curl -s "${BASE_URL}/health/detailed")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q '"database_connected".*true'; then
    print_success "Detailed health shows database connected"
    test_result 0
else
    print_error "Detailed health should show database connected"
    test_result 1
fi
echo ""

# ============================================================================
# Cleanup test users created during this test
# ============================================================================
print_section "Cleanup"
echo "Cleaning up test users..."
curl -s -X DELETE "${API_BASE}/profile/dup_user_1_${TEST_TS}" > /dev/null 2>&1
curl -s -X DELETE "${API_BASE}/profile/${PREF_USER}" > /dev/null 2>&1
echo "Cleanup complete"

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
