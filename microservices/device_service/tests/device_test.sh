#!/bin/bash

# Device CRUD Operations Testing Script
# Tests device registration, retrieval, update, and deletion

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
echo "Device Service CRUD Tests"
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
  "user_id": "test_user_device_123",
  "email": "devicetest@example.com",
  "organization_id": "org_test_123",
  "role": "admin",
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
        echo -e "${RED}Cannot proceed without authentication token${NC}"
        exit 1
    fi
else
    print_result 1 "Failed to generate test token"
    echo -e "${RED}Cannot proceed without authentication token${NC}"
    exit 1
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

# Test 2: Register Device
print_section "Test 2: Register Device"
DEVICE_ID=""
echo "POST ${API_BASE}"
REGISTER_PAYLOAD='{
  "device_name": "Test Smart Frame 001",
  "device_type": "smart_frame",
  "manufacturer": "TestCorp",
  "model": "SF-2024",
  "serial_number": "SN123456789TEST",
  "firmware_version": "1.0.0",
  "hardware_version": "1.0",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "connectivity_type": "wifi",
  "security_level": "standard",
  "location": {
    "latitude": 39.9042,
    "longitude": 116.4074,
    "address": "Beijing Test Location"
  },
  "metadata": {
    "test": true,
    "environment": "testing"
  },
  "tags": ["test", "smart_frame", "automated"]
}'
echo "Request Body:"
echo "$REGISTER_PAYLOAD" | jq '.'

REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$REGISTER_PAYLOAD")
HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    DEVICE_ID=$(echo "$RESPONSE_BODY" | jq -r '.device_id')
    if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
        print_result 0 "Device registered successfully"
        echo -e "${YELLOW}Device ID: ${DEVICE_ID}${NC}"
    else
        print_result 1 "Device registration returned 200 but no device_id found"
    fi
else
    print_result 1 "Failed to register device"
fi

# Test 3: Get Device Details
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 3: Get Device Details"
    echo "GET ${API_BASE}/${DEVICE_ID}"

    GET_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/${DEVICE_ID}" \
      -H "Authorization: Bearer ${JWT_TOKEN}")
    HTTP_CODE=$(echo "$GET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(echo "$RESPONSE_BODY" | jq -r '.device_id')
        if [ "$RETRIEVED_ID" = "$DEVICE_ID" ]; then
            print_result 0 "Device details retrieved successfully"
        else
            print_result 1 "Device ID mismatch in retrieved data"
        fi
    else
        print_result 1 "Failed to get device details"
    fi
else
    echo -e "${YELLOW}Skipping Test 3: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: Update Device
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 4: Update Device"
    echo "PUT ${API_BASE}/${DEVICE_ID}"
    UPDATE_PAYLOAD='{
      "device_name": "Updated Test Smart Frame 001",
      "firmware_version": "1.1.0",
      "status": "active",
      "location": {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "address": "New York Test Location"
      },
      "tags": ["test", "smart_frame", "automated", "updated"]
    }'
    echo "Request Body:"
    echo "$UPDATE_PAYLOAD" | jq '.'

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/${DEVICE_ID}" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$UPDATE_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        UPDATED_NAME=$(echo "$RESPONSE_BODY" | jq -r '.device_name')
        if [[ "$UPDATED_NAME" == *"Updated"* ]]; then
            print_result 0 "Device updated successfully"
        else
            print_result 1 "Device update did not reflect changes"
        fi
    else
        print_result 1 "Failed to update device"
    fi
else
    echo -e "${YELLOW}Skipping Test 4: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: List Devices
print_section "Test 5: List Devices"
echo "GET ${API_BASE}"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    COUNT=$(echo "$RESPONSE_BODY" | jq -r '.count')
    print_result 0 "Device list retrieved successfully (count: $COUNT)"
else
    print_result 1 "Failed to list devices"
fi

# Test 6: List Devices with Filters
print_section "Test 6: List Devices with Filters"
echo "GET ${API_BASE}?device_type=smart_frame&status=active"

FILTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}?device_type=smart_frame&status=active" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$FILTER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$FILTER_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Filtered device list retrieved successfully"
else
    print_result 1 "Failed to retrieve filtered device list"
fi

# Test 7: Get Device Stats
print_section "Test 7: Get Device Statistics"
echo "GET ${API_BASE}/stats"

STATS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/stats" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Device statistics retrieved successfully"
else
    print_result 1 "Failed to get device statistics"
fi

# Test 8: Get Device Health
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 8: Get Device Health"
    echo "GET ${API_BASE}/${DEVICE_ID}/health"

    HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/${DEVICE_ID}/health" \
      -H "Authorization: Bearer ${JWT_TOKEN}")
    HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        HEALTH_SCORE=$(echo "$RESPONSE_BODY" | jq -r '.health_score')
        print_result 0 "Device health retrieved successfully (score: $HEALTH_SCORE)"
    else
        print_result 1 "Failed to get device health"
    fi
else
    echo -e "${YELLOW}Skipping Test 8: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 9: Decommission Device
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 9: Decommission Device"
    echo "DELETE ${API_BASE}/${DEVICE_ID}"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/${DEVICE_ID}" \
      -H "Authorization: Bearer ${JWT_TOKEN}")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Device decommissioned successfully"
    else
        print_result 1 "Failed to decommission device"
    fi
else
    echo -e "${YELLOW}Skipping Test 9: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 10: Unauthorized Access (no token)
print_section "Test 10: Unauthorized Access (should fail)"
echo "GET ${API_BASE}"

UNAUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}")
HTTP_CODE=$(echo "$UNAUTH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$UNAUTH_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "401" ]; then
    print_result 0 "Unauthorized access rejected correctly"
else
    print_result 1 "Unauthorized access handling failed"
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
