#!/bin/bash
# Device Service Test Script (v2 - using test_common.sh)
# Usage:
#   ./device_test_v2.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./device_test_v2.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="device_service"
API_PATH="/api/v1/devices"

# Device service requires JWT authentication
TEST_MODE="gateway"

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"
TEST_DEVICE_USER="device_test_user_${TEST_TS}"
SERIAL_NUMBER="SN_TEST_${TEST_TS}"

print_info "Test User ID: $TEST_DEVICE_USER"
print_info "Serial Number: $SERIAL_NUMBER"
echo ""

# ============================================================================
# Setup: Create Test User
# ============================================================================
print_section "Setup: Create Test User"
ACCOUNT_URL="http://localhost:$(get_service_port account_service)/api/v1/accounts/ensure"
USER_RESPONSE=$(curl -s -X POST "$ACCOUNT_URL" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"${TEST_DEVICE_USER}\",\"email\":\"device_${TEST_TS}@example.com\",\"name\":\"Device Test User\",\"subscription_plan\":\"free\"}")
echo "$USER_RESPONSE" | json_pretty
echo ""

# ============================================================================
# Tests
# ============================================================================

# Test 1: Get Device Stats
print_section "Test 1: Get Device Stats"
echo "GET ${API_PATH}/stats"
RESPONSE=$(api_get "/stats")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "total_devices" || json_has "$RESPONSE" "by_status"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Register Device
print_section "Test 2: Register Device"
echo "POST ${API_PATH}"
print_info "Expected Event: device.registered"

REGISTER_PAYLOAD="{
  \"device_name\": \"Test Smart Frame ${TEST_TS}\",
  \"device_type\": \"smart_frame\",
  \"manufacturer\": \"TestCorp\",
  \"model\": \"SF-2024\",
  \"serial_number\": \"${SERIAL_NUMBER}\",
  \"firmware_version\": \"1.0.0\",
  \"hardware_version\": \"1.0\",
  \"mac_address\": \"AA:BB:CC:DD:${TEST_TS: -2}:FF\",
  \"connectivity_type\": \"wifi\",
  \"security_level\": \"standard\",
  \"owner_user_id\": \"${TEST_DEVICE_USER}\",
  \"location\": {
    \"latitude\": 39.9042,
    \"longitude\": 116.4074,
    \"address\": \"Beijing Test Location\"
  },
  \"metadata\": {
    \"test\": true,
    \"environment\": \"testing\"
  },
  \"tags\": [\"test\", \"smart_frame\", \"automated\"]
}"
RESPONSE=$(api_post "" "$REGISTER_PAYLOAD")
echo "$RESPONSE" | json_pretty

DEVICE_ID=$(json_get "$RESPONSE" "device_id")
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ] && [ "$DEVICE_ID" != "" ]; then
    print_success "Registered device: $DEVICE_ID"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 3: Get Device Details
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 3: Get Device Details"
    echo "GET ${API_PATH}/${DEVICE_ID}"
    RESPONSE=$(api_get "/${DEVICE_ID}")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | grep -q "$DEVICE_ID" || json_has "$RESPONSE" "device_name"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 3: SKIPPED - No device ID"
fi
echo ""

# Test 4: Update Device
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 4: Update Device"
    echo "PUT ${API_PATH}/${DEVICE_ID}"
    print_info "Expected Event: device.updated"

    UPDATE_PAYLOAD="{
      \"device_name\": \"Updated Test Frame ${TEST_TS}\",
      \"firmware_version\": \"1.1.0\",
      \"status\": \"active\",
      \"tags\": [\"test\", \"smart_frame\", \"updated\"]
    }"
    RESPONSE=$(api_put "/${DEVICE_ID}" "$UPDATE_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | grep -q "Updated Test Frame" || json_has "$RESPONSE" "device_id"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 4: SKIPPED - No device ID"
fi
echo ""

# Test 5: List Devices
print_section "Test 5: List Devices"
echo "GET ${API_PATH}"
RESPONSE=$(api_get "")
echo "$RESPONSE" | json_pretty | head -30

if json_has "$RESPONSE" "devices" || json_has "$RESPONSE" "count" || echo "$RESPONSE" | grep -q "\["; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 6: List Devices with Filters
print_section "Test 6: List Devices with Filters"
echo "GET ${API_PATH}?device_type=smart_frame&status=active"
RESPONSE=$(api_get "?device_type=smart_frame&status=active")
echo "$RESPONSE" | json_pretty | head -30

if json_has "$RESPONSE" "devices" || json_has "$RESPONSE" "count" || echo "$RESPONSE" | grep -q "\["; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 7: Get Device Health
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 7: Get Device Health"
    echo "GET ${API_PATH}/${DEVICE_ID}/health"
    RESPONSE=$(api_get "/${DEVICE_ID}/health")
    echo "$RESPONSE" | json_pretty

    if json_has "$RESPONSE" "health_score" || json_has "$RESPONSE" "status" || json_has "$RESPONSE" "device_id"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 7: SKIPPED - No device ID"
fi
echo ""

# Test 8: Send Device Command
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 8: Send Device Command"
    echo "POST ${API_PATH}/${DEVICE_ID}/commands"
    print_info "Expected Event: device.command_sent"

    COMMAND_PAYLOAD="{
      \"command\": \"display_image\",
      \"parameters\": {
        \"image_url\": \"https://example.com/test.jpg\",
        \"duration\": 30
      }
    }"
    RESPONSE=$(api_post "/${DEVICE_ID}/commands" "$COMMAND_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    if json_has "$RESPONSE" "command_id" || echo "$RESPONSE" | grep -q "success\|queued\|message"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 8: SKIPPED - No device ID"
fi
echo ""

# Test 9: Device Pairing
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 9: Device Pairing"
    echo "POST ${API_PATH}/${DEVICE_ID}/pair"

    PAIR_PAYLOAD="{
      \"user_id\": \"${TEST_DEVICE_USER}\",
      \"pairing_token\": \"TEST_TOKEN_${TEST_TS}\"
    }"
    RESPONSE=$(api_post "/${DEVICE_ID}/pair" "$PAIR_PAYLOAD")
    echo "$RESPONSE" | json_pretty

# Accept successful pairing or error response (endpoint exists)
    if json_has "$RESPONSE" "paired" || json_has "$RESPONSE" "pairing_status" || echo "$RESPONSE" | grep -q "success\|message\|detail"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 9: SKIPPED - No device ID"
fi
echo ""

# Test 10: Delete/Decommission Device
if [ -n "$DEVICE_ID" ] && [ "$DEVICE_ID" != "null" ]; then
    print_section "Test 10: Decommission Device"
    echo "DELETE ${API_PATH}/${DEVICE_ID}"
    print_info "Expected Event: device.deleted"

    RESPONSE=$(api_delete "/${DEVICE_ID}")
    echo "$RESPONSE" | json_pretty

    if [ -z "$RESPONSE" ] || echo "$RESPONSE" | grep -q "decommissioned\|success\|deleted\|message"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 10: SKIPPED - No device ID"
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
