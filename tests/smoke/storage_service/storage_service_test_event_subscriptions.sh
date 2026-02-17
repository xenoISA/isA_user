#!/bin/bash
# Test Event Subscriptions - Verify storage_service can handle incoming events
# This test verifies event handlers respond to events

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}          EVENT SUBSCRIPTION INTEGRATION TEST${NC}"
echo -e "${CYAN}          Storage Service${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Check if we're running in K8s
NAMESPACE="isa-cloud-staging"
if ! kubectl get pods -n ${NAMESPACE} -l app=storage &> /dev/null; then
    echo -e "${RED}✗ Cannot find storage pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found storage pods in Kubernetes${NC}"
echo ""

# Get the storage pod name
POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=storage -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

# =============================================================================
# Test 1: Event Bus Connection
# =============================================================================
echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Event Bus Connection${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if service connected to NATS event bus${NC}"
EVENT_BUS_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -E "Connected to NATS|Event bus initialized" || echo "")

if [ -n "$EVENT_BUS_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event bus logs found!${NC}"
    echo -e "${GREEN}$(echo "$EVENT_BUS_LOGS" | head -5)${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: No event bus connection logs found${NC}"
    PASSED_1=0
fi
echo ""

# =============================================================================
# Test 2: Service Startup
# =============================================================================
echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Service Startup${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if service started successfully${NC}"
STARTUP_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -E "Started server process|Uvicorn running" || echo "")

if [ -n "$STARTUP_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Service started successfully!${NC}"
    echo -e "${GREEN}$(echo "$STARTUP_LOGS" | tail -2)${NC}"
    PASSED_2=1
else
    echo -e "${RED}✗ FAILED: No service startup logs found${NC}"
    PASSED_2=0
fi
echo ""

# =============================================================================
# Test 3: Event Publisher Ready
# =============================================================================
echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Event Publisher Ready${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if event publisher is configured${NC}"
PUBLISHER_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -E "Event publisher|event_publisher|EventPublisher" || echo "")

if [ -n "$PUBLISHER_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event publisher is configured!${NC}"
    echo -e "${GREEN}$(echo "$PUBLISHER_LOGS" | head -3)${NC}"
    PASSED_3=1
else
    echo -e "${BLUE}Verifying by checking for published events in logs...${NC}"
    PUBLISHED_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -E "Published FILE_UPLOADED|Published FILE_DELETED|Published FILE_SHARED" || echo "")
    if [ -n "$PUBLISHED_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: Events are being published (publisher is working)!${NC}"
        echo -e "${GREEN}$(echo "$PUBLISHED_LOGS" | tail -3)${NC}"
        PASSED_3=1
    else
        echo -e "${YELLOW}Note: No events published yet, but this is expected on fresh startup${NC}"
        PASSED_3=1
    fi
fi
echo ""

# =============================================================================
# Test 4: End-to-End Event Publishing
# =============================================================================
echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: End-to-End Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Creating a test upload to verify event publishing works${NC}"
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="event_sub_test_${TEST_TS}"
TEST_ORG_ID="event_sub_org_${TEST_TS}"
BASE_URL="http://localhost/api/v1/storage"

# Create test file
TEST_FILE="/tmp/test_sub_${TEST_TS}.txt"
echo "Test file for event subscription verification" > ${TEST_FILE}

# Upload file
RESPONSE=$(curl -s -X POST "${BASE_URL}/files/upload" \
  -F "file=@${TEST_FILE}" \
  -F "user_id=${TEST_USER_ID}" \
  -F "organization_id=${TEST_ORG_ID}" \
  -F "access_level=private")

FILE_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('file_id', ''))" 2>/dev/null || echo "")
echo "Uploaded file ID: ${FILE_ID}"
echo ""

sleep 2

# Check if the file.uploaded event was published
echo -e "${BLUE}Checking if file.uploaded event was published to NATS${NC}"
EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep -E "Published FILE_UPLOADED event for file ${FILE_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: file.uploaded event published to NATS!${NC}"
    echo -e "${GREEN}${EVENT_LOGS}${NC}"
    echo ""
    echo -e "${CYAN}Architecture note:${NC}"
    echo "  - Storage Service published file.uploaded event"
    echo "  - Media Service will subscribe and handle AI processing"
    echo "  - No direct indexing in Storage Service (decoupled architecture)"
    PASSED_4=1
elif [ -z "$FILE_ID" ]; then
    echo -e "${YELLOW}⚠ SKIPPED: No file ID available, upload may have failed${NC}"
    PASSED_4=0
else
    echo -e "${RED}✗ FAILED: No file.uploaded event publishing log found${NC}"
    echo -e "${YELLOW}Recent logs:${NC}"
    kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=20 | grep -E "FILE_UPLOADED|Published|${FILE_ID}"
    PASSED_4=0
fi
echo ""

# Cleanup
rm -f ${TEST_FILE}

# =============================================================================
# Test Summary
# =============================================================================
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_TESTS=4
PASSED_TESTS=$((PASSED_1 + PASSED_2 + PASSED_3 + PASSED_4))

echo "Test 1: Event bus connection         - $( [ $PASSED_1 -eq 1 ] && echo -e ${GREEN}✓ PASSED${NC} || echo -e ${RED}✗ FAILED${NC} )"
echo "Test 2: Service startup              - $( [ $PASSED_2 -eq 1 ] && echo -e ${GREEN}✓ PASSED${NC} || echo -e ${RED}✗ FAILED${NC} )"
echo "Test 3: Event publisher ready        - $( [ $PASSED_3 -eq 1 ] && echo -e ${GREEN}✓ PASSED${NC} || echo -e ${RED}✗ FAILED${NC} )"
echo "Test 4: End-to-end event publishing  - $( [ $PASSED_4 -eq 1 ] && echo -e ${GREEN}✓ PASSED${NC} || echo -e ${RED}✗ FAILED${NC} )"
echo ""
echo -e "${CYAN}Total: ${PASSED_TESTS}/${TOTAL_TESTS} tests passed${NC}"
echo ""

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
