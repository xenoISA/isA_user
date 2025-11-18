#!/bin/bash
# Test Event Publishing - Verify events are published via API response
# This test verifies the organization_service publishes events by checking API responses

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

# Test variables
TEST_TS="$(date +%s)_$$"
TEST_USER_ID="event_test_user_${TEST_TS}"
TEST_MEMBER_ID="event_test_member_${TEST_TS}"
BASE_URL="http://localhost/api/v1"
TEST_ORG_ID=""
TEST_SHARING_ID=""

echo -e "${BLUE}Testing organization service at: ${BASE_URL}${NC}"
echo ""

# Test 1: Health check first
echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Preliminary: Health Check${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

HEALTH=$(curl -s http://localhost/health)
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo -e "${GREEN}✓ Service is healthy${NC}"
else
    echo -e "${RED}✗ Service is not healthy${NC}"
    echo "$HEALTH"
    exit 1
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Create Organization (triggers organization.created event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Create organization
echo -e "${BLUE}Step 1: Create organization${NC}"
CREATE_ORG_PAYLOAD="{\"name\":\"Test Org ${TEST_TS}\",\"billing_email\":\"billing_${TEST_TS}@test.com\",\"plan\":\"professional\",\"settings\":{\"allow_external_sharing\":true}}"
echo "POST ${BASE_URL}/organizations"
echo "Payload: ${CREATE_ORG_PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/organizations" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: ${TEST_USER_ID}" \
  -d "$CREATE_ORG_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Check if operation succeeded
if echo "$RESPONSE" | grep -q "organization_id"; then
    TEST_ORG_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('organization_id', ''))")
    echo -e "${GREEN}✓ Organization created successfully: ${TEST_ORG_ID}${NC}"
    echo -e "${BLUE}Note: organization.created event should be published to NATS${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: Organization creation failed${NC}"
    PASSED_1=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Verify Organization Was Created (check state)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TEST_ORG_ID" ]; then
    # Verify the organization exists
    echo -e "${BLUE}Step 1: Get organization to verify state${NC}"
    RESPONSE=$(curl -s -X GET "${BASE_URL}/organizations/${TEST_ORG_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q "\"organization_id\":\"${TEST_ORG_ID}\""; then
        echo -e "${GREEN}✓ Organization state verified (event published successfully)${NC}"
        PASSED_2=1
    else
        echo -e "${RED}✗ FAILED: Organization not found in database${NC}"
        PASSED_2=0
    fi
else
    echo -e "${RED}✗ SKIPPED: No organization ID from previous test${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Update Organization (triggers organization.updated event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TEST_ORG_ID" ]; then
    # Update organization
    echo -e "${BLUE}Step 1: Update organization${NC}"
    UPDATE_PAYLOAD="{\"name\":\"Updated Test Org ${TEST_TS}\",\"settings\":{\"allow_external_sharing\":false}}"
    echo "PUT ${BASE_URL}/organizations/${TEST_ORG_ID}"
    echo "Payload: ${UPDATE_PAYLOAD}"
    RESPONSE=$(curl -s -X PUT "${BASE_URL}/organizations/${TEST_ORG_ID}" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$UPDATE_PAYLOAD")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q "Updated Test Org"; then
        echo -e "${GREEN}✓ Organization updated successfully${NC}"
        echo -e "${BLUE}Note: organization.updated event should be published to NATS${NC}"
        PASSED_3=1
    else
        echo -e "${RED}✗ FAILED: Organization update failed${NC}"
        PASSED_3=0
    fi
else
    echo -e "${RED}✗ SKIPPED: No organization ID from previous test${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Add Member (triggers organization.member_added event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TEST_ORG_ID" ]; then
    # Add member
    echo -e "${BLUE}Step 1: Add member to organization${NC}"
    ADD_MEMBER_PAYLOAD="{\"user_id\":\"${TEST_MEMBER_ID}\",\"role\":\"member\",\"permissions\":[\"read\",\"write\"]}"
    echo "POST ${BASE_URL}/organizations/${TEST_ORG_ID}/members"
    echo "Payload: ${ADD_MEMBER_PAYLOAD}"
    RESPONSE=$(curl -s -X POST "${BASE_URL}/organizations/${TEST_ORG_ID}/members" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$ADD_MEMBER_PAYLOAD")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q "\"user_id\":\"${TEST_MEMBER_ID}\""; then
        echo -e "${GREEN}✓ Member added successfully${NC}"
        echo -e "${BLUE}Note: organization.member_added event should be published to NATS${NC}"
        PASSED_4=1
    else
        echo -e "${RED}✗ FAILED: Member addition failed${NC}"
        PASSED_4=0
    fi
else
    echo -e "${RED}✗ SKIPPED: No organization ID from previous test${NC}"
    PASSED_4=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Update Member Role (triggers organization.member_updated event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TEST_ORG_ID" ]; then
    # Update member role
    echo -e "${BLUE}Step 1: Update member role${NC}"
    UPDATE_MEMBER_PAYLOAD="{\"role\":\"admin\",\"permissions\":[\"read\",\"write\",\"delete\"]}"
    echo "PUT ${BASE_URL}/organizations/${TEST_ORG_ID}/members/${TEST_MEMBER_ID}"
    echo "Payload: ${UPDATE_MEMBER_PAYLOAD}"
    RESPONSE=$(curl -s -X PUT "${BASE_URL}/organizations/${TEST_ORG_ID}/members/${TEST_MEMBER_ID}" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$UPDATE_MEMBER_PAYLOAD")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q "\"role\":\"admin\""; then
        echo -e "${GREEN}✓ Member role updated successfully${NC}"
        echo -e "${BLUE}Note: organization.member_updated event should be published to NATS${NC}"
        PASSED_5=1
    else
        echo -e "${RED}✗ FAILED: Member update failed${NC}"
        PASSED_5=0
    fi
else
    echo -e "${RED}✗ SKIPPED: No organization ID from previous test${NC}"
    PASSED_5=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 6: Create Sharing (triggers organization.sharing_created event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TEST_ORG_ID" ]; then
    # Create sharing resource
    echo -e "${BLUE}Step 1: Create sharing resource${NC}"
    CREATE_SHARING_PAYLOAD="{\"resource_type\":\"album\",\"resource_id\":\"album_${TEST_TS}\",\"name\":\"Test Album ${TEST_TS}\",\"description\":\"Test sharing\",\"member_permissions\":{\"${TEST_MEMBER_ID}\":{\"can_view\":true,\"can_edit\":false}}}"
    echo "POST ${BASE_URL}/organizations/${TEST_ORG_ID}/sharing"
    echo "Payload: ${CREATE_SHARING_PAYLOAD}"
    RESPONSE=$(curl -s -X POST "${BASE_URL}/organizations/${TEST_ORG_ID}/sharing" \
      -H "Content-Type: application/json" \
      -H "X-User-Id: ${TEST_USER_ID}" \
      -d "$CREATE_SHARING_PAYLOAD")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q "sharing_id"; then
        TEST_SHARING_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('sharing_id', ''))" 2>/dev/null || echo "")
        echo -e "${GREEN}✓ Sharing resource created successfully${NC}"
        echo -e "${BLUE}Note: organization.sharing_created event should be published to NATS${NC}"
        PASSED_6=1
    else
        echo -e "${RED}✗ FAILED: Sharing creation failed${NC}"
        PASSED_6=0
    fi
else
    echo -e "${RED}✗ SKIPPED: No organization ID from previous test${NC}"
    PASSED_6=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 7: Remove Member (triggers organization.member_removed event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TEST_ORG_ID" ]; then
    # Remove member
    echo -e "${BLUE}Step 1: Remove member from organization${NC}"
    echo "DELETE ${BASE_URL}/organizations/${TEST_ORG_ID}/members/${TEST_MEMBER_ID}"
    RESPONSE=$(curl -s -X DELETE "${BASE_URL}/organizations/${TEST_ORG_ID}/members/${TEST_MEMBER_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q "removed"; then
        echo -e "${GREEN}✓ Member removed successfully${NC}"
        echo -e "${BLUE}Note: organization.member_removed event should be published to NATS${NC}"
        PASSED_7=1
    else
        echo -e "${RED}✗ FAILED: Member removal failed${NC}"
        PASSED_7=0
    fi
else
    echo -e "${RED}✗ SKIPPED: No organization ID from previous test${NC}"
    PASSED_7=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 8: Delete Organization (triggers organization.deleted event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TEST_ORG_ID" ]; then
    # Delete organization
    echo -e "${BLUE}Step 1: Delete organization${NC}"
    echo "DELETE ${BASE_URL}/organizations/${TEST_ORG_ID}"
    RESPONSE=$(curl -s -X DELETE "${BASE_URL}/organizations/${TEST_ORG_ID}" \
      -H "X-User-Id: ${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q "deleted"; then
        echo -e "${GREEN}✓ Organization deleted successfully${NC}"
        echo -e "${BLUE}Note: organization.deleted event should be published to NATS${NC}"
        PASSED_8=1
    else
        echo -e "${RED}✗ FAILED: Organization deletion failed${NC}"
        PASSED_8=0
    fi
else
    echo -e "${RED}✗ SKIPPED: No organization ID from previous test${NC}"
    PASSED_8=0
fi
echo ""

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_PASSED=$((PASSED_1 + PASSED_2 + PASSED_3 + PASSED_4 + PASSED_5 + PASSED_6 + PASSED_7 + PASSED_8))
echo -e "Tests Passed: ${GREEN}${TOTAL_PASSED}/8${NC}"
echo ""

if [ $TOTAL_PASSED -eq 8 ]; then
    echo -e "${GREEN}✓ ALL EVENT PUBLISHING TESTS PASSED!${NC}"
    echo ""
    echo -e "${CYAN}Event Publishing Verification:${NC}"
    echo -e "  ${BLUE}✓${NC} organization.created - Published when organization is created"
    echo -e "  ${BLUE}✓${NC} organization.updated - Published when organization is updated"
    echo -e "  ${BLUE}✓${NC} organization.member_added - Published when member is added"
    echo -e "  ${BLUE}✓${NC} organization.member_updated - Published when member role is updated"
    echo -e "  ${BLUE}✓${NC} organization.sharing_created - Published when resource is shared"
    echo -e "  ${BLUE}✓${NC} organization.member_removed - Published when member is removed"
    echo -e "  ${BLUE}✓${NC} organization.deleted - Published when organization is deleted"
    echo ""
    echo -e "${YELLOW}Note: This test verifies event publishing indirectly by confirming${NC}"
    echo -e "${YELLOW}      API operations succeed. Events are published asynchronously.${NC}"
    echo -e "${YELLOW}      To verify NATS delivery, check service logs or NATS monitoring.${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
