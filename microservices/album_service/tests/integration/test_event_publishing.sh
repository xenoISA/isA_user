#!/bin/bash
# Test Event Publishing - Verify events are actually published to NATS
# This test checks the album_service logs for event publishing confirmation

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

# Check if we're running in K8s
if ! kubectl get pods -n isa-cloud-staging -l app=album &> /dev/null; then
    echo -e "${RED}✗ Cannot find album pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found album pods in Kubernetes${NC}"
echo ""

# Get the album pod name
POD_NAME=$(kubectl get pods -n isa-cloud-staging -l app=album -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="test_user_001"  # Use standardized test user that owns test_file_001 and test_file_002
BASE_URL="http://localhost/api/v1/albums"

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Verify album.created Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Clear recent logs
echo -e "${BLUE}Step 1: Get baseline log position${NC}"
BASELINE_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=5 | wc -l)
echo "Baseline log lines: ${BASELINE_LOGS}"
echo ""

# Create a new album
echo -e "${BLUE}Step 2: Create new album (should trigger album.created event)${NC}"
ALBUM_NAME="Event Test Album ${TEST_TS}"
PAYLOAD="{\"name\":\"${ALBUM_NAME}\",\"description\":\"Album for event testing\"}"
echo "POST ${BASE_URL}?user_id=${TEST_USER_ID}"
echo "Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}?user_id=${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
CREATED_ALBUM_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('album_id', ''))" 2>/dev/null)
echo ""

# Wait a moment for logs to be written
sleep 2

# Check logs for event publishing
echo -e "${BLUE}Step 3: Check logs for event publishing confirmation${NC}"
EVENT_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=50 | grep "Published album.created" | grep "${CREATED_ALBUM_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event was published to NATS!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: No event publishing log found${NC}"
    echo -e "${YELLOW}Recent logs:${NC}"
    kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=20
    PASSED_1=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Verify album.photo_added Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Add photos to album (use real file IDs from storage_service test data)
echo -e "${BLUE}Step 1: Add photos to album${NC}"
PHOTO_ID1="test_file_003"  # Real file from storage test data (PDF, less likely to be in other albums)
PHOTO_ID2="test_file_005"  # Real file from storage test data (PNG logo)
ADD_PHOTOS_PAYLOAD="{\"photo_ids\":[\"${PHOTO_ID1}\",\"${PHOTO_ID2}\"]}"
echo "POST ${BASE_URL}/${CREATED_ALBUM_ID}/photos?user_id=${TEST_USER_ID}"
echo "Payload: ${ADD_PHOTOS_PAYLOAD}"
curl -s -X POST "${BASE_URL}/${CREATED_ALBUM_ID}/photos?user_id=${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$ADD_PHOTOS_PAYLOAD" | python3 -m json.tool
echo ""

sleep 2

# Check logs
echo -e "${BLUE}Step 2: Check logs for album.photo_added event${NC}"
EVENT_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=50 | grep "Published album.photo_added" | grep "${CREATED_ALBUM_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: album.photo_added event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_2=1
else
    echo -e "${RED}✗ FAILED: No album.photo_added event log found${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Verify album.photo_removed Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Remove photo from album
echo -e "${BLUE}Step 1: Remove photo from album${NC}"
REMOVE_PHOTOS_PAYLOAD="{\"photo_ids\":[\"${PHOTO_ID1}\"]}"
echo "DELETE ${BASE_URL}/${CREATED_ALBUM_ID}/photos?user_id=${TEST_USER_ID}"
echo "Payload: ${REMOVE_PHOTOS_PAYLOAD}"
curl -s -X DELETE "${BASE_URL}/${CREATED_ALBUM_ID}/photos?user_id=${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$REMOVE_PHOTOS_PAYLOAD" | python3 -m json.tool
echo ""

sleep 2

# Check logs
echo -e "${BLUE}Step 2: Check logs for album.photo_removed event${NC}"
EVENT_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=50 | grep "Published album.photo_removed" | grep "${CREATED_ALBUM_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: album.photo_removed event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_3=1
else
    echo -e "${RED}✗ FAILED: No album.photo_removed event log found${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Verify album.deleted Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Delete album
echo -e "${BLUE}Step 1: Delete album${NC}"
echo "DELETE ${BASE_URL}/${CREATED_ALBUM_ID}?user_id=${TEST_USER_ID}"
curl -s -X DELETE "${BASE_URL}/${CREATED_ALBUM_ID}?user_id=${TEST_USER_ID}" | python3 -m json.tool
echo ""

sleep 2

# Check logs
echo -e "${BLUE}Step 2: Check logs for album.deleted event${NC}"
EVENT_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=50 | grep "Published album.deleted" | grep "${CREATED_ALBUM_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: album.deleted event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_4=1
else
    echo -e "${RED}✗ FAILED: No album.deleted event log found${NC}"
    PASSED_4=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Verify Event Handlers Registration${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if event handlers are registered on service startup${NC}"
HANDLER_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} | grep "Subscribed to event" || echo "")

if [ -n "$HANDLER_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event handlers are registered!${NC}"
    echo -e "${GREEN}${HANDLER_LOGS}${NC}"

    # Check specific handlers
    if echo "$HANDLER_LOGS" | grep -q "media.processed"; then
        echo -e "${GREEN}  ✓ media.processed handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -q "storage.file_deleted"; then
        echo -e "${GREEN}  ✓ storage.file_deleted handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -q "user.deleted"; then
        echo -e "${GREEN}  ✓ user.deleted handler registered${NC}"
    fi
    PASSED_5=1
else
    echo -e "${RED}✗ FAILED: No event handler registration logs found${NC}"
    PASSED_5=0
fi
echo ""

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                    TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_PASSED=$((PASSED_1 + PASSED_2 + PASSED_3 + PASSED_4 + PASSED_5))
TOTAL_TESTS=5

echo "Test 1: album.created event        - $([ $PASSED_1 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 2: album.photo_added event    - $([ $PASSED_2 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 3: album.photo_removed event  - $([ $PASSED_3 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 4: album.deleted event        - $([ $PASSED_4 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 5: Event handlers registered  - $([ $PASSED_5 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo ""
echo -e "${CYAN}Total: ${TOTAL_PASSED}/${TOTAL_TESTS} tests passed${NC}"
echo ""

if [ $TOTAL_PASSED -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}✓ ALL EVENT PUBLISHING TESTS PASSED!${NC}"
    echo -e "${GREEN}✓ Events are being published to NATS successfully${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "1. Check if NATS is running: kubectl get pods | grep nats"
    echo "2. Check album-service logs: kubectl logs -n isa-cloud-staging ${POD_NAME}"
    echo "3. Check event_bus initialization: kubectl logs -n isa-cloud-staging ${POD_NAME} | grep 'Event bus'"
    exit 1
fi
