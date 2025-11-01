#!/bin/bash

# Audit Service Testing Script
# Tests audit event logging, querying, security alerts, and compliance reporting

BASE_URL="http://localhost:8205"
API_BASE="${BASE_URL}/api/v1/audit"
AUTH_URL="http://localhost:8201/api/v1/auth"

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
EVENT_ID=""
TEST_USER_ID="test_audit_user_$(date +%s)"

echo "======================================================================"
echo "Audit Service Tests"
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

# Test 0: Generate Test Token from Auth Service
print_section "Test 0: Generate Test Token from Auth Service"
echo "POST ${AUTH_URL}/dev-token"
TOKEN_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"email\": \"${TEST_USER_ID}@example.com\",
  \"role\": \"admin\",
  \"expires_in\": 3600
}"

TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_URL}/dev-token" \
  -H "Content-Type: application/json" \
  -d "$TOKEN_PAYLOAD")
HTTP_CODE=$(echo "$TOKEN_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    JWT_TOKEN=$(echo "$RESPONSE_BODY" | jq -r '.token' 2>/dev/null)
    if [ -n "$JWT_TOKEN" ] && [ "$JWT_TOKEN" != "null" ]; then
        print_result 0 "Test token generated successfully"
        echo -e "${YELLOW}Token (first 50 chars): ${JWT_TOKEN:0:50}...${NC}"
    else
        print_result 1 "Token generation failed - no token in response"
        exit 1
    fi
else
    print_result 1 "Failed to generate test token"
    exit 1
fi

# Test 1: Health Check
print_section "Test 1: Health Check"
echo "GET ${BASE_URL}/health"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Health check successful"
else
    print_result 1 "Health check failed"
fi

# Test 2: Detailed Health Check
print_section "Test 2: Detailed Health Check"
echo "GET ${BASE_URL}/health/detailed"
DETAILED_HEALTH=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health/detailed")
HTTP_CODE=$(echo "$DETAILED_HEALTH" | tail -n1)
RESPONSE_BODY=$(echo "$DETAILED_HEALTH" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Detailed health check successful"
else
    print_result 1 "Detailed health check failed"
fi

# Test 3: Get Service Info
print_section "Test 3: Get Service Info"
echo "GET ${API_BASE}/info"
INFO_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/info")
HTTP_CODE=$(echo "$INFO_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$INFO_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Service info retrieved successfully"
else
    print_result 1 "Failed to get service info"
fi

# Test 4: Get Service Stats
print_section "Test 4: Get Service Stats"
echo "GET ${API_BASE}/stats"
STATS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/stats")
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Service stats retrieved successfully"
else
    print_result 1 "Failed to get service stats"
fi

# Test 5: Create Audit Event
print_section "Test 5: Create Audit Event"
echo "POST ${API_BASE}/events"
EVENT_PAYLOAD="{
  \"event_type\": \"user_login\",
  \"category\": \"authentication\",
  \"user_id\": \"${TEST_USER_ID}\",
  \"organization_id\": \"org_test_123\",
  \"resource_type\": \"session\",
  \"resource_id\": \"session_123\",
  \"action\": \"login\",
  \"severity\": \"low\",
  \"success\": true,
  \"ip_address\": \"192.168.1.100\",
  \"user_agent\": \"Mozilla/5.0 Test Browser\",
  \"metadata\": {
    \"login_method\": \"password\",
    \"location\": \"Beijing\"
  }
}"
echo "Request Body:"
echo "$EVENT_PAYLOAD" | jq '.'

CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/events" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$EVENT_PAYLOAD")
HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    EVENT_ID=$(echo "$RESPONSE_BODY" | jq -r '.id // .event_id' 2>/dev/null)
    if [ -n "$EVENT_ID" ] && [ "$EVENT_ID" != "null" ]; then
        print_result 0 "Audit event created successfully"
        echo -e "${YELLOW}Event ID: ${EVENT_ID}${NC}"
    else
        print_result 0 "Audit event created (no ID returned)"
    fi
else
    print_result 1 "Failed to create audit event"
fi

# Test 6: Batch Create Audit Events
print_section "Test 6: Batch Create Audit Events"
echo "POST ${API_BASE}/events/batch"
# Note: Batch endpoint expects a list directly, not wrapped in an object
BATCH_PAYLOAD="[
  {
    \"event_type\": \"resource_create\",
    \"category\": \"data_access\",
    \"user_id\": \"${TEST_USER_ID}\",
    \"resource_type\": \"document\",
    \"resource_id\": \"doc_001\",
    \"action\": \"create\",
    \"severity\": \"low\",
    \"success\": true
  },
  {
    \"event_type\": \"resource_update\",
    \"category\": \"data_access\",
    \"user_id\": \"${TEST_USER_ID}\",
    \"resource_type\": \"document\",
    \"resource_id\": \"doc_001\",
    \"action\": \"update\",
    \"severity\": \"low\",
    \"success\": true
  }
]"

BATCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/events/batch" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$BATCH_PAYLOAD")
HTTP_CODE=$(echo "$BATCH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$BATCH_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Batch audit events created successfully"
else
    print_result 1 "Failed to create batch audit events"
fi

# Test 7: Query Audit Events
print_section "Test 7: Query Audit Events"
echo "POST ${API_BASE}/events/query"
QUERY_PAYLOAD="{
  \"user_id\": \"${TEST_USER_ID}\",
  \"start_time\": \"$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)\",
  \"end_time\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
  \"limit\": 50
}"
echo "Request Body:"
echo "$QUERY_PAYLOAD" | jq '.'

QUERY_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/events/query" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$QUERY_PAYLOAD")
HTTP_CODE=$(echo "$QUERY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$QUERY_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    EVENT_COUNT=$(echo "$RESPONSE_BODY" | jq -r '.total_count // .count' 2>/dev/null || echo "0")
    print_result 0 "Audit events queried successfully (count: $EVENT_COUNT)"
else
    print_result 1 "Failed to query audit events"
fi

# Test 8: List Audit Events (Simple)
print_section "Test 8: List Audit Events"
echo "GET ${API_BASE}/events?limit=10"

LIST_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/events?limit=10" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$LIST_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Audit events list retrieved successfully"
else
    print_result 1 "Failed to list audit events"
fi

# Test 9: Get User Activities
print_section "Test 9: Get User Activities"
echo "GET ${API_BASE}/users/${TEST_USER_ID}/activities?limit=10"

ACTIVITIES_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/users/${TEST_USER_ID}/activities?limit=10" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$ACTIVITIES_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$ACTIVITIES_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    ACTIVITY_COUNT=$(echo "$RESPONSE_BODY" | jq -r 'length' 2>/dev/null || echo "0")
    print_result 0 "User activities retrieved successfully (count: $ACTIVITY_COUNT)"
else
    print_result 1 "Failed to get user activities"
fi

# Test 10: Get User Activity Summary
print_section "Test 10: Get User Activity Summary"
echo "GET ${API_BASE}/users/${TEST_USER_ID}/summary"

SUMMARY_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/users/${TEST_USER_ID}/summary" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$SUMMARY_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SUMMARY_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL_EVENTS=$(echo "$RESPONSE_BODY" | jq -r '.total_events' 2>/dev/null || echo "0")
    print_result 0 "User activity summary retrieved successfully (events: $TOTAL_EVENTS)"
else
    print_result 1 "Failed to get user activity summary"
fi

# Test 11: Create Security Alert
print_section "Test 11: Create Security Alert"
echo "POST ${API_BASE}/security/alerts"
ALERT_PAYLOAD="{
  \"threat_type\": \"suspicious_login\",
  \"severity\": \"high\",
  \"source_ip\": \"192.168.1.99\",
  \"target_resource\": \"auth_service\",
  \"description\": \"Multiple failed login attempts detected\",
  \"metadata\": {
    \"user_id\": \"${TEST_USER_ID}\",
    \"failed_attempts\": 5,
    \"time_window\": \"5 minutes\"
  }
}"
echo "Request Body:"
echo "$ALERT_PAYLOAD" | jq '.'

ALERT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/security/alerts" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$ALERT_PAYLOAD")
HTTP_CODE=$(echo "$ALERT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$ALERT_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Security alert created successfully"
else
    print_result 1 "Failed to create security alert"
fi

# Test 12: List Security Events
print_section "Test 12: List Security Events"
echo "GET ${API_BASE}/security/events?limit=10"

SECURITY_EVENTS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/security/events?limit=10" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$SECURITY_EVENTS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SECURITY_EVENTS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    SECURITY_COUNT=$(echo "$RESPONSE_BODY" | jq -r 'length' 2>/dev/null || echo "0")
    print_result 0 "Security events retrieved successfully (count: $SECURITY_COUNT)"
else
    print_result 1 "Failed to get security events"
fi

# Test 13: Get Compliance Standards
print_section "Test 13: Get Compliance Standards"
echo "GET ${API_BASE}/compliance/standards"

STANDARDS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/compliance/standards" \
  -H "Authorization: Bearer ${JWT_TOKEN}")
HTTP_CODE=$(echo "$STANDARDS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STANDARDS_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    STANDARDS_COUNT=$(echo "$RESPONSE_BODY" | jq -r 'length' 2>/dev/null || echo "0")
    print_result 0 "Compliance standards retrieved successfully (count: $STANDARDS_COUNT)"
else
    print_result 1 "Failed to get compliance standards"
fi

# Test 14: Generate Compliance Report
print_section "Test 14: Generate Compliance Report"
echo "POST ${API_BASE}/compliance/reports"
REPORT_PAYLOAD="{
  \"report_type\": \"audit_summary\",
  \"compliance_standard\": \"GDPR\",
  \"period_start\": \"$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)\",
  \"period_end\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
  \"include_details\": true,
  \"filters\": {
    \"organization_id\": \"org_test_123\"
  }
}"
echo "Request Body:"
echo "$REPORT_PAYLOAD" | jq '.'

REPORT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/compliance/reports" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$REPORT_PAYLOAD")
HTTP_CODE=$(echo "$REPORT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$REPORT_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Compliance report generated successfully"
else
    print_result 1 "Failed to generate compliance report"
fi

# Test 15: Maintenance Cleanup
print_section "Test 15: Maintenance Cleanup (Old Events)"
echo "POST ${API_BASE}/maintenance/cleanup"
CLEANUP_PAYLOAD="{
  \"retention_days\": 365,
  \"dry_run\": true
}"
echo "Request Body:"
echo "$CLEANUP_PAYLOAD" | jq '.'

CLEANUP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/maintenance/cleanup" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -d "$CLEANUP_PAYLOAD")
HTTP_CODE=$(echo "$CLEANUP_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CLEANUP_RESPONSE" | sed '$d')

echo "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Maintenance cleanup executed successfully"
else
    print_result 1 "Failed to execute maintenance cleanup"
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

