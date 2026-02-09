#!/bin/bash
# ============================================================================
# Telemetry Service - Smoke Tests
#
# Tests end-to-end functionality with real infrastructure.
# Target: 15-18 test scenarios
#
# Usage:
#   ./smoke_test.sh                     # Direct mode (no JWT)
#   TEST_MODE=gateway ./smoke_test.sh   # Gateway mode with JWT
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../test_common.sh"

# ============================================================================
# Service Configuration
# ============================================================================
SERVICE_NAME="telemetry_service"
SERVICE_PORT=8225
API_PATH="/api/v1/telemetry"

# Initialize test framework
init_test

# ============================================================================
# Test Data (generated dynamically - zero hardcoded data)
# ============================================================================
TEST_TS="$(date +%s)_$$"
TEST_DEVICE_ID="device_smoke_${TEST_TS}"
TEST_ACCOUNT_ID="account_smoke_${TEST_TS}"

# IDs to track for cleanup
METRIC_DEFINITION_ID=""
ALERT_RULE_ID=""
SUBSCRIPTION_ID=""
INGESTED_DATA_ID=""

# ============================================================================
# Test 1: Health Check
# ============================================================================
print_section "Test 1: Health Check"
RESPONSE=$(curl -s "${BASE_URL}/health")
if json_has "$RESPONSE" "status"; then
    STATUS=$(json_get "$RESPONSE" "status")
    if [ "$STATUS" = "healthy" ]; then
        print_success "Health check passed: status=$STATUS"
        test_result 0
    else
        print_error "Health check failed: status=$STATUS"
        test_result 1
    fi
else
    print_error "Health check failed: no status field"
    test_result 1
fi

# ============================================================================
# Test 2: Create Metric Definition
# ============================================================================
print_section "Test 2: Create Metric Definition"
CREATE_METRIC_PAYLOAD=$(cat <<EOF
{
    "name": "smoke_test_cpu_${TEST_TS}",
    "description": "Smoke test CPU metric",
    "unit": "percent",
    "data_type": "float",
    "metric_type": "gauge",
    "aggregation_types": ["avg", "max", "min"],
    "retention_days": 30
}
EOF
)
RESPONSE=$(api_post "/metrics" "$CREATE_METRIC_PAYLOAD")
METRIC_DEFINITION_ID=$(json_get "$RESPONSE" "metric_id")
if [ -n "$METRIC_DEFINITION_ID" ] && [ "$METRIC_DEFINITION_ID" != "null" ]; then
    print_success "Created metric definition: $METRIC_DEFINITION_ID"
    test_result 0
else
    print_error "Failed to create metric definition"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 3: Get Metric Definition
# ============================================================================
print_section "Test 3: Get Metric Definition"
if [ -n "$METRIC_DEFINITION_ID" ]; then
    RESPONSE=$(api_get "/metrics/${METRIC_DEFINITION_ID}")
    RETRIEVED_ID=$(json_get "$RESPONSE" "metric_id")
    if [ "$RETRIEVED_ID" = "$METRIC_DEFINITION_ID" ]; then
        print_success "Retrieved metric definition: $RETRIEVED_ID"
        test_result 0
    else
        print_error "Failed to retrieve metric definition"
        echo "Response: $RESPONSE"
        test_result 1
    fi
else
    print_error "Skipped - no metric definition ID"
    test_result 1
fi

# ============================================================================
# Test 4: List Metric Definitions
# ============================================================================
print_section "Test 4: List Metric Definitions"
RESPONSE=$(api_get "/metrics")
if json_has "$RESPONSE" "items" || json_has "$RESPONSE" "metrics"; then
    print_success "Listed metric definitions"
    test_result 0
else
    print_error "Failed to list metric definitions"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 5: Ingest Telemetry Data
# ============================================================================
print_section "Test 5: Ingest Telemetry Data"
INGEST_PAYLOAD=$(cat <<EOF
{
    "device_id": "${TEST_DEVICE_ID}",
    "account_id": "${TEST_ACCOUNT_ID}",
    "data_points": [
        {
            "metric_name": "cpu_usage",
            "value": 45.5,
            "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "tags": {"host": "smoke-test-host"}
        },
        {
            "metric_name": "memory_usage",
            "value": 2048.0,
            "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "tags": {"host": "smoke-test-host"}
        }
    ]
}
EOF
)
RESPONSE=$(api_post "/ingest" "$INGEST_PAYLOAD")
if json_has "$RESPONSE" "success" || json_has "$RESPONSE" "ingested_count" || json_has "$RESPONSE" "status"; then
    print_success "Ingested telemetry data"
    test_result 0
else
    print_error "Failed to ingest telemetry data"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 6: Ingest Batch Telemetry Data
# ============================================================================
print_section "Test 6: Ingest Batch Telemetry Data"
BATCH_PAYLOAD=$(cat <<EOF
{
    "batch": [
        {
            "device_id": "${TEST_DEVICE_ID}",
            "account_id": "${TEST_ACCOUNT_ID}",
            "data_points": [
                {"metric_name": "disk_io", "value": 100.0, "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
            ]
        },
        {
            "device_id": "${TEST_DEVICE_ID}_2",
            "account_id": "${TEST_ACCOUNT_ID}",
            "data_points": [
                {"metric_name": "network_rx", "value": 5000.0, "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
            ]
        }
    ]
}
EOF
)
RESPONSE=$(api_post "/ingest/batch" "$BATCH_PAYLOAD")
if json_has "$RESPONSE" "success" || json_has "$RESPONSE" "batch_id" || json_has "$RESPONSE" "processed"; then
    print_success "Ingested batch telemetry data"
    test_result 0
else
    print_error "Failed to ingest batch data"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 7: Query Telemetry Data
# ============================================================================
print_section "Test 7: Query Telemetry Data"
QUERY_PAYLOAD=$(cat <<EOF
{
    "device_id": "${TEST_DEVICE_ID}",
    "metric_names": ["cpu_usage", "memory_usage"],
    "start_time": "$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)",
    "end_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "limit": 100
}
EOF
)
RESPONSE=$(api_post "/query" "$QUERY_PAYLOAD")
if json_has "$RESPONSE" "data" || json_has "$RESPONSE" "results" || json_has "$RESPONSE" "data_points"; then
    print_success "Queried telemetry data"
    test_result 0
else
    print_error "Failed to query telemetry data"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 8: Create Alert Rule
# ============================================================================
print_section "Test 8: Create Alert Rule"
ALERT_RULE_PAYLOAD=$(cat <<EOF
{
    "name": "smoke_test_alert_${TEST_TS}",
    "description": "Smoke test alert rule",
    "metric_name": "cpu_usage",
    "condition": "gt",
    "threshold": 90.0,
    "severity": "warning",
    "evaluation_window": 300,
    "enabled": true,
    "notification_channels": ["email"]
}
EOF
)
RESPONSE=$(api_post "/alerts/rules" "$ALERT_RULE_PAYLOAD")
ALERT_RULE_ID=$(json_get "$RESPONSE" "rule_id")
if [ -n "$ALERT_RULE_ID" ] && [ "$ALERT_RULE_ID" != "null" ]; then
    print_success "Created alert rule: $ALERT_RULE_ID"
    test_result 0
else
    # Try alternative field name
    ALERT_RULE_ID=$(json_get "$RESPONSE" "alert_rule_id")
    if [ -n "$ALERT_RULE_ID" ] && [ "$ALERT_RULE_ID" != "null" ]; then
        print_success "Created alert rule: $ALERT_RULE_ID"
        test_result 0
    else
        print_error "Failed to create alert rule"
        echo "Response: $RESPONSE"
        test_result 1
    fi
fi

# ============================================================================
# Test 9: Get Alert Rule
# ============================================================================
print_section "Test 9: Get Alert Rule"
if [ -n "$ALERT_RULE_ID" ]; then
    RESPONSE=$(api_get "/alerts/rules/${ALERT_RULE_ID}")
    RETRIEVED_ID=$(json_get "$RESPONSE" "rule_id")
    if [ -z "$RETRIEVED_ID" ] || [ "$RETRIEVED_ID" = "null" ]; then
        RETRIEVED_ID=$(json_get "$RESPONSE" "alert_rule_id")
    fi
    if [ "$RETRIEVED_ID" = "$ALERT_RULE_ID" ]; then
        print_success "Retrieved alert rule: $RETRIEVED_ID"
        test_result 0
    else
        print_error "Failed to retrieve alert rule"
        echo "Response: $RESPONSE"
        test_result 1
    fi
else
    print_error "Skipped - no alert rule ID"
    test_result 1
fi

# ============================================================================
# Test 10: List Alert Rules
# ============================================================================
print_section "Test 10: List Alert Rules"
RESPONSE=$(api_get "/alerts/rules")
if json_has "$RESPONSE" "items" || json_has "$RESPONSE" "rules"; then
    print_success "Listed alert rules"
    test_result 0
else
    print_error "Failed to list alert rules"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 11: List Alerts
# ============================================================================
print_section "Test 11: List Alerts"
RESPONSE=$(api_get "/alerts")
if json_has "$RESPONSE" "items" || json_has "$RESPONSE" "alerts"; then
    print_success "Listed alerts"
    test_result 0
else
    # May return empty list or success without items
    if json_has "$RESPONSE" "total" || json_has "$RESPONSE" "success"; then
        print_success "Listed alerts (empty or success response)"
        test_result 0
    else
        print_error "Failed to list alerts"
        echo "Response: $RESPONSE"
        test_result 1
    fi
fi

# ============================================================================
# Test 12: Get Device Telemetry Stats
# ============================================================================
print_section "Test 12: Get Device Telemetry Stats"
RESPONSE=$(api_get "/stats/device/${TEST_DEVICE_ID}")
if json_has "$RESPONSE" "device_id" || json_has "$RESPONSE" "stats" || json_has "$RESPONSE" "data_points_count"; then
    print_success "Retrieved device stats"
    test_result 0
else
    print_error "Failed to get device stats"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 13: Get Service Stats
# ============================================================================
print_section "Test 13: Get Service Stats"
RESPONSE=$(api_get "/stats")
if json_has "$RESPONSE" "total_data_points" || json_has "$RESPONSE" "stats" || json_has "$RESPONSE" "service"; then
    print_success "Retrieved service stats"
    test_result 0
else
    print_error "Failed to get service stats"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 14: Create Real-Time Subscription
# ============================================================================
print_section "Test 14: Create Real-Time Subscription"
SUBSCRIPTION_PAYLOAD=$(cat <<EOF
{
    "device_id": "${TEST_DEVICE_ID}",
    "metric_names": ["cpu_usage", "memory_usage"],
    "callback_url": "http://localhost:9999/webhook/telemetry"
}
EOF
)
RESPONSE=$(api_post "/subscriptions" "$SUBSCRIPTION_PAYLOAD")
SUBSCRIPTION_ID=$(json_get "$RESPONSE" "subscription_id")
if [ -n "$SUBSCRIPTION_ID" ] && [ "$SUBSCRIPTION_ID" != "null" ]; then
    print_success "Created subscription: $SUBSCRIPTION_ID"
    test_result 0
else
    print_error "Failed to create subscription"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 15: Get Subscription
# ============================================================================
print_section "Test 15: Get Subscription"
if [ -n "$SUBSCRIPTION_ID" ]; then
    RESPONSE=$(api_get "/subscriptions/${SUBSCRIPTION_ID}")
    RETRIEVED_ID=$(json_get "$RESPONSE" "subscription_id")
    if [ "$RETRIEVED_ID" = "$SUBSCRIPTION_ID" ]; then
        print_success "Retrieved subscription: $RETRIEVED_ID"
        test_result 0
    else
        print_error "Failed to retrieve subscription"
        echo "Response: $RESPONSE"
        test_result 1
    fi
else
    print_error "Skipped - no subscription ID"
    test_result 1
fi

# ============================================================================
# Test 16: Update Alert Rule
# ============================================================================
print_section "Test 16: Update Alert Rule"
if [ -n "$ALERT_RULE_ID" ]; then
    UPDATE_RULE_PAYLOAD=$(cat <<EOF
{
    "description": "Updated smoke test alert",
    "threshold": 95.0,
    "enabled": false
}
EOF
)
    RESPONSE=$(api_put "/alerts/rules/${ALERT_RULE_ID}" "$UPDATE_RULE_PAYLOAD")
    if json_has "$RESPONSE" "rule_id" || json_has "$RESPONSE" "alert_rule_id" || json_has "$RESPONSE" "success"; then
        print_success "Updated alert rule"
        test_result 0
    else
        print_error "Failed to update alert rule"
        echo "Response: $RESPONSE"
        test_result 1
    fi
else
    print_error "Skipped - no alert rule ID"
    test_result 1
fi

# ============================================================================
# Test 17: Delete Subscription
# ============================================================================
print_section "Test 17: Delete Subscription"
if [ -n "$SUBSCRIPTION_ID" ]; then
    RESPONSE=$(api_delete "/subscriptions/${SUBSCRIPTION_ID}")
    if json_has "$RESPONSE" "success" || [ -z "$RESPONSE" ]; then
        print_success "Deleted subscription"
        test_result 0
    else
        print_error "Failed to delete subscription"
        echo "Response: $RESPONSE"
        test_result 1
    fi
else
    print_error "Skipped - no subscription ID"
    test_result 1
fi

# ============================================================================
# Test 18: Delete Alert Rule
# ============================================================================
print_section "Test 18: Delete Alert Rule"
if [ -n "$ALERT_RULE_ID" ]; then
    RESPONSE=$(api_delete "/alerts/rules/${ALERT_RULE_ID}")
    if json_has "$RESPONSE" "success" || [ -z "$RESPONSE" ]; then
        print_success "Deleted alert rule"
        test_result 0
    else
        print_error "Failed to delete alert rule"
        echo "Response: $RESPONSE"
        test_result 1
    fi
else
    print_error "Skipped - no alert rule ID"
    test_result 1
fi

# ============================================================================
# Cleanup: Delete Metric Definition
# ============================================================================
print_section "Cleanup: Delete Metric Definition"
if [ -n "$METRIC_DEFINITION_ID" ]; then
    RESPONSE=$(api_delete "/metrics/${METRIC_DEFINITION_ID}")
    if json_has "$RESPONSE" "success" || [ -z "$RESPONSE" ]; then
        print_success "Cleaned up metric definition"
    else
        print_info "Cleanup warning: $RESPONSE"
    fi
fi

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
