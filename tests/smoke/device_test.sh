#!/bin/bash

# Device Service End-to-End Smoke Tests
# Tests the complete Device Service functionality from API to database to events

set -e

# Configuration
DEVICE_SERVICE_URL="${DEVICE_SERVICE_URL:-http://localhost:8220}"
AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-http://localhost:8210}"
TEST_USER_ID="${TEST_USER_ID:-smoke-test-user}"
TEST_JWT_TOKEN="${TEST_JWT_TOKEN:-Bearer test-jwt-token}"
TIMEOUT="${TIMEOUT:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test utilities
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

log_test_start() {
    echo -e "${BLUE}=== Starting Test: $1 ===${NC}"
}

log_test_result() {
    if [ $1 -eq 0 ]; then
        log_success "$2 - PASSED"
    else
        log_error "$2 - FAILED (exit code: $1)"
    fi
}

# Helper functions
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local headers="$4"
    
    if [ -n "$headers" ]; then
        curl -s -w "\n%{http_code}" -X "$method" \
             -H "Content-Type: application/json" \
             -H "Authorization: $TEST_JWT_TOKEN" \
             $headers \
             -d "$data" \
             "$DEVICE_SERVICE_URL$endpoint"
    else
        curl -s -w "\n%{http_code}" -X "$method" \
             -H "Content-Type: application/json" \
             -H "Authorization: $TEST_JWT_TOKEN" \
             -d "$data" \
             "$DEVICE_SERVICE_URL$endpoint"
    fi
}

check_response() {
    local response="$1"
    local expected_status="$2"
    local test_name="$3"
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "$expected_status" ]; then
        log_test_result 0 "$test_name"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        return 0
    else
        log_test_result 1 "$test_name (HTTP $http_code, expected $expected_status)"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        return 1
    fi
}

wait_for_service() {
    local service_name="$1"
    local service_url="$2"
    local max_attempts="${3:-30}"
    
    log_info "Waiting for $service_name to be available at $service_url"
    
    for i in $(seq 1 $max_attempts); do
        if curl -s --max-time 5 "$service_url/health" >/dev/null 2>&1; then
            log_success "$service_name is available"
            return 0
        fi
        log_info "Attempt $i/$max_attempts: $service_name not ready, waiting..."
        sleep 2
    done
    
    log_error "$service_name not available after $max_attempts attempts"
    return 1
}

# Test Data Setup
setup_test_data() {
    log_info "Setting up test data..."
    
    # Create test user via Auth Service (simplified)
    local user_data='{
        "user_id": "'$TEST_USER_ID'",
        "email": "'$TEST_USER_ID'@test.com",
        "password": "testpassword123"
    }'
    
    response=$(curl -s -w "\n%{http_code}" -X POST \
               -H "Content-Type: application/json" \
               -d "$user_data" \
               "$AUTH_SERVICE_URL/api/v1/users")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "201" ] || [ "$http_code" = "409" ]; then
        log_success "Test user setup complete"
    else
        log_error "Failed to setup test user (HTTP $http_code)"
    fi
}

cleanup_test_data() {
    log_info "Cleaning up test data..."
    
    # Delete test devices
    devices_response=$(curl -s -X GET \
                          -H "Authorization: $TEST_JWT_TOKEN" \
                          "$DEVICE_SERVICE_URL/api/v1/devices?limit=100")
    
    if echo "$devices_response" | jq -e '.devices | length' 2>/dev/null >/dev/null; then
        device_ids=$(echo "$devices_response" | jq -r '.devices[].device_id')
        
        for device_id in $device_ids; do
            curl -s -X DELETE \
                 -H "Authorization: $TEST_JWT_TOKEN" \
                 "$DEVICE_SERVICE_URL/api/v1/devices/$device_id" >/dev/null
        done
        
        log_success "Cleaned up test devices"
    fi
}

# Health Check Tests
test_health_check() {
    log_test_start "Health Check"
    
    response=$(curl -s -w "\n%{http_code}" "$DEVICE_SERVICE_URL/health")
    check_response "$response" "200" "Health Check"
}

test_detailed_health_check() {
    log_test_start "Detailed Health Check"
    
    response=$(curl -s -w "\n%{http_code}" "$DEVICE_SERVICE_URL/health/detailed")
    check_response "$response" "200" "Detailed Health Check"
}

# Device Registration Tests
test_device_registration() {
    log_test_start "Device Registration"
    
    local device_data='{
        "device_name": "Smoke Test Device",
        "device_type": "smart_frame",
        "manufacturer": "TestCorp",
        "model": "ST-SF1000",
        "serial_number": "ST123456789",
        "firmware_version": "1.0.0",
        "mac_address": "00:1B:44:11:22:33",
        "connectivity_type": "wifi",
        "security_level": "standard",
        "metadata": {
            "test": true,
            "smoke_test": true
        },
        "tags": ["smoke_test", "test_device"]
    }'
    
    response=$(make_request "POST" "/api/v1/devices" "$device_data")
    check_response "$response" "201" "Device Registration"
    
    if [ $? -eq 0 ]; then
        # Extract device_id for subsequent tests
        TEST_DEVICE_ID=$(echo "$response" | head -n -1 | jq -r '.device_id')
        export TEST_DEVICE_ID
        log_success "Device registered with ID: $TEST_DEVICE_ID"
    fi
}

test_device_registration_validation() {
    log_test_start "Device Registration Validation"
    
    # Test missing required fields
    local invalid_device_data='{
        "device_name": "Invalid Device"
        # Missing required fields
    }'
    
    response=$(make_request "POST" "/api/v1/devices" "$invalid_device_data")
    check_response "$response" "400" "Missing Required Fields"
    
    # Test invalid device type
    local invalid_type_data='{
        "device_name": "Test Device",
        "device_type": "invalid_type",
        "manufacturer": "TestCorp",
        "model": "ST-1000",
        "serial_number": "123456789",
        "firmware_version": "1.0.0",
        "connectivity_type": "wifi",
        "security_level": "standard"
    }'
    
    response=$(make_request "POST" "/api/v1/devices" "$invalid_type_data")
    check_response "$response" "400" "Invalid Device Type"
    
    # Test invalid MAC address
    local invalid_mac_data='{
        "device_name": "Test Device",
        "device_type": "smart_frame",
        "manufacturer": "TestCorp",
        "model": "ST-1000",
        "serial_number": "123456789",
        "firmware_version": "1.0.0",
        "mac_address": "invalid-mac-address",
        "connectivity_type": "wifi",
        "security_level": "standard"
    }'
    
    response=$(make_request "POST" "/api/v1/devices" "$invalid_mac_data")
    check_response "$response" "400" "Invalid MAC Address"
}

test_device_duplicate_serial() {
    log_test_start "Duplicate Serial Number Prevention"
    
    # Register first device
    local device_data1='{
        "device_name": "Duplicate Test Device 1",
        "device_type": "sensor",
        "manufacturer": "TestCorp",
        "model": "ST-1000",
        "serial_number": "DUPLICATE123",
        "firmware_version": "1.0.0",
        "connectivity_type": "wifi",
        "security_level": "standard"
    }'
    
    response1=$(make_request "POST" "/api/v1/devices" "$device_data1")
    
    # Register second device with same serial
    local device_data2='{
        "device_name": "Duplicate Test Device 2",
        "device_type": "sensor",
        "manufacturer": "TestCorp",
        "model": "ST-1000",
        "serial_number": "DUPLICATE123",
        "firmware_version": "1.0.0",
        "connectivity_type": "wifi",
        "security_level": "standard"
    }'
    
    response2=$(make_request "POST" "/api/v1/devices" "$device_data2")
    
    http_code2=$(echo "$response2" | tail -n1)
    
    if [ "$http_code2" = "409" ]; then
        log_test_result 0 "Duplicate Serial Prevention"
    else
        log_test_result 1 "Duplicate Serial Prevention (HTTP $http_code2, expected 409)"
    fi
}

# Device Authentication Tests
test_device_authentication() {
    log_test_start "Device Authentication"
    
    if [ -z "$TEST_DEVICE_ID" ]; then
        log_warning "No device ID available, skipping authentication test"
        return 1
    fi
    
    local auth_data='{
        "device_id": "'$TEST_DEVICE_ID'",
        "device_secret": "test_secret_123",
        "auth_type": "secret_key"
    }'
    
    response=$(make_request "POST" "/api/v1/devices/auth" "$auth_data")
    check_response "$response" "200" "Device Authentication"
    
    if [ $? -eq 0 ]; then
        # Extract access token for subsequent tests
        TEST_DEVICE_TOKEN=$(echo "$response" | head -n -1 | jq -r '.access_token')
        export TEST_DEVICE_TOKEN
        log_success "Device authenticated, token: ${TEST_DEVICE_TOKEN:0:20}..."
    fi
}

test_device_authentication_invalid() {
    log_test_start "Invalid Device Authentication"
    
    local invalid_auth_data='{
        "device_id": "nonexistent-device",
        "device_secret": "wrong_secret",
        "auth_type": "secret_key"
    }'
    
    response=$(make_request "POST" "/api/v1/devices/auth" "$invalid_auth_data")
    check_response "$response" "401" "Invalid Device Authentication"
}

# Device Management Tests
test_get_device() {
    log_test_start "Get Device"
    
    if [ -z "$TEST_DEVICE_ID" ]; then
        log_warning "No device ID available, skipping get device test"
        return 1
    fi
    
    response=$(make_request "GET" "/api/v1/devices/$TEST_DEVICE_ID")
    check_response "$response" "200" "Get Device"
}

test_update_device() {
    log_test_start "Update Device"
    
    if [ -z "$TEST_DEVICE_ID" ]; then
        log_warning "No device ID available, skipping update device test"
        return 1
    fi
    
    local update_data='{
        "device_name": "Updated Smoke Test Device",
        "firmware_version": "2.0.0",
        "status": "active"
    }'
    
    response=$(make_request "PUT" "/api/v1/devices/$TEST_DEVICE_ID" "$update_data")
    check_response "$response" "200" "Update Device"
}

test_list_devices() {
    log_test_start "List Devices"
    
    response=$(make_request "GET" "/api/v1/devices")
    check_response "$response" "200" "List Devices"
    
    if [ $? -eq 0 ]; then
        device_count=$(echo "$response" | head -n -1 | jq -r '.count')
        log_success "Found $device_count devices"
    fi
}

test_list_devices_with_filters() {
    log_test_start "List Devices with Filters"
    
    response=$(make_request "GET" "/api/v1/devices?device_type=smart_frame&status=active")
    check_response "$response" "200" "List Devices with Filters"
    
    if [ $? -eq 0 ]; then
        device_count=$(echo "$response" | head -n -1 | jq -r '.count')
        log_success "Found $device_count smart_frame devices with active status"
    fi
}

# Device Command Tests
test_send_device_command() {
    log_test_start "Send Device Command"
    
    if [ -z "$TEST_DEVICE_ID" ]; then
        log_warning "No device ID available, skipping command test"
        return 1
    fi
    
    local command_data='{
        "command": "reboot",
        "parameters": {
            "delay": 5
        },
        "timeout": 30,
        "priority": 5,
        "require_ack": true
    }'
    
    response=$(make_request "POST" "/api/v1/devices/$TEST_DEVICE_ID/commands" "$command_data")
    check_response "$response" "200" "Send Device Command"
    
    if [ $? -eq 0 ]; then
        command_id=$(echo "$response" | head -n -1 | jq -r '.command_id')
        log_success "Command sent with ID: $command_id"
        export TEST_COMMAND_ID="$command_id"
    fi
}

test_bulk_command() {
    log_test_start "Bulk Device Command"
    
    # First, ensure we have multiple devices
    setup_test_data
    test_device_registration
    
    response=$(make_request "GET" "/api/v1/devices?limit=5")
    
    if echo "$response" | head -n -1 | jq -e '.devices | length >= 2' 2>/dev/null >/dev/null; then
        device_ids=$(echo "$response" | head -n -1 | jq -r '.devices[:2] | .[].device_id')
        
        local bulk_data='{
            "device_ids": ['$(echo "$device_ids" | head -n -1 | jq -r '.[0]')', '$(echo "$device_ids" | head -n -1 | jq -r '.[1]')'],
            "command": "reboot",
            "parameters": {
                "delay": 10
            },
            "timeout": 30,
            "priority": 5,
            "require_ack": true
        }'
        
        response=$(make_request "POST" "/api/v1/devices/bulk/commands" "$bulk_data")
        check_response "$response" "200" "Bulk Device Command"
        
        if [ $? -eq 0 ]; then
            bulk_command_id=$(echo "$response" | head -n -1 | jq -r '.command_id')
            log_success "Bulk command sent with ID: $bulk_command_id"
        fi
    else
        log_warning "Not enough devices for bulk command test"
    fi
}

# Smart Frame Tests
test_register_smart_frame() {
    log_test_start "Register Smart Frame"
    
    local frame_data='{
        "device_name": "Smoke Test Smart Frame",
        "manufacturer": "FrameCorp",
        "model": "SF-10.1",
        "serial_number": "SF123456789",
        "mac_address": "00:1B:44:11:22:34",
        "screen_size": "10.1 inches",
        "resolution": "1920x1080",
        "supported_formats": ["jpg", "png", "mp4"],
        "connectivity_type": "wifi",
        "initial_config": {
            "brightness": 80,
            "display_mode": "photo_slideshow",
            "slideshow_interval": 30
        }
    }'
    
    response=$(make_request "POST" "/api/v1/devices/frames" "$frame_data")
    check_response "$response" "201" "Register Smart Frame"
    
    if [ $? -eq 0 ]; then
        frame_id=$(echo "$response" | head -n -1 | jq -r '.device_id')
        export TEST_FRAME_ID="$frame_id"
        log_success "Smart frame registered with ID: $TEST_FRAME_ID"
    fi
}

test_frame_display_control() {
    log_test_start "Frame Display Control"
    
    if [ -z "$TEST_FRAME_ID" ]; then
        log_warning "No frame ID available, skipping display control test"
        return 1
    fi
    
    local display_data='{
        "brightness": 85,
        "display_mode": "clock_display",
        "slideshow_interval": 45
    }'
    
    response=$(make_request "POST" "/api/v1/devices/frames/$TEST_FRAME_ID/display" "$display_data")
    check_response "$response" "200" "Frame Display Control"
}

test_frame_sync() {
    log_test_start "Frame Content Sync"
    
    if [ -z "$TEST_FRAME_ID" ]; then
        log_warning "No frame ID available, skipping sync test"
        return 1
    fi
    
    local sync_data='{
        "album_ids": ["album1", "album2"],
        "force": false,
        "priority": "normal"
    }'
    
    response=$(make_request "POST" "/api/v1/devices/frames/$TEST_FRAME_ID/sync" "$sync_data")
    check_response "$response" "200" "Frame Content Sync"
    
    if [ $? -eq 0 ]; then
        sync_id=$(echo "$response" | head -n -1 | jq -r '.sync_id')
        log_success "Frame sync started with ID: $sync_id"
    fi
}

# Performance and Load Tests
test_concurrent_requests() {
    log_test_start "Concurrent Requests"
    
    local device_data='{
        "device_name": "Concurrent Test Device",
        "device_type": "sensor",
        "manufacturer": "TestCorp",
        "model": "CT-1000",
        "serial_number": "CT123456789",
        "firmware_version": "1.0.0",
        "connectivity_type": "wifi",
        "security_level": "standard"
    }'
    
    # Launch 10 concurrent requests
    local pids=()
    for i in {1..10}; do
        (
            response=$(make_request "POST" "/api/v1/devices" "$device_data")
            http_code=$(echo "$response" | tail -n1)
            echo "Concurrent request $i: HTTP $http_code"
        ) &
        pids+=($!)
    done
    
    # Wait for all background processes
    for pid in "${pids[@]}"; do
        wait $pid
    done
    
    log_success "Concurrent requests completed"
}

test_rate_limiting() {
    log_test_start "Rate Limiting"
    
    # Make rapid requests to trigger rate limiting
    local auth_data='{
        "device_id": "rate-limit-test",
        "device_secret": "test_secret",
        "auth_type": "secret_key"
    }'
    
    local rate_limited=0
    for i in {1..6}; do
        response=$(make_request "POST" "/api/v1/devices/auth" "$auth_data")
        http_code=$(echo "$response" | tail -n1)
        
        if [ "$http_code" = "429" ]; then
            rate_limited=1
            break
        fi
        sleep 0.1
    done
    
    if [ $rate_limited -eq 1 ]; then
        log_test_result 0 "Rate Limiting"
    else
        log_test_result 1 "Rate Limiting (not triggered)"
    fi
}

# Error Handling Tests
test_error_handling() {
    log_test_start "Error Handling"
    
    # Test 404 error
    response=$(make_request "GET" "/api/v1/devices/nonexistent-device")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "404" ]; then
        log_test_result 0 "404 Error Handling"
    else
        log_test_result 1 "404 Error Handling (HTTP $http_code, expected 404)"
    fi
    
    # Test 405 method not allowed
    response=$(curl -s -w "\n%{http_code}" -X PUT "$DEVICE_SERVICE_URL/api/v1/devices")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "405" ]; then
        log_test_result 0 "405 Error Handling"
    else
        log_test_result 1 "405 Error Handling (HTTP $http_code, expected 405)"
    fi
    
    # Test invalid JSON
    response=$(curl -s -w "\n%{http_code}" -X POST \
               -H "Content-Type: application/json" \
               -d "invalid json" \
               "$DEVICE_SERVICE_URL/api/v1/devices")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "400" ]; then
        log_test_result 0 "Invalid JSON Error Handling"
    else
        log_test_result 1 "Invalid JSON Error Handling (HTTP $http_code, expected 400)"
    fi
}

# Integration Tests
test_end_to_end_workflow() {
    log_test_start "End-to-End Workflow"
    
    # Setup: Register and authenticate device
    test_device_registration
    test_device_authentication
    
    if [ $? -eq 0 ] && [ -n "$TEST_DEVICE_ID" ]; then
        # Execute command
        test_send_device_command
        
        # Check device status
        sleep 2
        test_get_device
        
        # List devices
        test_list_devices
        
        log_success "End-to-End workflow completed successfully"
    else
        log_test_result 1 "End-to-End Workflow (setup failed)"
    fi
}

# Main execution
main() {
    echo "========================================"
    echo "Device Service Smoke Tests"
    echo "========================================"
    echo "Service URL: $DEVICE_SERVICE_URL"
    echo "Auth Service URL: $AUTH_SERVICE_URL"
    echo "Test User ID: $TEST_USER_ID"
    echo "Timeout: ${TIMEOUT}s"
    echo ""
    
    # Check if jq is available
    if ! command -v jq >/dev/null 2>&1; then
        log_error "jq is required for JSON parsing. Please install jq."
        exit 1
    fi
    
    # Check if services are available
    if ! wait_for_service "Device Service" "$DEVICE_SERVICE_URL"; then
        exit 1
    fi
    
    if ! wait_for_service "Auth Service" "$AUTH_SERVICE_URL"; then
        log_warning "Auth service not available, some tests may fail"
    fi
    
    # Setup test data
    setup_test_data
    
    # Run tests
    local tests=(
        "test_health_check"
        "test_detailed_health_check"
        "test_device_registration"
        "test_device_registration_validation"
        "test_device_duplicate_serial"
        "test_device_authentication"
        "test_device_authentication_invalid"
        "test_get_device"
        "test_update_device"
        "test_list_devices"
        "test_list_devices_with_filters"
        "test_send_device_command"
        "test_bulk_command"
        "test_register_smart_frame"
        "test_frame_display_control"
        "test_frame_sync"
        "test_concurrent_requests"
        "test_rate_limiting"
        "test_error_handling"
        "test_end_to_end_workflow"
    )
    
    local passed=0
    local total=0
    
    for test in "${tests[@]}"; do
        echo ""
        $test
        if [ $? -eq 0 ]; then
            ((passed++))
        fi
        ((total++))
    done
    
    # Cleanup
    cleanup_test_data
    
    # Summary
    echo ""
    echo "========================================"
    echo "Test Summary"
    echo "========================================"
    echo "Total Tests: $total"
    echo "Passed: $passed"
    echo "Failed: $((total - passed))"
    echo "Success Rate: $(( passed * 100 / total ))%"
    
    if [ $passed -eq $total ]; then
        echo ""
        log_success "All smoke tests passed! ✓"
        exit 0
    else
        echo ""
        log_error "Some smoke tests failed! ✗"
        exit 1
    fi
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
