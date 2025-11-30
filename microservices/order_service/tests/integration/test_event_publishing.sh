#!/bin/bash
# Test Event Publishing - Verify events are actually published to NATS
# This test checks the order_service logs for event publishing confirmation

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
echo -e "${CYAN}          Order Service${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Check if we're running in K8s
NAMESPACE="isa-cloud-staging"
if ! kubectl get pods -n ${NAMESPACE} -l app=order &> /dev/null; then
    echo -e "${RED}✗ Cannot find order pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found order pods in Kubernetes${NC}"
echo ""

# Get the order pod name
POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=order -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="event_test_user_${TEST_TS}"
BASE_URL="http://localhost/api/v1/orders"

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Verify order.created Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Clear recent logs baseline
echo -e "${BLUE}Step 1: Get baseline log position${NC}"
BASELINE_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=5 | wc -l)
echo "Baseline log lines: ${BASELINE_LOGS}"
echo ""

# Create a new order
echo -e "${BLUE}Step 2: Create new order (should trigger order.created event)${NC}"
PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"order_type\":\"purchase\",\"total_amount\":10.00,\"currency\":\"USD\",\"metadata\":{\"description\":\"Event test order\"}}"
echo "POST ${BASE_URL}"
echo "Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Extract order_id from response
ORDER_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('order', {}).get('order_id', ''))" 2>/dev/null)

# Wait a moment for logs to be written
sleep 2

# Check logs for event publishing
echo -e "${BLUE}Step 3: Check logs for event publishing confirmation${NC}"
EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep -i "published.*order.created\|order.created.*event" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: order.created event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: No order.created event publishing log found${NC}"
    echo -e "${YELLOW}Recent logs:${NC}"
    kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=20
    PASSED_1=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Verify order.completed Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$ORDER_ID" ] && [ "$ORDER_ID" != "null" ]; then
    echo -e "${BLUE}Step 1: Complete the order${NC}"
    COMPLETE_PAYLOAD='{"payment_confirmed":true,"transaction_id":"test_tx_'${TEST_TS}'"}'
    echo "POST ${BASE_URL}/${ORDER_ID}/complete"
    echo "Payload: ${COMPLETE_PAYLOAD}"
    curl -s -X POST "${BASE_URL}/${ORDER_ID}/complete" \
      -H "Content-Type: application/json" \
      -d "$COMPLETE_PAYLOAD" | python3 -m json.tool 2>/dev/null || true
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for order.completed event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep -i "published.*order.completed\|order.completed.*event" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: order.completed event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_2=1
    else
        echo -e "${RED}✗ FAILED: No order.completed event log found${NC}"
        PASSED_2=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No valid order_id to test completion${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Verify order.canceled Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Create another order to cancel
CANCEL_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"order_type\":\"subscription\",\"total_amount\":29.99,\"currency\":\"USD\",\"metadata\":{\"description\":\"Order to cancel\"}}"
echo -e "${BLUE}Step 1: Create order to cancel${NC}"
CANCEL_RESPONSE=$(curl -s -X POST "${BASE_URL}" \
  -H "Content-Type: application/json" \
  -d "$CANCEL_PAYLOAD")
CANCEL_ORDER_ID=$(echo "$CANCEL_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('order', {}).get('order_id', ''))" 2>/dev/null)
echo ""

sleep 1

if [ -n "$CANCEL_ORDER_ID" ] && [ "$CANCEL_ORDER_ID" != "null" ]; then
    echo -e "${BLUE}Step 2: Cancel the order${NC}"
    CANCEL_REQ='{"reason":"Event integration test"}'
    echo "POST ${BASE_URL}/${CANCEL_ORDER_ID}/cancel"
    curl -s -X POST "${BASE_URL}/${CANCEL_ORDER_ID}/cancel" \
      -H "Content-Type: application/json" \
      -d "$CANCEL_REQ" | python3 -m json.tool 2>/dev/null || true
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 3: Check logs for order.canceled event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep -i "published.*order.canceled\|order.canceled.*event" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: order.canceled event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_3=1
    else
        echo -e "${RED}✗ FAILED: No order.canceled event log found${NC}"
        PASSED_3=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: Failed to create order for cancellation test${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Verify Event Handlers Registration${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if event handlers are registered on service startup${NC}"
HANDLER_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -i "registered handler\|event handler" || echo "")

if [ -n "$HANDLER_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event handlers are registered!${NC}"
    echo -e "${GREEN}${HANDLER_LOGS}${NC}"

    # Check specific handlers
    if echo "$HANDLER_LOGS" | grep -qi "payment.completed\|payment_completed"; then
        echo -e "${GREEN}  ✓ payment.completed handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -qi "payment.failed\|payment_failed"; then
        echo -e "${GREEN}  ✓ payment.failed handler registered${NC}"
    fi
    PASSED_4=1
else
    echo -e "${RED}✗ FAILED: No event handler registration logs found${NC}"
    PASSED_4=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Verify Event Bus Connection${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if order service connected to NATS event bus${NC}"
BUS_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -i "event bus\|nats" | head -5 || echo "")

if [ -n "$BUS_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event bus connection logs found!${NC}"
    echo -e "${GREEN}${BUS_LOGS}${NC}"
    PASSED_5=1
else
    echo -e "${RED}✗ FAILED: No event bus connection logs found${NC}"
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

echo "Test 1: order.created event         - $([ $PASSED_1 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 2: order.completed event       - $([ $PASSED_2 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 3: order.canceled event        - $([ $PASSED_3 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 4: Event handlers registered   - $([ $PASSED_4 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 5: Event bus connection        - $([ $PASSED_5 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
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
    echo "2. Check order logs: kubectl logs -n ${NAMESPACE} ${POD_NAME}"
    echo "3. Check event_bus initialization: kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep 'Event bus'"
    exit 1
fi
