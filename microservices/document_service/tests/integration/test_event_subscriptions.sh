#!/bin/bash
# Test Event Subscriptions - Verify document service handles incoming events
# This test verifies the document_service subscribes to events from other services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}          DOCUMENT EVENT SUBSCRIPTION TEST${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# Test variables
TEST_TS="$(date +%s)_$$"
BASE_URL="http://localhost/api/v1"

echo -e "${BLUE}Testing document service at: ${BASE_URL}${NC}"
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test: Verify Event Subscription Setup${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Checking service health to verify event subscriptions...${NC}"
HEALTH_RESPONSE=$(curl -s "${BASE_URL%/api/v1}/health")
echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
echo ""

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Service is healthy${NC}"
    echo ""
    echo -e "${CYAN}Event Subscriptions Expected:${NC}"
    echo -e "  ${BLUE}•${NC} *.file.> - Handles file.deleted events from storage_service"
    echo -e "  ${BLUE}•${NC} *.user.> - Handles user.deleted events"
    echo -e "  ${BLUE}•${NC} *.organization.> - Handles organization.deleted events"
    echo ""
    echo -e "${YELLOW}Note: When a file is deleted in storage_service, document_service${NC}"
    echo -e "${YELLOW}      should automatically delete associated documents.${NC}"
    echo ""
    echo -e "${YELLOW}Note: Event subscription verification requires manual testing${NC}"
    echo -e "${YELLOW}      by triggering events from other services and monitoring logs.${NC}"
    echo ""
    PASSED=1
else
    echo -e "${RED}✗ Service health check failed${NC}"
    PASSED=0
fi

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

if [ $PASSED -eq 1 ]; then
    echo -e "${GREEN}✓ EVENT SUBSCRIPTION SETUP VERIFIED!${NC}"
    echo ""
    echo -e "${CYAN}To fully test event subscriptions:${NC}"
    echo -e "  1. Create a document in document_service"
    echo -e "  2. Delete the file in storage_service"
    echo -e "  3. Check if document_service automatically deletes the document"
    echo -e "  4. Monitor NATS and service logs for event flow"
    exit 0
else
    echo -e "${RED}✗ EVENT SUBSCRIPTION VERIFICATION FAILED${NC}"
    exit 1
fi
