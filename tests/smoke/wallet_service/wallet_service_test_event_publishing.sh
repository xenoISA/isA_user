#!/bin/bash
# Test Event Publishing - Verify events are actually published to NATS
# This test checks the wallet_service logs for event publishing confirmation

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
if ! kubectl get pods -n ${NAMESPACE} -l app=wallet &> /dev/null; then
    echo -e "${RED}✗ Cannot find wallet pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found wallet pods in Kubernetes${NC}"
echo ""

# Get the wallet pod name
POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=wallet -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="wallet_event_test_${TEST_TS}"
BASE_URL="http://localhost/api/v1"

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Verify wallet.created Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Clear recent logs
echo -e "${BLUE}Step 1: Get baseline log position${NC}"
BASELINE_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=5 | wc -l)
echo "Baseline log lines: ${BASELINE_LOGS}"
echo ""

# Create a new wallet
echo -e "${BLUE}Step 2: Create new wallet (should trigger wallet.created event)${NC}"
PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"wallet_type\":\"fiat\",\"currency\":\"USD\",\"initial_balance\":100.00}"
echo "POST ${BASE_URL}/wallets"
echo "Payload: ${PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/wallets" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Extract wallet_id from response
WALLET_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('wallet_id', ''))" 2>/dev/null || echo "")

if [ -z "$WALLET_ID" ]; then
    echo -e "${RED}✗ Failed to create wallet or extract wallet_id${NC}"
    PASSED_1=0
else
    # Wait a moment for logs to be written
    sleep 2

    # Check logs for event publishing
    echo -e "${BLUE}Step 3: Check logs for event publishing confirmation${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published wallet.created" | grep "${WALLET_ID}" || echo "")

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
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Verify wallet.deposited Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$WALLET_ID" ]; then
    # Deposit to wallet
    echo -e "${BLUE}Step 1: Deposit to wallet${NC}"
    DEPOSIT_PAYLOAD='{"amount":50.00,"description":"Event test deposit","reference_id":"event_test_deposit_001"}'
    echo "POST ${BASE_URL}/wallets/${WALLET_ID}/deposit"
    echo "Payload: ${DEPOSIT_PAYLOAD}"
    curl -s -X POST "${BASE_URL}/wallets/${WALLET_ID}/deposit" \
      -H "Content-Type: application/json" \
      -d "$DEPOSIT_PAYLOAD" | python3 -m json.tool
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for wallet.deposited event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published wallet.deposited" | grep "${WALLET_ID}" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: wallet.deposited event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_2=1
    else
        echo -e "${RED}✗ FAILED: No wallet.deposited event log found${NC}"
        PASSED_2=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No wallet_id available from Test 1${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Verify wallet.consumed Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$WALLET_ID" ]; then
    # Consume from wallet
    echo -e "${BLUE}Step 1: Consume from wallet${NC}"
    CONSUME_PAYLOAD='{"amount":10.00,"description":"Event test consumption","metadata":{"test":"event_publishing"}}'
    echo "POST ${BASE_URL}/wallets/${WALLET_ID}/consume"
    echo "Payload: ${CONSUME_PAYLOAD}"
    curl -s -X POST "${BASE_URL}/wallets/${WALLET_ID}/consume" \
      -H "Content-Type: application/json" \
      -d "$CONSUME_PAYLOAD" | python3 -m json.tool
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for wallet.consumed event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep -E "(Published wallet.consumed|Published wallet.tokens.deducted)" | grep "${WALLET_ID}" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: wallet.consumed/tokens.deducted event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_3=1
    else
        echo -e "${RED}✗ FAILED: No wallet.consumed event log found${NC}"
        PASSED_3=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No wallet_id available from Test 1${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Verify wallet.withdrawn Event Publishing${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$WALLET_ID" ]; then
    # Withdraw from wallet
    echo -e "${BLUE}Step 1: Withdraw from wallet${NC}"
    WITHDRAW_PAYLOAD='{"amount":25.00,"description":"Event test withdrawal","destination":"test_bank_account"}'
    echo "POST ${BASE_URL}/wallets/${WALLET_ID}/withdraw"
    echo "Payload: ${WITHDRAW_PAYLOAD}"
    curl -s -X POST "${BASE_URL}/wallets/${WALLET_ID}/withdraw" \
      -H "Content-Type: application/json" \
      -d "$WITHDRAW_PAYLOAD" | python3 -m json.tool
    echo ""

    sleep 2

    # Check logs
    echo -e "${BLUE}Step 2: Check logs for wallet.withdrawn event${NC}"
    EVENT_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} --tail=50 | grep "Published wallet.withdrawn" | grep "${WALLET_ID}" || echo "")

    if [ -n "$EVENT_LOGS" ]; then
        echo -e "${GREEN}✓ SUCCESS: wallet.withdrawn event was published!${NC}"
        echo -e "${GREEN}Log entry: ${EVENT_LOGS}${NC}"
        PASSED_4=1
    else
        echo -e "${RED}✗ FAILED: No wallet.withdrawn event log found${NC}"
        PASSED_4=0
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED: No wallet_id available from Test 1${NC}"
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
    if echo "$HANDLER_LOGS" | grep -q "user.created"; then
        echo -e "${GREEN}  ✓ user.created handler registered${NC}"
    fi
    if echo "$HANDLER_LOGS" | grep -q "billing.calculated"; then
        echo -e "${GREEN}  ✓ billing.calculated handler registered${NC}"
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

echo "Test 1: wallet.created event          - $([ $PASSED_1 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 2: wallet.deposited event        - $([ $PASSED_2 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 3: wallet.consumed event         - $([ $PASSED_3 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 4: wallet.withdrawn event        - $([ $PASSED_4 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 5: Event handlers registered     - $([ $PASSED_5 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
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
    echo "2. Check wallet logs: kubectl logs -n ${NAMESPACE} ${POD_NAME}"
    echo "3. Check event_bus initialization: kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep 'Event bus'"
    exit 1
fi
