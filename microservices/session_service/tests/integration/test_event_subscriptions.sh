#!/bin/bash
# Test Event Subscriptions - Verify session_service can handle incoming events
# This test checks the session_service logs for event subscription registration

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}======================================================================"
echo -e "          EVENT SUBSCRIPTION INTEGRATION TEST"
echo -e "          Session Service"
echo -e "======================================================================${NC}"
echo ""

# Check if we're running in K8s
NAMESPACE="isa-cloud-staging"
if ! kubectl get pods -n ${NAMESPACE} -l app=session &> /dev/null; then
    echo -e "${RED}✗ Cannot find session pods in Kubernetes${NC}"
    echo "Please ensure the service is deployed to K8s"
    exit 1
fi

echo -e "${BLUE}✓ Found session pods in Kubernetes${NC}"
echo ""

# Get the session pod name
POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=session -o jsonpath='{.items[0].metadata.name}')
echo -e "${BLUE}Using pod: ${POD_NAME}${NC}"
echo ""

echo -e "${YELLOW}======================================================================"
echo -e "Test 1: Verify Event Handlers Registration"
echo -e "======================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if event handlers are registered on service startup${NC}"
HANDLER_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -i "Subscribed to\|registered handler" || echo "")

if [ -n "$HANDLER_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event handlers are registered!${NC}"
    echo -e "${GREEN}${HANDLER_LOGS}${NC}"

    # Check for account_service.user.deleted handler
    if echo "$HANDLER_LOGS" | grep -qi "account_service.user.deleted"; then
        echo -e "${GREEN}  ✓ account_service.user.deleted handler registered${NC}"
        PASSED_1=1
    else
        echo -e "${YELLOW}  ⚠ account_service.user.deleted handler not found${NC}"
        PASSED_1=0
    fi
else
    echo -e "${RED}✗ FAILED: No event handler registration logs found${NC}"
    PASSED_1=0
fi
echo ""

echo -e "${YELLOW}======================================================================"
echo -e "Test 2: Verify Event Bus Connection"
echo -e "======================================================================${NC}"
echo ""

echo -e "${BLUE}Checking if event bus is connected${NC}"
EVENT_BUS_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -i "Event bus\|NATS" || echo "")

if [ -n "$EVENT_BUS_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: Event bus logs found${NC}"

    if echo "$EVENT_BUS_LOGS" | grep -qi "initialized successfully\|connected"; then
        echo -e "${GREEN}  ✓ Event bus initialized successfully${NC}"
        PASSED_2=1
    else
        echo -e "${YELLOW}  ⚠ Event bus connection status unclear${NC}"
        PASSED_2=0
    fi
else
    echo -e "${RED}✗ FAILED: No event bus logs found${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}======================================================================"
echo -e "Test 3: Check Event Subscription Capabilities"
echo -e "======================================================================${NC}"
echo ""

echo -e "${BLUE}Verifying session_service can subscribe to events${NC}"

# Check if there are any errors related to event subscription
ERROR_LOGS=$(kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep -i "failed to.*event\|error.*subscrib" || echo "")

if [ -z "$ERROR_LOGS" ]; then
    echo -e "${GREEN}✓ SUCCESS: No event subscription errors found${NC}"
    PASSED_3=1
else
    echo -e "${RED}✗ FAILED: Found event subscription errors:${NC}"
    echo -e "${RED}${ERROR_LOGS}${NC}"
    PASSED_3=0
fi
echo ""

# Summary
echo -e "${CYAN}======================================================================"
echo -e "                    TEST SUMMARY"
echo -e "======================================================================${NC}"
echo ""

TOTAL_PASSED=$((PASSED_1 + PASSED_2 + PASSED_3))
TOTAL_TESTS=3

echo "Test 1: Event handlers registered      - $([ $PASSED_1 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 2: Event bus connection            - $([ $PASSED_2 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo "Test 3: Event subscription capabilities - $([ $PASSED_3 -eq 1 ] && echo -e "${GREEN}✓ PASSED${NC}" || echo -e "${RED}✗ FAILED${NC}")"
echo ""
echo -e "${CYAN}Total: ${TOTAL_PASSED}/${TOTAL_TESTS} tests passed${NC}"
echo ""

if [ $TOTAL_PASSED -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}✓ ALL EVENT SUBSCRIPTION TESTS PASSED!${NC}"
    echo -e "${GREEN}✓ session_service can successfully receive events from:${NC}"
    echo -e "${GREEN}  - account_service (user.deleted)${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "1. Check if NATS is running: kubectl get pods -n ${NAMESPACE} | grep nats"
    echo "2. Check session logs: kubectl logs -n ${NAMESPACE} ${POD_NAME}"
    echo "3. Check event_bus initialization: kubectl logs -n ${NAMESPACE} ${POD_NAME} | grep 'Event bus'"
    exit 1
fi
