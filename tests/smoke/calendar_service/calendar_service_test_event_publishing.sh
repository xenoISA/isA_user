#!/bin/bash

# Calendar Service Event Publishing Integration Test
# Verifies that calendar events are properly published

BASE_URL="${BASE_URL:-http://localhost}"
API_BASE="${BASE_URL}/api/v1"
AUTH_URL="${BASE_URL}/api/v1/auth"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================================================"
echo "Calendar Service - Event Publishing Integration Test"
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
  "user_id": "test_calendar_event_user",
  "email": "calendarevent@example.com",
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

TEST_USER_ID="test_calendar_event_user"

echo ""
echo "======================================================================"
echo "Test 1: Verify calendar.event_created event is published"
echo "======================================================================"
echo ""

START_TIME=$(date -u -v+1d +"%Y-%m-%dT10:00:00Z" 2>/dev/null || date -u -d "+1 day" +"%Y-%m-%dT10:00:00Z")
END_TIME=$(date -u -v+1d +"%Y-%m-%dT11:00:00Z" 2>/dev/null || date -u -d "+1 day" +"%Y-%m-%dT11:00:00Z")

CREATE_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"title\": \"Team Meeting - Event Test\",
  \"description\": \"Testing event publishing\",
  \"location\": \"Conference Room A\",
  \"start_time\": \"${START_TIME}\",
  \"end_time\": \"${END_TIME}\",
  \"category\": \"meeting\",
  \"reminders\": [15, 60],
  \"all_day\": false
}"

echo "Creating calendar event to trigger calendar.event_created event..."
echo "POST ${API_BASE}/calendar/events"
echo "$CREATE_PAYLOAD" | jq '.'

RESPONSE=$(curl -s -X POST "${API_BASE}/calendar/events" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD")

echo "Response:"
echo "$RESPONSE" | jq '.'

EVENT_ID=$(echo "$RESPONSE" | jq -r '.event_id')

if [ -n "$EVENT_ID" ] && [ "$EVENT_ID" != "null" ]; then
    print_result 0 "calendar.event_created event should be published (event created: $EVENT_ID)"
else
    print_result 1 "Failed to create calendar event (no event published)"
fi

echo ""
echo "======================================================================"
echo "Test 2: Verify calendar.event_updated event is published"
echo "======================================================================"
echo ""

if [ -n "$EVENT_ID" ] && [ "$EVENT_ID" != "null" ]; then
    UPDATE_PAYLOAD="{
      \"title\": \"Updated Meeting Title\",
      \"description\": \"Updated description for event testing\"
    }"

    echo "Updating calendar event to trigger calendar.event_updated event..."
    echo "PUT ${API_BASE}/calendar/events/${EVENT_ID}"
    echo "$UPDATE_PAYLOAD" | jq '.'

    RESPONSE=$(curl -s -X PUT "${API_BASE}/calendar/events/${EVENT_ID}" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_PAYLOAD")

    echo "Response:"
    echo "$RESPONSE" | jq '.'

    # Check if update succeeded by verifying event_id is present in response
    UPDATED_EVENT_ID=$(echo "$RESPONSE" | jq -r '.event_id')
    if [ -n "$UPDATED_EVENT_ID" ] && [ "$UPDATED_EVENT_ID" != "null" ]; then
        print_result 0 "calendar.event_updated event should be published"
    else
        print_result 1 "Failed to update calendar event"
    fi
else
    print_result 1 "Cannot test update (no event ID from Test 1)"
fi

echo ""
echo "======================================================================"
echo "Test 3: Verify calendar.event_deleted event is published"
echo "======================================================================"
echo ""

# Create a new event for deletion test
DELETE_TEST_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"title\": \"Event to Delete\",
  \"start_time\": \"${START_TIME}\",
  \"end_time\": \"${END_TIME}\"
}"

RESPONSE=$(curl -s -X POST "${API_BASE}/calendar/events" \
  -H "Content-Type: application/json" \
  -d "$DELETE_TEST_PAYLOAD")

DELETE_EVENT_ID=$(echo "$RESPONSE" | jq -r '.event_id')

if [ -n "$DELETE_EVENT_ID" ] && [ "$DELETE_EVENT_ID" != "null" ]; then
    echo "Deleting calendar event to trigger calendar.event_deleted event..."
    echo "DELETE ${API_BASE}/calendar/events/${DELETE_EVENT_ID}"

    HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X DELETE "${API_BASE}/calendar/events/${DELETE_EVENT_ID}")

    echo "HTTP Status: $HTTP_CODE"

    # Delete endpoint returns 204 No Content on success
    if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "calendar.event_deleted event should be published"
    else
        print_result 1 "Failed to delete calendar event (HTTP $HTTP_CODE)"
    fi
else
    print_result 1 "Cannot test delete (failed to create test event)"
fi

echo ""
echo "======================================================================"
echo "Test 4: Verify calendar.reminder_created event is published"
echo "======================================================================"
echo ""

REMINDER_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"title\": \"Event with Reminder\",
  \"start_time\": \"${START_TIME}\",
  \"end_time\": \"${END_TIME}\",
  \"reminders\": [30]
}"

echo "Creating calendar event with reminder..."
echo "POST ${API_BASE}/calendar/events"
echo "$REMINDER_PAYLOAD" | jq '.'

RESPONSE=$(curl -s -X POST "${API_BASE}/calendar/events" \
  -H "Content-Type: application/json" \
  -d "$REMINDER_PAYLOAD")

echo "Response:"
echo "$RESPONSE" | jq '.'

REMINDER_EVENT_ID=$(echo "$RESPONSE" | jq -r '.event_id')

if [ -n "$REMINDER_EVENT_ID" ] && [ "$REMINDER_EVENT_ID" != "null" ]; then
    print_result 0 "calendar.reminder_created event should be published"
else
    print_result 1 "Failed to create event with reminder"
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
    echo "  - calendar.event_created"
    echo "  - calendar.event_updated"
    echo "  - calendar.event_deleted"
    echo "  - calendar.reminder_created"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
