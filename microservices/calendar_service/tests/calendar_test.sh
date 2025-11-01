#!/bin/bash

# Calendar Service Test Script
# 日历服务测试脚本

BASE_URL="http://localhost:8217"
USER_ID="test_user_$(date +%s)"

echo "========================================"
echo "Calendar Service Test Suite"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo "Test 1: Health Check"
response=$(curl -s -w "\n%{http_code}" $BASE_URL/health)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 2: Create Event
echo "Test 2: Create Calendar Event"
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
    echo -e "${GREEN}✓ PASSED${NC}"
    EVENT_ID=$(echo "$body" | grep -o '"event_id":"[^"]*' | cut -d'"' -f4)
    echo "Event ID: $EVENT_ID"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    echo "Response: $body"
fi
echo ""

# Test 3: Get Event
if [ ! -z "$EVENT_ID" ]; then
    echo "Test 3: Get Event Details"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/calendar/events/$EVENT_ID?user_id=$USER_ID")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        echo "Response: $body"
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    fi
    echo ""
fi

# Test 4: List Events
echo "Test 4: List Events"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/calendar/events?user_id=$USER_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 5: Get Upcoming Events
echo "Test 5: Get Upcoming Events (7 days)"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/calendar/upcoming?user_id=$USER_ID&days=7")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 6: Get Today's Events
echo "Test 6: Get Today's Events"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/calendar/today?user_id=$USER_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 7: Update Event
if [ ! -z "$EVENT_ID" ]; then
    echo "Test 7: Update Event"
    response=$(curl -s -w "\n%{http_code}" -X PUT "$BASE_URL/api/v1/calendar/events/$EVENT_ID?user_id=$USER_ID" \
      -H "Content-Type: application/json" \
      -d '{
        "title": "Updated Team Meeting",
        "location": "Conference Room B"
      }')
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        echo "Response: $body"
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    fi
    echo ""
fi

# Test 8: Delete Event
if [ ! -z "$EVENT_ID" ]; then
    echo "Test 8: Delete Event"
    response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/v1/calendar/events/$EVENT_ID?user_id=$USER_ID")
    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "204" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    fi
    echo ""
fi

echo "========================================"
echo "Test Suite Complete"
echo "========================================"

