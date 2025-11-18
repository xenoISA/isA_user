#!/bin/bash
# Test Event Publishing - Verify events are actually published to NATS
# This test checks the payment_service logs for event publishing confirmation

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
if ! kubectl get pods -l app=payment-service &> /dev/null; then
    echo -e "${RED}✗ Cannot find payment-service pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found payment-service pods in Kubernetes${NC}"
echo ""

# Get the payment-service pod name
POD_NAME=$(kubectl get pods -l app=payment-service -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="event_test_user_${TEST_TS}"
BASE_URL="http://localhost/api/v1/payments"

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Verify payment.intent.created Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Clear recent logs
echo -e "${BLUE}Step 1: Get baseline log position${NC}"
BASELINE_LOGS=$(kubectl logs ${POD_NAME} --tail=5 | wc -l)
echo "Baseline log lines: ${BASELINE_LOGS}"
echo ""

# Create a payment intent
echo -e "${BLUE}Step 2: Create payment intent (should trigger payment.intent.created event)${NC}"
PAYLOAD="{\"amount\":29.99,\"currency\":\"USD\",\"description\":\"Test payment\",\"user_id\":\"${TEST_USER_ID}\",\"metadata\":{\"test\":true}}"
echo "POST ${BASE_URL}/payments/intent"
echo "Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/payments/intent" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
PAYMENT_INTENT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('payment_intent_id', ''))")
echo ""

# Wait a moment for logs to be written
sleep 2

# Check logs for event publishing
echo -e "${BLUE}Step 3: Check logs for event publishing confirmation${NC}"
EVENT_LOGS=$(kubectl logs ${POD_NAME} --tail=50 | grep "Published payment.intent.created" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event was published to NATS!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: No event publishing log found${NC}"
    echo -e "${YELLOW}Recent logs:${NC}"
    kubectl logs ${POD_NAME} --tail=20
    PASSED_1=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Verify payment.completed Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$PAYMENT_INTENT_ID" ] && [ "$PAYMENT_INTENT_ID" != "null" ]; then
    # Confirm the payment
    echo -e "${BLUE}Step 1: Confirm payment${NC}"
    CONFIRM_PAYLOAD='{"processor_response":{"status":"succeeded","test":true}}'
    echo "POST ${BASE_URL}/payments/${PAYMENT_INTENT_ID}/confirm"
    echo "Payload: ${CONFIRM_PAYLOAD}"
    curl -s -X POST "${BASE_URL}/payments/${PAYMENT_INTENT_ID}/confirm" \
      -H "Content-Type: application/json" \
      -d "$CONFIRM_PAYLOAD" | python3 -m json.tool
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for payment.completed event${NC}"
    EVENT_LOGS=$(kubectl logs ${POD_NAME} --tail=50 | grep "Published payment.completed" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: payment.completed event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_2=1
    else
        echo -e "${RED}✗ FAILED: No payment.completed event log found${NC}"
        PASSED_2=0
    fi
else
    echo -e "${RED}✗ SKIPPED: No payment intent ID from Test 1${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Verify subscription.created Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Create a subscription plan first
echo -e "${BLUE}Step 1: Create subscription plan${NC}"
PLAN_ID="plan_test_event_${TEST_TS}"
PLAN_PAYLOAD="{\"plan_id\":\"${PLAN_ID}\",\"name\":\"Test Event Plan\",\"tier\":\"pro\",\"price\":29.99,\"billing_cycle\":\"monthly\",\"features\":{\"storage_gb\":100},\"trial_days\":14}"
curl -s -X POST "${BASE_URL}/plans" \
  -H "Content-Type: application/json" \
  -d "$PLAN_PAYLOAD" > /dev/null
echo ""

# Create subscription
echo -e "${BLUE}Step 2: Create subscription${NC}"
SUB_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"plan_id\":\"${PLAN_ID}\",\"metadata\":{\"test\":true}}"
echo "POST ${BASE_URL}/subscriptions"
RESPONSE=$(curl -s -X POST "${BASE_URL}/subscriptions" \
  -H "Content-Type: application/json" \
  -d "$SUB_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
SUBSCRIPTION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('subscription', {}).get('subscription_id', ''))")
echo ""

sleep 2

# Check logs
echo -e "${BLUE}Step 3: Check logs for subscription.created event${NC}"
EVENT_LOGS=$(kubectl logs ${POD_NAME} --tail=50 | grep "Published subscription.created" || echo "")

if [ -n "$EVENT_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: subscription.created event was published!${NC}"
    echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
    PASSED_3=1
else
    echo -e "${RED}✗ FAILED: No subscription.created event log found${NC}"
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
    CANCEL_PAYLOAD='{"immediate":false,"reason":"Event test cleanup"}'
    echo "POST ${BASE_URL}/subscriptions/${SUBSCRIPTION_ID}/cancel"
    curl -s -X POST "${BASE_URL}/subscriptions/${SUBSCRIPTION_ID}/cancel" \
      -H "Content-Type: application/json" \
      -d "$CANCEL_PAYLOAD" | python3 -m json.tool
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for subscription.canceled event${NC}"
    EVENT_LOGS=$(kubectl logs ${POD_NAME} --tail=50 | grep "Published subscription.canceled" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: subscription.canceled event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_4=1
    else
        echo -e "${RED}✗ FAILED: No subscription.canceled event log found${NC}"
        PASSED_4=0
    fi
else
    echo -e "${RED}✗ SKIPPED: No subscription ID from Test 3${NC}"
    PASSED_4=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Verify Event Handlers Registration${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if event handlers are registered on service startup${NC}"
HANDLER_LOGS=$(kubectl logs ${POD_NAME} | grep "Subscribed to event\|Registered handler" || echo "")

if [ -n "$HANDLER_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event handlers are registered!${NC}"
    echo -e "${GREEN}${HANDLER_LOGS}${NC}"

    # Check specific handlers
    if echo "$HANDLER_LOGS" | grep -q "order.created"; then
        echo -e "${GREEN}  ✓ order.created handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -q "wallet.balance_changed"; then
        echo -e "${GREEN}  ✓ wallet.balance_changed handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -q "wallet.insufficient_funds"; then
        echo -e "${GREEN}  ✓ wallet.insufficient_funds handler registered${NC}"
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

echo "Test 1: payment.intent.created event    - $([ $PASSED_1 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 2: payment.completed event         - $([ $PASSED_2 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 3: subscription.created event      - $([ $PASSED_3 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
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
    echo "1. Check if NATS is running: kubectl get pods | grep nats"
    echo "2. Check payment-service logs: kubectl logs ${POD_NAME}"
    echo "3. Check event_bus initialization: kubectl logs ${POD_NAME} | grep 'Event bus'"
    exit 1
fi
