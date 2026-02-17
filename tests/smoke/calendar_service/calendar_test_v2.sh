#!/bin/bash
# Calendar Service Test Script (v2 - using test_common.sh)
# Usage:
#   ./calendar_test_v2.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./calendar_test_v2.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="calendar_service"
API_PATH="/api/v1/calendar"

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"
TEST_CALENDAR_USER="calendar_test_user_${TEST_TS}"

# Calculate dates (macOS compatible)
START_TIME=$(date -u -v+1d +"%Y-%m-%dT10:00:00Z" 2>/dev/null || date -u -d "+1 day" +"%Y-%m-%dT10:00:00Z")
END_TIME=$(date -u -v+1d +"%Y-%m-%dT11:00:00Z" 2>/dev/null || date -u -d "+1 day" +"%Y-%m-%dT11:00:00Z")

print_info "Test User ID: $TEST_CALENDAR_USER"
print_info "Start Time: $START_TIME"
print_info "End Time: $END_TIME"
echo ""

# ============================================================================
# Setup: Create Test User
# ============================================================================
print_section "Setup: Create Test User"
ACCOUNT_URL="http://localhost:$(get_service_port account_service)/api/v1/accounts/ensure"
USER_RESPONSE=$(curl -s -X POST "$ACCOUNT_URL" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"${TEST_CALENDAR_USER}\",\"email\":\"calendar_${TEST_TS}@example.com\",\"name\":\"Calendar Test User\",\"subscription_plan\":\"free\"}")
echo "$USER_RESPONSE" | json_pretty
echo ""

# ============================================================================
# Tests
# ============================================================================

# Test 1: Create Calendar Event
print_section "Test 1: Create Calendar Event"
echo "POST ${API_PATH}/events"
print_info "Expected Event: calendar.event_created"

CREATE_PAYLOAD="{
  \"user_id\": \"${TEST_CALENDAR_USER}\",
  \"title\": \"Team Meeting ${TEST_TS}\",
  \"description\": \"Weekly team sync\",
  \"location\": \"Conference Room A\",
  \"start_time\": \"${START_TIME}\",
  \"end_time\": \"${END_TIME}\",
  \"category\": \"meeting\",
  \"reminders\": [15, 60],
  \"all_day\": false
}"
RESPONSE=$(api_post "/events" "$CREATE_PAYLOAD")
echo "$RESPONSE" | json_pretty

CREATED_EVENT_ID=$(json_get "$RESPONSE" "event_id")
if [ -n "$CREATED_EVENT_ID" ] && [ "$CREATED_EVENT_ID" != "null" ] && [ "$CREATED_EVENT_ID" != "" ]; then
    print_success "Created event: $CREATED_EVENT_ID"
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Get Event Details
if [ -n "$CREATED_EVENT_ID" ] && [ "$CREATED_EVENT_ID" != "null" ]; then
    print_section "Test 2: Get Event Details"
    echo "GET ${API_PATH}/events/${CREATED_EVENT_ID}?user_id=${TEST_CALENDAR_USER}"
    RESPONSE=$(api_get "/events/${CREATED_EVENT_ID}?user_id=${TEST_CALENDAR_USER}")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | grep -q "$CREATED_EVENT_ID" || json_has "$RESPONSE" "title"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 2: SKIPPED - No event ID"
fi
echo ""

# Test 3: List Events
print_section "Test 3: List User Events"
echo "GET ${API_PATH}/events?user_id=${TEST_CALENDAR_USER}"
RESPONSE=$(api_get "/events?user_id=${TEST_CALENDAR_USER}")
echo "$RESPONSE" | json_pretty | head -30

if json_has "$RESPONSE" "events" || echo "$RESPONSE" | grep -q "\["; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 4: Get Upcoming Events
print_section "Test 4: Get Upcoming Events"
echo "GET ${API_PATH}/upcoming?user_id=${TEST_CALENDAR_USER}&days=7"
RESPONSE=$(api_get "/upcoming?user_id=${TEST_CALENDAR_USER}&days=7")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q "\["; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 5: Get Today's Events
print_section "Test 5: Get Today's Events"
echo "GET ${API_PATH}/today?user_id=${TEST_CALENDAR_USER}"
RESPONSE=$(api_get "/today?user_id=${TEST_CALENDAR_USER}")
echo "$RESPONSE" | json_pretty | head -20

if echo "$RESPONSE" | grep -q "\["; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 6: Update Event
if [ -n "$CREATED_EVENT_ID" ] && [ "$CREATED_EVENT_ID" != "null" ]; then
    print_section "Test 6: Update Event"
    echo "PUT ${API_PATH}/events/${CREATED_EVENT_ID}?user_id=${TEST_CALENDAR_USER}"
    print_info "Expected Event: calendar.event_updated"

    UPDATE_PAYLOAD="{
      \"title\": \"Updated Team Meeting ${TEST_TS}\",
      \"location\": \"Conference Room B\"
    }"
    RESPONSE=$(api_put "/events/${CREATED_EVENT_ID}?user_id=${TEST_CALENDAR_USER}" "$UPDATE_PAYLOAD")
    echo "$RESPONSE" | json_pretty

    if echo "$RESPONSE" | grep -q "Updated Team Meeting" || json_has "$RESPONSE" "event_id"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 6: SKIPPED - No event ID"
fi
echo ""

# Test 7: Sync Calendar Status
print_section "Test 7: Get Sync Status"
echo "GET ${API_PATH}/sync/status?user_id=${TEST_CALENDAR_USER}"
RESPONSE=$(api_get "/sync/status?user_id=${TEST_CALENDAR_USER}")
echo "$RESPONSE" | json_pretty

# Accept "not found" as valid response for new users who haven't synced yet
if json_has "$RESPONSE" "status" || json_has "$RESPONSE" "sync_status" || echo "$RESPONSE" | grep -q "last_sync\|not found\|detail"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 8: Delete Event
if [ -n "$CREATED_EVENT_ID" ] && [ "$CREATED_EVENT_ID" != "null" ]; then
    print_section "Test 8: Delete Event"
    echo "DELETE ${API_PATH}/events/${CREATED_EVENT_ID}?user_id=${TEST_CALENDAR_USER}"
    print_info "Expected Event: calendar.event_deleted"

    RESPONSE=$(api_delete "/events/${CREATED_EVENT_ID}?user_id=${TEST_CALENDAR_USER}")

    # DELETE returns 204 No Content, so check if empty or success
    if [ -z "$RESPONSE" ] || echo "$RESPONSE" | grep -q "deleted\|success"; then
        test_result 0
    else
        test_result 1
    fi
else
    print_section "Test 8: SKIPPED - No event ID"
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
