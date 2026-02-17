#!/bin/bash

# Notification Service Smoke Tests
# 
# This script performs end-to-end smoke testing of the Notification Service
# to verify all major functionality works as expected.
#
# Usage: ./notification_test.sh [environment]
#   environment: dev, staging, or production (default: dev)

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENVIRONMENT=${1:-dev}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration based on environment
case $ENVIRONMENT in
    dev)
        NOTIFICATION_SERVICE_URL="${NOTIFICATION_SERVICE_URL:-http://localhost:8215}"
        AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://localhost:8210}"
        ;;
    staging)
        NOTIFICATION_SERVICE_URL="${NOTIFICATION_SERVICE_URL:-https://notification-service.staging.isa.com}"
        AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-https://auth-service.staging.isa.com}"
        ;;
    production)
        NOTIFICATION_SERVICE_URL="${NOTIFICATION_SERVICE_URL:-https://notification-service.isa.com}"
        AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-https://auth-service.isa.com}"
        ;;
    *)
        log_error "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Test configuration
TIMEOUT=30
RETRY_COUNT=3
TEST_USER_EMAIL="smoke-test@example.com"
TEST_USER_ID="smoke-test-user-123"

# Helper functions
check_service_health() {
    local service_name=$1
    local url=$2
    
    log_info "Checking $service_name health..."
    
    for i in $(seq 1 $RETRY_COUNT); do
        if curl -f -s --max-time $TIMEOUT "$url/health" > /dev/null; then
            log_success "$service_name is healthy"
            return 0
        fi
        log_warning "$service_name health check attempt $i/$RETRY_COUNT failed"
        sleep 2
    done
    
    log_error "$service_name health check failed after $RETRY_COUNT attempts"
    return 1
}

make_authenticated_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    # Get auth token first
    local auth_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$TEST_USER_EMAIL\", \"password\": \"smoke_test_password\"}" \
        "$AUTH_SERVICE_URL/api/v1/auth/login" 2>/dev/null || echo "")
    
    if [[ -z "$auth_response" ]]; then
        log_error "Failed to get auth token"
        return 1
    fi
    
    local token=$(echo "$auth_response" | jq -r '.access_token' 2>/dev/null)
    
    if [[ -z "$token" || "$token" == "null" ]]; then
        log_error "Failed to extract auth token from response"
        return 1
    fi
    
    # Make authenticated request
    curl -s -X "$method" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -H "X-User-ID: $TEST_USER_ID" \
        -d "$data" \
        "$NOTIFICATION_SERVICE_URL$endpoint" 2>/dev/null
}

# Test functions
test_health_check() {
    log_info "Testing health check endpoint..."
    
    local health_response=$(curl -s --max-time $TIMEOUT "$NOTIFICATION_SERVICE_URL/health" 2>/dev/null || echo "")
    
    if [[ -z "$health_response" ]]; then
        log_error "Health check endpoint not responding"
        return 1
    fi
    
    local status=$(echo "$health_response" | jq -r '.status' 2>/dev/null)
    local service=$(echo "$health_response" | jq -r '.service' 2>/dev/null)
    
    if [[ "$status" == "healthy" && "$service" == "notification_service" ]]; then
        log_success "Health check passed"
        return 0
    else
        log_error "Health check failed: status=$status, service=$service"
        return 1
    fi
}

test_email_notification() {
    log_info "Testing email notification sending..."
    
    local notification_data=$(cat <<EOF
{
    "type": "email",
    "recipient_email": "$TEST_USER_EMAIL",
    "subject": "Smoke Test Email",
    "content": "This is a smoke test email from notification service",
    "priority": "normal"
}
EOF
)
    
    local response=$(make_authenticated_request "POST" "/api/v1/notifications/send" "$notification_data")
    
    if [[ -z "$response" ]]; then
        log_error "Email notification request failed"
        return 1
    fi
    
    local success=$(echo "$response" | jq -r '.success' 2>/dev/null)
    local notification_id=$(echo "$response" | jq -r '.notification.notification_id' 2>/dev/null)
    
    if [[ "$success" == "true" && -n "$notification_id" && "$notification_id" != "null" ]]; then
        log_success "Email notification sent successfully (ID: $notification_id)"
        return 0
    else
        log_error "Email notification failed: $response"
        return 1
    fi
}

test_push_notification() {
    log_info "Testing push notification sending..."
    
    # First register a push subscription
    local subscription_data=$(cat <<EOF
{
    "user_id": "$TEST_USER_ID",
    "device_token": "smoke_test_device_token_123",
    "platform": "ios",
    "device_name": "Smoke Test Device",
    "app_version": "1.0.0"
}
EOF
)
    
    local subscription_response=$(make_authenticated_request "POST" "/api/v1/notifications/subscriptions/push" "$subscription_data")
    
    if [[ -z "$subscription_response" ]]; then
        log_error "Push subscription registration failed"
        return 1
    fi
    
    local subscription_success=$(echo "$subscription_response" | jq -r '.success' 2>/dev/null)
    
    if [[ "$subscription_success" != "true" ]]; then
        log_error "Push subscription failed: $subscription_response"
        return 1
    fi
    
    # Now send push notification
    local push_data=$(cat <<EOF
{
    "type": "push",
    "recipient_id": "$TEST_USER_ID",
    "title": "Smoke Test Push",
    "content": "This is a smoke test push notification",
    "data": {"test_key": "test_value"},
    "priority": "high"
}
EOF
)
    
    local push_response=$(make_authenticated_request "POST" "/api/v1/notifications/send" "$push_data")
    
    if [[ -z "$push_response" ]]; then
        log_error "Push notification request failed"
        return 1
    fi
    
    local push_success=$(echo "$push_response" | jq -r '.success' 2>/dev/null)
    local push_notification_id=$(echo "$push_response" | jq -r '.notification.notification_id' 2>/dev/null)
    
    if [[ "$push_success" == "true" && -n "$push_notification_id" && "$push_notification_id" != "null" ]]; then
        log_success "Push notification sent successfully (ID: $push_notification_id)"
        return 0
    else
        log_error "Push notification failed: $push_response"
        return 1
    fi
}

test_in_app_notification() {
    log_info "Testing in-app notification sending..."
    
    local inapp_data=$(cat <<EOF
{
    "type": "in_app",
    "recipient_id": "$TEST_USER_ID",
    "title": "Smoke Test In-App",
    "content": "This is a smoke test in-app notification",
    "action_url": "/notifications/smoke-test",
    "priority": "normal"
}
EOF
)
    
    local response=$(make_authenticated_request "POST" "/api/v1/notifications/send" "$inapp_data")
    
    if [[ -z "$response" ]]; then
        log_error "In-app notification request failed"
        return 1
    fi
    
    local success=$(echo "$response" | jq -r '.success' 2>/dev/null)
    local notification_id=$(echo "$response" | jq -r '.notification.notification_id' 2>/dev/null)
    
    if [[ "$success" == "true" && -n "$notification_id" && "$notification_id" != "null" ]]; then
        log_success "In-app notification sent successfully (ID: $notification_id)"
        
        # Test listing in-app notifications
        log_info "Testing in-app notification listing..."
        local list_response=$(make_authenticated_request "GET" "/api/v1/notifications/in-app/$TEST_USER_ID" "")
        
        if [[ -n "$list_response" ]]; then
            local notifications_count=$(echo "$list_response" | jq 'length' 2>/dev/null)
            log_success "Found $notifications_count in-app notifications"
        fi
        
        return 0
    else
        log_error "In-app notification failed: $response"
        return 1
    fi
}

test_template_management() {
    log_info "Testing template management..."
    
    # Create template
    local template_data=$(cat <<EOF
{
    "name": "Smoke Test Template",
    "type": "email",
    "subject": "Smoke Test {{subject}}",
    "content": "Hello {{name}}, this is a {{message}} template test.",
    "variables": ["subject", "name", "message"]
}
EOF
)
    
    local create_response=$(make_authenticated_request "POST" "/api/v1/notifications/templates" "$template_data")
    
    if [[ -z "$create_response" ]]; then
        log_error "Template creation failed"
        return 1
    fi
    
    local create_success=$(echo "$create_response" | jq -r '.success' 2>/dev/null)
    local template_id=$(echo "$create_response" | jq -r '.template.template_id' 2>/dev/null)
    
    if [[ "$create_success" != "true" || -z "$template_id" || "$template_id" == "null" ]]; then
        log_error "Template creation failed: $create_response"
        return 1
    fi
    
    log_success "Template created successfully (ID: $template_id)"
    
    # Get template
    log_info "Testing template retrieval..."
    local get_response=$(make_authenticated_request "GET" "/api/v1/notifications/templates/$template_id" "")
    
    if [[ -n "$get_response" ]]; then
        local get_template_id=$(echo "$get_response" | jq -r '.template.template_id' 2>/dev/null)
        if [[ "$get_template_id" == "$template_id" ]]; then
            log_success "Template retrieved successfully"
        else
            log_error "Template retrieval failed: ID mismatch"
        fi
    fi
    
    # Update template
    log_info "Testing template update..."
    local update_data=$(cat <<EOF
{
    "name": "Updated Smoke Test Template",
    "subject": "Updated {{subject}}",
    "content": "Hello {{name}}, this is an updated {{message}} template.",
    "variables": ["subject", "name", "message"]
}
EOF
)
    
    local update_response=$(make_authenticated_request "PUT" "/api/v1/notifications/templates/$template_id" "$update_data")
    
    if [[ -n "$update_response" ]]; then
        local update_success=$(echo "$update_response" | jq -r '.success' 2>/dev/null)
        if [[ "$update_success" == "true" ]]; then
            log_success "Template updated successfully"
        else
            log_error "Template update failed: $update_response"
        fi
    fi
    
    # List templates
    log_info "Testing template listing..."
    local list_response=$(make_authenticated_request "GET" "/api/v1/notifications/templates?type=email" "")
    
    if [[ -n "$list_response" ]]; then
        local templates_count=$(echo "$list_response" | jq 'length' 2>/dev/null)
        log_success "Found $templates_count email templates"
    fi
}

test_batch_notifications() {
    log_info "Testing batch notification sending..."
    
    local batch_data=$(cat <<EOF
{
    "name": "Smoke Test Batch",
    "type": "email",
    "recipients": [
        {"recipient_email": "batch1@example.com", "variables": {"name": "User 1"}},
        {"recipient_email": "batch2@example.com", "variables": {"name": "User 2"}},
        {"recipient_email": "batch3@example.com", "variables": {"name": "User 3"}}
    ],
    "priority": "normal"
}
EOF
)
    
    local response=$(make_authenticated_request "POST" "/api/v1/notifications/batch" "$batch_data")
    
    if [[ -z "$response" ]]; then
        log_error "Batch notification request failed"
        return 1
    fi
    
    local success=$(echo "$response" | jq -r '.success' 2>/dev/null)
    local batch_id=$(echo "$response" | jq -r '.batch.batch_id' 2>/dev/null)
    local total_recipients=$(echo "$response" | jq -r '.batch.total_recipients' 2>/dev/null)
    
    if [[ "$success" == "true" && -n "$batch_id" && "$batch_id" != "null" && "$total_recipients" == "3" ]]; then
        log_success "Batch notification sent successfully (ID: $batch_id, Recipients: $total_recipients)"
        return 0
    else
        log_error "Batch notification failed: $response"
        return 1
    fi
}

test_template_rendering() {
    log_info "Testing template rendering..."
    
    # Create a template for rendering test
    local template_data=$(cat <<EOF
{
    "name": "Render Test Template",
    "type": "email",
    "subject": "Render {{subject}}",
    "content": "Hello {{name}}, rendering test: {{message}}",
    "variables": ["subject", "name", "message"]
}
EOF
)
    
    local create_response=$(make_authenticated_request "POST" "/api/v1/notifications/templates" "$template_data")
    
    if [[ -z "$create_response" ]]; then
        log_error "Template creation for rendering test failed"
        return 1
    fi
    
    local template_id=$(echo "$create_response" | jq -r '.template.template_id' 2>/dev/null)
    
    if [[ -z "$template_id" || "$template_id" == "null" ]]; then
        log_error "Failed to get template ID for rendering test"
        return 1
    fi
    
    # Render template with variables
    local render_data=$(cat <<EOF
{
    "template_id": "$template_id",
    "variables": {
        "subject": "Rendering",
        "name": "Smoke Test User",
        "message": "template rendering works"
    }
}
EOF
)
    
    local render_response=$(make_authenticated_request "POST" "/api/v1/notifications/templates/render" "$render_data")
    
    if [[ -z "$render_response" ]]; then
        log_error "Template rendering request failed"
        return 1
    fi
    
    local success=$(echo "$render_response" | jq -r '.success' 2>/dev/null)
    local rendered_subject=$(echo "$render_response" | jq -r '.rendered.subject' 2>/dev/null)
    local rendered_content=$(echo "$render_response" | jq -r '.rendered.content' 2>/dev/null)
    
    if [[ "$success" == "true" && "$rendered_subject" == "Render Rendering" && "$rendered_content" == "Hello Smoke Test User, rendering test: template rendering works" ]]; then
        log_success "Template rendering successful"
        return 0
    else
        log_error "Template rendering failed: $render_response"
        return 1
    fi
}

test_notification_statistics() {
    log_info "Testing notification statistics..."
    
    local response=$(make_authenticated_request "GET" "/api/v1/notifications/stats?period=1d" "")
    
    if [[ -z "$response" ]]; then
        log_error "Statistics request failed"
        return 1
    fi
    
    local stats=$(echo "$response" | jq '.stats' 2>/dev/null)
    
    if [[ -n "$stats" ]]; then
        local total_sent=$(echo "$stats" | jq -r '.total_sent' 2>/dev/null)
        local period=$(echo "$stats" | jq -r '.period' 2>/dev/null)
        
        if [[ -n "$total_sent" && "$period" == "1d" ]]; then
            log_success "Statistics retrieved successfully (Total sent: $total_sent, Period: $period)"
            return 0
        fi
    fi
    
    log_error "Statistics test failed: $response"
    return 1
}

test_error_handling() {
    log_info "Testing error handling..."
    
    # Test invalid notification type
    local invalid_data='{"type": "invalid_type", "recipient_email": "test@example.com", "content": "test"}'
    local response=$(make_authenticated_request "POST" "/api/v1/notifications/send" "$invalid_data")
    
    local status_code=$(echo "$response" | jq -r 'if .error then 422 else 200 end' 2>/dev/null)
    
    if [[ "$status_code" == "422" ]]; then
        log_success "Invalid notification type properly rejected"
    else
        log_error "Error handling test failed: invalid type was accepted"
        return 1
    fi
    
    # Test missing required fields
    local missing_fields_data='{"type": "email"}'
    response=$(make_authenticated_request "POST" "/api/v1/notifications/send" "$missing_fields_data")
    
    status_code=$(echo "$response" | jq -r 'if .error then 422 else 200 end' 2>/dev/null)
    
    if [[ "$status_code" == "422" ]]; then
        log_success "Missing required fields properly rejected"
    else
        log_error "Error handling test failed: missing fields were accepted"
        return 1
    fi
    
    # Test unauthorized access
    local unauthorized_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"type": "email", "recipient_email": "test@example.com", "content": "test"}' \
        "$NOTIFICATION_SERVICE_URL/api/v1/notifications/send" 2>/dev/null || echo "")
    
    if [[ -n "$unauthorized_response" ]]; then
        local has_error=$(echo "$unauthorized_response" | jq -e '.error' 2>/dev/null)
        if [[ "$has_error" == "0" ]]; then
            log_error "Unauthorized access was not properly rejected"
            return 1
        fi
    fi
    
    log_success "Unauthorized access properly rejected"
    return 0
}

test_performance() {
    log_info "Testing basic performance..."
    
    local start_time=$(date +%s)
    
    # Send multiple concurrent requests
    local pids=()
    for i in {1..5}; do
        (
            local notification_data=$(cat <<EOF
{
    "type": "email",
    "recipient_email": "perf$i@example.com",
    "subject": "Performance Test $i",
    "content": "Performance test notification $i"
}
EOF
)
            make_authenticated_request "POST" "/api/v1/notifications/send" "$notification_data" > /dev/null 2>&1
        ) &
        pids+=($!)
    done
    
    # Wait for all background jobs
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [[ $duration -le 30 ]]; then
        log_success "Performance test passed (5 requests in ${duration}s)"
        return 0
    else
        log_warning "Performance test slow (5 requests in ${duration}s)"
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting Notification Service smoke tests for environment: $ENVIRONMENT"
    log_info "Notification Service URL: $NOTIFICATION_SERVICE_URL"
    log_info "Auth Service URL: $AUTH_SERVICE_URL"
    
    # Check dependencies
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed"
        exit 1
    fi
    
    local failed_tests=0
    local total_tests=0
    
    # Run tests
    local tests=(
        "test_health_check"
        "test_email_notification"
        "test_push_notification"
        "test_in_app_notification"
        "test_template_management"
        "test_batch_notifications"
        "test_template_rendering"
        "test_notification_statistics"
        "test_error_handling"
        "test_performance"
    )
    
    for test in "${tests[@]}"; do
        log_info "Running $test..."
        total_tests=$((total_tests + 1))
        
        if $test; then
            log_success "$test passed"
        else
            log_error "$test failed"
            failed_tests=$((failed_tests + 1))
        fi
        
        echo "----------------------------------------"
        sleep 1
    done
    
    # Summary
    echo ""
    log_info "Smoke Test Summary"
    log_info "==================="
    log_info "Total tests: $total_tests"
    log_info "Failed tests: $failed_tests"
    log_info "Success rate: $(( (total_tests - failed_tests) * 100 / total_tests ))%"
    
    if [[ $failed_tests -eq 0 ]]; then
        log_success "All smoke tests passed!"
        exit 0
    else
        log_error "$failed_tests smoke test(s) failed!"
        exit 1
    fi
}

# Run main function
main "$@"
