#!/bin/bash

# Calendar Service Test Script
# 日历服务测试脚本

BASE_URL="http://localhost"
USER_ID="test_user_$(date +%s)"

echo "========================================"
echo "Calendar Service Test Suite"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper function to track test results
pass_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✓ PASSED${NC}"
}

fail_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}✗ FAILED${NC} (HTTP $1)"
}

# Test 1: Create Event
echo -e "${YELLOW}Test 1: Create Calendar Event${NC}"
START_TIME=$(date -u -v+1d +"%Y-%m-%dT10:00:00Z" 2>/dev/null || date -u -d "+1 day" +"%Y-%m-%dT10:00:00Z")
END_TIME=$(date -u -v+1d +"%Y-%m-%dT11:00:00Z" 2>/dev/null || date -u -d "+1 day" +"%Y-%m-%dT11:00:00Z")

response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/api/v1/calendar/events \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "title": "Team Meeting",
    "description": "Weekly team sync",
    "location": "Conference Room A",
    "start_time": "'$START_TIME'",
    "end_time": "'$END_TIME'",
    "category": "meeting",
    "reminders": [15, 60],
    "all_day": false
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "201" ]; then
    pass_test
    EVENT_ID=$(echo "$body" | grep -o '"event_id":"[^"]*' | cut -d'"' -f4)
    echo "Event ID: $EVENT_ID"
    echo "Response: $body"
else
    fail_test "$http_code"
    echo "Response: $body"
fi
echo ""

# Test 2: Get Event
if [ ! -z "$EVENT_ID" ]; then
    echo -e "${YELLOW}Test 2: Get Event Details${NC}"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/calendar/events/$EVENT_ID?user_id=$USER_ID")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        pass_test
        echo "Response: $body"
    else
        fail_test "$http_code"
    fi
    echo ""
fi

# Test 3: List Events
echo -e "${YELLOW}Test 3: List Events${NC}"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/calendar/events?user_id=$USER_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    pass_test
    echo "Response: $body"
else
    fail_test "$http_code"
fi
echo ""

# Test 4: Get Upcoming Events
echo -e "${YELLOW}Test 4: Get Upcoming Events (7 days)${NC}"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/calendar/upcoming?user_id=$USER_ID&days=7")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    pass_test
    echo "Response: $body"
else
    fail_test "$http_code"
fi
echo ""

# Test 5: Get Today's Events
echo -e "${YELLOW}Test 5: Get Today's Events${NC}"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/calendar/today?user_id=$USER_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    pass_test
    echo "Response: $body"
else
    fail_test "$http_code"
fi
echo ""

# Test 6: Update Event
if [ ! -z "$EVENT_ID" ]; then
    echo -e "${YELLOW}Test 6: Update Event${NC}"
    response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/api/v1/calendar/events/$EVENT_ID?user_id=$USER_ID" \
      -H "Content-Type: application/json" \
      -d '{
        "title": "Updated Team Meeting",
        "location": "Conference Room B"
      }')
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        pass_test
        echo "Response: $body"
    else
        fail_test "$http_code"
    fi
    echo ""
fi

# Test 7: Delete Event
if [ ! -z "$EVENT_ID" ]; then
    echo -e "${YELLOW}Test 7: Delete Event${NC}"
    response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/v1/calendar/events/$EVENT_ID?user_id=$USER_ID")
    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "204" ]; then
        pass_test
    else
        fail_test "$http_code"
    fi
    echo ""
fi

# Display test summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}           TEST SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
