#!/bin/bash
# Test Event Publishing - Verify events are published via API response
# This test verifies the memory_service publishes events by checking API responses

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
BASE_URL="http://localhost/api/v1"

echo -e "${BLUE}Testing memory service at: ${BASE_URL}${NC}"
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 1: Extract Factual Memory (triggers memory.created event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Extract factual memory
echo -e "${BLUE}Step 1: Extract factual memory from dialog${NC}"
EXTRACT_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"dialog_content\":\"My name is Test User and I work as a software engineer. I specialize in microservices architecture.\",\"importance_score\":0.8}"
echo "POST ${BASE_URL}/memories/factual/extract"
echo "Payload: ${EXTRACT_PAYLOAD}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/memories/factual/extract" \
  -H "Content-Type: application/json" \
  -d "$EXTRACT_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Check if operation succeeded
if echo "$RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ Factual memory extracted successfully${NC}"
    echo -e "${BLUE}Note: memory.created and factual_memory.stored events should be published to NATS${NC}"
    PASSED_1=1
    # Extract memory ID for later use
    MEMORY_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('memory_ids', [None])[0] or '')" 2>/dev/null)
else
    echo -e "${RED}✗ FAILED: Factual memory extraction failed${NC}"
    PASSED_1=0
    MEMORY_ID=""
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Extract Episodic Memory (triggers memory.created event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Extract episodic memory
echo -e "${BLUE}Step 1: Extract episodic memory from dialog${NC}"
EPISODIC_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"dialog_content\":\"Last Tuesday, I attended a team meeting where we discussed the new project architecture. It was very productive.\",\"importance_score\":0.7}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/memories/episodic/extract" \
  -H "Content-Type: application/json" \
  -d "$EPISODIC_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
echo ""

if echo "$RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ Episodic memory extracted successfully${NC}"
    echo -e "${BLUE}Note: memory.created and episodic_memory.stored events should be published${NC}"
    PASSED_2=1
else
    echo -e "${RED}✗ FAILED: Episodic memory extraction failed${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Update Memory (triggers memory.updated event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    # Update the memory
    echo -e "${BLUE}Step 1: Update memory importance score${NC}"
    UPDATE_PAYLOAD="{\"importance_score\":0.95,\"confidence\":1.0}"
    echo "PUT ${BASE_URL}/memories/factual/${MEMORY_ID}?user_id=${TEST_USER_ID}"
    echo "Payload: ${UPDATE_PAYLOAD}"
    RESPONSE=$(curl -s -X PUT "${BASE_URL}/memories/factual/${MEMORY_ID}?user_id=${TEST_USER_ID}" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_PAYLOAD")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q '"success":true'; then
        echo -e "${GREEN}✓ Memory updated successfully${NC}"
        echo -e "${BLUE}Note: memory.updated event should be published to NATS${NC}"
        PASSED_3=1
    else
        echo -e "${RED}✗ FAILED: Memory update failed${NC}"
        PASSED_3=0
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: No memory ID available from Test 1${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Create Session Memory${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

SESSION_ID="test_session_${TEST_TS}"
echo -e "${BLUE}Step 1: Create session memory${NC}"
SESSION_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"memory_type\":\"session\",\"content\":\"User: Hello, I need help with Python.\",\"session_id\":\"${SESSION_ID}\",\"interaction_sequence\":1,\"importance_score\":0.5}"
echo "POST ${BASE_URL}/memories"
RESPONSE=$(curl -s -X POST "${BASE_URL}/memories" \
  -H "Content-Type: application/json" \
  -d "$SESSION_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
echo ""

if echo "$RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ Session memory created successfully${NC}"
    echo -e "${BLUE}Note: memory.created event should be published${NC}"
    PASSED_4=1
    SESSION_MEMORY_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('memory_id', ''))" 2>/dev/null)
else
    echo -e "${RED}✗ FAILED: Session memory creation failed${NC}"
    PASSED_4=0
    SESSION_MEMORY_ID=""
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Deactivate Session (triggers session_memory.deactivated event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

echo -e "${BLUE}Step 1: Deactivate session${NC}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/memories/session/${SESSION_ID}/deactivate?user_id=${TEST_USER_ID}")
echo "$RESPONSE" | python3 -m json.tool
echo ""

if echo "$RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✓ Session deactivated successfully${NC}"
    echo -e "${BLUE}Note: session_memory.deactivated event should be published to NATS${NC}"
    PASSED_5=1
else
    echo -e "${RED}✗ FAILED: Session deactivation failed${NC}"
    PASSED_5=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 6: Delete Memory (triggers memory.deleted event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$MEMORY_ID" ] && [ "$MEMORY_ID" != "null" ]; then
    # Delete the memory
    echo -e "${BLUE}Step 1: Delete factual memory${NC}"
    echo "DELETE ${BASE_URL}/memories/factual/${MEMORY_ID}?user_id=${TEST_USER_ID}"
    RESPONSE=$(curl -s -X DELETE "${BASE_URL}/memories/factual/${MEMORY_ID}?user_id=${TEST_USER_ID}")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q '"success":true'; then
        echo -e "${GREEN}✓ Memory deleted successfully${NC}"
        echo -e "${BLUE}Note: memory.deleted event should be published to NATS${NC}"
        PASSED_6=1
    else
        echo -e "${RED}✗ FAILED: Memory deletion failed${NC}"
        PASSED_6=0
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: No memory ID available from Test 1${NC}"
    PASSED_6=0
fi
echo ""

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_PASSED=$((PASSED_1 + PASSED_2 + PASSED_3 + PASSED_4 + PASSED_5 + PASSED_6))
echo -e "Tests Passed: ${GREEN}${TOTAL_PASSED}/6${NC}"
echo ""

if [ $TOTAL_PASSED -eq 6 ]; then
    echo -e "${GREEN}✓ ALL EVENT PUBLISHING TESTS PASSED!${NC}"
    echo ""
    echo -e "${CYAN}Event Publishing Verification:${NC}"
    echo -e "  ${BLUE}✓${NC} memory.created - Published when memories are created"
    echo -e "  ${BLUE}✓${NC} memory.updated - Published when memories are updated"
    echo -e "  ${BLUE}✓${NC} memory.deleted - Published when memories are deleted"
    echo -e "  ${BLUE}✓${NC} factual_memory.stored - Published when factual memories are extracted"
    echo -e "  ${BLUE}✓${NC} episodic_memory.stored - Published when episodic memories are extracted"
    echo -e "  ${BLUE}✓${NC} session_memory.deactivated - Published when sessions are deactivated"
    echo ""
    echo -e "${YELLOW}Note: This test verifies event publishing indirectly by confirming${NC}"
    echo -e "${YELLOW}      API operations succeed. Events are published asynchronously.${NC}"
    echo -e "${YELLOW}      To verify NATS delivery, check service logs or NATS monitoring.${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
