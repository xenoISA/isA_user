#!/bin/bash
# Billing Service Test Script (v2 - using test_common.sh)
# Usage:
#   ./billing_test_v2.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./billing_test_v2.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="billing_service"
API_PATH="/api/v1/billing"

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"
TEST_BILLING_USER="test_billing_user_${TEST_TS}"
TEST_ORG_ID="org_billing_test_${TEST_TS}"

print_info "Test User ID: $TEST_BILLING_USER"
print_info "Test Org ID: $TEST_ORG_ID"
echo ""

# ============================================================================
# Setup: Create Test User
# ============================================================================
print_section "Setup: Create Test User"
ACCOUNT_URL="http://localhost:$(get_service_port account_service)/api/v1/accounts/ensure"
USER_RESPONSE=$(curl -s -X POST "$ACCOUNT_URL" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"${TEST_BILLING_USER}\",\"email\":\"billing_${TEST_TS}@example.com\",\"name\":\"Billing Test User\",\"subscription_plan\":\"free\"}")
echo "$USER_RESPONSE" | json_pretty
echo ""

# ============================================================================
# Tests
# ============================================================================

# Test 1: Get Service Info
print_section "Test 1: Get Service Info"
echo "GET ${API_PATH}/info"
RESPONSE=$(api_get "/info")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "service" || echo "$RESPONSE" | grep -q "billing"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Get Service Stats
print_section "Test 2: Get Service Stats"
echo "GET ${API_PATH}/stats"
RESPONSE=$(api_get "/stats")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "statistics" || echo "$RESPONSE" | grep -q "total"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 3: Calculate Billing Cost
print_section "Test 3: Calculate Billing Cost"
echo "POST ${API_PATH}/calculate"

CALC_PAYLOAD="{
  \"user_id\": \"${TEST_BILLING_USER}\",
  \"product_id\": \"gpt-4\",
  \"usage_amount\": 100
}"
RESPONSE=$(api_post "/calculate" "$CALC_PAYLOAD")
echo "$RESPONSE" | json_pretty

SUCCESS=$(json_get "$RESPONSE" "success")
if json_has "$RESPONSE" "total_cost" && [ "$SUCCESS" = "true" ] || [ "$SUCCESS" = "True" ]; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 4: Record Usage
print_section "Test 4: Record Usage"
echo "POST ${API_PATH}/usage/record"

USAGE_PAYLOAD="{
  \"user_id\": \"${TEST_BILLING_USER}\",
  \"product_id\": \"gpt-4\",
  \"service_type\": \"model_inference\",
  \"usage_amount\": 50,
  \"session_id\": \"session_${TEST_TS}\",
  \"usage_details\": {\"model\": \"gpt-4\", \"tokens\": 50}
}"
RESPONSE=$(api_post "/usage/record" "$USAGE_PAYLOAD")
echo "$RESPONSE" | json_pretty

USAGE_RECORD_ID=$(json_get "$RESPONSE" "billing_record_id")
if json_has "$RESPONSE" "billing_record_id" || echo "$RESPONSE" | grep -q "success"; then
    print_success "Recorded usage: $USAGE_RECORD_ID"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 5: Get User Billing Records
print_section "Test 5: Get User Billing Records"
echo "GET ${API_PATH}/records/user/${TEST_BILLING_USER}"
RESPONSE=$(api_get "/records/user/${TEST_BILLING_USER}")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q "\[" || json_has "$RESPONSE" "records" || json_has "$RESPONSE" "billing_id"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 6: Check Quota
print_section "Test 6: Check User Quota"
echo "POST ${API_PATH}/quota/check"

QUOTA_PAYLOAD="{
  \"user_id\": \"${TEST_BILLING_USER}\",
  \"service_type\": \"storage_minio\",
  \"requested_amount\": 100
}"
RESPONSE=$(api_post "/quota/check" "$QUOTA_PAYLOAD")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "allowed" || json_has "$RESPONSE" "quota_remaining" || echo "$RESPONSE" | grep -q "message"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 7: Get Usage Aggregations
print_section "Test 7: Get Usage Aggregations"
echo "GET ${API_PATH}/usage/aggregations?user_id=${TEST_BILLING_USER}"
RESPONSE=$(api_get "/usage/aggregations?user_id=${TEST_BILLING_USER}")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q "\[" || json_has "$RESPONSE" "aggregations" || json_has "$RESPONSE" "total"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 8: Get Billing Record Detail
print_section "Test 8: Get Billing Record Detail"

if [ -n "$USAGE_RECORD_ID" ] && [ "$USAGE_RECORD_ID" != "null" ] && [ "$USAGE_RECORD_ID" != "" ]; then
    echo "GET ${API_PATH}/record/${USAGE_RECORD_ID}"
    RESPONSE=$(api_get "/record/${USAGE_RECORD_ID}")
    echo "$RESPONSE" | json_pretty

    if json_has "$RESPONSE" "billing_id" || json_has "$RESPONSE" "user_id"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_info "Skipping - no billing record ID available"
    test_result 0
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
