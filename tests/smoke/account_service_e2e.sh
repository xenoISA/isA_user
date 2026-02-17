#!/bin/bash
# Account Service - E2E Smoke Tests
# Tests critical paths for account management
# Usage:
#   ./account_test_e2e.sh              # Direct mode (default)
#   TEST_MODE=gateway ./account_test_e2e.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="account_service"
API_PATH="/api/v1/accounts"

# Initialize test (sets up BASE_URL, API_BASE, JWT if needed)
init_test

# ============================================================================
# Test Variables
# ============================================================================
# Generate unique test data to avoid conflicts
TIMESTAMP=$(date +%s)
PID=$$
UNIQUE_SUFFIX="${TIMESTAMP}_${PID}"

# Test user data (will be created during tests)
TEST_USER_1_ID="user_e2e_${UNIQUE_SUFFIX}_1"
TEST_USER_1_EMAIL="e2e_test_1_${UNIQUE_SUFFIX}@example.com"
TEST_USER_1_NAME="E2E Test User 1"

TEST_USER_2_ID="user_e2e_${UNIQUE_SUFFIX}_2"
TEST_USER_2_EMAIL="e2e_test_2_${UNIQUE_SUFFIX}@example.com"
TEST_USER_2_NAME="E2E Test User 2"

TEST_USER_SEARCH_ID="user_search_${UNIQUE_SUFFIX}"
TEST_USER_SEARCH_EMAIL="search_${UNIQUE_SUFFIX}@example.com"
TEST_USER_SEARCH_NAME="SearchableUser_${UNIQUE_SUFFIX}"

# ============================================================================
# Test Setup
# ============================================================================
print_info "E2E Test Configuration:"
print_info "  Test Mode: $TEST_MODE"
print_info "  Base URL: $BASE_URL"
print_info "  Timestamp: $TIMESTAMP"
print_info "  Test User 1: $TEST_USER_1_ID"
print_info "  Test User 2: $TEST_USER_2_ID"
echo ""

# ============================================================================
# Test 1: Health Check
# ============================================================================
print_section "Test 1: Health Check"
echo "GET /health"

RESPONSE=$(curl -s "${BASE_URL}/health")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "status"; then
    STATUS=$(json_get "$RESPONSE" "status")
    if [ "$STATUS" = "healthy" ]; then
        print_success "Service is healthy"
        test_result 0
    else
        print_error "Service status: $STATUS"
        test_result 1
    fi
else
    print_error "Health check failed - no status field"
    test_result 1
fi
echo ""

# ============================================================================
# Test 2: Ensure Account (Idempotent Create)
# ============================================================================
print_section "Test 2: Ensure Account (Idempotent Create)"
echo "POST ${API_PATH}/ensure"

# First call - should create new account
RESPONSE_1=$(api_post "/ensure" "{
    \"user_id\": \"${TEST_USER_1_ID}\",
    \"email\": \"${TEST_USER_1_EMAIL}\",
    \"name\": \"${TEST_USER_1_NAME}\"
}")

echo "First call (create):"
echo "$RESPONSE_1" | json_pretty

if json_has "$RESPONSE_1" "user_id"; then
    USER_ID_1=$(json_get "$RESPONSE_1" "user_id")
    EMAIL_1=$(json_get "$RESPONSE_1" "email")

    if [ "$USER_ID_1" = "$TEST_USER_1_ID" ] && [ "$EMAIL_1" = "$TEST_USER_1_EMAIL" ]; then
        print_success "Account created successfully"

        # Second call - should return existing account (idempotent)
        echo ""
        echo "Second call (idempotent):"
        RESPONSE_2=$(api_post "/ensure" "{
            \"user_id\": \"${TEST_USER_1_ID}\",
            \"email\": \"${TEST_USER_1_EMAIL}\",
            \"name\": \"${TEST_USER_1_NAME}\"
        }")

        echo "$RESPONSE_2" | json_pretty

        USER_ID_2=$(json_get "$RESPONSE_2" "user_id")
        if [ "$USER_ID_2" = "$TEST_USER_1_ID" ]; then
            print_success "Idempotent call returned same user"
            test_result 0
        else
            print_error "Idempotent call returned different user"
            test_result 1
        fi
    else
        print_error "Created user data doesn't match request"
        test_result 1
    fi
else
    print_error "Failed to create account"
    test_result 1
fi
echo ""

# ============================================================================
# Test 3: Get Account Profile
# ============================================================================
print_section "Test 3: Get Account Profile"
echo "GET ${API_PATH}/profile/${TEST_USER_1_ID}"

RESPONSE=$(api_get "/profile/${TEST_USER_1_ID}")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "user_id"; then
    USER_ID=$(json_get "$RESPONSE" "user_id")
    EMAIL=$(json_get "$RESPONSE" "email")
    NAME=$(json_get "$RESPONSE" "name")

    if [ "$USER_ID" = "$TEST_USER_1_ID" ] && [ "$EMAIL" = "$TEST_USER_1_EMAIL" ] && [ "$NAME" = "$TEST_USER_1_NAME" ]; then
        print_success "Profile retrieved successfully with correct data"
        test_result 0
    else
        print_error "Profile data doesn't match"
        test_result 1
    fi
else
    print_error "Failed to get profile"
    test_result 1
fi
echo ""

# ============================================================================
# Test 4: Update Account Profile
# ============================================================================
print_section "Test 4: Update Account Profile"
echo "PUT ${API_PATH}/profile/${TEST_USER_1_ID}"

NEW_NAME="Updated E2E Test User 1"
RESPONSE=$(api_put "/profile/${TEST_USER_1_ID}" "{
    \"name\": \"${NEW_NAME}\"
}")

echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "name"; then
    UPDATED_NAME=$(json_get "$RESPONSE" "name")

    if [ "$UPDATED_NAME" = "$NEW_NAME" ]; then
        print_success "Profile updated successfully"
        test_result 0
    else
        print_error "Updated name doesn't match: expected '$NEW_NAME', got '$UPDATED_NAME'"
        test_result 1
    fi
else
    print_error "Failed to update profile"
    test_result 1
fi
echo ""

# ============================================================================
# Test 5: Update Account Preferences
# ============================================================================
print_section "Test 5: Update Account Preferences"
echo "PUT ${API_PATH}/preferences/${TEST_USER_1_ID}"

RESPONSE=$(api_put "/preferences/${TEST_USER_1_ID}" "{
    \"theme\": \"dark\",
    \"language\": \"en\",
    \"timezone\": \"UTC\",
    \"notification_email\": true,
    \"notification_push\": false
}")

echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "Preferences updated successfully"; then
    print_success "Preferences updated"

    # Verify preferences by getting profile
    echo ""
    echo "Verifying preferences in profile:"
    PROFILE=$(api_get "/profile/${TEST_USER_1_ID}")
    echo "$PROFILE" | json_pretty | grep -A 10 "preferences"

    if echo "$PROFILE" | grep -q '"theme".*"dark"'; then
        print_success "Preferences verified in profile"
        test_result 0
    else
        print_error "Preferences not found in profile"
        test_result 1
    fi
else
    print_error "Failed to update preferences"
    test_result 1
fi
echo ""

# ============================================================================
# Test 6: Get Account by Email
# ============================================================================
print_section "Test 6: Get Account by Email"
echo "GET ${API_PATH}/by-email/${TEST_USER_1_EMAIL}"

RESPONSE=$(api_get "/by-email/${TEST_USER_1_EMAIL}")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "user_id"; then
    USER_ID=$(json_get "$RESPONSE" "user_id")
    EMAIL=$(json_get "$RESPONSE" "email")

    if [ "$USER_ID" = "$TEST_USER_1_ID" ] && [ "$EMAIL" = "$TEST_USER_1_EMAIL" ]; then
        print_success "Account found by email"
        test_result 0
    else
        print_error "Account data doesn't match"
        test_result 1
    fi
else
    print_error "Failed to get account by email"
    test_result 1
fi
echo ""

# ============================================================================
# Test 7: List Accounts with Pagination
# ============================================================================
print_section "Test 7: List Accounts with Pagination"
echo "GET ${API_PATH}?page=1&page_size=10"

# Create second test user first
api_post "/ensure" "{
    \"user_id\": \"${TEST_USER_2_ID}\",
    \"email\": \"${TEST_USER_2_EMAIL}\",
    \"name\": \"${TEST_USER_2_NAME}\"
}" > /dev/null

RESPONSE=$(api_get "?page=1&page_size=10")
echo "$RESPONSE" | json_pretty | head -40

if json_has "$RESPONSE" "accounts"; then
    # Extract account count using Python
    ACCOUNT_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('accounts', [])))" 2>/dev/null)

    if [ "$ACCOUNT_COUNT" -ge 1 ]; then
        print_success "Listed $ACCOUNT_COUNT accounts"
        test_result 0
    else
        print_error "No accounts returned"
        test_result 1
    fi
else
    print_error "Failed to list accounts"
    test_result 1
fi
echo ""

# ============================================================================
# Test 8: Search Accounts
# ============================================================================
print_section "Test 8: Search Accounts"

# Create a user with a unique searchable name
api_post "/ensure" "{
    \"user_id\": \"${TEST_USER_SEARCH_ID}\",
    \"email\": \"${TEST_USER_SEARCH_EMAIL}\",
    \"name\": \"${TEST_USER_SEARCH_NAME}\"
}" > /dev/null

echo "GET ${API_PATH}/search?query=${TEST_USER_SEARCH_NAME}&limit=10"

RESPONSE=$(api_get "/search?query=${TEST_USER_SEARCH_NAME}&limit=10")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q '\['; then
    # Check if response is an array with at least one result
    RESULT_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)

    if [ "$RESULT_COUNT" -ge 1 ]; then
        print_success "Search returned $RESULT_COUNT result(s)"

        # Verify the search result contains our test user
        if echo "$RESPONSE" | grep -q "$TEST_USER_SEARCH_ID"; then
            print_success "Search found the correct user"
            test_result 0
        else
            print_error "Search didn't find the expected user"
            test_result 1
        fi
    else
        print_error "Search returned no results"
        test_result 1
    fi
else
    print_error "Search failed - invalid response format"
    test_result 1
fi
echo ""

# ============================================================================
# Test 9: Account Service Statistics
# ============================================================================
print_section "Test 9: Account Service Statistics"
echo "GET ${API_PATH}/stats"

RESPONSE=$(api_get "/stats")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "total_accounts"; then
    TOTAL_ACCOUNTS=$(json_get "$RESPONSE" "total_accounts")
    ACTIVE_ACCOUNTS=$(json_get "$RESPONSE" "active_accounts")

    # Verify stats are numeric
    if echo "$TOTAL_ACCOUNTS" | grep -E -q '^[0-9]+$'; then
        print_success "Total accounts: $TOTAL_ACCOUNTS, Active: $ACTIVE_ACCOUNTS"
        test_result 0
    else
        print_error "Invalid stats format"
        test_result 1
    fi
else
    print_error "Failed to get stats"
    test_result 1
fi
echo ""

# ============================================================================
# Test 10: Change Account Status (Admin Operation)
# ============================================================================
print_section "Test 10: Change Account Status"
echo "PUT ${API_PATH}/status/${TEST_USER_2_ID}"

# Deactivate account
echo "Deactivating account..."
RESPONSE=$(api_put "/status/${TEST_USER_2_ID}" "{
    \"is_active\": false,
    \"reason\": \"E2E test deactivation\"
}")

echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "deactivated successfully"; then
    print_success "Account deactivated"

    # Verify status change by getting profile
    echo ""
    echo "Verifying account status:"
    PROFILE=$(api_get "/profile/${TEST_USER_2_ID}")
    IS_ACTIVE=$(json_get "$PROFILE" "is_active")

    if [ "$IS_ACTIVE" = "False" ] || [ "$IS_ACTIVE" = "false" ]; then
        print_success "Account status verified as inactive"

        # Reactivate account
        echo ""
        echo "Reactivating account..."
        RESPONSE_2=$(api_put "/status/${TEST_USER_2_ID}" "{
            \"is_active\": true,
            \"reason\": \"E2E test reactivation\"
        }")

        if echo "$RESPONSE_2" | grep -q "activated successfully"; then
            print_success "Account reactivated"
            test_result 0
        else
            print_error "Failed to reactivate account"
            test_result 1
        fi
    else
        print_error "Account status not changed"
        test_result 1
    fi
else
    print_error "Failed to deactivate account"
    test_result 1
fi
echo ""

# ============================================================================
# Test 11: Error Handling - Invalid Email
# ============================================================================
print_section "Test 11: Error Handling - Invalid Email"
echo "POST ${API_PATH}/ensure (with invalid email)"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${API_BASE}/ensure" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"invalid_user\",\"email\":\"invalid-email\",\"name\":\"Test\"}")

if [ "$HTTP_CODE" = "400" ]; then
    print_success "Correctly rejected invalid email with HTTP 400"
    test_result 0
else
    print_error "Expected HTTP 400, got HTTP $HTTP_CODE"
    test_result 1
fi
echo ""

# ============================================================================
# Test 12: Error Handling - Non-existent User
# ============================================================================
print_section "Test 12: Error Handling - Non-existent User"
echo "GET ${API_PATH}/profile/nonexistent_user_${UNIQUE_SUFFIX}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    "${API_BASE}/profile/nonexistent_user_${UNIQUE_SUFFIX}")

if [ "$HTTP_CODE" = "404" ]; then
    print_success "Correctly returned HTTP 404 for non-existent user"
    test_result 0
else
    print_error "Expected HTTP 404, got HTTP $HTTP_CODE"
    test_result 1
fi
echo ""

# ============================================================================
# Test 13: Delete Account (Soft Delete)
# ============================================================================
print_section "Test 13: Delete Account (Soft Delete)"
echo "DELETE ${API_PATH}/profile/${TEST_USER_SEARCH_ID}"

RESPONSE=$(api_delete "/profile/${TEST_USER_SEARCH_ID}?reason=E2E+test+cleanup")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "deleted successfully"; then
    print_success "Account deleted successfully"

    # Verify account is deleted (should return 404 or show as deleted)
    echo ""
    echo "Verifying account deletion:"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        "${API_BASE}/profile/${TEST_USER_SEARCH_ID}")

    # Account might be soft-deleted or return 404
    if [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "200" ]; then
        print_success "Account deletion verified (HTTP $HTTP_CODE)"
        test_result 0
    else
        print_error "Unexpected HTTP code after deletion: $HTTP_CODE"
        test_result 1
    fi
else
    print_error "Failed to delete account"
    test_result 1
fi
echo ""

# ============================================================================
# Cleanup
# ============================================================================
print_info "Cleaning up test accounts..."

# Clean up test users (soft delete if they exist)
for USER_ID in "$TEST_USER_1_ID" "$TEST_USER_2_ID"; do
    api_delete "/profile/${USER_ID}?reason=E2E+test+cleanup" > /dev/null 2>&1 || true
done

print_success "Cleanup completed"
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
