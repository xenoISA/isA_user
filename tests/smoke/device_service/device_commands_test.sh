#!/bin/bash

# Device Commands Testing Script
# Tests device command sending and smart frame operations

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1/devices"
AUTH_URL="http://localhost/api/v1/auth"

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
echo "Device Commands & Smart Frame Tests"
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
print_section "Test 0: Generate Test Token"
echo "POST ${AUTH_URL}/dev-token"
TOKEN_PAYLOAD='{
  "user_id": "test_user_commands_123",
  "email": "commands@example.com",
  "organization_id": "org_test_001",
  "role": "admin",
  "expires_in": 3600
}'

TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_URL}/dev-token" \
  -H "Content-Type: application/json" \
  -d "$TOKEN_PAYLOAD")
HTTP_CODE=$(echo "$TOKEN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')

JWT_TOKEN=""
if [ "$HTTP_CODE" = "200" ]; then
    JWT_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.token')
    if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
        print_result 0 "Test token generated"
    else
        print_result 1 "Token generation failed"
        exit 1
    fi
else
    print_result 1 "Failed to generate test token"
    exit 1
fi

# Create a test device for commands
TEST_DEVICE_ID="test_cmd_device_$(date +%s)"

# Test 1: Register Device for Command Testing
print_section "Test 1: Register Test Device"
echo "POST ${API_BASE}"
REGISTER_PAYLOAD="{
  \"device_name\": \"Test Command Device\",
  \"device_type\": \"smart_frame\",
  \"manufacturer\": \"TestCorp\",
  \"model\": \"SF-CMD-2024\",
  \"serial_number\": \"SN_CMD_$TEST_DEVICE_ID\",
  \"firmware_version\": \"1.0.0\",
  \"connectivity_type\": \"wifi\",
  \"security_level\": \"standard\"
}"

REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$REGISTER_PAYLOAD")
HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

DEVICE_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    DEVICE_ID=$(echo "$RESPONSE_BODY" | jq -r '.device_id')
    print_result 0 "Test device registered"
    echo -e "${YELLOW}Device ID: ${DEVICE_ID}${NC}"
else
    print_result 1 "Failed to register test device"
fi

# Test 2: Send Basic Command
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 2: Send Basic Command"
    echo "POST ${API_BASE}/${DEVICE_ID}/commands"
    COMMAND_PAYLOAD='{
      "command": "status_check",
      "parameters": {
        "include_diagnostics": true
      },
      "timeout": 30,
      "priority": 5,
      "require_ack": true
    }'
    echo "Request Body:"
    echo "$COMMAND_PAYLOAD" | jq '.'

    COMMAND_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/${DEVICE_ID}/commands" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$COMMAND_PAYLOAD")
    HTTP_CODE=$(echo "$COMMAND_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$COMMAND_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        COMMAND_ID=$(echo "$RESPONSE_BODY" | jq -r '.command_id')
        if [ -n "$COMMAND_ID" ] && [ "$COMMAND_ID" != "null" ]; then
            print_result 0 "Basic command sent successfully"
        else
            print_result 1 "Command sent but no command_id returned"
        fi
    else
        print_result 1 "Failed to send basic command"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Send Reboot Command
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 3: Send Reboot Command"
    echo "POST ${API_BASE}/${DEVICE_ID}/commands"
    REBOOT_PAYLOAD='{
      "command": "reboot",
      "parameters": {
        "delay_seconds": 5,
        "reason": "Testing"
      },
      "timeout": 60,
      "priority": 8,
      "require_ack": true
    }'

    REBOOT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/${DEVICE_ID}/commands" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$REBOOT_PAYLOAD")
    HTTP_CODE=$(echo "$REBOOT_RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Reboot command sent successfully"
    else
        print_result 1 "Failed to send reboot command"
    fi
else
    echo -e "${YELLOW}Skipping Test 3: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: List Smart Frames
print_section "Test 4: List Smart Frames"
echo "GET ${API_BASE}/frames"

FRAMES_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/frames" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$FRAMES_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$FRAMES_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Smart frames list retrieved"
else
    print_result 1 "Failed to retrieve smart frames list"
fi

# Test 5: Control Frame Display
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 5: Control Frame Display"
    echo "POST ${API_BASE}/frames/${DEVICE_ID}/display"
    DISPLAY_PAYLOAD='{
      "action": "display_photo",
      "photo_id": "test_photo_123",
      "transition": "fade",
      "duration": 10
    }'
    echo "Request Body:"
    echo "$DISPLAY_PAYLOAD" | jq '.'

    DISPLAY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/frames/${DEVICE_ID}/display" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$DISPLAY_PAYLOAD")
    HTTP_CODE=$(echo "$DISPLAY_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DISPLAY_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Frame display command sent"
    else
        print_result 1 "Failed to send frame display command"
    fi
else
    echo -e "${YELLOW}Skipping Test 5: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: Sync Frame Content
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 6: Sync Frame Content"
    echo "POST ${API_BASE}/frames/${DEVICE_ID}/sync"
    SYNC_PAYLOAD='{
      "album_ids": ["album_123", "album_456"],
      "sync_type": "incremental",
      "force": false
    }'
    echo "Request Body:"
    echo "$SYNC_PAYLOAD" | jq '.'

    SYNC_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/frames/${DEVICE_ID}/sync" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$SYNC_PAYLOAD")
    HTTP_CODE=$(echo "$SYNC_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$SYNC_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Frame sync command sent"
    else
        print_result 1 "Failed to send frame sync command"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Update Frame Config
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 7: Update Frame Config"
    echo "PUT ${API_BASE}/frames/${DEVICE_ID}/config"
    CONFIG_PAYLOAD='{
      "brightness": 85,
      "auto_brightness": true,
      "slideshow_interval": 60,
      "display_mode": "photo_slideshow",
      "orientation": "auto"
    }'
    echo "Request Body:"
    echo "$CONFIG_PAYLOAD" | jq '.'

    CONFIG_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/frames/${DEVICE_ID}/config" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$CONFIG_PAYLOAD")
    HTTP_CODE=$(echo "$CONFIG_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$CONFIG_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Frame config updated"
    else
        print_result 1 "Failed to update frame config"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Bulk Send Commands
print_section "Test 8: Bulk Send Commands"
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    echo "POST ${API_BASE}/bulk/commands"
    # Updated to use flattened structure instead of nested command object
    BULK_PAYLOAD="{
      \"device_ids\": [\"$DEVICE_ID\"],
      \"command\": \"update_firmware\",
      \"parameters\": {
        \"version\": \"1.2.0\",
        \"auto_restart\": true
      },
      \"timeout\": 300,
      \"priority\": 7,
      \"require_ack\": true
    }"
    echo "Request Body:"
    echo "$BULK_PAYLOAD" | jq '.'

    BULK_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/bulk/commands" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$BULK_PAYLOAD")
    HTTP_CODE=$(echo "$BULK_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$BULK_RESPONSE" | sed '$d')

    echo "Response:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RESULTS_COUNT=$(echo "$RESPONSE_BODY" | jq -r '.results | length')
        print_result 0 "Bulk commands sent (results: $RESULTS_COUNT)"
    else
        print_result 1 "Failed to send bulk commands"
    fi
else
    echo -e "${YELLOW}Skipping Test 8: No device ID available${NC}"
    ((TESTS_FAILED++))
fi

# Cleanup: Delete test device
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Cleanup: Delete Test Device"
    echo "DELETE ${API_BASE}/${DEVICE_ID}"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/${DEVICE_ID}" \
      -H "Authorization: Bearer ${JWT_TOKEN}")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}Test device deleted successfully${NC}"
    else
        echo -e "${YELLOW}Warning: Failed to delete test device${NC}"
    fi
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
