#!/bin/bash

# Telemetry Service Test Script
# Tests data ingestion, queries, metrics, alerts, aggregation, and exports

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE="http://localhost:8225"
AUTH_SERVICE_BASE="http://localhost:8201"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Variables to store test data
TEST_TOKEN=""
TEST_DEVICE_ID="test_device_telemetry_$(date +%s)"
METRIC_NAME="temperature"
ALERT_RULE_ID=""
SUBSCRIPTION_ID=""

# Helper function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

# Helper function to increment test counter
increment_test() {
    ((TOTAL_TESTS++))
}

# Helper function to mark test as passed
pass_test() {
    ((TESTS_PASSED++))
    echo -e "${GREEN}✓ PASSED${NC}: $1"
}

# Helper function to mark test as failed
fail_test() {
    ((TESTS_FAILED++))
    echo -e "${RED}✗ FAILED${NC}: $1"
}

# Start tests
echo "======================================================================"
echo "Telemetry Service Test Suite"
echo "======================================================================"
echo ""

# ======================
# Test 0: Generate Test Token
# ======================
print_section "Test 0: Generate Test Token from Auth Service"
increment_test

echo "POST ${AUTH_SERVICE_BASE}/api/v1/auth/dev-token"
TOKEN_RESPONSE=$(curl -s -X POST "${AUTH_SERVICE_BASE}/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_telemetry_user_123",
    "email": "telemetry_test@example.com",
    "organization_id": "org_test_telemetry",
    "role": "admin",
    "expires_in": 3600
  }')

echo "Response:"
echo "$TOKEN_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${AUTH_SERVICE_BASE}/api/v1/auth/dev-token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_telemetry_user_123", "email": "telemetry_test@example.com", "role": "admin"}')

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    TEST_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.token')
    echo -e "${YELLOW}Token (first 50 chars): ${TEST_TOKEN:0:50}...${NC}"
    echo -e "${YELLOW}Test Device ID: ${TEST_DEVICE_ID}${NC}"
    pass_test "Test token generated successfully"
else
    fail_test "Failed to generate test token"
    echo "Cannot proceed without authentication token"
    exit 1
fi

# ======================
# Test 1: Health Check
# ======================
print_section "Test 1: Health Check"
increment_test

echo "GET ${API_BASE}/health"
HEALTH_RESPONSE=$(curl -s "${API_BASE}/health")
echo "Response:"
echo "$HEALTH_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/health")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Health check successful"
else
    fail_test "Health check failed"
fi

# ======================
# Test 2: Detailed Health Check
# ======================
print_section "Test 2: Detailed Health Check"
increment_test

echo "GET ${API_BASE}/health/detailed"
DETAILED_HEALTH_RESPONSE=$(curl -s "${API_BASE}/health/detailed")
echo "Response:"
echo "$DETAILED_HEALTH_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/health/detailed")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Detailed health check successful"
else
    fail_test "Detailed health check failed"
fi

# ======================
# Test 3: Get Service Stats
# ======================
print_section "Test 3: Get Service Statistics"
increment_test

echo "GET ${API_BASE}/api/v1/service/stats"
SERVICE_STATS_RESPONSE=$(curl -s "${API_BASE}/api/v1/service/stats")
echo "Response:"
echo "$SERVICE_STATS_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/service/stats")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Service statistics retrieved successfully"
else
    fail_test "Failed to get service statistics"
fi

# ======================
# Test 4: Create Metric Definition
# ======================
print_section "Test 4: Create Metric Definition"
increment_test

echo "POST ${API_BASE}/api/v1/metrics"
METRIC_REQUEST='{
  "name": "temperature",
  "description": "Temperature sensor reading",
  "data_type": "numeric",
  "metric_type": "gauge",
  "unit": "celsius",
  "min_value": -40,
  "max_value": 85,
  "retention_days": 90,
  "aggregation_interval": 60
}'

METRIC_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/metrics" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$METRIC_REQUEST")

echo "Response:"
echo "$METRIC_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/metrics" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$METRIC_REQUEST")

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    pass_test "Metric definition created successfully"
else
    fail_test "Failed to create metric definition"
fi

# ======================
# Test 5: List Metrics
# ======================
print_section "Test 5: List Metric Definitions"
increment_test

echo "GET ${API_BASE}/api/v1/metrics"
METRICS_LIST_RESPONSE=$(curl -s "${API_BASE}/api/v1/metrics" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$METRICS_LIST_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/metrics" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Metrics list retrieved successfully"
else
    fail_test "Failed to get metrics list"
fi

# ======================
# Test 6: Get Metric Definition
# ======================
print_section "Test 6: Get Metric Definition"
increment_test

echo "GET ${API_BASE}/api/v1/metrics/${METRIC_NAME}"
METRIC_DETAILS_RESPONSE=$(curl -s "${API_BASE}/api/v1/metrics/${METRIC_NAME}" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$METRIC_DETAILS_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/metrics/${METRIC_NAME}" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Metric definition retrieved successfully"
else
    fail_test "Failed to get metric definition"
fi

# ======================
# Test 7: Ingest Single Data Point
# ======================
print_section "Test 7: Ingest Single Data Point"
increment_test

echo "POST ${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/telemetry"
DATA_POINT='{
  "metric_name": "temperature",
  "value": 25.5,
  "unit": "celsius",
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
  "tags": {
    "location": "room1",
    "sensor_type": "dht22"
  },
  "quality": 100
}'

INGEST_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/telemetry" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$DATA_POINT")

echo "Response:"
echo "$INGEST_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/telemetry" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$DATA_POINT")

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    pass_test "Single data point ingested successfully"
else
    fail_test "Failed to ingest single data point"
fi

# ======================
# Test 8: Ingest Batch Data Points
# ======================
print_section "Test 8: Ingest Batch Data Points"
increment_test

echo "POST ${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/telemetry/batch"
BATCH_DATA='{
  "data_points": [
    {
      "metric_name": "temperature",
      "value": 26.0,
      "unit": "celsius",
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "quality": 100
    },
    {
      "metric_name": "humidity",
      "value": 65.2,
      "unit": "percent",
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "quality": 100
    }
  ]
}'

BATCH_INGEST_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/telemetry/batch" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$BATCH_DATA")

echo "Response:"
echo "$BATCH_INGEST_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/telemetry/batch" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$BATCH_DATA")

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    pass_test "Batch data points ingested successfully"
else
    fail_test "Failed to ingest batch data points"
fi

# ======================
# Test 9: Get Latest Value
# ======================
print_section "Test 9: Get Latest Value"
increment_test

echo "GET ${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/metrics/${METRIC_NAME}/latest"
LATEST_RESPONSE=$(curl -s "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/metrics/${METRIC_NAME}/latest" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$LATEST_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/metrics/${METRIC_NAME}/latest" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Latest value retrieved successfully"
else
    fail_test "Failed to get latest value"
fi

# ======================
# Test 10: Get Device Metrics
# ======================
print_section "Test 10: Get Device Metrics"
increment_test

echo "GET ${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/metrics"
DEVICE_METRICS_RESPONSE=$(curl -s "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/metrics" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$DEVICE_METRICS_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/metrics" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Device metrics retrieved successfully"
else
    fail_test "Failed to get device metrics"
fi

# ======================
# Test 11: Query Telemetry Data
# ======================
print_section "Test 11: Query Telemetry Data"
increment_test

echo "POST ${API_BASE}/api/v1/query"
QUERY_REQUEST='{
  "devices": ["'$TEST_DEVICE_ID'"],
  "metrics": ["temperature"],
  "start_time": "'$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)'",
  "end_time": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
  "aggregation": "avg",
  "interval": 3600
}'

QUERY_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/query" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$QUERY_REQUEST")

echo "Response:"
echo "$QUERY_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/query" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$QUERY_REQUEST")

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Telemetry data queried successfully"
else
    fail_test "Failed to query telemetry data"
fi

# ======================
# Test 12: Create Alert Rule
# ======================
print_section "Test 12: Create Alert Rule"
increment_test

echo "POST ${API_BASE}/api/v1/alerts/rules"
ALERT_RULE_REQUEST='{
  "name": "High Temperature Alert",
  "description": "Alert when temperature exceeds 30C",
  "metric_name": "temperature",
  "condition": "greater_than",
  "threshold_value": "30",
  "evaluation_window": 300,
  "trigger_count": 2,
  "level": "warning",
  "device_ids": ["'$TEST_DEVICE_ID'"],
  "notification_channels": ["email"],
  "cooldown_minutes": 15,
  "enabled": true
}'

ALERT_RULE_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/alerts/rules" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$ALERT_RULE_REQUEST")

echo "Response:"
echo "$ALERT_RULE_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/alerts/rules" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$ALERT_RULE_REQUEST")

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    ALERT_RULE_ID=$(echo "$ALERT_RULE_RESPONSE" | jq -r '.rule_id // .id // "unknown"')
    echo -e "${YELLOW}Alert Rule ID: ${ALERT_RULE_ID}${NC}"
    pass_test "Alert rule created successfully"
else
    fail_test "Failed to create alert rule"
fi

# ======================
# Test 13: List Alert Rules
# ======================
print_section "Test 13: List Alert Rules"
increment_test

echo "GET ${API_BASE}/api/v1/alerts/rules"
ALERT_RULES_LIST_RESPONSE=$(curl -s "${API_BASE}/api/v1/alerts/rules" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$ALERT_RULES_LIST_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/alerts/rules" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Alert rules list retrieved successfully"
else
    fail_test "Failed to get alert rules list"
fi

# ======================
# Test 14: Get Alert Rule Details
# ======================
if [ -n "$ALERT_RULE_ID" ] && [ "$ALERT_RULE_ID" != "unknown" ]; then
    print_section "Test 14: Get Alert Rule Details"
    increment_test

    echo "GET ${API_BASE}/api/v1/alerts/rules/${ALERT_RULE_ID}"
    ALERT_RULE_DETAILS_RESPONSE=$(curl -s "${API_BASE}/api/v1/alerts/rules/${ALERT_RULE_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "Response:"
    echo "$ALERT_RULE_DETAILS_RESPONSE" | jq '.'
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/alerts/rules/${ALERT_RULE_ID}" \
      -H "Authorization: Bearer ${TEST_TOKEN}")
    echo "HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" == "200" ]; then
        pass_test "Alert rule details retrieved successfully"
    else
        fail_test "Failed to get alert rule details"
    fi
else
    echo -e "${YELLOW}⊘ SKIPPED: Test 14 - No alert rule ID available${NC}"
fi

# ======================
# Test 15: List Alerts
# ======================
print_section "Test 15: List Alerts"
increment_test

echo "GET ${API_BASE}/api/v1/alerts"
ALERTS_LIST_RESPONSE=$(curl -s "${API_BASE}/api/v1/alerts" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$ALERTS_LIST_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/alerts" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Alerts list retrieved successfully"
else
    fail_test "Failed to get alerts list"
fi

# ======================
# Test 16: Get Device Stats
# ======================
print_section "Test 16: Get Device Telemetry Statistics"
increment_test

echo "GET ${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/stats"
DEVICE_STATS_RESPONSE=$(curl -s "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/stats" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$DEVICE_STATS_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/devices/${TEST_DEVICE_ID}/stats" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Device telemetry statistics retrieved successfully"
else
    fail_test "Failed to get device telemetry statistics"
fi

# ======================
# Test 17: Get Service Telemetry Stats
# ======================
print_section "Test 17: Get Service Telemetry Statistics"
increment_test

echo "GET ${API_BASE}/api/v1/stats"
TELEMETRY_STATS_RESPONSE=$(curl -s "${API_BASE}/api/v1/stats" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "Response:"
echo "$TELEMETRY_STATS_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/stats" \
  -H "Authorization: Bearer ${TEST_TOKEN}")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    pass_test "Service telemetry statistics retrieved successfully"
else
    fail_test "Failed to get service telemetry statistics"
fi

# ======================
# Test 18: Create Real-time Subscription
# ======================
print_section "Test 18: Create Real-time Subscription"
increment_test

echo "POST ${API_BASE}/api/v1/subscribe"
SUBSCRIPTION_REQUEST='{
  "device_ids": ["'$TEST_DEVICE_ID'"],
  "metric_names": ["temperature"],
  "filter_condition": "value > 25",
  "max_frequency": 1000
}'

SUBSCRIPTION_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/subscribe" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$SUBSCRIPTION_REQUEST")

echo "Response:"
echo "$SUBSCRIPTION_RESPONSE" | jq '.'
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_BASE}/api/v1/subscribe" \
  -H "Authorization: Bearer ${TEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$SUBSCRIPTION_REQUEST")

echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    SUBSCRIPTION_ID=$(echo "$SUBSCRIPTION_RESPONSE" | jq -r '.subscription_id // "unknown"')
    echo -e "${YELLOW}Subscription ID: ${SUBSCRIPTION_ID}${NC}"
    pass_test "Real-time subscription created successfully"
else
    fail_test "Failed to create real-time subscription"
fi

# ======================
# Summary
# ======================
echo ""
echo "======================================================================"
echo -e "${BLUE}Test Summary${NC}"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Total: $TOTAL_TESTS"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed successfully!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
