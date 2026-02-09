#!/bin/bash

# Location Service Testing Script
# Tests location tracking, place management, and query capabilities

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1/locations"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# JSON parsing function
json_value() {
    local json="$1"
    local key="$2"

    if command -v jq &> /dev/null; then
        echo "$json" | jq -r ".$key"
    else
        echo "$json" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$key', ''))"
    fi
}

# Pretty print JSON
pretty_json() {
    local json="$1"

    if command -v jq &> /dev/null; then
        echo "$json" | jq '.'
    else
        echo "$json" | python3 -m json.tool 2>/dev/null || echo "$json"
    fi
}

echo "======================================================================"
echo "Location Service Tests"
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

# Test 1: Report Location
print_section "Test 1: Report Device Location (San Francisco)"
echo "POST ${API_BASE}"
LOCATION_PAYLOAD='{
  "device_id": "test_device_001",
  "user_id": "test_user_sf",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "accuracy": 10.5,
  "city": "San Francisco",
  "state": "California",
  "country": "USA",
  "address": "Market Street, San Francisco, CA",
  "location_method": "gps",
  "source": "device"
}'
echo "Request Body:"
pretty_json "$LOCATION_PAYLOAD"

REPORT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}" \
  -H "Content-Type: application/json" \
  -d "$LOCATION_PAYLOAD")
HTTP_CODE=$(echo "$REPORT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REPORT_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

LOCATION_ID=""
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        if command -v jq &> /dev/null; then
            LOCATION_ID=$(echo "$RESPONSE_BODY" | jq -r '.data.location_id // empty')
        else
            LOCATION_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('location_id', ''))" 2>/dev/null)
        fi
        print_result 0 "Location reported successfully"
        echo -e "${YELLOW}Location ID: $LOCATION_ID${NC}"
    else
        print_result 1 "Report returned success but success=false"
    fi
else
    print_result 1 "Failed to report location"
fi

# Sleep to ensure data is committed
sleep 1

# Test 2: Report Another Location (New York)
print_section "Test 2: Report Another Location (New York)"
echo "POST ${API_BASE}"
NY_PAYLOAD='{
  "device_id": "test_device_002",
  "user_id": "test_user_ny",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 15.0,
  "city": "New York",
  "state": "New York",
  "country": "USA",
  "address": "Times Square, New York, NY",
  "location_method": "gps"
}'
echo "Request Body:"
pretty_json "$NY_PAYLOAD"

NY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}" \
  -H "Content-Type: application/json" \
  -d "$NY_PAYLOAD")
HTTP_CODE=$(echo "$NY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$NY_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    print_result 0 "Second location reported successfully"
else
    print_result 1 "Failed to report second location"
fi

sleep 1

# Test 3: Get Latest Location for Device
print_section "Test 3: Get Latest Device Location"
echo "GET ${API_BASE}/device/test_device_001/latest"

LATEST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/device/test_device_001/latest")
HTTP_CODE=$(echo "$LATEST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LATEST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    DEVICE_ID=$(json_value "$RESPONSE_BODY" "device_id")
    if [ "$DEVICE_ID" = "test_device_001" ]; then
        print_result 0 "Latest location retrieved successfully"
    else
        print_result 1 "Retrieved device ID doesn't match"
    fi
else
    print_result 1 "Failed to retrieve latest location"
fi

# Test 4: Get Location History
print_section "Test 4: Get Location History for Device"
echo "GET ${API_BASE}/device/test_device_001/history?limit=10"

HISTORY_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/device/test_device_001/history?limit=10")
HTTP_CODE=$(echo "$HISTORY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$HISTORY_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    if command -v jq &> /dev/null; then
        COUNT=$(echo "$RESPONSE_BODY" | jq -r '.data.locations | length')
    else
        COUNT=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', {}).get('locations', [])))" 2>/dev/null)
    fi
    print_result 0 "Location history retrieved (count: $COUNT)"
else
    print_result 1 "Failed to retrieve location history"
fi

# Test 5: Get All User Locations
print_section "Test 5: Get All User Locations"
echo "GET ${API_BASE}/user/test_user_sf"

USER_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/user/test_user_sf")
HTTP_CODE=$(echo "$USER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$USER_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "User locations retrieved successfully"
else
    print_result 1 "Failed to retrieve user locations"
fi

# Test 6: Create a Place (Home)
print_section "Test 6: Create a Place (Home)"
echo "POST ${BASE_URL}/api/v1/places"
PLACE_PAYLOAD='{
  "user_id": "test_user_sf",
  "name": "Home",
  "category": "home",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "address": "123 Market Street, San Francisco, CA"
}'
echo "Request Body:"
pretty_json "$PLACE_PAYLOAD"

PLACE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/v1/places" \
  -H "Content-Type: application/json" \
  -d "$PLACE_PAYLOAD")
HTTP_CODE=$(echo "$PLACE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$PLACE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

PLACE_ID=""
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    SUCCESS=$(json_value "$RESPONSE_BODY" "success")
    if [ "$SUCCESS" = "true" ]; then
        if command -v jq &> /dev/null; then
            PLACE_ID=$(echo "$RESPONSE_BODY" | jq -r '.data.place_id // empty')
        else
            PLACE_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('place_id', ''))" 2>/dev/null)
        fi
        print_result 0 "Place created successfully"
        echo -e "${YELLOW}Place ID: $PLACE_ID${NC}"
    else
        print_result 1 "Create place returned success but success=false"
    fi
else
    print_result 1 "Failed to create place"
fi

sleep 1

# Test 7: List User Places
print_section "Test 7: List User Places"
echo "GET ${BASE_URL}/api/v1/places/user/test_user_sf"

PLACES_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/places/user/test_user_sf")
HTTP_CODE=$(echo "$PLACES_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$PLACES_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    if command -v jq &> /dev/null; then
        COUNT=$(echo "$RESPONSE_BODY" | jq -r '.data.places | length')
    else
        COUNT=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('data', {}).get('places', [])))" 2>/dev/null)
    fi
    print_result 0 "User places listed (count: $COUNT)"
else
    print_result 1 "Failed to list user places"
fi

# Test 8: Calculate Distance Between Two Points
print_section "Test 8: Calculate Distance (SF to NY)"
echo "GET ${BASE_URL}/api/v1/distance?lat1=37.7749&lon1=-122.4194&lat2=40.7128&lon2=-74.0060"

DISTANCE_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/api/v1/distance?lat1=37.7749&lon1=-122.4194&lat2=40.7128&lon2=-74.0060")
HTTP_CODE=$(echo "$DISTANCE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$DISTANCE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    if command -v jq &> /dev/null; then
        DISTANCE=$(echo "$RESPONSE_BODY" | jq -r '.data.distance_meters')
    else
        DISTANCE=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('distance_meters', 0))" 2>/dev/null)
    fi
    echo -e "${YELLOW}Distance: $DISTANCE meters (~4,130 km expected)${NC}"
    print_result 0 "Distance calculated successfully"
else
    print_result 1 "Failed to calculate distance"
fi

# Test 9: Update Place
if [ -n "$PLACE_ID" ] && [ "$PLACE_ID" != "null" ]; then
    print_section "Test 9: Update Place"
    echo "PUT ${BASE_URL}/api/v1/places/${PLACE_ID}"
    UPDATE_PLACE_PAYLOAD='{
      "name": "Home Sweet Home",
      "address": "456 Market Street, San Francisco, CA"
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_PLACE_PAYLOAD"

    UPDATE_PLACE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/v1/places/${PLACE_ID}" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_PLACE_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_PLACE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_PLACE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(json_value "$RESPONSE_BODY" "success")
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Place updated successfully"
        else
            print_result 1 "Update returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to update place"
    fi
else
    echo -e "${YELLOW}Skipping Test 9: No place ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 10: Delete Place
if [ -n "$PLACE_ID" ] && [ "$PLACE_ID" != "null" ]; then
    print_section "Test 10: Delete Place"
    echo "DELETE ${BASE_URL}/api/v1/places/${PLACE_ID}"

    DELETE_PLACE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}/api/v1/places/${PLACE_ID}")
    HTTP_CODE=$(echo "$DELETE_PLACE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_PLACE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS=$(json_value "$RESPONSE_BODY" "success")
        if [ "$SUCCESS" = "true" ]; then
            print_result 0 "Place deleted successfully"
        else
            print_result 1 "Delete returned 200 but success=false"
        fi
    else
        print_result 1 "Failed to delete place"
    fi
else
    echo -e "${YELLOW}Skipping Test 10: No place ID available${NC}"
    ((TESTS_FAILED++))
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
    echo -e "${GREEN}All location service tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi
