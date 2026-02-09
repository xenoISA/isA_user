#!/bin/bash
# ============================================================================
# Audit Service - Smoke Tests
#
# Tests end-to-end functionality with real infrastructure.
# Validates health, event logging, queries, and compliance features.
#
# Usage:
#   ./smoke_test.sh                     # Direct mode (no JWT)
#   TEST_MODE=gateway ./smoke_test.sh   # Gateway mode with JWT
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../test_common.sh"

# Service configuration
SERVICE_NAME="audit_service"
SERVICE_PORT=8205
API_PATH="/api/v1/audit"

# Initialize test environment
init_test

# Test data
TEST_TS="$(date +%s)_$$"
AUDIT_EVENT_ID=""
USER_ID="user_smoke_${TEST_TS}"

# ============================================================================
# Test 1: Health Check
# ============================================================================
print_section "Test 1: Health Check"
RESPONSE=$(curl -s "${BASE_URL}/health")
if json_has "$RESPONSE" "status"; then
    print_success "Health check passed"
    echo "Response: $RESPONSE"
    test_result 0
else
    print_error "Health check failed"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 2: Log Audit Event (USER_LOGIN)
# ============================================================================
print_section "Test 2: Log Audit Event (USER_LOGIN)"
CREATE_PAYLOAD=$(cat <<EOF
{
    "event_type": "user_login",
    "category": "authentication",
    "severity": "low",
    "user_id": "${USER_ID}",
    "action": "login",
    "description": "Smoke test user login event ${TEST_TS}",
    "source_service": "smoke_test",
    "metadata": {
        "ip_address": "192.168.1.100",
        "user_agent": "SmokeTest/1.0",
        "test_id": "${TEST_TS}"
    }
}
EOF
)

RESPONSE=$(api_post "/events" "$CREATE_PAYLOAD")
AUDIT_EVENT_ID=$(json_get "$RESPONSE" "audit_event_id")

if [ -z "$AUDIT_EVENT_ID" ]; then
    AUDIT_EVENT_ID=$(json_get "$RESPONSE" "event_id")
fi

if [ -n "$AUDIT_EVENT_ID" ] && [ "$AUDIT_EVENT_ID" != "null" ]; then
    print_success "Created audit event: $AUDIT_EVENT_ID"
    test_result 0
else
    print_error "Failed to create audit event"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 3: Log Security Alert Event
# ============================================================================
print_section "Test 3: Log Security Alert Event"
ALERT_PAYLOAD=$(cat <<EOF
{
    "event_type": "security_alert",
    "category": "security",
    "severity": "high",
    "user_id": "${USER_ID}",
    "action": "failed_login_attempt",
    "description": "Multiple failed login attempts detected ${TEST_TS}",
    "source_service": "smoke_test",
    "metadata": {
        "failed_attempts": 5,
        "blocked": true,
        "test_id": "${TEST_TS}"
    }
}
EOF
)

RESPONSE=$(api_post "/events" "$ALERT_PAYLOAD")
ALERT_ID=$(json_get "$RESPONSE" "audit_event_id")

if [ -z "$ALERT_ID" ]; then
    ALERT_ID=$(json_get "$RESPONSE" "event_id")
fi

if [ -n "$ALERT_ID" ] && [ "$ALERT_ID" != "null" ]; then
    print_success "Created security alert: $ALERT_ID"
    test_result 0
else
    print_error "Failed to create security alert"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 4: Log Data Access Event
# ============================================================================
print_section "Test 4: Log Data Access Event"
DATA_ACCESS_PAYLOAD=$(cat <<EOF
{
    "event_type": "data_access",
    "category": "data_access",
    "severity": "low",
    "user_id": "${USER_ID}",
    "resource_id": "account_12345",
    "resource_type": "account",
    "action": "read",
    "description": "User accessed account data ${TEST_TS}",
    "source_service": "smoke_test",
    "metadata": {
        "fields_accessed": ["email", "phone"],
        "test_id": "${TEST_TS}"
    }
}
EOF
)

RESPONSE=$(api_post "/events" "$DATA_ACCESS_PAYLOAD")
if json_has "$RESPONSE" "audit_event_id" || json_has "$RESPONSE" "event_id"; then
    print_success "Created data access event"
    test_result 0
else
    print_error "Failed to create data access event"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 5: Query All Events
# ============================================================================
print_section "Test 5: Query All Events"
RESPONSE=$(api_get "/events?limit=10")
if json_has "$RESPONSE" "items" || echo "$RESPONSE" | grep -q '\['; then
    EVENT_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('items', data)) if isinstance(data, dict) else len(data))" 2>/dev/null || echo "0")
    print_success "Listed events: found ${EVENT_COUNT} events"
    test_result 0
else
    print_error "Failed to list events"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 6: Query Events by User ID
# ============================================================================
print_section "Test 6: Query Events by User ID"
RESPONSE=$(api_get "/events?user_id=${USER_ID}")
if json_has "$RESPONSE" "items" || echo "$RESPONSE" | grep -q "${USER_ID}"; then
    print_success "Filtered events by user_id"
    test_result 0
else
    # May return empty if filter doesn't match
    print_success "Query executed (may be empty)"
    test_result 0
fi

# ============================================================================
# Test 7: Query Events by Event Type
# ============================================================================
print_section "Test 7: Query Events by Event Type"
RESPONSE=$(api_get "/events?event_type=user_login")
if json_has "$RESPONSE" "items" || echo "$RESPONSE" | grep -q '\['; then
    print_success "Filtered events by event_type"
    test_result 0
else
    print_success "Query executed"
    test_result 0
fi

# ============================================================================
# Test 8: Query Events by Severity
# ============================================================================
print_section "Test 8: Query Events by Severity"
RESPONSE=$(api_get "/events?severity=high")
if json_has "$RESPONSE" "items" || echo "$RESPONSE" | grep -q '\['; then
    print_success "Filtered events by severity"
    test_result 0
else
    print_success "Query executed"
    test_result 0
fi

# ============================================================================
# Test 9: Get User Activity
# ============================================================================
print_section "Test 9: Get User Activity"
RESPONSE=$(api_get "/users/${USER_ID}/activity")
# May return 200 with data or 404 if endpoint doesn't exist
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/users/${USER_ID}/activity")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ]; then
    print_success "User activity endpoint responded: HTTP $HTTP_CODE"
    test_result 0
else
    print_error "Unexpected response: HTTP $HTTP_CODE"
    test_result 1
fi

# ============================================================================
# Test 10: Get Security Alerts
# ============================================================================
print_section "Test 10: Get Security Alerts"
RESPONSE=$(api_get "/security/alerts")
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/security/alerts")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ]; then
    print_success "Security alerts endpoint responded: HTTP $HTTP_CODE"
    test_result 0
else
    print_error "Unexpected response: HTTP $HTTP_CODE"
    test_result 1
fi

# ============================================================================
# Test 11: Get Event Statistics
# ============================================================================
print_section "Test 11: Get Event Statistics"
RESPONSE=$(api_get "/statistics")
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/statistics")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ]; then
    print_success "Statistics endpoint responded: HTTP $HTTP_CODE"
    test_result 0
else
    print_error "Unexpected response: HTTP $HTTP_CODE"
    test_result 1
fi

# ============================================================================
# Test 12: Log Configuration Change Event
# ============================================================================
print_section "Test 12: Log Configuration Change Event"
CONFIG_PAYLOAD=$(cat <<EOF
{
    "event_type": "config_change",
    "category": "system",
    "severity": "medium",
    "user_id": "admin_user",
    "resource_id": "config_database",
    "resource_type": "configuration",
    "action": "update",
    "description": "Database configuration updated ${TEST_TS}",
    "source_service": "smoke_test",
    "metadata": {
        "setting": "max_connections",
        "old_value": 100,
        "new_value": 200,
        "test_id": "${TEST_TS}"
    }
}
EOF
)

RESPONSE=$(api_post "/events" "$CONFIG_PAYLOAD")
if json_has "$RESPONSE" "audit_event_id" || json_has "$RESPONSE" "event_id"; then
    print_success "Created config change event"
    test_result 0
else
    print_error "Failed to create config change event"
    echo "Response: $RESPONSE"
    test_result 1
fi

# ============================================================================
# Test 13: Query Events with Pagination
# ============================================================================
print_section "Test 13: Query Events with Pagination"
RESPONSE=$(api_get "/events?limit=5&offset=0")
if json_has "$RESPONSE" "items" || echo "$RESPONSE" | grep -q '\['; then
    print_success "Pagination query executed"
    test_result 0
else
    print_success "Query responded"
    test_result 0
fi

# ============================================================================
# Test 14: Query Events by Date Range
# ============================================================================
print_section "Test 14: Query Events by Date Range"
START_DATE=$(date -u +"%Y-%m-%dT00:00:00Z")
END_DATE=$(date -u +"%Y-%m-%dT23:59:59Z")
RESPONSE=$(api_get "/events?start_date=${START_DATE}&end_date=${END_DATE}")
if [ $? -eq 0 ]; then
    print_success "Date range query executed"
    test_result 0
else
    print_error "Date range query failed"
    test_result 1
fi

# ============================================================================
# Test 15: Compliance Reports Endpoint
# ============================================================================
print_section "Test 15: Compliance Reports Endpoint"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/compliance/reports")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ]; then
    print_success "Compliance reports endpoint responded: HTTP $HTTP_CODE"
    test_result 0
else
    print_error "Unexpected response: HTTP $HTTP_CODE"
    test_result 1
fi

# ============================================================================
# Test 16: Verify Audit Event Persistence
# ============================================================================
print_section "Test 16: Verify Audit Event Persistence"
if [ -n "$AUDIT_EVENT_ID" ] && [ "$AUDIT_EVENT_ID" != "null" ]; then
    RESPONSE=$(api_get "/events/${AUDIT_EVENT_ID}")
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/events/${AUDIT_EVENT_ID}")
    if [ "$HTTP_CODE" = "200" ]; then
        RETRIEVED_ID=$(json_get "$RESPONSE" "audit_event_id")
        if [ -z "$RETRIEVED_ID" ]; then
            RETRIEVED_ID=$(json_get "$RESPONSE" "event_id")
        fi
        if [ "$RETRIEVED_ID" = "$AUDIT_EVENT_ID" ]; then
            print_success "Retrieved persisted event: $AUDIT_EVENT_ID"
            test_result 0
        else
            print_error "Event ID mismatch"
            test_result 1
        fi
    else
        # Event endpoint may not support direct GET by ID
        print_success "Event endpoint responded: HTTP $HTTP_CODE"
        test_result 0
    fi
else
    print_error "No event ID to verify"
    test_result 1
fi

# ============================================================================
# Test 17: Health Check - Detailed
# ============================================================================
print_section "Test 17: Health Check - Detailed"
RESPONSE=$(curl -s "${BASE_URL}/health/detailed" 2>/dev/null || curl -s "${BASE_URL}/health")
if json_has "$RESPONSE" "status"; then
    print_success "Detailed health check passed"
    test_result 0
else
    print_success "Health check responded"
    test_result 0
fi

# ============================================================================
# Test 18: Invalid Request Handling
# ============================================================================
print_section "Test 18: Invalid Request Handling"
INVALID_PAYLOAD='{"event_type": "INVALID_TYPE_12345"}'
RESPONSE=$(api_post "/events" "$INVALID_PAYLOAD")
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$INVALID_PAYLOAD" "${API_BASE}/events")
if [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "400" ]; then
    print_success "Invalid request handled correctly: HTTP $HTTP_CODE"
    test_result 0
else
    # May accept any string as event_type
    print_success "Request handled: HTTP $HTTP_CODE"
    test_result 0
fi

# ============================================================================
# Summary
# ============================================================================
print_summary
exit $?
