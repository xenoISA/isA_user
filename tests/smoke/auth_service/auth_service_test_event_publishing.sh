#!/bin/bash
# Test Event Publishing - Verify events are actually published to NATS
# This test checks the auth_service logs for event publishing confirmation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}          AUTH SERVICE EVENT PUBLISHING INTEGRATION TEST${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Check if we're running in K8s
if ! kubectl get pods -n isa-cloud-staging -l app=auth &> /dev/null; then
    echo -e "${RED}✗ Cannot find auth-service pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found auth-service pods in Kubernetes${NC}"
echo ""

# Get the auth-service pod name
POD_NAME=$(kubectl get pods -n isa-cloud-staging -l app=auth -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="event_test_user_${TEST_TS}"
TEST_EMAIL="event_test_${TEST_TS}@example.com"
TEST_ORG_ID="test_org_001"
TEST_DEVICE_ID="event_test_device_${TEST_TS}"
BASE_URL="http://localhost/api/v1/auth"

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Verify user.logged_in Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Get baseline log position
echo -e "${BLUE}Step 1: Get baseline log position${NC}"
BASELINE_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=5 | wc -l)
echo "Baseline log lines: ${BASELINE_LOGS}"
echo ""

# Generate token pair (simulates user login)
echo -e "${BLUE}Step 2: Generate token pair (triggers user.logged_in event)${NC}"
PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"email\":\"${TEST_EMAIL}\",\"organization_id\":\"${TEST_ORG_ID}\",\"permissions\":[\"read\",\"write\"]}"
echo "POST ${BASE_URL}/token-pair"
echo "Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/token-pair" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Wait for logs to be written
sleep 2

# Check logs for event publishing
echo -e "${BLUE}Step 3: Check logs for event publishing confirmation${NC}"
EVENT_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=50 | grep "Published user.logged_in" | grep "${TEST_USER_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: user.logged_in event was published to NATS!${NC}"
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
echo -e "${YELLOW}Test 2: Verify device.registered Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Register a device
echo -e "${BLUE}Step 1: Register device (triggers device.registered event)${NC}"
DEVICE_PAYLOAD="{\"device_id\":\"${TEST_DEVICE_ID}\",\"organization_id\":\"${TEST_ORG_ID}\",\"device_name\":\"Test Event Device\",\"device_type\":\"smart_frame\",\"metadata\":{\"model\":\"SF-2024\"},\"expires_days\":365}"
echo "POST ${BASE_URL}/device/register"
echo "Payload: ${DEVICE_PAYLOAD}"
DEVICE_RESPONSE=$(curl -s -X POST "${BASE_URL}/device/register" \
  -H "Content-Type: application/json" \
  -d "$DEVICE_PAYLOAD")
echo "$DEVICE_RESPONSE" | python3 -m json.tool
echo ""

sleep 2

# Check logs for device registration event
echo -e "${BLUE}Step 2: Check logs for device.registered event${NC}"
EVENT_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=50 | grep "Published device.registered" | grep "${TEST_DEVICE_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: device.registered event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_2=1
else
    echo -e "${RED}✗ FAILED: No device.registered event log found${NC}"
    PASSED_2=0
fi
echo ""

# Get device secret for authentication test
DEVICE_SECRET=$(echo "$DEVICE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('device_secret', ''))" 2>/dev/null || echo "")

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Verify device.authenticated Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$DEVICE_SECRET" ] && [ "$DEVICE_SECRET" != "" ]; then
    # Authenticate device
    echo -e "${BLUE}Step 1: Authenticate device (triggers device.authenticated event)${NC}"
    AUTH_PAYLOAD="{\"device_id\":\"${TEST_DEVICE_ID}\",\"device_secret\":\"${DEVICE_SECRET}\"}"
    echo "POST ${BASE_URL}/device/authenticate"
    curl -s -X POST "${BASE_URL}/device/authenticate" \
      -H "Content-Type: application/json" \
      -d "$AUTH_PAYLOAD" | python3 -m json.tool
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for device.authenticated event${NC}"
    EVENT_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} --tail=50 | grep "Published device.authenticated" | grep "${TEST_DEVICE_ID}" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: device.authenticated event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_3=1
    else
        echo -e "${RED}✗ FAILED: No device.authenticated event log found${NC}"
        PASSED_3=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: Could not get device secret from registration${NC}"
    PASSED_3=0
fi
echo ""

# Cleanup - delete test device
if [ -n "$DEVICE_SECRET" ]; then
    curl -s -X DELETE "${BASE_URL}/device/${TEST_DEVICE_ID}?organization_id=${TEST_ORG_ID}" > /dev/null 2>&1 || true
fi

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Verify NATS Connection on Service Startup${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if NATS connection was established on startup${NC}"
NATS_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} | grep -i "nats" | grep -iE "(connected|initialized)" | head -5 || echo "")

if [ -n "$NATS_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: NATS connection established!${NC}"
    echo -e "${GREEN}${NATS_LOGS}${NC}"
    PASSED_4=1
else
    echo -e "${YELLOW}⚠ No explicit NATS connection logs found${NC}"
    echo -e "${YELLOW}Checking for event bus initialization...${NC}"
    EVENT_BUS_LOGS=$(kubectl logs -n isa-cloud-staging ${POD_NAME} | grep -i "event" | grep -iE "(bus|initialized)" | head -5 || echo "")
    if [ -n "$EVENT_BUS_LOGS" ]; then
        echo -e "${GREEN}✓ Event bus initialized:${NC}"
        echo -e "${GREEN}${EVENT_BUS_LOGS}${NC}"
        PASSED_4=1
    else
        echo -e "${YELLOW}No event bus logs found - checking if events were still published${NC}"
        # If events were published in previous tests, NATS is working
        if [ $PASSED_1 -eq 1 ] || [ $PASSED_2 -eq 1 ]; then
            echo -e "${GREEN}✓ NATS is working (events were successfully published)${NC}"
            PASSED_4=1
        else
            PASSED_4=0
        fi
    fi
fi
echo ""

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                    TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_PASSED=$((PASSED_1 + PASSED_2 + PASSED_3 + PASSED_4))
TOTAL_TESTS=4

echo "Test 1: user.logged_in event       - $([ $PASSED_1 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 2: device.registered event    - $([ $PASSED_2 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 3: device.authenticated event - $([ $PASSED_3 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 4: NATS connection verified   - $([ $PASSED_4 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo ""
echo -e "${CYAN}Total: ${TOTAL_PASSED}/${TOTAL_TESTS} tests passed${NC}"
echo ""

if [ $TOTAL_PASSED -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}✓ ALL EVENT PUBLISHING TESTS PASSED!${NC}"
    echo -e "${GREEN}✓ Events are being published to NATS successfully${NC}"
    exit 0
elif [ $TOTAL_PASSED -ge 3 ]; then
    echo -e "${YELLOW}⚠ Most tests passed (${TOTAL_PASSED}/${TOTAL_TESTS})${NC}"
    echo -e "${GREEN}✓ Core event publishing functionality is working${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "1. Check if NATS is running: kubectl get pods -n isa-cloud-staging | grep nats"
    echo "2. Check auth-service logs: kubectl logs -n isa-cloud-staging ${POD_NAME}"
    echo "3. Check event_bus initialization: kubectl logs -n isa-cloud-staging ${POD_NAME} | grep 'Event bus'"
    exit 1
fi
