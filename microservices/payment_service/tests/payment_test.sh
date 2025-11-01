#!/bin/bash

# Payment Service CRUD Tests
# Tests subscription plans, subscriptions, payments, invoices, and refunds

BASE_URL="http://localhost:8207"
API_BASE="${BASE_URL}/api/v1"
AUTH_URL="http://localhost:8201/api/v1/auth"

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
echo "Payment Service CRUD Tests"
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

# Test 0: Generate test token from auth service
print_section "Test 0: Generate Test Token from Auth Service"
echo "POST ${AUTH_URL}/dev-token"
TOKEN_PAYLOAD='{
  "user_id": "test_payment_user_123",
  "email": "paymenttest@example.com",
  "organization_id": "org_test_123",
  "role": "user",
  "expires_in": 3600
}'
echo "Request Body:"
echo "$TOKEN_PAYLOAD" | jq '.'

TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_URL}/dev-token" \
  -H "Content-Type: application/json" \
  -d "$TOKEN_PAYLOAD")
HTTP_CODE=$(echo "$TOKEN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

JWT_TOKEN=""
if [ "$HTTP_CODE" = "200" ]; then
    JWT_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.token')
    if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
        print_result 0 "Test token generated successfully"
        echo -e "${YELLOW}Token (first 50 chars): ${JWT_TOKEN:0:50}...${NC}"
    else
        print_result 1 "Token generation failed"
        exit 1
    fi
else
    print_result 1 "Failed to generate test token"
    exit 1
fi

USER_ID="test_payment_user_123"

# Test 1: Health Check
print_section "Test 1: Health Check"
echo "GET ${BASE_URL}/health"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Health check successful"
else
    print_result 1 "Health check failed"
fi

# Test 2: Get Service Info
print_section "Test 2: Get Service Info"
echo "GET ${BASE_URL}/info"
INFO_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/info")
HTTP_CODE=$(echo "$INFO_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INFO_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Service info retrieved successfully"
else
    print_result 1 "Failed to get service info"
fi

# Test 3: Create Subscription Plan
print_section "Test 3: Create Subscription Plan"
PLAN_ID="plan_test_pro_monthly_$(date +%s)"
echo "POST ${API_BASE}/plans"
CREATE_PLAN_PAYLOAD="{
  \"plan_id\": \"${PLAN_ID}\",
  \"name\": \"Test Pro Plan\",
  \"tier\": \"pro\",
  \"price\": 29.99,
  \"billing_cycle\": \"monthly\",
  \"features\": {
    \"storage_gb\": 100,
    \"users\": 5,
    \"api_calls\": 10000
  },
  \"trial_days\": 14
}"
echo "Request Body:"
echo "$CREATE_PLAN_PAYLOAD" | jq '.'

CREATE_PLAN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/plans" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PLAN_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_PLAN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_PLAN_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    CREATED_PLAN_ID=$(echo "$RESPONSE_BODY" | jq -r '.plan_id')
    if [ "$CREATED_PLAN_ID" = "$PLAN_ID" ]; then
        print_result 0 "Subscription plan created successfully"
        echo -e "${YELLOW}Plan ID: ${PLAN_ID}${NC}"
    else
        print_result 1 "Plan ID mismatch"
    fi
else
    print_result 1 "Failed to create subscription plan"
fi

# Test 4: Get Subscription Plan
print_section "Test 4: Get Subscription Plan"
echo "GET ${API_BASE}/plans/${PLAN_ID}"

GET_PLAN_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/plans/${PLAN_ID}")
HTTP_CODE=$(echo "$GET_PLAN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$GET_PLAN_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    RETRIEVED_PLAN_ID=$(echo "$RESPONSE_BODY" | jq -r '.plan_id')
    if [ "$RETRIEVED_PLAN_ID" = "$PLAN_ID" ]; then
        print_result 0 "Subscription plan retrieved successfully"
    else
        print_result 1 "Plan ID mismatch in retrieved data"
    fi
else
    print_result 1 "Failed to get subscription plan"
fi

# Test 5: List Subscription Plans
print_section "Test 5: List Subscription Plans"
echo "GET ${API_BASE}/plans"

LIST_PLANS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/plans")
HTTP_CODE=$(echo "$LIST_PLANS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_PLANS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    PLANS_COUNT=$(echo "$RESPONSE_BODY" | jq 'length')
    print_result 0 "Subscription plans listed successfully (count: $PLANS_COUNT)"
else
    print_result 1 "Failed to list subscription plans"
fi

# Test 6: Create Subscription
print_section "Test 6: Create Subscription"
echo "POST ${API_BASE}/subscriptions"
CREATE_SUB_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"plan_id\": \"${PLAN_ID}\",
  \"metadata\": {
    \"source\": \"test_suite\",
    \"environment\": \"test\"
  }
}"
echo "Request Body:"
echo "$CREATE_SUB_PAYLOAD" | jq '.'

CREATE_SUB_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/subscriptions" \
  -H "Content-Type: application/json" \
  -d "$CREATE_SUB_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_SUB_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_SUB_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

SUBSCRIPTION_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    SUBSCRIPTION_ID=$(echo "$RESPONSE_BODY" | jq -r '.subscription.subscription_id')
    if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
        print_result 0 "Subscription created successfully"
        echo -e "${YELLOW}Subscription ID: ${SUBSCRIPTION_ID}${NC}"
    else
        print_result 1 "Failed to get subscription ID"
    fi
else
    print_result 1 "Failed to create subscription"
fi

# Test 7: Get User Subscription
print_section "Test 7: Get User Subscription"
echo "GET ${API_BASE}/subscriptions/user/${USER_ID}"

GET_USER_SUB_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/subscriptions/user/${USER_ID}")
HTTP_CODE=$(echo "$GET_USER_SUB_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$GET_USER_SUB_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    RETRIEVED_SUB_ID=$(echo "$RESPONSE_BODY" | jq -r '.subscription.subscription_id')
    if [ "$RETRIEVED_SUB_ID" = "$SUBSCRIPTION_ID" ]; then
        print_result 0 "User subscription retrieved successfully"
    else
        print_result 1 "Subscription ID mismatch"
    fi
else
    print_result 1 "Failed to get user subscription"
fi

# Test 8: Create Payment Intent
print_section "Test 8: Create Payment Intent"
echo "POST ${API_BASE}/payments/intent"
PAYMENT_INTENT_PAYLOAD="{
  \"amount\": 29.99,
  \"currency\": \"USD\",
  \"description\": \"Test payment for subscription\",
  \"user_id\": \"${USER_ID}\",
  \"metadata\": {
    \"subscription_id\": \"${SUBSCRIPTION_ID}\",
    \"test\": true
  }
}"
echo "Request Body:"
echo "$PAYMENT_INTENT_PAYLOAD" | jq '.'

PAYMENT_INTENT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/payments/intent" \
  -H "Content-Type: application/json" \
  -d "$PAYMENT_INTENT_PAYLOAD")
HTTP_CODE=$(echo "$PAYMENT_INTENT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$PAYMENT_INTENT_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

PAYMENT_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    PAYMENT_ID=$(echo "$RESPONSE_BODY" | jq -r '.payment_intent_id')
    if [ -n "$PAYMENT_ID" ] && [ "$PAYMENT_ID" != "null" ]; then
        print_result 0 "Payment intent created successfully"
        echo -e "${YELLOW}Payment ID: ${PAYMENT_ID}${NC}"
    else
        print_result 1 "Failed to get payment ID"
    fi
else
    print_result 1 "Failed to create payment intent"
fi

# Test 9: Confirm Payment
if [ -n "$PAYMENT_ID" ] && [ "$PAYMENT_ID" != "null" ]; then
    print_section "Test 9: Confirm Payment"
    echo "POST ${API_BASE}/payments/${PAYMENT_ID}/confirm"
    CONFIRM_PAYLOAD='{
      "processor_response": {
        "status": "succeeded",
        "test": true
      }
    }'
    echo "Request Body:"
    echo "$CONFIRM_PAYLOAD" | jq '.'

    CONFIRM_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/payments/${PAYMENT_ID}/confirm" \
      -H "Content-Type: application/json" \
      -d "$CONFIRM_PAYLOAD")
    HTTP_CODE=$(echo "$CONFIRM_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CONFIRM_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        PAYMENT_STATUS=$(echo "$RESPONSE_BODY" | jq -r '.status')
        if [ "$PAYMENT_STATUS" = "succeeded" ]; then
            print_result 0 "Payment confirmed successfully"
        else
            print_result 1 "Payment status is not succeeded"
        fi
    else
        print_result 1 "Failed to confirm payment"
    fi
else
    echo -e "${RED}ERROR: No payment ID available for Test 9${NC}"
    print_result 1 "Cannot test without payment ID"
fi

# Test 10: Get Payment History
print_section "Test 10: Get Payment History"
echo "GET ${API_BASE}/payments/user/${USER_ID}"

PAYMENT_HISTORY_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/payments/user/${USER_ID}?limit=10")
HTTP_CODE=$(echo "$PAYMENT_HISTORY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$PAYMENT_HISTORY_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    PAYMENTS_COUNT=$(echo "$RESPONSE_BODY" | jq '.payments | length')
    print_result 0 "Payment history retrieved successfully (count: $PAYMENTS_COUNT)"
else
    print_result 1 "Failed to get payment history"
fi

# Test 11: Create Invoice
print_section "Test 11: Create Invoice"
echo "POST ${API_BASE}/invoices"
CREATE_INVOICE_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"subscription_id\": \"${SUBSCRIPTION_ID}\",
  \"amount_due\": 29.99,
  \"line_items\": [
    {
      \"description\": \"Pro Plan - Monthly\",
      \"amount\": 29.99,
      \"quantity\": 1
    }
  ]
}"
echo "Request Body:"
echo "$CREATE_INVOICE_PAYLOAD" | jq '.'

CREATE_INVOICE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/invoices" \
  -H "Content-Type: application/json" \
  -d "$CREATE_INVOICE_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_INVOICE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_INVOICE_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

INVOICE_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    INVOICE_ID=$(echo "$RESPONSE_BODY" | jq -r '.invoice_id')
    if [ -n "$INVOICE_ID" ] && [ "$INVOICE_ID" != "null" ]; then
        print_result 0 "Invoice created successfully"
        echo -e "${YELLOW}Invoice ID: ${INVOICE_ID}${NC}"
    else
        print_result 1 "Failed to get invoice ID"
    fi
else
    print_result 1 "Failed to create invoice"
fi

# Test 12: Get Invoice
if [ -n "$INVOICE_ID" ] && [ "$INVOICE_ID" != "null" ]; then
    print_section "Test 12: Get Invoice"
    echo "GET ${API_BASE}/invoices/${INVOICE_ID}"

    GET_INVOICE_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/invoices/${INVOICE_ID}")
    HTTP_CODE=$(echo "$GET_INVOICE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_INVOICE_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_INVOICE_ID=$(echo "$RESPONSE_BODY" | jq -r '.invoice.invoice_id')
        if [ "$RETRIEVED_INVOICE_ID" = "$INVOICE_ID" ]; then
            print_result 0 "Invoice retrieved successfully"
        else
            print_result 1 "Invoice ID mismatch"
        fi
    else
        print_result 1 "Failed to get invoice"
    fi
else
    echo -e "${RED}ERROR: No invoice ID available for Test 12${NC}"
    print_result 1 "Cannot test without invoice ID"
fi

# Test 13: Create Refund
if [ -n "$PAYMENT_ID" ] && [ "$PAYMENT_ID" != "null" ]; then
    print_section "Test 13: Create Refund"
    echo "POST ${API_BASE}/refunds"
    CREATE_REFUND_PAYLOAD="{
      \"payment_id\": \"${PAYMENT_ID}\",
      \"amount\": 10.00,
      \"reason\": \"Customer requested partial refund\",
      \"requested_by\": \"${USER_ID}\"
    }"
    echo "Request Body:"
    echo "$CREATE_REFUND_PAYLOAD" | jq '.'

    CREATE_REFUND_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/refunds" \
      -H "Content-Type: application/json" \
      -d "$CREATE_REFUND_PAYLOAD")
    HTTP_CODE=$(echo "$CREATE_REFUND_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CREATE_REFUND_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    REFUND_ID=""
    if [ "$HTTP_CODE" = "200" ]; then
        REFUND_ID=$(echo "$RESPONSE_BODY" | jq -r '.refund_id')
        if [ -n "$REFUND_ID" ] && [ "$REFUND_ID" != "null" ]; then
            print_result 0 "Refund created successfully"
            echo -e "${YELLOW}Refund ID: ${REFUND_ID}${NC}"
        else
            print_result 1 "Failed to get refund ID"
        fi
    else
        print_result 1 "Failed to create refund"
    fi

    # Test 14: Process Refund
    if [ -n "$REFUND_ID" ] && [ "$REFUND_ID" != "null" ]; then
        print_section "Test 14: Process Refund"
        echo "POST ${API_BASE}/refunds/${REFUND_ID}/process"
        PROCESS_REFUND_PAYLOAD="{
          \"approved_by\": \"admin_test\"
        }"
        echo "Request Body:"
        echo "$PROCESS_REFUND_PAYLOAD" | jq '.'

        PROCESS_REFUND_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/refunds/${REFUND_ID}/process" \
          -H "Content-Type: application/json" \
          -d "$PROCESS_REFUND_PAYLOAD")
        HTTP_CODE=$(echo "$PROCESS_REFUND_RESPONSE" | tail -n1)
        RESPONSE_BODY=$(echo "$PROCESS_REFUND_RESPONSE" | sed '$d')

        echo "Response:"
        echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
        echo "HTTP Status: $HTTP_CODE"

        if [ "$HTTP_CODE" = "200" ]; then
            REFUND_STATUS=$(echo "$RESPONSE_BODY" | jq -r '.status')
            print_result 0 "Refund processed successfully (status: $REFUND_STATUS)"
        else
            print_result 1 "Failed to process refund"
        fi
    else
        echo -e "${RED}ERROR: No refund ID available for Test 14${NC}"
        print_result 1 "Cannot test without refund ID"
    fi
else
    echo -e "${RED}ERROR: No payment ID available for Test 13${NC}"
    print_result 1 "Cannot test without payment ID"
fi

# Test 15: Record Usage
if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    print_section "Test 15: Record Usage"
    echo "POST ${API_BASE}/usage"
    USAGE_PAYLOAD="{
      \"user_id\": \"${USER_ID}\",
      \"subscription_id\": \"${SUBSCRIPTION_ID}\",
      \"metric_name\": \"api_calls\",
      \"quantity\": 100,
      \"metadata\": {
        \"endpoint\": \"/api/test\",
        \"test\": true
      }
    }"
    echo "Request Body:"
    echo "$USAGE_PAYLOAD" | jq '.'

    USAGE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/usage" \
      -H "Content-Type: application/json" \
      -d "$USAGE_PAYLOAD")
    HTTP_CODE=$(echo "$USAGE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$USAGE_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Usage recorded successfully"
        else
            print_result 1 "Usage recording failed"
        fi
    else
        print_result 1 "Failed to record usage"
    fi
else
    echo -e "${RED}ERROR: No subscription ID available for Test 15${NC}"
    print_result 1 "Cannot test without subscription ID"
fi

# Test 16: Get Revenue Statistics
print_section "Test 16: Get Revenue Statistics"
echo "GET ${API_BASE}/stats/revenue"

REVENUE_STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/stats/revenue")
HTTP_CODE=$(echo "$REVENUE_STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REVENUE_STATS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Revenue statistics retrieved successfully"
else
    print_result 1 "Failed to get revenue statistics"
fi

# Test 17: Get Subscription Statistics
print_section "Test 17: Get Subscription Statistics"
echo "GET ${API_BASE}/stats/subscriptions"

SUB_STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/stats/subscriptions")
HTTP_CODE=$(echo "$SUB_STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SUB_STATS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Subscription statistics retrieved successfully"
else
    print_result 1 "Failed to get subscription statistics"
fi

# Test 18: Get Service Stats
print_section "Test 18: Get Service Stats"
echo "GET ${API_BASE}/stats"

SERVICE_STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/stats")
HTTP_CODE=$(echo "$SERVICE_STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SERVICE_STATS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Service statistics retrieved successfully"
else
    print_result 1 "Failed to get service statistics"
fi

# Test 19: Update Subscription
if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    print_section "Test 19: Update Subscription"
    echo "PUT ${API_BASE}/subscriptions/${SUBSCRIPTION_ID}"
    UPDATE_SUB_PAYLOAD='{
      "cancel_at_period_end": true,
      "metadata": {
        "updated": true,
        "test": true
      }
    }'
    echo "Request Body:"
    echo "$UPDATE_SUB_PAYLOAD" | jq '.'

    UPDATE_SUB_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/subscriptions/${SUBSCRIPTION_ID}" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_SUB_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_SUB_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_SUB_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        CANCEL_AT_END=$(echo "$RESPONSE_BODY" | jq -r '.subscription.cancel_at_period_end')
        if [ "$CANCEL_AT_END" = "true" ]; then
            print_result 0 "Subscription updated successfully"
        else
            print_result 1 "Subscription update did not apply changes"
        fi
    else
        print_result 1 "Failed to update subscription"
    fi
else
    echo -e "${RED}ERROR: No subscription ID available for Test 19${NC}"
    print_result 1 "Cannot test without subscription ID"
fi

# Test 20: Cancel Subscription
if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    print_section "Test 20: Cancel Subscription"
    echo "POST ${API_BASE}/subscriptions/${SUBSCRIPTION_ID}/cancel"
    CANCEL_SUB_PAYLOAD='{
      "immediate": false,
      "reason": "Testing cancellation flow",
      "feedback": "This is a test cancellation"
    }'
    echo "Request Body:"
    echo "$CANCEL_SUB_PAYLOAD" | jq '.'

    CANCEL_SUB_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/subscriptions/${SUBSCRIPTION_ID}/cancel" \
      -H "Content-Type: application/json" \
      -d "$CANCEL_SUB_PAYLOAD")
    HTTP_CODE=$(echo "$CANCEL_SUB_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CANCEL_SUB_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUB_STATUS=$(echo "$RESPONSE_BODY" | jq -r '.status')
        print_result 0 "Subscription cancelled successfully (status: $SUB_STATUS)"
    else
        print_result 1 "Failed to cancel subscription"
    fi
else
    echo -e "${RED}ERROR: No subscription ID available for Test 20${NC}"
    print_result 1 "Cannot test without subscription ID"
fi

# Summary
echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Total: $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
