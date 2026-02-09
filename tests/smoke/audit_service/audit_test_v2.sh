#!/bin/bash
# Audit Service Test Script (v2 - using test_common.sh)
# Usage:
#   ./audit_test_v2.sh                    # Direct mode (default)
#   TEST_MODE=gateway ./audit_test_v2.sh  # Gateway mode with JWT

# ============================================================================
# Load Test Framework
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../../tests/test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="audit_service"
API_PATH="/api/v1/audit"

# For audit service, always get JWT token (it requires auth)
TEST_MODE="gateway"

# Initialize test
init_test

# ============================================================================
# Test Data
# ============================================================================
TEST_TS="$(date +%s)_$$"
TEST_AUDIT_USER="test_audit_user_${TEST_TS}"

print_info "Test User ID: $TEST_AUDIT_USER"
echo ""

# ============================================================================
# Tests
# ============================================================================

# Test 1: Get Service Info
print_section "Test 1: Get Service Info"
echo "GET ${API_PATH}/info"
RESPONSE=$(api_get "/info")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "service" || json_has "$RESPONSE" "version"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 2: Get Service Stats
print_section "Test 2: Get Service Stats"
echo "GET ${API_PATH}/stats"
RESPONSE=$(api_get "/stats")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "total_events" || echo "$RESPONSE" | grep -q "events"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 3: Create Audit Event
print_section "Test 3: Create Audit Event"
echo "POST ${API_PATH}/events"

EVENT_PAYLOAD="{
  \"event_type\": \"user_login\",
  \"category\": \"authentication\",
  \"user_id\": \"${TEST_AUDIT_USER}\",
  \"organization_id\": \"org_test_123\",
  \"resource_type\": \"session\",
  \"resource_id\": \"session_${TEST_TS}\",
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
RESPONSE=$(api_post "/events" "$EVENT_PAYLOAD")
echo "$RESPONSE" | json_pretty

EVENT_ID=$(json_get "$RESPONSE" "id")
if [ -z "$EVENT_ID" ]; then
    EVENT_ID=$(json_get "$RESPONSE" "event_id")
fi

if [ -n "$EVENT_ID" ] && [ "$EVENT_ID" != "" ]; then
    print_success "Created event: $EVENT_ID"
    test_result 0
else
    # Check if it was still successful
    if echo "$RESPONSE" | grep -q "event_type\|success"; then
        test_result 0
    else
        test_result 1
    fi
fi
echo ""

# Test 4: Batch Create Audit Events
print_section "Test 4: Batch Create Audit Events"
echo "POST ${API_PATH}/events/batch"

BATCH_PAYLOAD="[
  {
    \"event_type\": \"resource_create\",
    \"category\": \"data_access\",
    \"user_id\": \"${TEST_AUDIT_USER}\",
    \"resource_type\": \"document\",
    \"resource_id\": \"doc_001\",
    \"action\": \"create\",
    \"severity\": \"low\",
    \"success\": true
  },
  {
    \"event_type\": \"resource_update\",
    \"category\": \"data_access\",
    \"user_id\": \"${TEST_AUDIT_USER}\",
    \"resource_type\": \"document\",
    \"resource_id\": \"doc_001\",
    \"action\": \"update\",
    \"severity\": \"low\",
    \"success\": true
  }
]"
RESPONSE=$(api_post "/events/batch" "$BATCH_PAYLOAD")
echo "$RESPONSE" | json_pretty

if echo "$RESPONSE" | grep -q "created\|success\|count"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 5: Query Audit Events
print_section "Test 5: Query Audit Events"
echo "POST ${API_PATH}/events/query"

# Get dates (macOS compatible)
START_TIME=$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

QUERY_PAYLOAD="{
  \"user_id\": \"${TEST_AUDIT_USER}\",
  \"start_time\": \"${START_TIME}\",
  \"end_time\": \"${END_TIME}\",
  \"limit\": 50
}"
RESPONSE=$(api_post "/events/query" "$QUERY_PAYLOAD")
echo "$RESPONSE" | json_pretty | head -30

if json_has "$RESPONSE" "events" || json_has "$RESPONSE" "total_count"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 6: List Audit Events
print_section "Test 6: List Audit Events"
echo "GET ${API_PATH}/events?limit=10"
RESPONSE=$(api_get "/events?limit=10")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q "\[" || json_has "$RESPONSE" "events"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 7: Get User Activities
print_section "Test 7: Get User Activities"
echo "GET ${API_PATH}/users/${TEST_AUDIT_USER}/activities?limit=10"
RESPONSE=$(api_get "/users/${TEST_AUDIT_USER}/activities?limit=10")
echo "$RESPONSE" | json_pretty | head -30

if echo "$RESPONSE" | grep -q "\["; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 8: Get User Activity Summary
print_section "Test 8: Get User Activity Summary"
echo "GET ${API_PATH}/users/${TEST_AUDIT_USER}/summary"
RESPONSE=$(api_get "/users/${TEST_AUDIT_USER}/summary")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "total_events" || json_has "$RESPONSE" "user_id"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 9: Create Security Alert
print_section "Test 9: Create Security Alert"
echo "POST ${API_PATH}/security/alerts"

ALERT_PAYLOAD="{
  \"threat_type\": \"suspicious_login\",
  \"severity\": \"high\",
  \"source_ip\": \"192.168.1.99\",
  \"target_resource\": \"auth_service\",
  \"description\": \"Multiple failed login attempts detected\",
  \"metadata\": {
    \"user_id\": \"${TEST_AUDIT_USER}\",
    \"failed_attempts\": 5,
    \"time_window\": \"5 minutes\"
  }
}"
RESPONSE=$(api_post "/security/alerts" "$ALERT_PAYLOAD")
echo "$RESPONSE" | json_pretty

if json_has "$RESPONSE" "alert_id" || echo "$RESPONSE" | grep -q "created\|success"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 10: List Security Events
print_section "Test 10: List Security Events"
echo "GET ${API_PATH}/security/events?limit=10"
RESPONSE=$(api_get "/security/events?limit=10")
echo "$RESPONSE" | json_pretty | head -20

if echo "$RESPONSE" | grep -q "\["; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 11: Get Compliance Standards
print_section "Test 11: Get Compliance Standards"
echo "GET ${API_PATH}/compliance/standards"
RESPONSE=$(api_get "/compliance/standards")
echo "$RESPONSE" | json_pretty | head -20

if echo "$RESPONSE" | grep -q "\[" || json_has "$RESPONSE" "standards"; then
    test_result 0
else
    test_result 1
fi
echo ""

# Test 12: Generate Compliance Report
print_section "Test 12: Generate Compliance Report"
echo "POST ${API_PATH}/compliance/reports"

PERIOD_START=$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)

REPORT_PAYLOAD="{
  \"report_type\": \"audit_summary\",
  \"compliance_standard\": \"GDPR\",
  \"period_start\": \"${PERIOD_START}\",
  \"period_end\": \"${END_TIME}\",
  \"include_details\": true,
  \"filters\": {
    \"organization_id\": \"org_test_123\"
  }
}"
RESPONSE=$(api_post "/compliance/reports" "$REPORT_PAYLOAD")
echo "$RESPONSE" | json_pretty | head -30

if json_has "$RESPONSE" "report_id" || echo "$RESPONSE" | grep -q "report\|generated"; then
    test_result 0
else
    test_result 1
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
