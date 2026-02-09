#!/bin/bash
# Test Event Publishing - Verify events are actually published to NATS
# This test checks the product_service logs for event publishing confirmation

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
if ! kubectl get pods -n ${NAMESPACE} -l app=product &> /dev/null; then
    echo -e "${RED}✗ Cannot find product pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found product pods in Kubernetes${NC}"
echo ""

# Get the product pod name
POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=product -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="test_user_001"  # Using existing real user
TEST_PLAN_ID="pro-plan"
BASE_URL="http://localhost/api/v1/product"

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Verify subscription.created Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Clear recent logs
echo -e "${BLUE}Step 1: Get baseline log position${NC}"
BASELINE_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=5 | wc -l)
echo "Baseline log lines: ${BASELINE_LOGS}"
echo ""

# Create a new subscription
echo -e "${BLUE}Step 2: Create new subscription (should trigger subscription.created event)${NC}"
PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"plan_id\":\"${TEST_PLAN_ID}\",\"billing_cycle\":\"monthly\",\"metadata\":{\"source\":\"event_test\"}}"
echo "POST ${BASE_URL}/subscriptions"
echo "Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/subscriptions" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Extract subscription_id from response
SUBSCRIPTION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('subscription_id', ''))" 2>/dev/null || echo "")

# Wait a moment for logs to be written
sleep 2

# Check logs for event publishing
echo -e "${BLUE}Step 3: Check logs for event publishing confirmation${NC}"
if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published subscription.created" | grep "${SUBSCRIPTION_ID}" || echo "")
else
    # Fallback: just search for the event type
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published subscription.created" || echo "")
fi

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
echo -e "${YELLOW}Test 2: Verify subscription.status_changed Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    # Update the subscription status
    echo -e "${BLUE}Step 1: Update subscription status (active)${NC}"
    echo "PUT ${BASE_URL}/subscriptions/${SUBSCRIPTION_ID}/status"
    STATUS_RESPONSE=$(curl -s -X PUT "${BASE_URL}/subscriptions/${SUBSCRIPTION_ID}/status" \
      -H "Content-Type: application/json" \
      -d '{"status":"active"}')
    echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for subscription.status_changed event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep -E "Published subscription status change event" | grep "${SUBSCRIPTION_ID}" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: subscription status change event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_2=1
    else
        echo -e "${RED}✗ FAILED: No subscription status change event log found${NC}"
        PASSED_2=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No subscription ID available${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Verify product.usage.recorded Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Record product usage
echo -e "${BLUE}Step 1: Record product usage${NC}"
USAGE_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"product_id\":\"prod_ai_tokens\",\"usage_amount\":100.5,\"subscription_id\":\"${SUBSCRIPTION_ID}\",\"usage_details\":{\"endpoint\":\"/api/test\"}}"
echo "POST ${BASE_URL}/usage/record"
echo "Payload: ${USAGE_PAYLOAD}"
USAGE_RESPONSE=$(curl -s -X POST "${BASE_URL}/usage/record" \
  -H "Content-Type: application/json" \
  -d "$USAGE_PAYLOAD")
echo "$USAGE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$USAGE_RESPONSE"
echo ""

sleep 2

# Check logs
echo -e "${BLUE}Step 2: Check logs for product.usage.recorded event${NC}"
EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published product.usage.recorded" | grep "${TEST_USER_ID}" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: product.usage.recorded event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_3=1
else
    echo -e "${RED}✗ FAILED: No product.usage.recorded event log found${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Verify subscription.canceled Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    # Cancel subscription
    echo -e "${BLUE}Step 1: Cancel subscription${NC}"
    echo "PUT ${BASE_URL}/subscriptions/${SUBSCRIPTION_ID}/status"
    curl -s -X PUT "${BASE_URL}/subscriptions/${SUBSCRIPTION_ID}/status" \
      -H "Content-Type: application/json" \
      -d '{"status":"canceled"}' | python3 -m json.tool 2>/dev/null
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for subscription status change (to canceled) event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep -E "Published subscription status change event.*canceled" | grep "${SUBSCRIPTION_ID}" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: subscription.canceled event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_4=1
    else
        echo -e "${RED}✗ FAILED: No subscription.canceled event log found${NC}"
        PASSED_4=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No subscription ID available${NC}"
    PASSED_4=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Verify Event Handlers Registration${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if event handlers are registered on service startup${NC}"
HANDLER_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} 2>/dev/null | grep -E "Subscribed to .* events" || echo "")

if [ -n "$HANDLER_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event handlers are registered!${NC}"
    echo -e "${GREEN}${HANDLER_LOGS}${NC}"

    # Check specific handlers
    if echo "$HANDLER_LOGS" | grep -q "payment.completed"; then
        echo -e "${GREEN}  ✓ payment.completed handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -q "wallet.insufficient_funds"; then
        echo -e "${GREEN}  ✓ wallet.insufficient_funds handler registered${NC}"
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

echo "Test 1: subscription.created event      - $([ $PASSED_1 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 2: subscription.status_changed     - $([ $PASSED_2 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 3: product.usage.recorded event    - $([ $PASSED_3 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 4: subscription.canceled event     - $([ $PASSED_4 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 5: Event handlers registered       - $([ $PASSED_5 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
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
    echo "2. Check product logs: kubectl logs -n ${NAMESPACE} ${POD_NAME}"
    echo "3. Check event_bus initialization: kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep 'Event bus'"
    exit 1
fi
