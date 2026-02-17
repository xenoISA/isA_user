#!/bin/bash
# ============================================================================
# Event Service Smoke Test - Subscription Management
# ============================================================================
# Tests subscription management endpoints for the Event Service
# Target: localhost:8230
# Tests: 3 (create subscription, list subscriptions, delete subscription)
# ============================================================================

set -e

# ============================================================================
# Configuration
# ============================================================================
BASE_URL="${EVENT_SERVICE_URL:-http://localhost:8230}"
API_BASE="${BASE_URL}/api/v1/events"
SCRIPT_NAME="event_service_test_subscriptions.sh"
TEST_TS=$(date +%s)

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# Test Counters
# ============================================================================
PASSED=0
FAILED=0
TOTAL=0

# Stored subscription ID for cleanup
CREATED_SUBSCRIPTION_ID=""

# ============================================================================
# Helper Functions
# ============================================================================
print_header() {
    echo ""
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN}  EVENT SERVICE SMOKE TEST - SUBSCRIPTION MANAGEMENT${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${YELLOW}Base URL: ${BASE_URL}${NC}"
    echo -e "${YELLOW}API Base: ${API_BASE}${NC}"
    echo ""
}

print_test() {
    echo -e "${YELLOW}[$1] $2${NC}"
}

test_passed() {
    PASSED=$((PASSED + 1))
    TOTAL=$((TOTAL + 1))
    echo -e "${GREEN}  PASSED${NC}"
}

test_failed() {
    FAILED=$((FAILED + 1))
    TOTAL=$((TOTAL + 1))
    echo -e "${RED}  FAILED: $1${NC}"
}

print_summary() {
    echo ""
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "${CYAN}  TEST SUMMARY${NC}"
    echo -e "${CYAN}============================================================================${NC}"
    echo -e "Total Tests: ${TOTAL}"
    echo -e "${GREEN}Passed: ${PASSED}${NC}"
    echo -e "${RED}Failed: ${FAILED}${NC}"
    echo ""
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}ALL TESTS PASSED${NC}"
        exit 0
    else
        echo -e "${RED}SOME TESTS FAILED${NC}"
        exit 1
    fi
}

extract_json_field() {
    local json="$1"
    local field="$2"
    echo "$json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('$field', ''))" 2>/dev/null || echo ""
}

# ============================================================================
# Tests
# ============================================================================

print_header

# ---------------------------------------------------------------------------
# Test 1: Create Event Subscription
# ---------------------------------------------------------------------------
print_test "1/3" "Create Event Subscription - POST /api/v1/events/subscriptions"

PAYLOAD=$(cat <<EOF
{
    "subscriber_name": "smoke_test_subscriber_${TEST_TS}",
    "subscriber_type": "service",
    "event_types": ["user.created", "user.updated", "smoke_test.*"],
    "event_sources": ["backend", "frontend"],
    "callback_url": "http://localhost:9999/webhook/events",
    "enabled": true,
    "retry_policy": {
        "max_retries": 3,
        "initial_delay_ms": 1000,
        "backoff_multiplier": 2
    }
}
EOF
)

echo "  Request: POST ${API_BASE}/subscriptions"
echo "  Payload: $PAYLOAD"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    "${API_BASE}/subscriptions" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response: $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    CREATED_SUBSCRIPTION_ID=$(extract_json_field "$BODY" "subscription_id")
    if [ -n "$CREATED_SUBSCRIPTION_ID" ] && [ "$CREATED_SUBSCRIPTION_ID" != "null" ]; then
        echo "  Created Subscription ID: $CREATED_SUBSCRIPTION_ID"
        test_passed
    else
        test_failed "Response does not contain subscription_id"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 2: List Event Subscriptions
# ---------------------------------------------------------------------------
print_test "2/3" "List Event Subscriptions - GET /api/v1/events/subscriptions"

echo "  Request: GET ${API_BASE}/subscriptions"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    "${API_BASE}/subscriptions" 2>/dev/null)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "  HTTP Status: $HTTP_CODE"
echo "  Response (truncated): ${BODY:0:500}..."

if [ "$HTTP_CODE" = "200" ]; then
    # Response should be an array
    if echo "$BODY" | grep -q '\['; then
        # Count subscriptions
        COUNT=$(echo "$BODY" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
        echo "  Found $COUNT subscriptions"
        test_passed
    else
        test_failed "Response should be an array"
    fi
else
    test_failed "Expected HTTP 200, got $HTTP_CODE"
fi

# ---------------------------------------------------------------------------
# Test 3: Delete Event Subscription
# ---------------------------------------------------------------------------
print_test "3/3" "Delete Event Subscription - DELETE /api/v1/events/subscriptions/{id}"

if [ -z "$CREATED_SUBSCRIPTION_ID" ] || [ "$CREATED_SUBSCRIPTION_ID" = "null" ]; then
    echo "  Skipping: No subscription ID from previous test"
    test_failed "No subscription ID available from test 1"
else
    echo "  Request: DELETE ${API_BASE}/subscriptions/${CREATED_SUBSCRIPTION_ID}"

    RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE \
        "${API_BASE}/subscriptions/${CREATED_SUBSCRIPTION_ID}" 2>/dev/null)

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    echo "  HTTP Status: $HTTP_CODE"
    echo "  Response: $BODY"

    if [ "$HTTP_CODE" = "200" ]; then
        if echo "$BODY" | grep -q '"status"' && echo "$BODY" | grep -q '"deleted"'; then
            test_passed
        else
            # Check for subscription_id in response
            if echo "$BODY" | grep -q "$CREATED_SUBSCRIPTION_ID"; then
                test_passed
            else
                test_failed "Response does not confirm deletion"
            fi
        fi
    else
        test_failed "Expected HTTP 200, got $HTTP_CODE"
    fi
fi

# ============================================================================
# Summary
# ============================================================================
print_summary
