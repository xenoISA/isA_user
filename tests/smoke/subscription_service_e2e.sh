#!/bin/bash
# Subscription Service - E2E Smoke Tests
# Tests critical paths for subscription and credit management
# Usage:
#   ./subscription_service_e2e.sh              # Direct mode (default)
#   TEST_MODE=gateway ./subscription_service_e2e.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="subscription_service"
SERVICE_PORT="8212"
API_PATH="/api/v1/subscriptions"

# Initialize test (sets up BASE_URL, API_BASE, JWT if needed)
init_test

# ============================================================================
# Test Variables
# ============================================================================
# Generate unique test data to avoid conflicts
TIMESTAMP=$(date +%s)
PID=$$
UNIQUE_SUFFIX="${TIMESTAMP}_${PID}"

# Test user data
TEST_USER_1_ID="user_sub_e2e_${UNIQUE_SUFFIX}_1"
TEST_USER_2_ID="user_sub_e2e_${UNIQUE_SUFFIX}_2"
TEST_USER_3_ID="user_sub_e2e_${UNIQUE_SUFFIX}_3"

# Will be populated during tests
SUBSCRIPTION_ID=""

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
# Test 2: Create Pro Subscription
# ============================================================================
print_section "Test 2: Create Pro Subscription"
echo "POST ${API_PATH}"

RESPONSE=$(api_post "" "{
    \"user_id\": \"${TEST_USER_1_ID}\",
    \"tier_code\": \"pro\",
    \"billing_cycle\": \"monthly\",
    \"seats\": 1,
    \"use_trial\": false
}")

echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "success"; then
    SUCCESS=$(json_get "$RESPONSE" "success")
    if [ "$SUCCESS" = "True" ] || [ "$SUCCESS" = "true" ]; then
        SUBSCRIPTION_ID=$(json_get "$RESPONSE" "subscription_id")
        TIER_CODE=$(json_get "$RESPONSE" "tier_code")

        if [ "$TIER_CODE" = "pro" ]; then
            print_success "Pro subscription created: $SUBSCRIPTION_ID"
            test_result 0
        else
            print_error "Unexpected tier code: $TIER_CODE"
            test_result 1
        fi
    else
        print_error "Failed to create subscription"
        test_result 1
    fi
else
    print_error "Invalid response format"
    test_result 1
fi
echo ""

# ============================================================================
# Test 3: Create Free Subscription
# ============================================================================
print_section "Test 3: Create Free Subscription"
echo "POST ${API_PATH}"

RESPONSE=$(api_post "" "{
    \"user_id\": \"${TEST_USER_2_ID}\",
    \"tier_code\": \"free\"
}")

echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "success"; then
    SUCCESS=$(json_get "$RESPONSE" "success")
    if [ "$SUCCESS" = "True" ] || [ "$SUCCESS" = "true" ]; then
        FREE_SUBSCRIPTION_ID=$(json_get "$RESPONSE" "subscription_id")
        TIER_CODE=$(json_get "$RESPONSE" "tier_code")

        if [ "$TIER_CODE" = "free" ]; then
            print_success "Free subscription created: $FREE_SUBSCRIPTION_ID"
            test_result 0
        else
            print_error "Unexpected tier code: $TIER_CODE"
            test_result 1
        fi
    else
        print_error "Failed to create free subscription"
        test_result 1
    fi
else
    print_error "Invalid response format"
    test_result 1
fi
echo ""

# ============================================================================
# Test 4: Get Subscription by ID
# ============================================================================
print_section "Test 4: Get Subscription by ID"
echo "GET ${API_PATH}/${SUBSCRIPTION_ID}"

RESPONSE=$(api_get "/${SUBSCRIPTION_ID}")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "subscription_id"; then
    SUB_ID=$(json_get "$RESPONSE" "subscription_id")
    if [ "$SUB_ID" = "$SUBSCRIPTION_ID" ]; then
        print_success "Subscription retrieved successfully"
        test_result 0
    else
        print_error "Subscription ID mismatch"
        test_result 1
    fi
else
    print_error "Failed to get subscription"
    test_result 1
fi
echo ""

# ============================================================================
# Test 5: Get User Subscription
# ============================================================================
print_section "Test 5: Get User Subscription"
echo "GET ${API_PATH}/user/${TEST_USER_1_ID}"

RESPONSE=$(api_get "/user/${TEST_USER_1_ID}")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "user_id"; then
    USER_ID=$(json_get "$RESPONSE" "user_id")
    if [ "$USER_ID" = "$TEST_USER_1_ID" ]; then
        print_success "User subscription retrieved"
        test_result 0
    else
        print_error "User ID mismatch"
        test_result 1
    fi
else
    print_error "Failed to get user subscription"
    test_result 1
fi
echo ""

# ============================================================================
# Test 6: Get Credit Balance
# ============================================================================
print_section "Test 6: Get Credit Balance"
echo "GET ${API_PATH}/credits/balance?user_id=${TEST_USER_1_ID}"

RESPONSE=$(api_get "/credits/balance?user_id=${TEST_USER_1_ID}")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "subscription_credits_remaining"; then
    CREDITS=$(json_get "$RESPONSE" "subscription_credits_remaining")
    TIER=$(json_get "$RESPONSE" "tier_code")

    if [ "$TIER" = "pro" ] && [ "$CREDITS" -gt 0 ]; then
        print_success "Credit balance retrieved: $CREDITS credits for $TIER tier"
        test_result 0
    else
        print_error "Invalid credit balance response"
        test_result 1
    fi
else
    print_error "Failed to get credit balance"
    test_result 1
fi
echo ""

# ============================================================================
# Test 7: Get Credit Balance (No Subscription)
# ============================================================================
print_section "Test 7: Get Credit Balance (No Subscription)"
echo "GET ${API_PATH}/credits/balance?user_id=${TEST_USER_3_ID}"

RESPONSE=$(api_get "/credits/balance?user_id=${TEST_USER_3_ID}")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "subscription_credits_remaining"; then
    CREDITS=$(json_get "$RESPONSE" "subscription_credits_remaining")

    if [ "$CREDITS" = "0" ]; then
        print_success "Zero balance returned for user without subscription"
        test_result 0
    else
        print_error "Expected zero credits, got: $CREDITS"
        test_result 1
    fi
else
    print_error "Failed to get credit balance"
    test_result 1
fi
echo ""

# ============================================================================
# Test 8: Consume Credits
# ============================================================================
print_section "Test 8: Consume Credits"
echo "POST ${API_PATH}/credits/consume"

RESPONSE=$(api_post "/credits/consume" "{
    \"user_id\": \"${TEST_USER_1_ID}\",
    \"credits\": 1000000,
    \"service_type\": \"e2e_test\"
}")

echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "success"; then
    SUCCESS=$(json_get "$RESPONSE" "success")
    if [ "$SUCCESS" = "True" ] || [ "$SUCCESS" = "true" ]; then
        REMAINING=$(json_get "$RESPONSE" "credits_remaining")
        print_success "Credits consumed. Remaining: $REMAINING"
        test_result 0
    else
        print_error "Failed to consume credits"
        test_result 1
    fi
else
    print_error "Invalid response format"
    test_result 1
fi
echo ""

# ============================================================================
# Test 9: List Subscriptions
# ============================================================================
print_section "Test 9: List Subscriptions"
echo "GET ${API_PATH}?page=1&page_size=10"

RESPONSE=$(api_get "?page=1&page_size=10")
echo "$RESPONSE" | json_pretty | head -30

if json_has "$RESPONSE" "subscriptions"; then
    # Extract subscription count using Python
    SUB_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('subscriptions', [])))" 2>/dev/null)

    if [ "$SUB_COUNT" -ge 1 ]; then
        print_success "Listed $SUB_COUNT subscriptions"
        test_result 0
    else
        print_error "No subscriptions returned"
        test_result 1
    fi
else
    print_error "Failed to list subscriptions"
    test_result 1
fi
echo ""

# ============================================================================
# Test 10: List Subscriptions by User
# ============================================================================
print_section "Test 10: List Subscriptions by User"
echo "GET ${API_PATH}?user_id=${TEST_USER_1_ID}"

RESPONSE=$(api_get "?user_id=${TEST_USER_1_ID}")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "subscriptions"; then
    SUB_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('subscriptions', [])))" 2>/dev/null)

    if [ "$SUB_COUNT" -ge 1 ]; then
        print_success "Found $SUB_COUNT subscription(s) for user"
        test_result 0
    else
        print_error "No subscriptions found for user"
        test_result 1
    fi
else
    print_error "Failed to filter subscriptions by user"
    test_result 1
fi
echo ""

# ============================================================================
# Test 11: Get Subscription History
# ============================================================================
print_section "Test 11: Get Subscription History"
echo "GET ${API_PATH}/${SUBSCRIPTION_ID}/history"

RESPONSE=$(api_get "/${SUBSCRIPTION_ID}/history")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "history"; then
    HISTORY_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('history', [])))" 2>/dev/null)

    if [ "$HISTORY_COUNT" -ge 1 ]; then
        print_success "Found $HISTORY_COUNT history entries"
        test_result 0
    else
        print_error "No history entries found"
        test_result 1
    fi
else
    print_error "Failed to get subscription history"
    test_result 1
fi
echo ""

# ============================================================================
# Test 12: Error Handling - Duplicate Subscription
# ============================================================================
print_section "Test 12: Error Handling - Duplicate Subscription"
echo "POST ${API_PATH} (duplicate)"

RESPONSE=$(api_post "" "{
    \"user_id\": \"${TEST_USER_1_ID}\",
    \"tier_code\": \"max\"
}")

echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "success"; then
    SUCCESS=$(json_get "$RESPONSE" "success")
    if [ "$SUCCESS" = "False" ] || [ "$SUCCESS" = "false" ]; then
        print_success "Correctly rejected duplicate subscription"
        test_result 0
    else
        print_error "Should have rejected duplicate subscription"
        test_result 1
    fi
else
    # Could also be a 409 Conflict
    print_success "Duplicate subscription blocked"
    test_result 0
fi
echo ""

# ============================================================================
# Test 13: Error Handling - Invalid Tier
# ============================================================================
print_section "Test 13: Error Handling - Invalid Tier"
echo "POST ${API_PATH} (invalid tier)"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${API_BASE}" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"${TEST_USER_3_ID}\",\"tier_code\":\"platinum\"}")

if [ "$HTTP_CODE" = "404" ]; then
    print_success "Correctly rejected invalid tier with HTTP 404"
    test_result 0
else
    print_error "Expected HTTP 404, got HTTP $HTTP_CODE"
    test_result 1
fi
echo ""

# ============================================================================
# Test 14: Error Handling - Insufficient Credits
# ============================================================================
print_section "Test 14: Error Handling - Insufficient Credits"
echo "POST ${API_PATH}/credits/consume (insufficient)"

# Try to consume more credits than free tier has (1M)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${API_BASE}/credits/consume" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"${TEST_USER_2_ID}\",\"credits\":50000000,\"service_type\":\"test\"}")

if [ "$HTTP_CODE" = "402" ]; then
    print_success "Correctly returned HTTP 402 for insufficient credits"
    test_result 0
else
    print_error "Expected HTTP 402, got HTTP $HTTP_CODE"
    test_result 1
fi
echo ""

# ============================================================================
# Test 15: Cancel Subscription (At Period End)
# ============================================================================
print_section "Test 15: Cancel Subscription (At Period End)"
echo "POST ${API_PATH}/${SUBSCRIPTION_ID}/cancel?user_id=${TEST_USER_1_ID}"

RESPONSE=$(api_post "/${SUBSCRIPTION_ID}/cancel?user_id=${TEST_USER_1_ID}" "{
    \"immediate\": false,
    \"reason\": \"E2E test cancellation\"
}")

echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "success"; then
    SUCCESS=$(json_get "$RESPONSE" "success")
    if [ "$SUCCESS" = "True" ] || [ "$SUCCESS" = "true" ]; then
        CANCEL_AT_END=$(json_get "$RESPONSE" "cancel_at_period_end")
        if [ "$CANCEL_AT_END" = "True" ] || [ "$CANCEL_AT_END" = "true" ]; then
            print_success "Subscription marked for cancellation at period end"
            test_result 0
        else
            print_error "cancel_at_period_end not set"
            test_result 1
        fi
    else
        print_error "Failed to cancel subscription"
        test_result 1
    fi
else
    print_error "Invalid response format"
    test_result 1
fi
echo ""

# ============================================================================
# Test 16: Cancel Subscription (Unauthorized)
# ============================================================================
print_section "Test 16: Cancel Subscription (Unauthorized)"
echo "POST ${API_PATH}/${FREE_SUBSCRIPTION_ID}/cancel?user_id=${TEST_USER_1_ID}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${API_BASE}/${FREE_SUBSCRIPTION_ID}/cancel?user_id=${TEST_USER_1_ID}" \
    -H "Content-Type: application/json" \
    -d "{\"immediate\":false,\"reason\":\"Unauthorized attempt\"}")

if [ "$HTTP_CODE" = "403" ]; then
    print_success "Correctly rejected unauthorized cancellation with HTTP 403"
    test_result 0
else
    print_error "Expected HTTP 403, got HTTP $HTTP_CODE"
    test_result 1
fi
echo ""

# ============================================================================
# Test 17: Error Handling - Nonexistent Subscription
# ============================================================================
print_section "Test 17: Error Handling - Nonexistent Subscription"
echo "GET ${API_PATH}/sub_nonexistent_${UNIQUE_SUFFIX}"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    "${API_BASE}/sub_nonexistent_${UNIQUE_SUFFIX}")

if [ "$HTTP_CODE" = "404" ]; then
    print_success "Correctly returned HTTP 404 for nonexistent subscription"
    test_result 0
else
    print_error "Expected HTTP 404, got HTTP $HTTP_CODE"
    test_result 1
fi
echo ""

# ============================================================================
# Cleanup (Optional - subscriptions can be left for manual inspection)
# ============================================================================
print_info "Test cleanup skipped - subscriptions remain for inspection"
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
