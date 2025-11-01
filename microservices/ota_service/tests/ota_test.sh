#!/bin/bash

# OTA Service Test Script
# Tests firmware management, update campaigns, device updates, and rollback operations

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE="http://localhost:8221"
AUTH_SERVICE_BASE="http://localhost:8201"
DEVICE_SERVICE_BASE="http://localhost:8220"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Variables to store test data
TEST_TOKEN=""
FIRMWARE_ID=""
CAMPAIGN_ID=""
UPDATE_ID=""
TEST_DEVICE_ID=""

# Helper function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

# Helper function to increment test counter
increment_test() {
    ((TOTAL_TESTS++))
}

# Helper function to mark test as passed
pass_test() {
    ((TESTS_PASSED++))
    echo -e "${GREEN}✓ PASSED${NC}: $1"
}

# Helper function to mark test as failed
fail_test() {
    ((TESTS_FAILED++))
    echo -e "${RED}✗ FAILED${NC}: $1"
}

# Start tests
echo "======================================================================"
echo "OTA Service Test Suite"
echo "======================================================================"
echo ""

# ======================
# Test 0: Generate Test Token
# ======================
print_section "Test 0: Generate Test Token from Auth Service"
increment_test

echo "POST ${AUTH_SERVICE_BASE}/api/v1/auth/dev-token"
TOKEN_RESPONSE=$(curl -s -X POST "${AUTH_SERVICE_BASE}/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_ota_user_123",
    "email": "ota_test@example.com",
    "organization_id": "org_test_ota",
    "role": "admin",
    "expires_in": 3600
  }')

echo "Response:"
echo "$TOKEN_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${AUTH_SERVICE_BASE}/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_ota_user_123", "email": "ota_test@example.com", "role": "admin"}')

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    TEST_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.token')
    echo -e "${YELLOW}Token (first 50 chars): ${TEST_TOKEN:0:50}...${NC}"
    pass_test "Test token generated successfully"
else
    fail_test "Failed to generate test token"
    echo "Cannot proceed without authentication token"
    exit 1
fi

# ======================
# Test 1: Health Check
# ======================
print_section "Test 1: Health Check"
increment_test

echo "GET ${API_BASE}/health"
HEALTH_RESPONSE=$(curl -s "${API_BASE}/health")
echo "Response:"
echo "$HEALTH_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/health")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Health check successful"
else
    fail_test "Health check failed"
fi

# ======================
# Test 2: Detailed Health Check
# ======================
print_section "Test 2: Detailed Health Check"
increment_test

echo "GET ${API_BASE}/health/detailed"
DETAILED_HEALTH_RESPONSE=$(curl -s "${API_BASE}/health/detailed" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$DETAILED_HEALTH_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/health/detailed" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Detailed health check successful"
else
    fail_test "Detailed health check failed"
fi

# ======================
# Test 3: Get Service Stats
# ======================
print_section "Test 3: Get Service Statistics"
increment_test

echo "GET ${API_BASE}/api/v1/service/stats"
SERVICE_STATS_RESPONSE=$(curl -s "${API_BASE}/api/v1/service/stats")
echo "Response:"
echo "$SERVICE_STATS_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/service/stats")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Service statistics retrieved successfully"
else
    fail_test "Failed to get service statistics"
fi

# ======================
# Test 4: Upload Firmware (requires multipart/form-data)
# ======================
print_section "Test 4: Upload Firmware"
increment_test

echo "POST ${API_BASE}/api/v1/firmware"

# Create a temporary firmware file for testing
TMP_FIRMWARE="/tmp/test_firmware_$(date +%s).bin"
echo "Test firmware content v1.0.0" > "$TMP_FIRMWARE"

# Calculate checksums
MD5_SUM=$(md5 -q "$TMP_FIRMWARE" 2>/dev/null || md5sum "$TMP_FIRMWARE" | cut -d' ' -f1)
SHA256_SUM=$(shasum -a 256 "$TMP_FIRMWARE" | cut -d' ' -f1)

echo -e "${YELLOW}Calculated MD5: ${MD5_SUM}${NC}"
echo -e "${YELLOW}Calculated SHA256: ${SHA256_SUM}${NC}"

FIRMWARE_METADATA='{
  "name": "TestFirmware",
  "version": "1.0.0",
  "device_model": "SmartFrame-Pro",
  "manufacturer": "TestCorp",
  "checksum_md5": "'$MD5_SUM'",
  "checksum_sha256": "'$SHA256_SUM'",
  "description": "Test firmware upload",
  "changelog": "Test release",
  "is_beta": false,
  "is_security_update": false
}'

FIRMWARE_UPLOAD_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/firmware" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -F "metadata=${FIRMWARE_METADATA}" \
  -F "file=@${TMP_FIRMWARE}")

echo "Response:"
echo "$FIRMWARE_UPLOAD_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/firmware" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -F "metadata=${FIRMWARE_METADATA}" \
  -F "file=@${TMP_FIRMWARE}")

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    FIRMWARE_ID=$(echo "$FIRMWARE_UPLOAD_RESPONSE" | jq -r '.firmware_id // .id // "unknown"')
    echo -e "${YELLOW}Firmware ID: ${FIRMWARE_ID}${NC}"
    pass_test "Firmware uploaded successfully"
else
    fail_test "Failed to upload firmware"
    echo -e "${RED}Error details: $(echo "$FIRMWARE_UPLOAD_RESPONSE" | jq -r '.detail // .error // "Unknown error"')${NC}"
fi

# Clean up temporary file
rm -f "$TMP_FIRMWARE"

# ======================
# Test 5: List Firmware
# ======================
print_section "Test 5: List Firmware"
increment_test

echo "GET ${API_BASE}/api/v1/firmware"
FIRMWARE_LIST_RESPONSE=$(curl -s "${API_BASE}/api/v1/firmware" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$FIRMWARE_LIST_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/firmware" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    FIRMWARE_COUNT=$(echo "$FIRMWARE_LIST_RESPONSE" | jq -r '.count // 0')
    echo -e "${YELLOW}Firmware count: ${FIRMWARE_COUNT}${NC}"
    pass_test "Firmware list retrieved successfully"
else
    fail_test "Failed to get firmware list"
fi

# ======================
# Test 6: Get Firmware Details
# ======================
if [ -n "$FIRMWARE_ID" ] && [ "$FIRMWARE_ID" != "unknown" ]; then
    print_section "Test 6: Get Firmware Details"
    increment_test

    echo "GET ${API_BASE}/api/v1/firmware/${FIRMWARE_ID}"
    FIRMWARE_DETAILS_RESPONSE=$(curl -s "${API_BASE}/api/v1/firmware/${FIRMWARE_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "Response:"
    echo "$FIRMWARE_DETAILS_RESPONSE" | jq '.'
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/firmware/${FIRMWARE_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" == "200" ]; then
        pass_test "Firmware details retrieved successfully"
    else
        fail_test "Failed to get firmware details"
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: Test 6 - No firmware ID available${NC}"
fi

# ======================
# Test 7: Create Update Campaign
# ======================
if [ -n "$FIRMWARE_ID" ] && [ "$FIRMWARE_ID" != "unknown" ]; then
    print_section "Test 7: Create Update Campaign"
    increment_test

    echo "POST ${API_BASE}/api/v1/campaigns"
    CAMPAIGN_REQUEST='{
      "name": "Test OTA Campaign",
      "description": "Automated test campaign",
      "firmware_id": "'$FIRMWARE_ID'",
      "target_devices": ["device_test_001", "device_test_002"],
      "deployment_strategy": "staged",
      "priority": "normal",
      "schedule_start": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "rollout_percentage": 50,
      "rollout_stages": [
        {"stage": 1, "percentage": 10, "duration_hours": 1},
        {"stage": 2, "percentage": 50, "duration_hours": 2},
        {"stage": 3, "percentage": 100, "duration_hours": 4}
      ],
      "auto_rollback_enabled": true,
      "max_failure_rate": 10.0,
      "requires_approval": false
    }'

    CAMPAIGN_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/campaigns" \
      -H "Authorization: Bearer ${TEST_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$CAMPAIGN_REQUEST")

    echo "Response:"
    echo "$CAMPAIGN_RESPONSE" | jq '.'
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/campaigns" \
      -H "Authorization: Bearer ${TEST_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$CAMPAIGN_REQUEST")

    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
        CAMPAIGN_ID=$(echo "$CAMPAIGN_RESPONSE" | jq -r '.campaign_id // .id // "unknown"')
        echo -e "${YELLOW}Campaign ID: ${CAMPAIGN_ID}${NC}"
        pass_test "Update campaign created successfully"
    else
        fail_test "Failed to create update campaign"
        echo -e "${RED}Error details: $(echo "$CAMPAIGN_RESPONSE" | jq -r '.detail // .error // "Unknown error"')${NC}"
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: Test 7 - No firmware ID available${NC}"
fi

# ======================
# Test 8: Get Campaign Details
# ======================
if [ -n "$CAMPAIGN_ID" ] && [ "$CAMPAIGN_ID" != "unknown" ]; then
    print_section "Test 8: Get Campaign Details"
    increment_test

    echo "GET ${API_BASE}/api/v1/campaigns/${CAMPAIGN_ID}"
    CAMPAIGN_DETAILS_RESPONSE=$(curl -s "${API_BASE}/api/v1/campaigns/${CAMPAIGN_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "Response:"
    echo "$CAMPAIGN_DETAILS_RESPONSE" | jq '.'
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/campaigns/${CAMPAIGN_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" == "200" ]; then
        pass_test "Campaign details retrieved successfully"
    else
        fail_test "Failed to get campaign details"
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: Test 8 - No campaign ID available${NC}"
fi

# ======================
# Test 9: List Campaigns
# ======================
print_section "Test 9: List Campaigns"
increment_test

echo "GET ${API_BASE}/api/v1/campaigns"
CAMPAIGNS_LIST_RESPONSE=$(curl -s "${API_BASE}/api/v1/campaigns" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$CAMPAIGNS_LIST_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/campaigns" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Campaigns list retrieved successfully"
else
    fail_test "Failed to get campaigns list"
fi

# ======================
# Test 10: Start Campaign
# ======================
if [ -n "$CAMPAIGN_ID" ] && [ "$CAMPAIGN_ID" != "unknown" ]; then
    print_section "Test 10: Start Campaign"
    increment_test

    echo "POST ${API_BASE}/api/v1/campaigns/${CAMPAIGN_ID}/start"
    START_CAMPAIGN_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/campaigns/${CAMPAIGN_ID}/start" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "Response:"
    echo "$START_CAMPAIGN_RESPONSE" | jq '.'
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/campaigns/${CAMPAIGN_ID}/start" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" == "200" ]; then
        pass_test "Campaign started successfully"
    else
        fail_test "Failed to start campaign"
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: Test 10 - No campaign ID available${NC}"
fi

# ======================
# Test 11: Update Single Device
# ======================
if [ -n "$FIRMWARE_ID" ] && [ "$FIRMWARE_ID" != "unknown" ]; then
    print_section "Test 11: Update Single Device"
    increment_test

    TEST_DEVICE_ID="test_device_ota_$(date +%s)"
    echo "POST ${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/update"
    DEVICE_UPDATE_REQUEST='{
      "firmware_id": "'$FIRMWARE_ID'",
      "priority": "normal",
      "schedule_time": null,
      "force_update": false
    }'

    DEVICE_UPDATE_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/update" \
      -H "Authorization: Bearer ${TEST_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$DEVICE_UPDATE_REQUEST")

    echo "Response:"
    echo "$DEVICE_UPDATE_RESPONSE" | jq '.'
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/update" \
      -H "Authorization: Bearer ${TEST_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$DEVICE_UPDATE_REQUEST")

    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
        UPDATE_ID=$(echo "$DEVICE_UPDATE_RESPONSE" | jq -r '.update_id // .id // "unknown"')
        echo -e "${YELLOW}Update ID: ${UPDATE_ID}${NC}"
        pass_test "Device update initiated successfully"
    else
        fail_test "Failed to initiate device update"
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: Test 11 - No firmware ID available${NC}"
fi

# ======================
# Test 12: Get Update Progress
# ======================
if [ -n "$UPDATE_ID" ] && [ "$UPDATE_ID" != "unknown" ]; then
    print_section "Test 12: Get Update Progress"
    increment_test

    echo "GET ${API_BASE}/api/v1/updates/${UPDATE_ID}"
    UPDATE_PROGRESS_RESPONSE=$(curl -s "${API_BASE}/api/v1/updates/${UPDATE_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "Response:"
    echo "$UPDATE_PROGRESS_RESPONSE" | jq '.'
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/updates/${UPDATE_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" == "200" ]; then
        pass_test "Update progress retrieved successfully"
    else
        fail_test "Failed to get update progress"
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: Test 12 - No update ID available${NC}"
fi

# ======================
# Test 13: Get Device Update History
# ======================
if [ -n "$TEST_DEVICE_ID" ]; then
    print_section "Test 13: Get Device Update History"
    increment_test

    echo "GET ${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/updates"
    UPDATE_HISTORY_RESPONSE=$(curl -s "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/updates" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "Response:"
    echo "$UPDATE_HISTORY_RESPONSE" | jq '.'
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/updates" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" == "200" ]; then
        pass_test "Device update history retrieved successfully"
    else
        fail_test "Failed to get device update history"
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: Test 13 - No device ID available${NC}"
fi

# ======================
# Test 14: Get Update Statistics
# ======================
print_section "Test 14: Get Update Statistics"
increment_test

echo "GET ${API_BASE}/api/v1/stats"
UPDATE_STATS_RESPONSE=$(curl -s "${API_BASE}/api/v1/stats" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$UPDATE_STATS_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/stats" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Update statistics retrieved successfully"
else
    fail_test "Failed to get update statistics"
fi

# ======================
# Test 15: Rollback Device
# ======================
if [ -n "$TEST_DEVICE_ID" ]; then
    print_section "Test 15: Rollback Device"
    increment_test

    echo "POST ${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/rollback"
    ROLLBACK_REQUEST='{"to_version": "0.9.0", "reason": "Test rollback"}'

    ROLLBACK_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/rollback" \
      -H "Authorization: Bearer ${TEST_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$ROLLBACK_REQUEST")

    echo "Response:"
    echo "$ROLLBACK_RESPONSE" | jq '.'
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/rollback" \
      -H "Authorization: Bearer ${TEST_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$ROLLBACK_REQUEST")

    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" == "200" ]; then
        pass_test "Device rollback initiated successfully"
    else
        fail_test "Failed to rollback device"
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: Test 15 - No device ID available${NC}"
fi

# ======================
# Summary
# ======================
echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Total: $TOTAL_TESTS"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed successfully!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
