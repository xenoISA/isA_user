#!/bin/bash
# Test Event Publishing - Verify events are actually published to NATS
# This test checks the account_service logs for event publishing confirmation

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
NAMESPACE="isa-cloud-staging"
if ! kubectl get pods -n ${NAMESPACE} -l app=account &> /dev/null; then
    echo -e "${RED}✗ Cannot find account pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found account pods in Kubernetes${NC}"
echo ""

# Get the account pod name
POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=account -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_EMAIL="event_test_${TEST_TS}@example.com"
TEST_USER_ID="event_test_user_${TEST_TS}"
BASE_URL="http://localhost/api/v1/accounts"

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Verify user.created Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Clear recent logs
echo -e "${BLUE}Step 1: Get baseline log position${NC}"
BASELINE_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=5 | wc -l)
echo "Baseline log lines: ${BASELINE_LOGS}"
echo ""

# Create a new account
echo -e "${BLUE}Step 2: Create new account (should trigger user.created event)${NC}"
PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"email\":\"${TEST_EMAIL}\",\"name\":\"Event Test User\",\"subscription_plan\":\"free\"}"
echo "POST ${BASE_URL}/ensure"
echo "Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/ensure" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Wait a moment for logs to be written
sleep 2

# Check logs for event publishing
echo -e "${BLUE}Step 3: Check logs for event publishing confirmation${NC}"
EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published user.created" | grep "${TEST_USER_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event was published to NATS!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: No event publishing log found${NC}"
    echo -e "${YELLOW}Recent logs:${NC}"
    kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=20
    PASSED_1=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Verify user.profile_updated Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Update the account
echo -e "${BLUE}Step 1: Update account profile${NC}"
UPDATE_EMAIL="updated_event_${TEST_TS}@example.com"
UPDATE_PAYLOAD="{\"name\":\"Updated Event Test\",\"email\":\"${UPDATE_EMAIL}\"}"
echo "PUT ${BASE_URL}/profile/${TEST_USER_ID}"
echo "Payload: ${UPDATE_PAYLOAD}"
curl -s -X PUT "${BASE_URL}/profile/${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$UPDATE_PAYLOAD" | python3 -m json.tool
echo ""

sleep 2

# Check logs
echo -e "${BLUE}Step 2: Check logs for user.profile_updated event${NC}"
EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published user.profile_updated" | grep "${TEST_USER_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: user.profile_updated event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_2=1
else
    echo -e "${RED}✗ FAILED: No user.profile_updated event log found${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Verify user.status_changed Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Deactivate account
echo -e "${BLUE}Step 1: Deactivate account${NC}"
STATUS_PAYLOAD='{"is_active":false,"reason":"Event integration test"}'
echo "PUT ${BASE_URL}/status/${TEST_USER_ID}"
curl -s -X PUT "${BASE_URL}/status/${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d "$STATUS_PAYLOAD" | python3 -m json.tool
echo ""

sleep 2

# Check logs
echo -e "${BLUE}Step 2: Check logs for user.status_changed event${NC}"
EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published user.status_changed" | grep "${TEST_USER_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: user.status_changed event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_3=1
else
    echo -e "${RED}✗ FAILED: No user.status_changed event log found${NC}"
    PASSED_3=0
fi
echo ""

# Reactivate for cleanup
curl -s -X PUT "${BASE_URL}/status/${TEST_USER_ID}" \
  -H "Content-Type: application/json" \
  -d '{"is_active":true,"reason":"Cleanup"}' > /dev/null

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Verify user.deleted Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Delete account
echo -e "${BLUE}Step 1: Delete account${NC}"
echo "DELETE ${BASE_URL}/profile/${TEST_USER_ID}"
curl -s -X DELETE "${BASE_URL}/profile/${TEST_USER_ID}?reason=Event%20test%20cleanup" | python3 -m json.tool
echo ""

sleep 2

# Check logs
echo -e "${BLUE}Step 2: Check logs for user.deleted event${NC}"
EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published user.deleted" | grep "${TEST_USER_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: user.deleted event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_4=1
else
    echo -e "${RED}✗ FAILED: No user.deleted event log found${NC}"
    PASSED_4=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Verify Event Handlers Registration${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if event handlers are registered on service startup${NC}"
HANDLER_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep "Subscribed to event" || echo "")

if [ -n "$HANDLER_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event handlers are registered!${NC}"
    echo -e "${GREEN}${HANDLER_LOGS}${NC}"

    # Check specific handlers
    if echo "$HANDLER_LOGS" | grep -q "payment.completed"; then
        echo -e "${GREEN}  ✓ payment.completed handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -q "organization.member_added"; then
        echo -e "${GREEN}  ✓ organization.member_added handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -q "wallet.created"; then
        echo -e "${GREEN}  ✓ wallet.created handler registered${NC}"
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

echo "Test 1: user.created event         - $([ $PASSED_1 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 2: user.profile_updated event - $([ $PASSED_2 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 3: user.status_changed event  - $([ $PASSED_3 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 4: user.deleted event         - $([ $PASSED_4 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
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
    echo "1. Check if NATS is running: kubectl get pods -n ${NAMESPACE} | grep nats"
    echo "2. Check account logs: kubectl logs -n ${NAMESPACE} ${POD_NAME}"
    echo "3. Check event_bus initialization: kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep 'Event bus'"
    exit 1
fi
