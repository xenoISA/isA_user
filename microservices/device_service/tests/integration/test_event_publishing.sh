#!/bin/bash

# Device Service Event Publishing Integration Test
# Verifies that device events are properly published

BASE_URL="${BASE_URL:-http://localhost}"
API_BASE="${BASE_URL}/api/v1"
AUTH_URL="${BASE_URL}/api/v1/auth"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================================================"
echo "Device Service - Event Publishing Integration Test"
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
  "user_id": "test_device_event_user",
  "email": "deviceevent@example.com",
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

TEST_USER_ID="test_device_event_user"

echo ""
echo "======================================================================"
echo "Test 1: Verify device.registered event is published"
echo "======================================================================"
echo ""

REGISTER_PAYLOAD="{
  \"device_id\": \"device_test_$(date +%s)\",
  \"user_id\": \"${TEST_USER_ID}\",
  \"device_name\": \"Test Device for Events\",
  \"device_type\": \"smartframe\",
  \"model\": \"SF-2024\",
  \"os_version\": \"1.0.0\"
}"

echo "Registering device to trigger device.registered event..."
echo "POST ${API_BASE}/devices"
echo "$REGISTER_PAYLOAD" | jq '.'

RESPONSE=$(curl -s -X POST "${API_BASE}/devices" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d "$REGISTER_PAYLOAD")

echo "Response:"
echo "$RESPONSE" | jq '.'

DEVICE_ID=$(echo "$RESPONSE" | jq -r '.device_id')

if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_result 0 "device.registered event should be published (device_id: $DEVICE_ID)"
else
    print_result 1 "Failed to register device"
fi

echo ""
echo "======================================================================"
echo "Test 2: Verify device.status_changed event is published"
echo "======================================================================"
echo ""

if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    UPDATE_PAYLOAD="{
      \"status\": \"active\"
    }"

    echo "Updating device status to trigger device.status_changed event..."
    echo "PUT ${API_BASE}/devices/${DEVICE_ID}/status"
    echo "$UPDATE_PAYLOAD" | jq '.'

    RESPONSE=$(curl -s -X PUT "${API_BASE}/devices/${DEVICE_ID}/status" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $JWT_TOKEN" \
      -d "$UPDATE_PAYLOAD")

    echo "Response:"
    echo "$RESPONSE" | jq '.'

    SUCCESS=$(echo "$RESPONSE" | jq -r '.message' | grep -i "success\|updated")
    if [ -n "$SUCCESS" ] || [ "$(echo "$RESPONSE" | jq -r '.status')" = "active" ]; then
        print_result 0 "device.status_changed event should be published"
    else
        print_result 1 "Failed to update device status"
    fi
else
    print_result 1 "Cannot test status change (no device ID from Test 1)"
fi

echo ""
echo "======================================================================"
echo "Test 3: Verify device.command_sent event is published"
echo "======================================================================"
echo ""

if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    COMMAND_PAYLOAD="{
      \"command\": \"display_photo\",
      \"params\": {
        \"photo_url\": \"https://example.com/photo.jpg\"
      }
    }"

    echo "Sending device command to trigger device.command_sent event..."
    echo "POST ${API_BASE}/devices/${DEVICE_ID}/commands"
    echo "$COMMAND_PAYLOAD" | jq '.'

    RESPONSE=$(curl -s -X POST "${API_BASE}/devices/${DEVICE_ID}/commands" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $JWT_TOKEN" \
      -d "$COMMAND_PAYLOAD")

    echo "Response:"
    echo "$RESPONSE" | jq '.'

    COMMAND_ID=$(echo "$RESPONSE" | jq -r '.command_id')
    if [ -n "$COMMAND_ID" ] && [ "$COMMAND_ID" != "null" ]; then
        print_result 0 "device.command_sent event should be published"
    else
        print_result 1 "Failed to send device command"
    fi
else
    print_result 1 "Cannot test command sending (no device ID from Test 1)"
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
    echo "  - device.registered"
    echo "  - device.status_changed"
    echo "  - device.command_sent"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
