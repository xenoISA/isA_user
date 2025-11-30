#!/bin/bash

# Subscription Service CRUD Tests
# Tests subscription management, credit allocation, and consumption

BASE_URL="http://localhost/api/v1/subscriptions"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

echo "======================================================================"
echo "Subscription Service CRUD Tests"
echo "======================================================================"
echo ""

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Function to print section header
print_section() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

# Generate unique test IDs
TEST_TS=$(date +%s)
USER_ID="sub_test_user_${TEST_TS}"
ORG_ID="sub_test_org_${TEST_TS}"

# Test 1: List Subscriptions (Empty)
print_section "Test 1: List Subscriptions"
echo "GET ${BASE_URL}"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "List subscriptions endpoint works"
else
    print_result 1 "List subscriptions failed"
fi

# Test 2: Create Subscription (Free Tier)
print_section "Test 2: Create Subscription (Free Tier)"
echo "POST ${BASE_URL}"

CREATE_PAYLOAD='{
  "user_id": "'${USER_ID}'",
  "tier_code": "free",
  "billing_cycle": "monthly",
  "metadata": {
    "test": true,
    "source": "subscription_test.sh"
  }
}'
echo "Request Body:"
echo "$CREATE_PAYLOAD" | jq '.'

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

SUBSCRIPTION_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    SUBSCRIPTION_ID=$(echo "$RESPONSE_BODY" | jq -r '.subscription.subscription_id // .subscription_id // empty')
    if [ -n "$SUBSCRIPTION_ID" ]; then
        print_result 0 "Created subscription: ${SUBSCRIPTION_ID}"
        echo -e "${YELLOW}Subscription ID: ${SUBSCRIPTION_ID}${NC}"
    else
        print_result 1 "Created but no subscription_id returned"
    fi
else
    print_result 1 "Failed to create subscription"
fi

# Test 3: Get Subscription by ID
print_section "Test 3: Get Subscription by ID"
if [ -n "$SUBSCRIPTION_ID" ]; then
    echo "GET ${BASE_URL}/${SUBSCRIPTION_ID}"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/${SUBSCRIPTION_ID}")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Get subscription by ID succeeded"
    else
        print_result 1 "Get subscription by ID failed"
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No subscription ID available${NC}"
    print_result 1 "Skipped - no subscription ID"
fi

# Test 4: Get User Subscription
print_section "Test 4: Get User Subscription"
echo "GET ${BASE_URL}/user/${USER_ID}"

USER_SUB_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/user/${USER_ID}")
HTTP_CODE=$(echo "$USER_SUB_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USER_SUB_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Get user subscription succeeded"
else
    print_result 1 "Get user subscription failed"
fi

# Test 5: Get Credit Balance
print_section "Test 5: Get Credit Balance"
echo "GET ${BASE_URL}/credits/balance?user_id=${USER_ID}"

BALANCE_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/credits/balance?user_id=${USER_ID}")
HTTP_CODE=$(echo "$BALANCE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$BALANCE_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    CREDITS_REMAINING=$(echo "$RESPONSE_BODY" | jq -r '.subscription_credits_remaining // .total_credits_available // 0')
    echo -e "${YELLOW}Credits Available: ${CREDITS_REMAINING}${NC}"
    print_result 0 "Get credit balance succeeded"
else
    print_result 1 "Get credit balance failed"
fi

# Test 6: Consume Credits
print_section "Test 6: Consume Credits"
echo "POST ${BASE_URL}/credits/consume"

CONSUME_PAYLOAD='{
  "user_id": "'${USER_ID}'",
  "credits_to_consume": 100,
  "service_type": "model_inference",
  "description": "Test credit consumption"
}'
echo "Request Body:"
echo "$CONSUME_PAYLOAD" | jq '.'

CONSUME_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/credits/consume" \
  -H "Content-Type: application/json" \
  -d "$CONSUME_PAYLOAD")
HTTP_CODE=$(echo "$CONSUME_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CONSUME_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

# 200 = success, 402 = insufficient credits (also valid for free tier)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "402" ]; then
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Credits consumed successfully"
    else
        print_result 0 "Credit consumption correctly rejected (insufficient credits)"
    fi
else
    print_result 1 "Credit consumption failed unexpectedly"
fi

# Test 7: List Subscriptions with Filter
print_section "Test 7: List Subscriptions with Filter"
echo "GET ${BASE_URL}?user_id=${USER_ID}"

FILTER_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}?user_id=${USER_ID}")
HTTP_CODE=$(echo "$FILTER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$FILTER_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL=$(echo "$RESPONSE_BODY" | jq -r '.total // 0')
    echo -e "${YELLOW}Total subscriptions for user: ${TOTAL}${NC}"
    print_result 0 "List with filter succeeded"
else
    print_result 1 "List with filter failed"
fi

# Test 8: Get Subscription History
print_section "Test 8: Get Subscription History"
if [ -n "$SUBSCRIPTION_ID" ]; then
    echo "GET ${BASE_URL}/${SUBSCRIPTION_ID}/history"

    HISTORY_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/${SUBSCRIPTION_ID}/history")
    HTTP_CODE=$(echo "$HISTORY_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$HISTORY_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        HISTORY_COUNT=$(echo "$RESPONSE_BODY" | jq -r '.history | length // 0')
        echo -e "${YELLOW}History entries: ${HISTORY_COUNT}${NC}"
        print_result 0 "Get subscription history succeeded"
    else
        print_result 1 "Get subscription history failed"
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No subscription ID available${NC}"
    print_result 1 "Skipped - no subscription ID"
fi

# Test 9: Create Pro Subscription
print_section "Test 9: Create Pro Subscription"
PRO_USER_ID="pro_test_user_${TEST_TS}"
echo "POST ${BASE_URL}"

PRO_PAYLOAD='{
  "user_id": "'${PRO_USER_ID}'",
  "tier_code": "pro",
  "billing_cycle": "monthly",
  "payment_method_id": "pm_test_123",
  "metadata": {
    "test": true,
    "tier": "pro"
  }
}'
echo "Request Body:"
echo "$PRO_PAYLOAD" | jq '.'

PRO_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}" \
  -H "Content-Type: application/json" \
  -d "$PRO_PAYLOAD")
HTTP_CODE=$(echo "$PRO_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$PRO_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

PRO_SUBSCRIPTION_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    PRO_SUBSCRIPTION_ID=$(echo "$RESPONSE_BODY" | jq -r '.subscription.subscription_id // .subscription_id // empty')
    CREDITS_ALLOCATED=$(echo "$RESPONSE_BODY" | jq -r '.credits_allocated // .subscription.credits_allocated // 0')
    echo -e "${YELLOW}Pro Subscription ID: ${PRO_SUBSCRIPTION_ID}${NC}"
    echo -e "${YELLOW}Credits Allocated: ${CREDITS_ALLOCATED}${NC}"
    print_result 0 "Created pro subscription"
else
    print_result 1 "Failed to create pro subscription"
fi

# Test 10: Cancel Subscription
print_section "Test 10: Cancel Subscription"
if [ -n "$SUBSCRIPTION_ID" ]; then
    echo "POST ${BASE_URL}/${SUBSCRIPTION_ID}/cancel?user_id=${USER_ID}"

    CANCEL_PAYLOAD='{
      "immediate": false,
      "reason": "Testing cancellation",
      "feedback": "Test script cleanup"
    }'
    echo "Request Body:"
    echo "$CANCEL_PAYLOAD" | jq '.'

    CANCEL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/${SUBSCRIPTION_ID}/cancel?user_id=${USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$CANCEL_PAYLOAD")
    HTTP_CODE=$(echo "$CANCEL_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CANCEL_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Subscription canceled successfully"
    else
        print_result 1 "Failed to cancel subscription"
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No subscription ID available${NC}"
    print_result 1 "Skipped - no subscription ID"
fi

# ====================
# Test Summary
# ====================
echo ""
echo "======================================================================"
echo "                         TEST SUMMARY"
echo "======================================================================"
echo ""
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL SUBSCRIPTION TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
