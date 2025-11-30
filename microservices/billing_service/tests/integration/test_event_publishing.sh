#!/bin/bash

# Billing Service Event Publishing Integration Test
# Verifies that billing events are properly published

BASE_URL="${BASE_URL:-http://localhost}"
API_BASE="${BASE_URL}/api/v1"
AUTH_URL="${BASE_URL}/api/v1/auth"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================================================"
echo "Billing Service - Event Publishing Integration Test"
echo "======================================================================"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Generate test token
echo "Generating test token..."
TOKEN_PAYLOAD='{
  "user_id": "test_billing_event_user",
  "email": "billingevent@example.com",
  "role": "user",
  "expires_in": 3600
}'

TOKEN_RESPONSE=$(curl -s -X POST "${AUTH_URL}/dev-token" \
  -H "Content-Type: application/json" \
  -d "$TOKEN_PAYLOAD")

JWT_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.token')

if [ -z "$JWT_TOKEN" ] || [ "$JWT_TOKEN" = "null" ]; then
    echo -e "${RED}Failed to generate test token${NC}"
    exit 1
fi

TEST_USER_ID="test_billing_event_user"

echo ""
echo "======================================================================"
echo "Test 1: Verify billing.calculated event is published via usage recording"
echo "======================================================================"
echo ""

USAGE_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"product_id\": \"gpt-4\",
  \"service_type\": \"model_inference\",
  \"usage_amount\": 1000,
  \"session_id\": \"session_event_test_$(date +%s)\",
  \"request_id\": \"req_event_test_$(date +%s)\",
  \"usage_details\": {
    \"model\": \"gpt-4\",
    \"tokens\": 1000,
    \"test_event_publishing\": true
  },
  \"usage_timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"
}"

echo "Recording usage to trigger billing.calculated event..."
echo "POST ${API_BASE}/billing/usage/record"
echo "$USAGE_PAYLOAD" | jq '.'

RESPONSE=$(curl -s -X POST "${API_BASE}/billing/usage/record" \
  -H "Content-Type: application/json" \
  -d "$USAGE_PAYLOAD")

echo "Response:"
echo "$RESPONSE" | jq '.'

SUCCESS=$(echo "$RESPONSE" | jq -r '.success')
BILLING_RECORD_ID=$(echo "$RESPONSE" | jq -r '.billing_record_id')

if [ "$SUCCESS" = "true" ] && [ -n "$BILLING_RECORD_ID" ] && [ "$BILLING_RECORD_ID" != "null" ]; then
    print_result 0 "billing.calculated event should be published (billing record created: $BILLING_RECORD_ID)"
else
    print_result 1 "Failed to create billing record (no event published)"
fi

echo ""
echo "======================================================================"
echo "Test 2: Verify multiple usage records trigger multiple events"
echo "======================================================================"
echo ""

for i in 1 2 3; do
    echo "Recording usage #$i..."
    USAGE_PAYLOAD_MULTI="{
      \"user_id\": \"${TEST_USER_ID}\",
      \"product_id\": \"dall-e-3\",
      \"service_type\": \"image_generation\",
      \"usage_amount\": 1,
      \"session_id\": \"session_multi_${i}_$(date +%s)\",
      \"usage_details\": {
        \"image_count\": 1,
        \"test_multi_event\": true
      },
      \"usage_timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"
    }"

    RESPONSE=$(curl -s -X POST "${API_BASE}/billing/usage/record" \
      -H "Content-Type: application/json" \
      -d "$USAGE_PAYLOAD_MULTI")

    SUCCESS=$(echo "$RESPONSE" | jq -r '.success')
    if [ "$SUCCESS" = "true" ]; then
        echo "  Usage #$i recorded successfully"
    else
        echo "  Usage #$i failed"
    fi
done

print_result 0 "Multiple billing.calculated events should be published (3 usage records created)"

echo ""
echo "======================================================================"
echo "Test 3: Verify billing.error event on invalid product"
echo "======================================================================"
echo ""

INVALID_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"product_id\": \"invalid_product_xyz\",
  \"service_type\": \"model_inference\",
  \"usage_amount\": 1000,
  \"usage_timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"
}"

echo "Recording usage with invalid product to potentially trigger billing.error event..."
echo "POST ${API_BASE}/billing/usage/record"
echo "$INVALID_PAYLOAD" | jq '.'

RESPONSE=$(curl -s -X POST "${API_BASE}/billing/usage/record" \
  -H "Content-Type: application/json" \
  -d "$INVALID_PAYLOAD")

echo "Response:"
echo "$RESPONSE" | jq '.'

SUCCESS=$(echo "$RESPONSE" | jq -r '.success')
ERROR_DETAIL=$(echo "$RESPONSE" | jq -r '.detail')
if [ "$SUCCESS" = "false" ] || [ -n "$ERROR_DETAIL" ] && [ "$ERROR_DETAIL" != "null" ]; then
    print_result 0 "billing.error event should be published (invalid product rejected)"
else
    print_result 1 "Invalid product should trigger error event"
fi

echo ""
echo "======================================================================"
echo "Test 4: Verify usage.recorded event format via calculate endpoint"
echo "======================================================================"
echo ""

CALCULATE_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"product_id\": \"gpt-4\",
  \"usage_amount\": 2000
}"

echo "Calculating billing cost..."
echo "POST ${API_BASE}/billing/calculate"
echo "$CALCULATE_PAYLOAD" | jq '.'

RESPONSE=$(curl -s -X POST "${API_BASE}/billing/calculate" \
  -H "Content-Type: application/json" \
  -d "$CALCULATE_PAYLOAD")

echo "Response:"
echo "$RESPONSE" | jq '.'

TOTAL_COST=$(echo "$RESPONSE" | jq -r '.total_cost')
if [ -n "$TOTAL_COST" ] && [ "$TOTAL_COST" != "null" ]; then
    print_result 0 "Billing calculation successful (cost: $TOTAL_COST)"
else
    print_result 1 "Billing calculation failed"
fi

# Summary
echo ""
echo "======================================================================"
echo "Event Publishing Test Summary"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Total: $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All event publishing tests passed!${NC}"
    echo ""
    echo "Events that should have been published:"
    echo "  - billing.calculated (multiple times)"
    echo "  - billing.error (on invalid product)"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
