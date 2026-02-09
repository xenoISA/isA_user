#!/bin/bash

# Weather Service Test Script
# 天气服务测试脚本
# Event-Driven Architecture v2.0 - via Kubernetes Ingress

BASE_URL="http://localhost"
USER_ID="test_user_$(date +%s)"

echo "========================================"
echo "Weather Service Test Suite"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
echo ""

# Test 1: Get Current Weather
echo "Test 1: Get Current Weather for New York"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/weather/current?location=New%20York&units=metric")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
elif [ "$http_code" = "404" ]; then
    echo -e "${YELLOW}⚠ WARNING${NC} - API key may not be configured"
    echo "Set OPENWEATHER_API_KEY environment variable"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    echo "Response: $body"
fi
echo ""

# Test 2: Get Weather Forecast
echo "Test 2: Get 5-Day Forecast for London"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/weather/forecast?location=London&days=5&units=metric")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
elif [ "$http_code" = "404" ]; then
    echo -e "${YELLOW}⚠ WARNING${NC} - API key may not be configured"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 3: Save Favorite Location
echo "Test 3: Save Favorite Location"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/api/v1/weather/locations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "location": "San Francisco",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "is_default": true,
    "nickname": "Home"
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "201" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    LOCATION_ID=$(echo "$body" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    echo "Location ID: $LOCATION_ID"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
    echo "Response: $body"
fi
echo ""

# Test 4: Get User Locations
echo "Test 4: Get User's Favorite Locations"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/weather/locations/$USER_ID")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 5: Get Weather Alerts
echo "Test 5: Get Weather Alerts"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/weather/alerts?location=Miami")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
fi
echo ""

# Test 6: Get Weather for Multiple Cities
echo "Test 6: Get Weather for Multiple Cities"
cities=("Tokyo" "Paris" "Sydney")

for city in "${cities[@]}"; do
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/weather/current?location=$city")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓${NC} $city: OK"
    else
        echo -e "${RED}✗${NC} $city: Failed (HTTP $http_code)"
    fi
done
echo ""

# Test 7: Delete Location
if [ ! -z "$LOCATION_ID" ]; then
    echo "Test 7: Delete Favorite Location"
    response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/v1/weather/locations/$LOCATION_ID?user_id=$USER_ID")
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
echo ""
echo -e "${YELLOW}Note:${NC} Some tests may fail if OPENWEATHER_API_KEY is not configured"
echo "Set it with: export OPENWEATHER_API_KEY=\"your_api_key_here\""

