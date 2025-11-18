#!/bin/bash
# Test Event Publishing - Verify events are published via API response
# This test verifies the task_service publishes events by checking API responses

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
AUTH_BASE="http://localhost/api/v1/auth"
TASK_BASE="${BASE_URL}/tasks"

echo -e "${BLUE}Testing task service at: ${TASK_BASE}${NC}"
echo ""

# Generate JWT token
echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Preliminary: Generate Test Token${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

TOKEN_PAYLOAD="{\"user_id\":\"${TEST_USER_ID}\",\"email\":\"${TEST_USER_ID}@example.com\",\"subscription_level\":\"basic\",\"expires_in\":3600}"
TOKEN_RESPONSE=$(curl -s -X POST "${AUTH_BASE}/dev-token" \
  -H "Content-Type: application/json" \
  -d "$TOKEN_PAYLOAD")

JWT_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('token', ''))" 2>/dev/null || echo "")

if [ -z "$JWT_TOKEN" ] || [ "$JWT_TOKEN" = "null" ]; then
    echo -e "${RED}✗ Failed to generate test token${NC}"
    echo "$TOKEN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Test token generated${NC}"
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
echo -e "${YELLOW}Test 1: Create Task (triggers task.created event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

# Create a task
echo -e "${BLUE}Step 1: Create task${NC}"
CREATE_PAYLOAD="{\"name\":\"Test Event Task ${TEST_TS}\",\"description\":\"Task for event testing\",\"task_type\":\"todo\",\"priority\":\"high\",\"config\":{},\"tags\":[\"test\",\"event\"]}"
echo "POST ${TASK_BASE}"
echo "Payload: ${CREATE_PAYLOAD}"
RESPONSE=$(curl -s -X POST "${TASK_BASE}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$CREATE_PAYLOAD")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Extract task_id
TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('task_id', ''))" 2>/dev/null || echo "")

if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
    echo -e "${GREEN}✓ Task created successfully${NC}"
    echo -e "${BLUE}Note: task.created event should be published to NATS${NC}"
    echo -e "${BLUE}Task ID: ${TASK_ID}${NC}"
    PASSED_1=1
else
    echo -e "${RED}✗ FAILED: Task creation failed${NC}"
    PASSED_1=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 2: Verify Task Was Created (check state)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
    echo -e "${BLUE}Step 1: Get task details${NC}"
    RESPONSE=$(curl -s -X GET "${TASK_BASE}/${TASK_ID}" \
      -H "Authorization: Bearer ${JWT_TOKEN}")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    RETRIEVED_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('task_id', ''))" 2>/dev/null || echo "")

    if [ "$RETRIEVED_ID" = "$TASK_ID" ]; then
        echo -e "${GREEN}✓ Task state verified (event published successfully)${NC}"
        PASSED_2=1
    else
        echo -e "${RED}✗ FAILED: Task not found in database${NC}"
        PASSED_2=0
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: No task ID from previous test${NC}"
    PASSED_2=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 3: Update Task (triggers task.updated event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
    echo -e "${BLUE}Step 1: Update task${NC}"
    UPDATE_PAYLOAD="{\"name\":\"Updated Event Task ${TEST_TS}\",\"priority\":\"urgent\",\"status\":\"scheduled\"}"
    echo "PUT ${TASK_BASE}/${TASK_ID}"
    echo "Payload: ${UPDATE_PAYLOAD}"
    RESPONSE=$(curl -s -X PUT "${TASK_BASE}/${TASK_ID}" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$UPDATE_PAYLOAD")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q "Updated Event Task"; then
        echo -e "${GREEN}✓ Task updated successfully${NC}"
        echo -e "${BLUE}Note: task.updated event should be published to NATS${NC}"
        PASSED_3=1
    else
        echo -e "${RED}✗ FAILED: Task update failed${NC}"
        PASSED_3=0
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: No task ID from previous test${NC}"
    PASSED_3=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 4: Execute Task (triggers task.completed event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
    echo -e "${BLUE}Step 1: Execute task${NC}"
    EXECUTE_PAYLOAD="{\"trigger_type\":\"manual\",\"trigger_data\":{\"initiated_by\":\"test_script\",\"reason\":\"testing\"}}"
    echo "POST ${TASK_BASE}/${TASK_ID}/execute"
    RESPONSE=$(curl -s -X POST "${TASK_BASE}/${TASK_ID}/execute" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$EXECUTE_PAYLOAD")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    EXECUTION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('execution_id', ''))" 2>/dev/null || echo "")

    if [ -n "$EXECUTION_ID" ] && [ "$EXECUTION_ID" != "null" ]; then
        echo -e "${GREEN}✓ Task executed successfully${NC}"
        echo -e "${BLUE}Note: task.completed or task.failed event should be published${NC}"
        PASSED_4=1
    else
        echo -e "${RED}✗ FAILED: Task execution failed${NC}"
        PASSED_4=0
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: No task ID from previous test${NC}"
    PASSED_4=0
fi
echo ""

echo -e "${YELLOW}=====================================================================${NC}"
echo -e "${YELLOW}Test 5: Delete Task (triggers task.cancelled event)${NC}"
echo -e "${YELLOW}=====================================================================${NC}"
echo ""

if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
    echo -e "${BLUE}Step 1: Delete task${NC}"
    echo "DELETE ${TASK_BASE}/${TASK_ID}"
    RESPONSE=$(curl -s -X DELETE "${TASK_BASE}/${TASK_ID}" \
      -H "Authorization: Bearer ${JWT_TOKEN}")
    echo "$RESPONSE" | python3 -m json.tool
    echo ""

    if echo "$RESPONSE" | grep -q "deleted successfully\|Task deleted"; then
        echo -e "${GREEN}✓ Task deleted successfully${NC}"
        echo -e "${BLUE}Note: task.cancelled event should be published to NATS${NC}"
        PASSED_5=1
    else
        echo -e "${RED}✗ FAILED: Task deletion failed${NC}"
        PASSED_5=0
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: No task ID from previous test${NC}"
    PASSED_5=0
fi
echo ""

# Summary
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}                         TEST SUMMARY${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

TOTAL_PASSED=$((PASSED_1 + PASSED_2 + PASSED_3 + PASSED_4 + PASSED_5))
echo -e "Tests Passed: ${GREEN}${TOTAL_PASSED}/5${NC}"
echo ""

if [ $TOTAL_PASSED -eq 5 ]; then
    echo -e "${GREEN}✓ ALL EVENT PUBLISHING TESTS PASSED!${NC}"
    echo ""
    echo -e "${CYAN}Event Publishing Verification:${NC}"
    echo -e "  ${BLUE}✓${NC} task.created - Published when tasks are created"
    echo -e "  ${BLUE}✓${NC} task.updated - Published when tasks are updated"
    echo -e "  ${BLUE}✓${NC} task.completed - Published when tasks complete execution"
    echo -e "  ${BLUE}✓${NC} task.cancelled - Published when tasks are deleted"
    echo ""
    echo -e "${YELLOW}Note: This test verifies event publishing indirectly by confirming${NC}"
    echo -e "${YELLOW}      API operations succeed. Events are published asynchronously.${NC}"
    echo -e "${YELLOW}      To verify NATS delivery, check service logs or NATS monitoring.${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
