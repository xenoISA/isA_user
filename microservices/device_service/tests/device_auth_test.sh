#!/bin/bash

# Device Authentication Testing Script
# Tests device authentication flow and token management

BASE_URL="http://localhost:8220"
API_BASE="${BASE_URL}/api/v1/devices"
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
echo "Device Authentication Tests"
echo "======================================================================"
echo ""

# Get organization ID - either from command line or use default
if [ -n "$1" ]; then
    ORG_ID="$1"
    echo -e "${CYAN}Using provided organization: $ORG_ID${NC}"
else
    ORG_ID="org_test_123"
    echo -e "${YELLOW}Using default organization: $ORG_ID${NC}"
fi

# Generate unique device ID for this test run
TEST_DEVICE_ID="test_device_$(date +%s)"

echo -e "${BLUE}Testing with Organization: $ORG_ID${NC}"
echo -e "${BLUE}Device ID: $TEST_DEVICE_ID${NC}"
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

# Test 1: Register Device in Auth Service
print_section "Test 1: Register Device in Auth Service"
echo "POST ${AUTH_URL}/device/register"
REGISTER_PAYLOAD="{
  \"device_id\": \"$TEST_DEVICE_ID\",
  \"organization_id\": \"$ORG_ID\",
  \"device_name\": \"Test Smart Frame Auth\",
  \"device_type\": \"smart_frame\",
  \"metadata\": {
    \"model\": \"SF-2024\",
    \"firmware\": \"1.0.0\"
  },
  \"expires_days\": 365
}"
echo "Request Body:"
echo "$REGISTER_PAYLOAD" | jq '.'

REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_URL}/device/register" \
  -H "Content-Type: application/json" \
  -d "$REGISTER_PAYLOAD")
HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

DEVICE_SECRET=""
if [ "$HTTP_CODE" = "200" ]; then
    DEVICE_SECRET=$(echo "$RESPONSE_BODY" | jq -r '.device_secret')
    if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
        print_result 0 "Device registered in auth service"
        echo -e "${YELLOW}Device Secret (first 20 chars): ${DEVICE_SECRET:0:20}...${NC}"
    else
        print_result 1 "Device registration failed - no secret returned"
    fi
else
    print_result 1 "Device registration failed in auth service"
    echo -e "${YELLOW}Note: Organization $ORG_ID may not exist. Run with existing org_id.${NC}"
fi

# Test 2: Authenticate Device via Device Service
if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
    print_section "Test 2: Authenticate Device via Device Service"
    echo "POST ${API_BASE}/auth"
    AUTH_PAYLOAD="{
  \"device_id\": \"$TEST_DEVICE_ID\",
  \"device_secret\": \"$DEVICE_SECRET\"
}"
    echo "Request Body:"
    echo "$AUTH_PAYLOAD" | jq '.'

    AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth" \
      -H "Content-Type: application/json" \
      -d "$AUTH_PAYLOAD")
    HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$AUTH_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    DEVICE_TOKEN=""
    if [ "$HTTP_CODE" = "200" ]; then
        DEVICE_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.access_token')
        if [ -n "$DEVICE_TOKEN" ] && [ "$DEVICE_TOKEN" != "null" ]; then
            print_result 0 "Device authenticated successfully"
            echo -e "${YELLOW}Access Token (first 50 chars): ${DEVICE_TOKEN:0:50}...${NC}"
        else
            print_result 1 "Authentication returned 200 but no token"
        fi
    else
        print_result 1 "Device authentication failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No device secret available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Authenticate with Invalid Secret
if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
    print_section "Test 3: Authenticate with Invalid Secret (should fail)"
    echo "POST ${API_BASE}/auth"
    INVALID_AUTH_PAYLOAD="{
  \"device_id\": \"$TEST_DEVICE_ID\",
  \"device_secret\": \"invalid_secret_12345\"
}"
    echo "Request Body:"
    echo "$INVALID_AUTH_PAYLOAD" | jq '.'

    INVALID_AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth" \
      -H "Content-Type: application/json" \
      -d "$INVALID_AUTH_PAYLOAD")
    HTTP_CODE=$(echo "$INVALID_AUTH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$INVALID_AUTH_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "401" ]; then
        print_result 0 "Invalid credentials rejected correctly"
    else
        print_result 1 "Invalid credentials handling failed"
    fi
else
    echo -e "${YELLOW}Skipping Test 3: No device registered${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: Authenticate Non-Existent Device
print_section "Test 4: Authenticate Non-Existent Device (should fail)"
echo "POST ${API_BASE}/auth"
NONEXIST_AUTH_PAYLOAD='{
  "device_id": "nonexistent_device_999",
  "device_secret": "fake_secret"
}'
echo "Request Body:"
echo "$NONEXIST_AUTH_PAYLOAD" | jq '.'

NONEXIST_AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth" \
  -H "Content-Type: application/json" \
  -d "$NONEXIST_AUTH_PAYLOAD")
HTTP_CODE=$(echo "$NONEXIST_AUTH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$NONEXIST_AUTH_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "401" ]; then
    print_result 0 "Non-existent device rejected correctly"
else
    print_result 1 "Non-existent device handling failed"
fi

# Test 5: Use Device Token for API Access
if [ -n "$DEVICE_TOKEN" ] && [ "$DEVICE_TOKEN" != "null" ]; then
    print_section "Test 5: Use Device Token for API Access"
    echo "GET ${BASE_URL}/api/v1/service/stats"

    STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/service/stats" \
      -H "Authorization: Bearer ${DEVICE_TOKEN}")
    HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Device token accepted for API access"
    else
        print_result 1 "Device token not accepted for API access"
    fi
else
    echo -e "${YELLOW}Skipping Test 5: No device token available${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: Revoke Device (cleanup)
if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "null" ]; then
    print_section "Test 6: Revoke Device (Cleanup)"
    echo "DELETE ${AUTH_URL}/device/${TEST_DEVICE_ID}?organization_id=${ORG_ID}"

    REVOKE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE \
      "${AUTH_URL}/device/${TEST_DEVICE_ID}?organization_id=${ORG_ID}")
    HTTP_CODE=$(echo "$REVOKE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$REVOKE_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Device revoked successfully (cleanup)"
    else
        print_result 1 "Failed to revoke device"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No device to revoke${NC}"
    ((TESTS_FAILED++))
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
    echo -e "${YELLOW}Some tests failed.${NC}"
    echo -e "${YELLOW}Note: If organization not found, run with: ./device_auth_test.sh <existing_org_id>${NC}"
    exit 1
fi
