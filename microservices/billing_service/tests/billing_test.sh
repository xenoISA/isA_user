#!/bin/bash

# Billing Service CRUD Tests
# Tests usage recording, billing calculation, quota management, and statistics

BASE_URL="http://localhost:8216"
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
echo "Billing Service CRUD Tests"
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
  "user_id": "test_billing_user_123",
  "email": "billingtest@example.com",
  "organization_id": "org_billing_test_123",
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

USER_ID="test_billing_user_123"
ORG_ID="org_billing_test_123"

# Test 0.5: Create a subscription in product service for testing
print_section "Test 0.5: Create Subscription for Testing"
PLAN_ID="free-plan"  # Use existing free plan from database
echo "POST http://localhost:8215/api/v1/product/subscriptions"
CREATE_SUB_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"plan_id\": \"${PLAN_ID}\",
  \"organization_id\": \"${ORG_ID}\",
  \"billing_cycle\": \"monthly\",
  \"metadata\": {
    \"test\": true
  }
}"
echo "Request Body:"
echo "$CREATE_SUB_PAYLOAD" | jq '.'

CREATE_SUB_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8215/api/v1/product/subscriptions" \
  -H "Content-Type: application/json" \
  -d "$CREATE_SUB_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_SUB_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_SUB_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

SUBSCRIPTION_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    SUBSCRIPTION_ID=$(echo "$RESPONSE_BODY" | jq -r '.subscription_id')
    if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
        print_result 0 "Test subscription created successfully"
        echo -e "${YELLOW}Subscription ID: ${SUBSCRIPTION_ID}${NC}"
    else
        print_result 1 "Failed to get subscription ID"
        SUBSCRIPTION_ID=""  # Fallback to empty
    fi
else
    print_result 1 "Failed to create test subscription"
    SUBSCRIPTION_ID=""  # Fallback to empty
fi

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
echo "GET ${API_BASE}/billing/info"
INFO_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/billing/info")
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

# Test 3: Calculate Billing Cost
print_section "Test 3: Calculate Billing Cost"
echo "POST ${API_BASE}/billing/calculate"
# Build payload conditionally based on whether we have subscription_id
if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    CALCULATE_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"organization_id\": \"${ORG_ID}\",
  \"subscription_id\": \"${SUBSCRIPTION_ID}\",
  \"product_id\": \"gpt-4\",
  \"usage_amount\": 1000
}"
else
    CALCULATE_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"organization_id\": \"${ORG_ID}\",
  \"product_id\": \"gpt-4\",
  \"usage_amount\": 1000
}"
fi
echo "Request Body:"
echo "$CALCULATE_PAYLOAD" | jq '.'

CALCULATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/billing/calculate" \
  -H "Content-Type: application/json" \
  -d "$CALCULATE_PAYLOAD")
HTTP_CODE=$(echo "$CALCULATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CALCULATE_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

CALCULATED_COST=""
if [ "$HTTP_CODE" = "200" ]; then
    CALCULATED_COST=$(echo "$RESPONSE_BODY" | jq -r '.total_cost')
    if [ -n "$CALCULATED_COST" ] && [ "$CALCULATED_COST" != "null" ]; then
        print_result 0 "Billing cost calculated successfully (cost: $CALCULATED_COST)"
    else
        print_result 1 "Failed to get calculated cost"
    fi
else
    print_result 1 "Failed to calculate billing cost"
fi

# Test 4: Record Usage and Bill
print_section "Test 4: Record Usage and Bill"
echo "POST ${API_BASE}/billing/usage/record"
# Build payload conditionally
if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    RECORD_USAGE_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"organization_id\": \"${ORG_ID}\",
  \"subscription_id\": \"${SUBSCRIPTION_ID}\",
  \"product_id\": \"gpt-4\",
  \"service_type\": \"model_inference\",
  \"usage_amount\": 1000,
  \"session_id\": \"session_test_$(date +%s)\",
  \"request_id\": \"req_test_$(date +%s)\",
  \"usage_details\": {
    \"model\": \"gpt-4\",
    \"tokens\": 1000,
    \"api_endpoint\": \"/v1/chat/completions\"
  },
  \"usage_timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"
}"
else
    RECORD_USAGE_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"organization_id\": \"${ORG_ID}\",
  \"product_id\": \"gpt-4\",
  \"service_type\": \"model_inference\",
  \"usage_amount\": 1000,
  \"session_id\": \"session_test_$(date +%s)\",
  \"request_id\": \"req_test_$(date +%s)\",
  \"usage_details\": {
    \"model\": \"gpt-4\",
    \"tokens\": 1000,
    \"api_endpoint\": \"/v1/chat/completions\"
  },
  \"usage_timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"
}"
fi
echo "Request Body:"
echo "$RECORD_USAGE_PAYLOAD" | jq '.'

RECORD_USAGE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/billing/usage/record" \
  -H "Content-Type: application/json" \
  -d "$RECORD_USAGE_PAYLOAD")
HTTP_CODE=$(echo "$RECORD_USAGE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RECORD_USAGE_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

BILLING_RECORD_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    BILLING_RECORD_ID=$(echo "$RESPONSE_BODY" | jq -r '.billing_record_id')
    SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
    if [ "$SUCCESS" = "true" ] && [ -n "$BILLING_RECORD_ID" ] && [ "$BILLING_RECORD_ID" != "null" ]; then
        print_result 0 "Usage recorded and billed successfully"
        echo -e "${YELLOW}Billing Record ID: ${BILLING_RECORD_ID}${NC}"
    else
        print_result 1 "Usage recording succeeded but no billing record ID"
    fi
else
    print_result 1 "Failed to record usage and bill"
fi

# Test 5: Get Billing Record
if [ -n "$BILLING_RECORD_ID" ] && [ "$BILLING_RECORD_ID" != "null" ]; then
    print_section "Test 5: Get Billing Record"
    echo "GET ${API_BASE}/billing/record/${BILLING_RECORD_ID}"

    GET_BILLING_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/billing/record/${BILLING_RECORD_ID}")
    HTTP_CODE=$(echo "$GET_BILLING_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_BILLING_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_BILLING_ID=$(echo "$RESPONSE_BODY" | jq -r '.billing_id')
        if [ "$RETRIEVED_BILLING_ID" = "$BILLING_RECORD_ID" ]; then
            print_result 0 "Billing record retrieved successfully"
        else
            print_result 1 "Billing record ID mismatch"
        fi
    else
        print_result 1 "Failed to get billing record"
    fi
else
    echo -e "${RED}ERROR: No billing record ID available for Test 5${NC}"
    print_result 1 "Cannot test without billing record ID"
fi

# Test 6: Get User Billing Records
print_section "Test 6: Get User Billing Records"
echo "GET ${API_BASE}/billing/records/user/${USER_ID}"

USER_BILLING_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/billing/records/user/${USER_ID}?limit=10")
HTTP_CODE=$(echo "$USER_BILLING_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USER_BILLING_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    RECORDS_COUNT=$(echo "$RESPONSE_BODY" | jq '.total_count')
    print_result 0 "User billing records retrieved successfully (count: $RECORDS_COUNT)"
else
    print_result 1 "Failed to get user billing records"
fi

# Test 7: Check Quota - Allowed
print_section "Test 7: Check Quota - Allowed"
echo "POST ${API_BASE}/billing/quota/check"
QUOTA_CHECK_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"organization_id\": \"${ORG_ID}\",
  \"subscription_id\": \"${SUBSCRIPTION_ID}\",
  \"service_type\": \"model_inference\",
  \"product_id\": \"gpt-4\",
  \"requested_amount\": 500
}"
echo "Request Body:"
echo "$QUOTA_CHECK_PAYLOAD" | jq '.'

QUOTA_CHECK_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/billing/quota/check" \
  -H "Content-Type: application/json" \
  -d "$QUOTA_CHECK_PAYLOAD")
HTTP_CODE=$(echo "$QUOTA_CHECK_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$QUOTA_CHECK_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    QUOTA_ALLOWED=$(echo "$RESPONSE_BODY" | jq -r '.allowed')
    print_result 0 "Quota check completed (allowed: $QUOTA_ALLOWED)"
else
    print_result 1 "Failed to check quota"
fi

# Test 8: Get Usage Aggregations
print_section "Test 8: Get Usage Aggregations"
echo "GET ${API_BASE}/billing/usage/aggregations?user_id=${USER_ID}&limit=10"

AGGREGATIONS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/billing/usage/aggregations?user_id=${USER_ID}&limit=10")
HTTP_CODE=$(echo "$AGGREGATIONS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$AGGREGATIONS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    AGG_COUNT=$(echo "$RESPONSE_BODY" | jq '.total_count')
    print_result 0 "Usage aggregations retrieved successfully (count: $AGG_COUNT)"
else
    print_result 1 "Failed to get usage aggregations"
fi

# Test 9: Get Billing Statistics
print_section "Test 9: Get Billing Statistics"
echo "GET ${API_BASE}/billing/stats"

STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/billing/stats")
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_RECORDS=$(echo "$RESPONSE_BODY" | jq -r '.total_billing_records')
    print_result 0 "Billing statistics retrieved successfully (total records: $TOTAL_RECORDS)"
else
    print_result 1 "Failed to get billing statistics"
fi

# Test 10: Update Billing Record Status
if [ -n "$BILLING_RECORD_ID" ] && [ "$BILLING_RECORD_ID" != "null" ]; then
    print_section "Test 10: Update Billing Record Status"
    echo "PUT ${API_BASE}/billing/record/${BILLING_RECORD_ID}/status?status=completed"

    UPDATE_STATUS_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
      "${API_BASE}/billing/record/${BILLING_RECORD_ID}/status?status=completed&wallet_transaction_id=wallet_tx_test_123")
    HTTP_CODE=$(echo "$UPDATE_STATUS_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_STATUS_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Billing record status updated successfully"
        else
            print_result 1 "Status update response success is false"
        fi
    else
        print_result 1 "Failed to update billing record status"
    fi
else
    echo -e "${RED}ERROR: No billing record ID available for Test 10${NC}"
    print_result 1 "Cannot test without billing record ID"
fi

# Test 11: Record Another Usage (Different Service Type)
print_section "Test 11: Record Usage - Storage Service"
echo "POST ${API_BASE}/billing/usage/record"
RECORD_STORAGE_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"organization_id\": \"${ORG_ID}\",
  \"subscription_id\": \"${SUBSCRIPTION_ID}\",
  \"product_id\": \"minio_storage\",
  \"service_type\": \"storage_minio\",
  \"usage_amount\": 5368709120,
  \"usage_details\": {
    \"bytes_stored\": 5368709120,
    \"storage_class\": \"standard\"
  },
  \"usage_timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"
}"
echo "Request Body:"
echo "$RECORD_STORAGE_PAYLOAD" | jq '.'

RECORD_STORAGE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/billing/usage/record" \
  -H "Content-Type: application/json" \
  -d "$RECORD_STORAGE_PAYLOAD")
HTTP_CODE=$(echo "$RECORD_STORAGE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RECORD_STORAGE_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "Storage usage recorded successfully"
    else
        print_result 1 "Storage usage recording failed"
    fi
else
    print_result 1 "Failed to record storage usage"
fi

# Test 12: Get User Billing Records with Filters
print_section "Test 12: Get User Billing Records - Filtered by Service Type"
echo "GET ${API_BASE}/billing/records/user/${USER_ID}?service_type=model_inference&limit=10"

FILTERED_BILLING_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET \
  "${API_BASE}/billing/records/user/${USER_ID}?service_type=model_inference&limit=10")
HTTP_CODE=$(echo "$FILTERED_BILLING_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$FILTERED_BILLING_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    FILTERED_COUNT=$(echo "$RESPONSE_BODY" | jq '.total_count')
    print_result 0 "Filtered billing records retrieved successfully (count: $FILTERED_COUNT)"
else
    print_result 1 "Failed to get filtered billing records"
fi

# Test 13: Calculate Billing Cost - Agent Execution
print_section "Test 13: Calculate Billing Cost - Agent Execution"
echo "POST ${API_BASE}/billing/calculate"
CALCULATE_AGENT_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"organization_id\": \"${ORG_ID}\",
  \"product_id\": \"advanced_agent\",
  \"usage_amount\": 10
}"
echo "Request Body:"
echo "$CALCULATE_AGENT_PAYLOAD" | jq '.'

CALCULATE_AGENT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/billing/calculate" \
  -H "Content-Type: application/json" \
  -d "$CALCULATE_AGENT_PAYLOAD")
HTTP_CODE=$(echo "$CALCULATE_AGENT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CALCULATE_AGENT_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    AGENT_COST=$(echo "$RESPONSE_BODY" | jq -r '.total_cost')
    print_result 0 "Agent execution cost calculated (cost: $AGENT_COST)"
else
    print_result 1 "Failed to calculate agent execution cost"
fi

# Test 14: Record Usage - API Gateway
print_section "Test 14: Record Usage - API Gateway"
echo "POST ${API_BASE}/billing/usage/record"
RECORD_API_PAYLOAD="{
  \"user_id\": \"${USER_ID}\",
  \"organization_id\": \"${ORG_ID}\",
  \"product_id\": \"api_gateway\",
  \"service_type\": \"api_gateway\",
  \"usage_amount\": 1000,
  \"usage_details\": {
    \"api_calls\": 1000,
    \"bandwidth_bytes\": 104857600
  },
  \"usage_timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"
}"
echo "Request Body:"
echo "$RECORD_API_PAYLOAD" | jq '.'

RECORD_API_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/billing/usage/record" \
  -H "Content-Type: application/json" \
  -d "$RECORD_API_PAYLOAD")
HTTP_CODE=$(echo "$RECORD_API_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RECORD_API_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS=$(echo "$RESPONSE_BODY" | jq -r '.success')
    if [ "$SUCCESS" = "true" ]; then
        print_result 0 "API Gateway usage recorded successfully"
    else
        print_result 1 "API Gateway usage recording failed"
    fi
else
    print_result 1 "Failed to record API Gateway usage"
fi

# Test 15: Get Usage Aggregations with Filters
print_section "Test 15: Get Usage Aggregations - Filtered by Organization"
echo "GET ${API_BASE}/billing/usage/aggregations?organization_id=${ORG_ID}&limit=20"

ORG_AGGREGATIONS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET \
  "${API_BASE}/billing/usage/aggregations?organization_id=${ORG_ID}&limit=20")
HTTP_CODE=$(echo "$ORG_AGGREGATIONS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$ORG_AGGREGATIONS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    ORG_AGG_COUNT=$(echo "$RESPONSE_BODY" | jq '.total_count')
    print_result 0 "Organization usage aggregations retrieved (count: $ORG_AGG_COUNT)"
else
    print_result 1 "Failed to get organization usage aggregations"
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
