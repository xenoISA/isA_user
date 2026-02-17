#!/bin/bash
# Account Service Test Script (v2 - using test_common.sh)
# Usage:
#   ./account_test_v2.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./account_test_v2.sh  # Gateway mode with JWT

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

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"
TEST_EMAIL="test_${TEST_TS}@example.com"
TEST_USER_ID="test_user_${TEST_TS}"

print_info "Test User ID: $TEST_USER_ID"
print_info "Test Email: $TEST_EMAIL"
echo ""

# ============================================================================
# BASIC FUNCTIONALITY TESTS
# ============================================================================

# Test 1: Get Service Stats
print_section "Test 1: Get Account Service Statistics"
echo "GET ${API_PATH}/stats"
RESPONSE=$(api_get "/stats")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "total_accounts"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Ensure Account (Create)
print_section "Test 2: Ensure Account (Create New)"
echo "POST ${API_PATH}/ensure"
print_info "Expected Event: user.created"

PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"email\":\"${TEST_EMAIL}\",\"name\":\"Test User Account\",\"subscription_plan\":\"free\"}"
RESPONSE=$(api_post "/ensure" "$PAYLOAD")
echo "$RESPONSE" | json_pretty

RETURNED_USER_ID=$(json_get "$RESPONSE" "user_id")
if [ -n "$RETURNED_USER_ID" ] && echo "$RESPONSE" | grep -q "$TEST_EMAIL"; then
    print_success "Created user: $RETURNED_USER_ID"
    test_result 0
else
    print_error "Failed to create user"
    test_result 1
fi
echo ""

# Test 3: Get Account Profile
print_section "Test 3: Get Account Profile"
echo "GET ${API_PATH}/profile/${TEST_USER_ID}"
RESPONSE=$(api_get "/profile/${TEST_USER_ID}")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "$TEST_USER_ID" && echo "$RESPONSE" | grep -q "$TEST_EMAIL"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 4: Update Account Profile
print_section "Test 4: Update Account Profile"
echo "PUT ${API_PATH}/profile/${TEST_USER_ID}"
print_info "Expected Event: user.profile_updated"

UPDATE_EMAIL="updated_${TEST_TS}@example.com"
UPDATE_PAYLOAD="{\"name\":\"Updated Test User\",\"email\":\"${UPDATE_EMAIL}\"}"
RESPONSE=$(api_put "/profile/${TEST_USER_ID}" "$UPDATE_PAYLOAD")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "Updated Test User" && echo "$RESPONSE" | grep -q "$UPDATE_EMAIL"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 5: Update Account Preferences
print_section "Test 5: Update Account Preferences"
echo "PUT ${API_PATH}/preferences/${TEST_USER_ID}"

PREFS_PAYLOAD='{"timezone":"America/New_York","language":"en","notification_email":true,"notification_push":false,"theme":"dark"}'
RESPONSE=$(api_put "/preferences/${TEST_USER_ID}" "$PREFS_PAYLOAD")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "Preferences updated successfully" || json_has "$RESPONSE" "message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 6: Verify Preferences Were Saved
print_section "Test 6: Verify Preferences Were Saved"
echo "GET ${API_PATH}/profile/${TEST_USER_ID}"
RESPONSE=$(api_get "/profile/${TEST_USER_ID}")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "America/New_York" && echo "$RESPONSE" | grep -q "dark"; then
    test_result 0
else
    test_result 1
fi
echo ""

# ============================================================================
# SEARCH AND QUERY TESTS
# ============================================================================

# Test 7: List Accounts (Paginated)
print_section "Test 7: List Accounts (Paginated)"
echo "GET ${API_PATH}?page=1&page_size=5"
RESPONSE=$(api_get "?page=1&page_size=5")
echo "$RESPONSE" | json_pretty | head -30

if json_has "$RESPONSE" "accounts" && json_has "$RESPONSE" "total_count"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 8: Search Accounts
print_section "Test 8: Search Accounts"
echo "GET ${API_PATH}/search?query=test&limit=10"
RESPONSE=$(api_get "/search?query=test&limit=10")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q "\["; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 9: Get Account by Email
print_section "Test 9: Get Account by Email"
echo "GET ${API_PATH}/by-email/${UPDATE_EMAIL}"
RESPONSE=$(api_get "/by-email/${UPDATE_EMAIL}")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "$TEST_USER_ID" && echo "$RESPONSE" | grep -q "$UPDATE_EMAIL"; then
    test_result 0
else
    test_result 1
fi
echo ""

# ============================================================================
# ACCOUNT STATUS MANAGEMENT TESTS
# ============================================================================

# Test 10: Change Account Status (Deactivate)
print_section "Test 10: Change Account Status (Deactivate)"
echo "PUT ${API_PATH}/status/${TEST_USER_ID}"
print_info "Expected Event: user.status_changed"

STATUS_PAYLOAD='{"is_active":false,"reason":"Testing account status change"}'
RESPONSE=$(api_put "/status/${TEST_USER_ID}" "$STATUS_PAYLOAD")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "deactivated successfully" || json_has "$RESPONSE" "message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 11: Verify Account is Deactivated
print_section "Test 11: Verify Account is Deactivated"
echo "GET ${API_PATH}/profile/${TEST_USER_ID}"
RESPONSE=$(api_get "/profile/${TEST_USER_ID}")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -qi "not found" || echo "$RESPONSE" | grep -q "404"; then
    print_success "Correctly filters out deactivated account"
    test_result 0
else
    print_error "Should not return deactivated account"
    test_result 1
fi
echo ""

# Test 12: Reactivate Account
print_section "Test 12: Reactivate Account"
echo "PUT ${API_PATH}/status/${TEST_USER_ID}"
print_info "Expected Event: user.status_changed"

REACTIVATE_PAYLOAD='{"is_active":true,"reason":"Reactivating for cleanup"}'
RESPONSE=$(api_put "/status/${TEST_USER_ID}" "$REACTIVATE_PAYLOAD")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "activated successfully" || json_has "$RESPONSE" "message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 13: Delete Account (Soft Delete)
print_section "Test 13: Delete Account (Soft Delete)"
echo "DELETE ${API_PATH}/profile/${TEST_USER_ID}?reason=Test cleanup"
print_info "Expected Event: user.deleted"

RESPONSE=$(api_delete "/profile/${TEST_USER_ID}?reason=Test%20cleanup")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "deleted successfully" || json_has "$RESPONSE" "message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
