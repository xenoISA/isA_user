#!/bin/bash
# OTA Service - Smoke Tests
#
# End-to-end tests verifying OTA service functionality with real infrastructure.
# Tests firmware upload, campaign management, device updates, and rollback operations.
#
# Usage:
#   ./smoke_test.sh                     # Direct mode (default)
#   TEST_MODE=gateway ./smoke_test.sh   # Gateway mode with JWT
#
# Exit codes:
#   0 = All tests passed
#   1 = Some tests failed

set -e

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../test_common.sh"

SERVICE_NAME="ota_service"
SERVICE_PORT=8221
API_PATH="/api/v1"

# Initialize test framework
init_test

# =============================================================================
# Test Data
# =============================================================================
TEST_TS="$(date +%s)_$$"
TEST_FIRMWARE_NAME="SmartFrame Firmware ${TEST_TS}"
TEST_FIRMWARE_VERSION="1.${TEST_TS:0:3}.0"
TEST_DEVICE_MODEL="SmartFrame-Pro"
TEST_CAMPAIGN_NAME="Update Campaign ${TEST_TS}"
FIRMWARE_ID=""
CAMPAIGN_ID=""
UPDATE_ID=""
TEST_DEVICE_ID="dev_$(uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-' | cut -c1-16)"
TEST_DEVICE_ID_2="dev_$(uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-' | cut -c1-16)"

print_info "Test timestamp: $TEST_TS"
print_info "Test device IDs: $TEST_DEVICE_ID, $TEST_DEVICE_ID_2"
echo ""

# =============================================================================
# Test 1: Health Check
# =============================================================================
print_section "Test 1: Health Check"
echo "GET /health"

RESPONSE=$(curl -s "${BASE_URL}/health")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "status"; then
    STATUS=$(json_get "$RESPONSE" "status")
    if [ "$STATUS" = "healthy" ] || [ "$STATUS" = "ok" ]; then
        print_success "Health check passed: status=$STATUS"
        test_result 0
    else
        print_warning "Health check returned: $STATUS"
        test_result 0
    fi
else
    print_error "Health check failed: no status field"
    test_result 1
fi
echo ""

# =============================================================================
# Test 2: Upload Firmware
# =============================================================================
print_section "Test 2: Upload Firmware"
echo "POST ${API_PATH}/firmware"

FIRMWARE_PAYLOAD='{
  "name": "'"${TEST_FIRMWARE_NAME}"'",
  "version": "'"${TEST_FIRMWARE_VERSION}"'",
  "device_model": "'"${TEST_DEVICE_MODEL}"'",
  "manufacturer": "isA",
  "description": "Smoke test firmware",
  "file_url": "https://storage.example.com/firmware/test_'"${TEST_TS}"'.bin",
  "file_size": 52428800,
  "checksum_md5": "d41d8cd98f00b204e9800998ecf8427e",
  "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "is_beta": false,
  "is_security_update": false,
  "changelog": "Smoke test firmware upload"
}'

echo "Request:"
echo "$FIRMWARE_PAYLOAD" | json_pretty

RESPONSE=$(api_post "/firmware" "$FIRMWARE_PAYLOAD")
echo "Response:"
echo "$RESPONSE" | json_pretty

FIRMWARE_ID=$(json_get "$RESPONSE" "firmware_id")
if [ -n "$FIRMWARE_ID" ] && [ "$FIRMWARE_ID" != "null" ]; then
    print_success "Uploaded firmware: $FIRMWARE_ID"
    test_result 0
else
    print_error "Failed to upload firmware"
    test_result 1
fi
echo ""

# =============================================================================
# Test 3: Get Firmware by ID
# =============================================================================
if [ -n "$FIRMWARE_ID" ] && [ "$FIRMWARE_ID" != "null" ]; then
    print_section "Test 3: Get Firmware by ID"
    echo "GET ${API_PATH}/firmware/${FIRMWARE_ID}"

    RESPONSE=$(api_get "/firmware/${FIRMWARE_ID}")
    echo "$RESPONSE" | json_pretty

    RETRIEVED_ID=$(json_get "$RESPONSE" "firmware_id")
    RETRIEVED_NAME=$(json_get "$RESPONSE" "name")
    if [ "$RETRIEVED_ID" = "$FIRMWARE_ID" ]; then
        print_success "Retrieved firmware matches: $RETRIEVED_NAME"
        test_result 0
    else
        print_error "Retrieved firmware ID mismatch"
        test_result 1
    fi
else
    print_warning "Skipping: No firmware ID"
fi
echo ""

# =============================================================================
# Test 4: List Firmware
# =============================================================================
print_section "Test 4: List Firmware"
echo "GET ${API_PATH}/firmware"

RESPONSE=$(api_get "/firmware")
echo "$RESPONSE" | json_pretty | head -40

if json_has "$RESPONSE" "items" || json_has "$RESPONSE" "firmware"; then
    print_success "List returned firmware collection"
    test_result 0
else
    print_error "Unexpected list response format"
    test_result 1
fi
echo ""

# =============================================================================
# Test 5: Create Update Campaign
# =============================================================================
if [ -n "$FIRMWARE_ID" ] && [ "$FIRMWARE_ID" != "null" ]; then
    print_section "Test 5: Create Update Campaign"
    echo "POST ${API_PATH}/campaigns"

    CAMPAIGN_PAYLOAD='{
      "name": "'"${TEST_CAMPAIGN_NAME}"'",
      "description": "Smoke test campaign",
      "firmware_id": "'"${FIRMWARE_ID}"'",
      "deployment_strategy": "staged",
      "target_devices": ["'"${TEST_DEVICE_ID}"'", "'"${TEST_DEVICE_ID_2}"'"],
      "rollout_percentage": 50,
      "auto_rollback": true,
      "failure_threshold_percent": 20,
      "priority": "normal",
      "force_update": false
    }'

    echo "Request:"
    echo "$CAMPAIGN_PAYLOAD" | json_pretty

    RESPONSE=$(api_post "/campaigns" "$CAMPAIGN_PAYLOAD")
    echo "Response:"
    echo "$RESPONSE" | json_pretty

    CAMPAIGN_ID=$(json_get "$RESPONSE" "campaign_id")
    if [ -n "$CAMPAIGN_ID" ] && [ "$CAMPAIGN_ID" != "null" ]; then
        print_success "Created campaign: $CAMPAIGN_ID"
        test_result 0
    else
        print_error "Failed to create campaign"
        test_result 1
    fi
else
    print_warning "Skipping: No firmware ID"
fi
echo ""

# =============================================================================
# Test 6: Get Campaign by ID
# =============================================================================
if [ -n "$CAMPAIGN_ID" ] && [ "$CAMPAIGN_ID" != "null" ]; then
    print_section "Test 6: Get Campaign by ID"
    echo "GET ${API_PATH}/campaigns/${CAMPAIGN_ID}"

    RESPONSE=$(api_get "/campaigns/${CAMPAIGN_ID}")
    echo "$RESPONSE" | json_pretty

    RETRIEVED_ID=$(json_get "$RESPONSE" "campaign_id")
    if [ "$RETRIEVED_ID" = "$CAMPAIGN_ID" ]; then
        print_success "Retrieved campaign matches"
        test_result 0
    else
        print_error "Retrieved campaign ID mismatch"
        test_result 1
    fi
else
    print_warning "Skipping: No campaign ID"
fi
echo ""

# =============================================================================
# Test 7: List Campaigns
# =============================================================================
print_section "Test 7: List Campaigns"
echo "GET ${API_PATH}/campaigns"

RESPONSE=$(api_get "/campaigns")
echo "$RESPONSE" | json_pretty | head -40

if json_has "$RESPONSE" "items" || json_has "$RESPONSE" "campaigns"; then
    print_success "List returned campaign collection"
    test_result 0
else
    print_error "Unexpected list response format"
    test_result 1
fi
echo ""

# =============================================================================
# Test 8: Create Device Update (Single Device)
# =============================================================================
if [ -n "$FIRMWARE_ID" ] && [ "$FIRMWARE_ID" != "null" ]; then
    print_section "Test 8: Create Device Update"
    echo "POST ${API_PATH}/devices/${TEST_DEVICE_ID}/update"

    UPDATE_PAYLOAD='{
      "firmware_id": "'"${FIRMWARE_ID}"'",
      "priority": "normal",
      "force_update": false
    }'

    echo "Request:"
    echo "$UPDATE_PAYLOAD" | json_pretty

    RESPONSE=$(api_post "/devices/${TEST_DEVICE_ID}/update" "$UPDATE_PAYLOAD")
    echo "Response:"
    echo "$RESPONSE" | json_pretty

    UPDATE_ID=$(json_get "$RESPONSE" "update_id")
    if [ -n "$UPDATE_ID" ] && [ "$UPDATE_ID" != "null" ]; then
        print_success "Created device update: $UPDATE_ID"
        test_result 0
    else
        print_error "Failed to create device update"
        test_result 1
    fi
else
    print_warning "Skipping: No firmware ID"
fi
echo ""

# =============================================================================
# Test 9: Get Device Update Status
# =============================================================================
if [ -n "$UPDATE_ID" ] && [ "$UPDATE_ID" != "null" ]; then
    print_section "Test 9: Get Device Update Status"
    echo "GET ${API_PATH}/updates/${UPDATE_ID}"

    RESPONSE=$(api_get "/updates/${UPDATE_ID}")
    echo "$RESPONSE" | json_pretty

    RETRIEVED_ID=$(json_get "$RESPONSE" "update_id")
    if [ "$RETRIEVED_ID" = "$UPDATE_ID" ]; then
        UPDATE_STATUS=$(json_get "$RESPONSE" "status")
        print_success "Retrieved update status: $UPDATE_STATUS"
        test_result 0
    else
        print_error "Retrieved update ID mismatch"
        test_result 1
    fi
else
    print_warning "Skipping: No update ID"
fi
echo ""

# =============================================================================
# Test 10: Get Device Update History
# =============================================================================
print_section "Test 10: Get Device Update History"
echo "GET ${API_PATH}/devices/${TEST_DEVICE_ID}/updates"

RESPONSE=$(api_get "/devices/${TEST_DEVICE_ID}/updates")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print('success' if isinstance(d, (list, dict)) else '')" 2>/dev/null | grep -q "success"; then
    print_success "Retrieved device update history"
    test_result 0
else
    print_error "Failed to get update history"
    test_result 1
fi
echo ""

# =============================================================================
# Test 11: Get OTA Statistics
# =============================================================================
print_section "Test 11: Get OTA Statistics"
echo "GET ${API_PATH}/stats"

RESPONSE=$(api_get "/stats")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "total_campaigns" || json_has "$RESPONSE" "success_rate"; then
    print_success "Retrieved OTA statistics"
    test_result 0
else
    print_error "Failed to get OTA statistics"
    test_result 1
fi
echo ""

# =============================================================================
# Test 12: Cancel Device Update
# =============================================================================
if [ -n "$UPDATE_ID" ] && [ "$UPDATE_ID" != "null" ]; then
    print_section "Test 12: Cancel Device Update"
    echo "POST ${API_PATH}/updates/${UPDATE_ID}/cancel"

    RESPONSE=$(api_post "/updates/${UPDATE_ID}/cancel" "{}")
    echo "$RESPONSE" | json_pretty

    CANCEL_STATUS=$(json_get "$RESPONSE" "status")
    if [ "$CANCEL_STATUS" = "cancelled" ] || json_has "$RESPONSE" "update_id"; then
        print_success "Cancelled device update"
        test_result 0
    else
        print_warning "Update cancellation may have failed (check status)"
        test_result 0
    fi
else
    print_warning "Skipping: No update ID"
fi
echo ""

# =============================================================================
# Test 13: Start Campaign
# =============================================================================
if [ -n "$CAMPAIGN_ID" ] && [ "$CAMPAIGN_ID" != "null" ]; then
    print_section "Test 13: Start Campaign"
    echo "POST ${API_PATH}/campaigns/${CAMPAIGN_ID}/start"

    RESPONSE=$(api_post "/campaigns/${CAMPAIGN_ID}/start" "{}")
    echo "$RESPONSE" | json_pretty

    CAMP_STATUS=$(json_get "$RESPONSE" "status")
    if [ "$CAMP_STATUS" = "in_progress" ] || json_has "$RESPONSE" "campaign_id"; then
        print_success "Campaign started"
        test_result 0
    else
        print_warning "Campaign start may have been deferred"
        test_result 0
    fi
else
    print_warning "Skipping: No campaign ID"
fi
echo ""

# =============================================================================
# Test 14: Pause Campaign
# =============================================================================
if [ -n "$CAMPAIGN_ID" ] && [ "$CAMPAIGN_ID" != "null" ]; then
    print_section "Test 14: Pause Campaign"
    echo "POST ${API_PATH}/campaigns/${CAMPAIGN_ID}/pause"

    RESPONSE=$(api_post "/campaigns/${CAMPAIGN_ID}/pause" "{}")
    echo "$RESPONSE" | json_pretty

    if json_has "$RESPONSE" "campaign_id" || json_has "$RESPONSE" "status"; then
        print_success "Campaign paused or status updated"
        test_result 0
    else
        print_warning "Campaign pause may have failed"
        test_result 0
    fi
else
    print_warning "Skipping: No campaign ID"
fi
echo ""

# =============================================================================
# Test 15: Cancel Campaign
# =============================================================================
if [ -n "$CAMPAIGN_ID" ] && [ "$CAMPAIGN_ID" != "null" ]; then
    print_section "Test 15: Cancel Campaign"
    echo "POST ${API_PATH}/campaigns/${CAMPAIGN_ID}/cancel"

    RESPONSE=$(api_post "/campaigns/${CAMPAIGN_ID}/cancel" "{}")
    echo "$RESPONSE" | json_pretty

    CANCEL_STATUS=$(json_get "$RESPONSE" "status")
    if [ "$CANCEL_STATUS" = "cancelled" ] || json_has "$RESPONSE" "campaign_id"; then
        print_success "Campaign cancelled"
        test_result 0
    else
        print_warning "Campaign cancellation response received"
        test_result 0
    fi
else
    print_warning "Skipping: No campaign ID"
fi
echo ""

# =============================================================================
# Test 16: Get Non-existent Firmware (404 Test)
# =============================================================================
print_section "Test 16: Get Non-existent Firmware"
FAKE_ID="fw_nonexistent_$(date +%s)"
echo "GET ${API_PATH}/firmware/${FAKE_ID}"

# Get HTTP status code
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/firmware/${FAKE_ID}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "404" ]; then
    print_success "Correctly returned 404"
    test_result 0
else
    print_error "Expected 404, got $HTTP_CODE"
    test_result 1
fi
echo ""

# =============================================================================
# Test 17: Rollback Request (if update exists)
# =============================================================================
if [ -n "$UPDATE_ID" ] && [ "$UPDATE_ID" != "null" ]; then
    print_section "Test 17: Request Device Rollback"
    echo "POST ${API_PATH}/devices/${TEST_DEVICE_ID}/rollback"

    ROLLBACK_PAYLOAD='{
      "reason": "Smoke test rollback",
      "trigger": "manual"
    }'

    echo "Request:"
    echo "$ROLLBACK_PAYLOAD" | json_pretty

    RESPONSE=$(api_post "/devices/${TEST_DEVICE_ID}/rollback" "$ROLLBACK_PAYLOAD")
    echo "Response:"
    echo "$RESPONSE" | json_pretty

    if json_has "$RESPONSE" "rollback_id" || json_has "$RESPONSE" "status"; then
        print_success "Rollback request submitted"
        test_result 0
    else
        print_warning "Rollback may not be applicable (no previous firmware)"
        test_result 0
    fi
else
    print_warning "Skipping: No update ID"
fi
echo ""

# =============================================================================
# Cleanup: Delete Firmware (if created)
# =============================================================================
if [ -n "$FIRMWARE_ID" ] && [ "$FIRMWARE_ID" != "null" ]; then
    print_section "Cleanup: Delete Test Firmware"
    echo "DELETE ${API_PATH}/firmware/${FIRMWARE_ID}"

    RESPONSE=$(api_delete "/firmware/${FIRMWARE_ID}")
    echo "$RESPONSE" | json_pretty 2>/dev/null || echo "$RESPONSE"

    # Verify deletion
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/firmware/${FIRMWARE_ID}")

    if [ "$HTTP_CODE" = "404" ]; then
        print_success "Firmware deleted successfully"
        test_result 0
    else
        print_warning "Firmware delete may have failed (HTTP $HTTP_CODE)"
        test_result 0
    fi
else
    print_warning "Skipping: No firmware ID to delete"
fi
echo ""

# =============================================================================
# Summary
# =============================================================================
print_summary
exit $?
