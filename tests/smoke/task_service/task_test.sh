#!/bin/bash

# Task Service Testing Script
# Tests task CRUD operations, execution, templates, and analytics

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1"
AUTH_BASE="http://localhost/api/v1/auth"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Variables
JWT_TOKEN=""
TASK_ID=""
TEMPLATE_ID=""
EXECUTION_ID=""

# Generate a unique test ID
TEST_ID="test_$(date +%s)"
TEST_USER_ID="test_user_task_${TEST_ID}"

echo "======================================================================"
echo "Task Service Tests"
echo "======================================================================"
echo ""

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Function to print section header
print_section() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

# Test 0: Generate Token from Auth Service
print_section "Test 0: Generate Test Token from Auth Service"
echo "POST ${AUTH_BASE}/dev-token"
TOKEN_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"email\": \"${TEST_USER_ID}@example.com\",
  \"subscription_level\": \"basic\",
  \"expires_in\": 3600
}"

TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_BASE}/dev-token" \
  -H "Content-Type: application/json" \
  -d "$TOKEN_PAYLOAD")
HTTP_CODE=$(echo "$TOKEN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    JWT_TOKEN=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('token', ''))")
    if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
        print_result 0 "Test token generated successfully"
        echo -e "${YELLOW}Token: ${JWT_TOKEN:0:50}...${NC}"
    else
        print_result 1 "Token generation failed - no token in response"
        exit 1
    fi
else
    print_result 1 "Failed to generate test token"
    exit 1
fi

# Pretty print JSON helper
pretty_json() {
    local json="$1"
    if command -v jq &> /dev/null; then
        echo "$json" | jq '.'
    else
        echo "$json" | python3 -m json.tool 2>/dev/null || echo "$json"
    fi
}

# Test 1: Create Task
print_section "Test 1: Create Task"
echo "POST ${API_BASE}/tasks"
CREATE_TASK_PAYLOAD="{
  \"name\": \"Test Task - Daily Weather\",
  \"description\": \"Automated daily weather report\",
  \"task_type\": \"daily_weather\",
  \"priority\": \"high\",
  \"config\": {
    \"location\": \"San Francisco\",
    \"units\": \"celsius\",
    \"include_forecast\": true
  },
  \"schedule\": {
    \"type\": \"cron\",
    \"cron_expression\": \"0 8 * * *\",
    \"timezone\": \"America/Los_Angeles\"
  },
  \"credits_per_run\": 1.5,
  \"tags\": [\"weather\", \"daily\", \"automated\"],
  \"metadata\": {
    \"category\": \"automation\",
    \"source\": \"test_script\"
  },
  \"due_date\": \"2025-12-31T23:59:59Z\"
}"

echo "Request Body:"
pretty_json "$CREATE_TASK_PAYLOAD"

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/tasks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$CREATE_TASK_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TASK_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('task_id', ''))")
    if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
        print_result 0 "Task created successfully"
        echo -e "${YELLOW}Task ID: $TASK_ID${NC}"
    else
        print_result 1 "Task creation returned 200 but no task_id"
    fi
else
    print_result 1 "Failed to create task"
fi

# Test 2: Get Task Details
if [ -n "$TASK_ID" ]; then
    print_section "Test 2: Get Task Details"
    echo "GET ${API_BASE}/tasks/${TASK_ID}"

    GET_TASK_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/tasks/${TASK_ID}" \
      -H "Authorization: Bearer ${JWT_TOKEN}")
    HTTP_CODE=$(echo "$GET_TASK_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_TASK_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_TASK_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('task_id', ''))")
        if [ "$RETRIEVED_TASK_ID" = "$TASK_ID" ]; then
            print_result 0 "Task details retrieved successfully"
        else
            print_result 1 "Retrieved task ID doesn't match"
        fi
    else
        print_result 1 "Failed to get task details"
    fi
else
    echo -e "${YELLOW}Skipping Test 2: No task ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 3: Update Task
if [ -n "$TASK_ID" ]; then
    print_section "Test 3: Update Task"
    echo "PUT ${API_BASE}/tasks/${TASK_ID}"
    UPDATE_TASK_PAYLOAD="{
      \"name\": \"Updated Test Task - Daily Weather\",
      \"priority\": \"urgent\",
      \"status\": \"scheduled\",
      \"config\": {
        \"location\": \"New York\",
        \"units\": \"fahrenheit\",
        \"include_forecast\": true,
        \"include_alerts\": true
      }
    }"

    echo "Request Body:"
    pretty_json "$UPDATE_TASK_PAYLOAD"

    UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/tasks/${TASK_ID}" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$UPDATE_TASK_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        UPDATED_NAME=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('name', ''))")
        if [[ "$UPDATED_NAME" == *"Updated"* ]]; then
            print_result 0 "Task updated successfully"
        else
            print_result 1 "Task update didn't apply changes"
        fi
    else
        print_result 1 "Failed to update task"
    fi
else
    echo -e "${YELLOW}Skipping Test 3: No task ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 4: List Tasks
print_section "Test 4: List User Tasks"
echo "GET ${API_BASE}/tasks?limit=10&offset=0"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/tasks?limit=10&offset=0" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TASK_COUNT=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('count', 0))")
    print_result 0 "Tasks list retrieved successfully (count: $TASK_COUNT)"
else
    print_result 1 "Failed to list tasks"
fi

# Test 5: List Tasks with Filters
print_section "Test 5: List Tasks with Filters (status=scheduled)"
echo "GET ${API_BASE}/tasks?status=scheduled&limit=10"

FILTERED_LIST=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/tasks?status=scheduled&limit=10" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$FILTERED_LIST" | tail -n1)
RESPONSE_BODY=$(echo "$FILTERED_LIST" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Filtered tasks list retrieved successfully"
else
    print_result 1 "Failed to get filtered tasks"
fi

# Test 6: Execute Task Manually
if [ -n "$TASK_ID" ]; then
    print_section "Test 6: Execute Task Manually"
    echo "POST ${API_BASE}/tasks/${TASK_ID}/execute"
    EXECUTE_PAYLOAD="{
      \"trigger_type\": \"manual\",
      \"trigger_data\": {
        \"initiated_by\": \"test_script\",
        \"reason\": \"testing\"
      }
    }"

    echo "Request Body:"
    pretty_json "$EXECUTE_PAYLOAD"

    EXECUTE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/tasks/${TASK_ID}/execute" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${JWT_TOKEN}" \
      -d "$EXECUTE_PAYLOAD")
    HTTP_CODE=$(echo "$EXECUTE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$EXECUTE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        EXECUTION_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('execution_id', ''))")
        if [ -n "$EXECUTION_ID" ] && [ "$EXECUTION_ID" != "null" ]; then
            print_result 0 "Task executed successfully"
            echo -e "${YELLOW}Execution ID: $EXECUTION_ID${NC}"
        else
            print_result 1 "Task execution returned 200 but no execution_id"
        fi
    else
        print_result 1 "Failed to execute task"
    fi
else
    echo -e "${YELLOW}Skipping Test 6: No task ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Get Task Execution History
if [ -n "$TASK_ID" ]; then
    print_section "Test 7: Get Task Execution History"
    echo "GET ${API_BASE}/tasks/${TASK_ID}/executions?limit=10"

    EXECUTIONS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/tasks/${TASK_ID}/executions?limit=10" \
      -H "Authorization: Bearer ${JWT_TOKEN}")
    HTTP_CODE=$(echo "$EXECUTIONS_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$EXECUTIONS_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Task execution history retrieved successfully"
    else
        print_result 1 "Failed to get task execution history"
    fi
else
    echo -e "${YELLOW}Skipping Test 7: No task ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 8: Get Task Analytics
print_section "Test 8: Get Task Analytics"
echo "GET ${API_BASE}/analytics?days=30"

ANALYTICS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/analytics?days=30" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$ANALYTICS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$ANALYTICS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_TASKS=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total_tasks', 0))")
    print_result 0 "Task analytics retrieved successfully (total_tasks: $TOTAL_TASKS)"
elif [ "$HTTP_CODE" = "404" ]; then
    print_result 0 "Task analytics not available yet (expected for new user)"
else
    print_result 1 "Failed to get task analytics"
fi

# Test 9: Create TODO Task
print_section "Test 9: Create TODO Task"
echo "POST ${API_BASE}/tasks"
TODO_PAYLOAD="{
  \"name\": \"Buy groceries\",
  \"description\": \"Milk, eggs, bread, and vegetables\",
  \"task_type\": \"todo\",
  \"priority\": \"medium\",
  \"config\": {},
  \"tags\": [\"shopping\", \"personal\"],
  \"due_date\": \"2025-10-20T18:00:00Z\"
}"

echo "Request Body:"
pretty_json "$TODO_PAYLOAD"

TODO_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/tasks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$TODO_PAYLOAD")
HTTP_CODE=$(echo "$TODO_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TODO_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TODO_TASK_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('task_id', ''))")
    if [ -n "$TODO_TASK_ID" ] && [ "$TODO_TASK_ID" != "null" ]; then
        print_result 0 "TODO task created successfully"
        echo -e "${YELLOW}TODO Task ID: $TODO_TASK_ID${NC}"
    else
        print_result 1 "TODO task creation returned 200 but no task_id"
    fi
else
    print_result 1 "Failed to create TODO task"
fi

# Test 10: Create Reminder Task
print_section "Test 10: Create Reminder Task"
echo "POST ${API_BASE}/tasks"
REMINDER_PAYLOAD="{
  \"name\": \"Doctor Appointment\",
  \"description\": \"Annual checkup at Dr. Smith's office\",
  \"task_type\": \"reminder\",
  \"priority\": \"high\",
  \"config\": {
    \"reminder_message\": \"Don't forget your doctor appointment at 10 AM!\",
    \"notification_methods\": [\"push\", \"email\"],
    \"repeat\": false
  },
  \"tags\": [\"health\", \"appointment\"],
  \"due_date\": \"2025-10-25T10:00:00Z\",
  \"reminder_time\": \"2025-10-25T09:00:00Z\"
}"

echo "Request Body:"
pretty_json "$REMINDER_PAYLOAD"

REMINDER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/tasks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$REMINDER_PAYLOAD")
HTTP_CODE=$(echo "$REMINDER_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REMINDER_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    REMINDER_TASK_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('task_id', ''))")
    if [ -n "$REMINDER_TASK_ID" ] && [ "$REMINDER_TASK_ID" != "null" ]; then
        print_result 0 "Reminder task created successfully"
        echo -e "${YELLOW}Reminder Task ID: $REMINDER_TASK_ID${NC}"
    else
        print_result 1 "Reminder task creation returned 200 but no task_id"
    fi
else
    print_result 1 "Failed to create reminder task"
fi

# Test 11: Delete Task
if [ -n "$TASK_ID" ]; then
    print_section "Test 11: Delete Task"
    echo "DELETE ${API_BASE}/tasks/${TASK_ID}"

    DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/tasks/${TASK_ID}" \
      -H "Authorization: Bearer ${JWT_TOKEN}")
    HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$DELETE_RESPONSE" | sed '$d')

    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Task deleted successfully"
    else
        print_result 1 "Failed to delete task"
    fi
else
    echo -e "${YELLOW}Skipping Test 11: No task ID available${NC}"
    ((TESTS_FAILED++))
fi

# Summary
echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Total: $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
