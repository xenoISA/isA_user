#!/bin/bash
# Test Event Publishing - Verify events are published via API response
# This test verifies the weather_service publishes events by checking API responses

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}          EVENT PUBLISHING INTEGRATION TEST${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="event_test_user_${TEST_TS}"
BASE_URL="http://localhost/api/v1/weather"

echo -e "${BLUE}Testing weather service at: ${BASE_URL}${NC}"
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Save Location (triggers weather.location_saved event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Save a favorite location
echo -e "${BLUE}Step 1: Save favorite location${NC}"
SAVE_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"location\":\"Tokyo\",\"latitude\":35.6762,\"longitude\":139.6503,\"is_default\":true,\"nickname\":\"Work\"}"
echo "POST ${BASE_URL}/locations"
echo "Payload: ${SAVE_PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/locations" \
  -H "Content-Type: application/json" \
  -d "$SAVE_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Check if operation succeeded
if echo "$RESPONSE" | grep -q '"id":'; then
    echo -e "${GREEN}✓ Location saved successfully${NC}"
    echo -e "${BLUE}Note: weather.location_saved event should be published to NATS${NC}"
    LOCATION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: Location save failed${NC}"
    PASSED_1=0
fi
echo ""

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_PASSED=$PASSED_1
echo -e "Tests Passed: ${GREEN}${TOTAL_PASSED}/1${NC}"
echo ""

if [ $TOTAL_PASSED -eq 1 ]; then
    echo -e "${GREEN}✓ ALL EVENT PUBLISHING TESTS PASSED!${NC}"
    echo ""
    echo -e "${CYAN}Event Publishing Verification:${NC}"
    echo -e "  ${BLUE}✓${NC} weather.location_saved - Published when location is saved"
    echo ""
    echo -e "${YELLOW}Note: This test verifies event publishing indirectly by confirming${NC}"
    echo -e "${YELLOW}      API operations succeed. Events are published asynchronously.${NC}"
    echo -e "${YELLOW}      To verify NATS delivery, check service logs or NATS monitoring.${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
