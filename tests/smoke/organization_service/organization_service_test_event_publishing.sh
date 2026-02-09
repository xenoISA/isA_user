#!/bin/bash
# Test Event Publishing - Verify events are actually published to NATS
# This test checks the organization_service logs for event publishing confirmation

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
echo -e "${CYAN}          Organization Service${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Check if we're running in K8s
NAMESPACE="isa-cloud-staging"
if ! kubectl get pods -n ${NAMESPACE} -l app=organization &> /dev/null; then
    echo -e "${RED}✗ Cannot find organization pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found organization pods in Kubernetes${NC}"
echo ""

# Get the organization pod name
POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=organization -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="event_test_user_${TEST_TS}"
TEST_MEMBER_ID="event_test_member_${TEST_TS}"
BASE_URL="http://localhost/api/v1/organizations"

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Verify organization.created Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Clear recent logs baseline
echo -e "${BLUE}Step 1: Get baseline log position${NC}"
BASELINE_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=5 | wc -l)
echo "Baseline log lines: ${BASELINE_LOGS}"
echo ""

# Create organization
echo -e "${BLUE}Step 2: Create new organization (should trigger organization.created event)${NC}"
PAYLOAD="{\"name\":\"Event Test Org ${TEST_TS}\",\"billing_email\":\"billing_${TEST_TS}@example.com\",\"plan\":\"professional\",\"settings\":{\"max_members\":10}}"
echo "POST ${BASE_URL}"
echo "Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: ${TEST_USER_ID}" \
  -d "$PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Extract organization_id from response
ORG_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('organization_id', ''))" 2>/dev/null)

# Wait a moment for logs to be written
sleep 2

# Check logs for event publishing
echo -e "${BLUE}Step 3: Check logs for event publishing confirmation${NC}"
EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published organization.created" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: organization.created event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: No organization.created event publishing log found${NC}"
    echo -e "${YELLOW}Recent logs:${NC}"
    kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=20
    PASSED_1=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Verify organization.member_added Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$ORG_ID" ] && [ "$ORG_ID" != "null" ]; then
    echo -e "${BLUE}Step 1: Add member to organization${NC}"
    MEMBER_PAYLOAD="{\"user_id\":\"${TEST_MEMBER_ID}\",\"role\":\"member\"}"
    echo "POST ${BASE_URL}/${ORG_ID}/members"
    echo "Payload: ${MEMBER_PAYLOAD}"
    curl -s -X POST "${BASE_URL}/${ORG_ID}/members" \
      -H "Content-Type: application/json" \
      -H "X-User-ID: ${TEST_USER_ID}" \
      -d "$MEMBER_PAYLOAD" | python3 -m json.tool 2>/dev/null || true
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for organization.member_added event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published organization.member_added" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: organization.member_added event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_2=1
    else
        echo -e "${RED}✗ FAILED: No organization.member_added event log found${NC}"
        PASSED_2=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No valid organization_id to test member addition${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Verify organization.updated Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$ORG_ID" ] && [ "$ORG_ID" != "null" ]; then
    echo -e "${BLUE}Step 1: Update organization${NC}"
    UPDATE_PAYLOAD="{\"name\":\"Updated Event Test Org ${TEST_TS}\",\"settings\":{\"max_members\":20}}"
    echo "PUT ${BASE_URL}/${ORG_ID}"
    echo "Payload: ${UPDATE_PAYLOAD}"
    curl -s -X PUT "${BASE_URL}/${ORG_ID}" \
      -H "Content-Type: application/json" \
      -H "X-User-ID: ${TEST_USER_ID}" \
      -d "$UPDATE_PAYLOAD" | python3 -m json.tool 2>/dev/null || true
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for organization.updated event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published organization.updated" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: organization.updated event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_3=1
    else
        echo -e "${RED}✗ FAILED: No organization.updated event log found${NC}"
        PASSED_3=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No valid organization_id to test update${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Verify organization.member_removed Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$ORG_ID" ] && [ "$ORG_ID" != "null" ]; then
    echo -e "${BLUE}Step 1: Remove member from organization${NC}"
    echo "DELETE ${BASE_URL}/${ORG_ID}/members/${TEST_MEMBER_ID}"
    curl -s -X DELETE "${BASE_URL}/${ORG_ID}/members/${TEST_MEMBER_ID}?reason=Event%20test" \
      -H "X-User-ID: ${TEST_USER_ID}" | python3 -m json.tool 2>/dev/null || true
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for organization.member_removed event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published organization.member_removed" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: organization.member_removed event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_4=1
    else
        echo -e "${RED}✗ FAILED: No organization.member_removed event log found${NC}"
        PASSED_4=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No valid organization_id to test member removal${NC}"
    PASSED_4=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Verify organization.deleted Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$ORG_ID" ] && [ "$ORG_ID" != "null" ]; then
    echo -e "${BLUE}Step 1: Delete organization${NC}"
    echo "DELETE ${BASE_URL}/${ORG_ID}"
    curl -s -X DELETE "${BASE_URL}/${ORG_ID}?reason=Event%20integration%20test" \
      -H "X-User-ID: ${TEST_USER_ID}" | python3 -m json.tool 2>/dev/null || true
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for organization.deleted event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published organization.deleted" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: organization.deleted event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_5=1
    else
        echo -e "${RED}✗ FAILED: No organization.deleted event log found${NC}"
        PASSED_5=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No valid organization_id to test deletion${NC}"
    PASSED_5=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 6: Verify Event Handlers Registration${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if event handlers are registered on service startup${NC}"
HANDLER_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -i "Subscribed to.*events\|registered handler\|event handler" || echo "")

if [ -n "$HANDLER_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event handlers are registered!${NC}"
    echo -e "${GREEN}${HANDLER_LOGS}${NC}"

    # Check specific handlers
    if echo "$HANDLER_LOGS" | grep -qi "account_service.user.deleted\|user.deleted"; then
        echo -e "${GREEN}  ✓ account_service.user.deleted handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -qi "album_service.album.deleted\|album.deleted"; then
        echo -e "${GREEN}  ✓ album_service.album.deleted handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -qi "billing_service.billing.subscription_changed\|subscription_changed"; then
        echo -e "${GREEN}  ✓ billing_service.billing.subscription_changed handler registered${NC}"
    fi
    PASSED_6=1
else
    echo -e "${RED}✗ FAILED: No event handler registration logs found${NC}"
    PASSED_6=0
fi
echo ""

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                    TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_PASSED=$((PASSED_1 + PASSED_2 + PASSED_3 + PASSED_4 + PASSED_5 + PASSED_6))
TOTAL_TESTS=6

echo "Test 1: organization.created event       - $([ $PASSED_1 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 2: member_added event               - $([ $PASSED_2 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 3: organization.updated event       - $([ $PASSED_3 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 4: member_removed event             - $([ $PASSED_4 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 5: organization.deleted event       - $([ $PASSED_5 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 6: Event handlers registered        - $([ $PASSED_6 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
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
    echo "2. Check organization logs: kubectl logs -n ${NAMESPACE} ${POD_NAME}"
    echo "3. Check event_bus initialization: kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep 'Event bus'"
    exit 1
fi
