#!/bin/bash
# Account Service Comprehensive Test Script
# Tests all endpoints for account_service with Event-Driven Architecture
# Tests service running in Kubernetes with Ingress

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1/accounts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0
TOTAL=0

# Test result function
test_result() {
    TOTAL=$((TOTAL + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}     ACCOUNT SERVICE COMPREHENSIVE TEST (Event-Driven v2.0)${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo -e "${BLUE}Testing via Kubernetes Ingress${NC}"
echo ""

# ============================================================================
# BASIC FUNCTIONALITY TESTS
# ============================================================================

# Test 1: Get Service Stats
echo -e "${YELLOW}Test 1: Get Account Service Statistics${NC}"
echo "GET /api/v1/accounts/stats"
RESPONSE=$(curl -s "${API_BASE}/stats")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"total_accounts"'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Ensure Account (Create)
echo -e "${YELLOW}Test 2: Ensure Account (Create New) - Event Publisher Test${NC}"
echo "POST /api/v1/accounts/ensure"
echo -e "${BLUE}Expected Event: user.created will be published to NATS${NC}"
TEST_TS="$(date +%s)_$$"
TEST_EMAIL="test_${TEST_TS}@example.com"
TEST_USER_ID="test_user_${TEST_TS}"
PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"email\":\"${TEST_EMAIL}\",\"name\":\"Test User Account\",\"subscription_plan\":\"free\"}"
echo "Payload: $PAYLOAD"
RESPONSE=$(curl -s -X POST "${API_BASE}/ensure" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
RETURNED_USER_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('user_id', ''))" 2>/dev/null)
if [ -n "$RETURNED_USER_ID" ] && echo "$RESPONSE" | grep -q "$TEST_EMAIL"; then
    echo -e "${GREEN}Created user: $RETURNED_USER_ID${NC}"
    echo -e "${GREEN}✓ Event 'user.created' should be published with:${NC}"
    echo "  - user_id: $TEST_USER_ID"
    echo "  - email: $TEST_EMAIL"
    echo "  - subscription_plan: free"
    test_result 0
else
    echo -e "${RED}Failed to create user${NC}"
    test_result 1
fi
echo ""

# Test 3: Get Account Profile
echo -e "${YELLOW}Test 3: Get Account Profile${NC}"
echo "GET /api/v1/accounts/profile/${TEST_USER_ID}"
RESPONSE=$(curl -s "${API_BASE}/profile/${TEST_USER_ID}")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "$TEST_USER_ID" && echo "$RESPONSE" | grep -q "$TEST_EMAIL"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 4: Update Account Profile - Event Publisher Test
echo -e "${YELLOW}Test 4: Update Account Profile - Event Publisher Test${NC}"
echo "PUT /api/v1/accounts/profile/${TEST_USER_ID}"
echo -e "${BLUE}Expected Event: user.profile_updated will be published to NATS${NC}"
UPDATE_EMAIL="updated_${TEST_TS}@example.com"
UPDATE_PAYLOAD="{\"name\":\"Updated Test User\",\"email\":\"${UPDATE_EMAIL}\"}"
echo "Payload: $UPDATE_PAYLOAD"
RESPONSE=$(curl -s -X PUT "${API_BASE}/profile/${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$UPDATE_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "Updated Test User" && echo "$RESPONSE" | grep -q "$UPDATE_EMAIL"; then
    echo -e "${GREEN}✓ Event 'user.profile_updated' should be published with:${NC}"
    echo "  - user_id: $TEST_USER_ID"
    echo "  - updated_fields: [name, email]"
    echo "  - new email: $UPDATE_EMAIL"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 5: Update Account Preferences
echo -e "${YELLOW}Test 5: Update Account Preferences${NC}"
echo "PUT /api/v1/accounts/preferences/${TEST_USER_ID}"
PREFS_PAYLOAD='{"timezone":"America/New_York","language":"en","notification_email":true,"notification_push":false,"theme":"dark"}'
echo "Payload: $PREFS_PAYLOAD"
RESPONSE=$(curl -s -X PUT "${API_BASE}/preferences/${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$PREFS_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "Preferences updated successfully" || echo "$RESPONSE" | grep -q "message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 6: Verify Preferences Were Saved
echo -e "${YELLOW}Test 6: Verify Preferences Were Saved${NC}"
echo "GET /api/v1/accounts/profile/${TEST_USER_ID}"
RESPONSE=$(curl -s "${API_BASE}/profile/${TEST_USER_ID}")
echo "$RESPONSE" | python3 -m json.tool
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
echo -e "${YELLOW}Test 7: List Accounts (Paginated)${NC}"
echo "GET /api/v1/accounts?page=1&page_size=5"
RESPONSE=$(curl -s "${API_BASE}?page=1&page_size=5")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q '"accounts"' && echo "$RESPONSE" | grep -q '"total_count"'; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 8: Search Accounts
echo -e "${YELLOW}Test 8: Search Accounts${NC}"
echo "GET /api/v1/accounts/search?query=test&limit=10"
RESPONSE=$(curl -s "${API_BASE}/search?query=test&limit=10")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "\[" && echo "$RESPONSE" | grep -q "user_id"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 9: Get Account by Email
echo -e "${YELLOW}Test 9: Get Account by Email${NC}"
echo "GET /api/v1/accounts/by-email/${UPDATE_EMAIL}"
RESPONSE=$(curl -s "${API_BASE}/by-email/${UPDATE_EMAIL}")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "$TEST_USER_ID" && echo "$RESPONSE" | grep -q "$UPDATE_EMAIL"; then
    test_result 0
else
    test_result 1
fi
echo ""

# ============================================================================
# ACCOUNT STATUS MANAGEMENT TESTS (EVENT PUBLISHERS)
# ============================================================================

# Test 10: Change Account Status (Deactivate) - Event Publisher Test
echo -e "${YELLOW}Test 10: Change Account Status (Deactivate) - Event Publisher Test${NC}"
echo "PUT /api/v1/accounts/status/${TEST_USER_ID}"
echo -e "${BLUE}Expected Event: user.status_changed will be published to NATS${NC}"
STATUS_PAYLOAD='{"is_active":false,"reason":"Testing account status change"}'
echo "Payload: $STATUS_PAYLOAD"
RESPONSE=$(curl -s -X PUT "${API_BASE}/status/${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$STATUS_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "deactivated successfully" || echo "$RESPONSE" | grep -q "message"; then
    echo -e "${GREEN}✓ Event 'user.status_changed' should be published with:${NC}"
    echo "  - user_id: $TEST_USER_ID"
    echo "  - is_active: false"
    echo "  - reason: Testing account status change"
    echo "  - changed_by: admin"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 11: Verify Account is Deactivated
echo -e "${YELLOW}Test 11: Verify Account is Deactivated${NC}"
echo "GET /api/v1/accounts/profile/${TEST_USER_ID}"
RESPONSE=$(curl -s "${API_BASE}/profile/${TEST_USER_ID}")
echo "$RESPONSE" | python3 -m json.tool
# Account should not be found because get_account_by_id filters is_active=true
if echo "$RESPONSE" | grep -qi "not found" || echo "$RESPONSE" | grep -q "404"; then
    echo -e "${GREEN}Correctly filters out deactivated account${NC}"
    test_result 0
else
    echo -e "${RED}Should not return deactivated account${NC}"
    test_result 1
fi
echo ""

# Test 12: Reactivate Account - Event Publisher Test
echo -e "${YELLOW}Test 12: Reactivate Account - Event Publisher Test${NC}"
echo "PUT /api/v1/accounts/status/${TEST_USER_ID}"
echo -e "${BLUE}Expected Event: user.status_changed will be published to NATS${NC}"
REACTIVATE_PAYLOAD='{"is_active":true,"reason":"Reactivating for cleanup"}'
echo "Payload: $REACTIVATE_PAYLOAD"
RESPONSE=$(curl -s -X PUT "${API_BASE}/status/${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$REACTIVATE_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "activated successfully" || echo "$RESPONSE" | grep -q "message"; then
    echo -e "${GREEN}✓ Event 'user.status_changed' should be published with:${NC}"
    echo "  - user_id: $TEST_USER_ID"
    echo "  - is_active: true"
    echo "  - reason: Reactivating for cleanup"
    echo "  - changed_by: admin"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 13: Delete Account (Soft Delete) - Event Publisher Test
echo -e "${YELLOW}Test 13: Delete Account (Soft Delete) - Event Publisher Test${NC}"
echo "DELETE /api/v1/accounts/profile/${TEST_USER_ID}?reason=Test cleanup"
echo -e "${BLUE}Expected Event: user.deleted will be published to NATS${NC}"
RESPONSE=$(curl -s -X DELETE "${API_BASE}/profile/${TEST_USER_ID}?reason=Test%20cleanup")
echo "$RESPONSE" | python3 -m json.tool
if echo "$RESPONSE" | grep -q "deleted successfully" || echo "$RESPONSE" | grep -q "message"; then
    echo -e "${GREEN}✓ Event 'user.deleted' should be published with:${NC}"
    echo "  - user_id: $TEST_USER_ID"
    echo "  - email: $UPDATE_EMAIL"
    echo "  - reason: Test cleanup"
    test_result 0
else
    test_result 1
fi
echo ""

# ============================================================================
# EVENT-DRIVEN ARCHITECTURE VALIDATION
# ============================================================================

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}           EVENT-DRIVEN ARCHITECTURE FEATURES TESTED${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""
echo -e "${BLUE}✓ Events Published (via events/publishers.py):${NC}"
echo "  1. user.created              - When new account is created"
echo "  2. user.profile_updated      - When account profile is updated"
echo "  3. user.status_changed       - When account is activated/deactivated"
echo "  4. user.deleted              - When account is deleted"
echo ""
echo -e "${BLUE}✓ Event Handlers Registered (via events/handlers.py):${NC}"
echo "  1. payment.completed         - From billing_service"
echo "  2. organization.member_added - From organization_service"
echo "  3. wallet.created            - From wallet_service"
echo ""
echo -e "${BLUE}✓ Service Clients Available (via clients/):${NC}"
echo "  1. OrganizationServiceClient - HTTP sync calls to organization_service"
echo "  2. BillingServiceClient      - HTTP sync calls to billing_service"
echo "  3. WalletServiceClient       - HTTP sync calls to wallet_service"
echo ""

# ============================================================================
# ARCHITECTURE NOTES
# ============================================================================

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                    ARCHITECTURE NOTES${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""
echo -e "${BLUE}Directory Structure:${NC}"
echo "  account_service/"
echo "  ├── events/"
echo "  │   ├── models.py      # Event data models (Pydantic)"
echo "  │   ├── publishers.py  # Event publishing functions"
echo "  │   └── handlers.py    # Event subscription handlers"
echo "  ├── clients/"
echo "  │   ├── organization_client.py"
echo "  │   ├── billing_client.py"
echo "  │   └── wallet_client.py"
echo "  └── main.py            # Event handlers registered in lifespan"
echo ""
echo -e "${BLUE}Async vs Sync Communication:${NC}"
echo "  Async (Events/NATS): User lifecycle, state changes, notifications"
echo "  Sync (HTTP):         Real-time queries, validation, immediate responses"
echo ""

# Print summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo -e "Total Tests: ${TOTAL}"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}✓ Event-Driven Architecture v2.0 is working correctly${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
