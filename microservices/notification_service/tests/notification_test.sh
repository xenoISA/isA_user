#!/bin/bash

# Notification Service Testing Script
# Tests notification sending, templates, in-app notifications, and push subscriptions

BASE_URL="http://localhost"
API_BASE="${BASE_URL}/api/v1/notifications"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# JSON parsing function (works with or without jq)
json_value() {
    local json="$1"
    local key="$2"

    if command -v jq &> /dev/null; then
        echo "$json" | jq -r ".$key"
    else
        # Fallback to python
        echo "$json" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$key', ''))"
    fi
}

# Pretty print JSON (works with or without jq)
pretty_json() {
    local json="$1"

    if command -v jq &> /dev/null; then
        echo "$json" | jq '.'
    else
        echo "$json" | python3 -m json.tool 2>/dev/null || echo "$json"
    fi
}

echo "======================================================================"
echo "Notification Service Tests"
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


# Test 1: Create Email Template
print_section "Test 1: Create Email Notification Template"
echo "POST ${API_BASE}/templates"
CREATE_TEMPLATE_PAYLOAD='{
  "name": "Welcome Email Template",
  "description": "Welcome email for new users",
  "type": "email",
  "subject": "Welcome to {{app_name}}!",
  "content": "Hello {{user_name}}, welcome to our platform!",
  "html_content": "<h1>Welcome {{user_name}}</h1><p>Thank you for joining {{app_name}}!</p>",
  "variables": ["user_name", "app_name"],
  "metadata": {
    "category": "onboarding"
  }
}'
echo "Request Body:"
pretty_json "$CREATE_TEMPLATE_PAYLOAD"

TEMPLATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/templates" \
  -H "Content-Type: application/json" \
  -d "$CREATE_TEMPLATE_PAYLOAD")
HTTP_CODE=$(echo "$TEMPLATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TEMPLATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

TEMPLATE_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    TEMPLATE_ID=$(json_value "$RESPONSE_BODY" "template.template_id")
    if [ -n "$TEMPLATE_ID" ] && [ "$TEMPLATE_ID" != "null" ]; then
        print_result 0 "Email template created successfully"
        echo -e "${YELLOW}Template ID: ${TEMPLATE_ID}${NC}"
    else
        print_result 1 "Template creation returned success but no template_id found"
    fi
else
    print_result 1 "Failed to create email template"
fi

# Test 2: Create In-App Template
print_section "Test 2: Create In-App Notification Template"
echo "POST ${API_BASE}/templates"
IN_APP_TEMPLATE_PAYLOAD='{
  "name": "System Alert Template",
  "description": "System notification template",
  "type": "in_app",
  "subject": "{{alert_type}} Alert",
  "content": "{{message}}",
  "variables": ["alert_type", "message"],
  "metadata": {
    "category": "system"
  }
}'
echo "Request Body:"
pretty_json "$IN_APP_TEMPLATE_PAYLOAD"

IN_APP_TEMPLATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/templates" \
  -H "Content-Type: application/json" \
  -d "$IN_APP_TEMPLATE_PAYLOAD")
HTTP_CODE=$(echo "$IN_APP_TEMPLATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$IN_APP_TEMPLATE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

IN_APP_TEMPLATE_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    IN_APP_TEMPLATE_ID=$(json_value "$RESPONSE_BODY" "template.template_id")
    if [ -n "$IN_APP_TEMPLATE_ID" ] && [ "$IN_APP_TEMPLATE_ID" != "null" ]; then
        print_result 0 "In-app template created successfully"
        echo -e "${YELLOW}In-App Template ID: ${IN_APP_TEMPLATE_ID}${NC}"
    else
        print_result 1 "In-app template creation returned success but no template_id found"
    fi
else
    print_result 1 "Failed to create in-app template"
fi

# Test 3: List Templates
print_section "Test 3: List All Templates"
echo "GET ${API_BASE}/templates?limit=10"
LIST_TEMPLATES_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/templates?limit=10")
HTTP_CODE=$(echo "$LIST_TEMPLATES_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_TEMPLATES_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Templates listed successfully"
else
    print_result 1 "Failed to list templates"
fi

# Test 4: Get Template by ID
if [ -n "$TEMPLATE_ID" ] && [ "$TEMPLATE_ID" != "null" ]; then
    print_section "Test 4: Get Template by ID"
    echo "GET ${API_BASE}/templates/${TEMPLATE_ID}"
    
    GET_TEMPLATE_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/templates/${TEMPLATE_ID}")
    HTTP_CODE=$(echo "$GET_TEMPLATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$GET_TEMPLATE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Template retrieved successfully"
    else
        print_result 1 "Failed to get template"
    fi
else
    echo -e "${YELLOW}Skipping Test 4: No template ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 5: Update Template
if [ -n "$TEMPLATE_ID" ] && [ "$TEMPLATE_ID" != "null" ]; then
    print_section "Test 5: Update Template"
    echo "PUT ${API_BASE}/templates/${TEMPLATE_ID}"
    UPDATE_TEMPLATE_PAYLOAD='{
      "description": "Updated welcome email template for new users",
      "metadata": {
        "category": "onboarding",
        "version": "2.0"
      }
    }'
    echo "Request Body:"
    pretty_json "$UPDATE_TEMPLATE_PAYLOAD"
    
    UPDATE_TEMPLATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_BASE}/templates/${TEMPLATE_ID}" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_TEMPLATE_PAYLOAD")
    HTTP_CODE=$(echo "$UPDATE_TEMPLATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$UPDATE_TEMPLATE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Template updated successfully"
    else
        print_result 1 "Failed to update template"
    fi
else
    echo -e "${YELLOW}Skipping Test 5: No template ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 6: Send Email Notification (without template)
print_section "Test 6: Send Email Notification (Direct)"
echo "POST ${API_BASE}/send"
SEND_EMAIL_PAYLOAD='{
  "type": "email",
  "recipient_email": "test@example.com",
  "subject": "Test Email Notification",
  "content": "This is a test email notification from the notification service.",
  "html_content": "<h2>Test Email</h2><p>This is a <strong>test email notification</strong> from the notification service.</p>",
  "priority": "high",
  "tags": ["test", "email"],
  "metadata": {
    "source": "test_script"
  }
}'
echo "Request Body:"
pretty_json "$SEND_EMAIL_PAYLOAD"

SEND_EMAIL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/send" \
  -H "Content-Type: application/json" \
  -d "$SEND_EMAIL_PAYLOAD")
HTTP_CODE=$(echo "$SEND_EMAIL_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SEND_EMAIL_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

NOTIFICATION_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    NOTIFICATION_ID=$(json_value "$RESPONSE_BODY" "notification.notification_id")
    if [ -n "$NOTIFICATION_ID" ] && [ "$NOTIFICATION_ID" != "null" ]; then
        print_result 0 "Email notification sent successfully"
        echo -e "${YELLOW}Notification ID: ${NOTIFICATION_ID}${NC}"
    else
        print_result 1 "Email notification returned success but no notification_id found"
    fi
else
    print_result 1 "Failed to send email notification"
fi

# Test 7: Send In-App Notification
print_section "Test 7: Send In-App Notification"
echo "POST ${API_BASE}/send"
SEND_IN_APP_PAYLOAD='{
  "type": "in_app",
  "recipient_id": "user_test_123",
  "subject": "New Feature Available",
  "content": "Check out our new feature in the dashboard!",
  "priority": "normal",
  "metadata": {
    "action_url": "/dashboard/features"
  }
}'
echo "Request Body:"
pretty_json "$SEND_IN_APP_PAYLOAD"

SEND_IN_APP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/send" \
  -H "Content-Type: application/json" \
  -d "$SEND_IN_APP_PAYLOAD")
HTTP_CODE=$(echo "$SEND_IN_APP_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SEND_IN_APP_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

IN_APP_NOTIFICATION_ID=""
if [ "$HTTP_CODE" = "200" ]; then
    IN_APP_NOTIFICATION_ID=$(json_value "$RESPONSE_BODY" "notification.notification_id")
    if [ -n "$IN_APP_NOTIFICATION_ID" ] && [ "$IN_APP_NOTIFICATION_ID" != "null" ]; then
        print_result 0 "In-app notification sent successfully"
        echo -e "${YELLOW}In-App Notification ID: ${IN_APP_NOTIFICATION_ID}${NC}"
    else
        print_result 1 "In-app notification returned success but no notification_id found"
    fi
else
    print_result 1 "Failed to send in-app notification"
fi

# Test 8: Send Notification with Template
if [ -n "$TEMPLATE_ID" ] && [ "$TEMPLATE_ID" != "null" ]; then
    print_section "Test 8: Send Notification Using Template"
    echo "POST ${API_BASE}/send"
    SEND_WITH_TEMPLATE_PAYLOAD="{
      \"type\": \"email\",
      \"recipient_email\": \"newuser@example.com\",
      \"template_id\": \"${TEMPLATE_ID}\",
      \"variables\": {
        \"user_name\": \"John Doe\",
        \"app_name\": \"iaPro Platform\"
      },
      \"priority\": \"high\"
    }"
    echo "Request Body:"
    pretty_json "$SEND_WITH_TEMPLATE_PAYLOAD"
    
    SEND_TEMPLATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/send" \
      -H "Content-Type: application/json" \
      -d "$SEND_WITH_TEMPLATE_PAYLOAD")
    HTTP_CODE=$(echo "$SEND_TEMPLATE_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$SEND_TEMPLATE_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Notification sent using template"
    else
        print_result 1 "Failed to send notification with template"
    fi
else
    echo -e "${YELLOW}Skipping Test 8: No template ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 9: List Notifications
print_section "Test 9: List All Notifications"
echo "GET ${API_BASE}?limit=10"
LIST_NOTIFICATIONS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}?limit=10")
HTTP_CODE=$(echo "$LIST_NOTIFICATIONS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_NOTIFICATIONS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Notifications listed successfully"
else
    print_result 1 "Failed to list notifications"
fi

# Test 10: List User's In-App Notifications
print_section "Test 10: List User's In-App Notifications"
TEST_USER_ID="user_test_123"
echo "GET ${API_BASE}/in-app/${TEST_USER_ID}?limit=10"
LIST_USER_NOTIFICATIONS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/in-app/${TEST_USER_ID}?limit=10")
HTTP_CODE=$(echo "$LIST_USER_NOTIFICATIONS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$LIST_USER_NOTIFICATIONS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "User in-app notifications listed successfully"
else
    print_result 1 "Failed to list user in-app notifications"
fi

# Test 11: Get Unread Count
print_section "Test 11: Get Unread Notification Count"
echo "GET ${API_BASE}/in-app/${TEST_USER_ID}/unread-count"
UNREAD_COUNT_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/in-app/${TEST_USER_ID}/unread-count")
HTTP_CODE=$(echo "$UNREAD_COUNT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$UNREAD_COUNT_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    UNREAD_COUNT=$(json_value "$RESPONSE_BODY" "unread_count")
    print_result 0 "Unread count retrieved successfully"
    echo -e "${YELLOW}Unread Count: ${UNREAD_COUNT}${NC}"
else
    print_result 1 "Failed to get unread count"
fi

# Test 12: Mark Notification as Read
if [ -n "$IN_APP_NOTIFICATION_ID" ] && [ "$IN_APP_NOTIFICATION_ID" != "null" ]; then
    print_section "Test 12: Mark Notification as Read"
    echo "POST ${API_BASE}/in-app/${IN_APP_NOTIFICATION_ID}/read?user_id=${TEST_USER_ID}"
    
    MARK_READ_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/in-app/${IN_APP_NOTIFICATION_ID}/read?user_id=${TEST_USER_ID}")
    HTTP_CODE=$(echo "$MARK_READ_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$MARK_READ_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Notification marked as read"
    else
        print_result 1 "Failed to mark notification as read"
    fi
else
    echo -e "${YELLOW}Skipping Test 12: No in-app notification ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 13: Mark Notification as Archived
if [ -n "$IN_APP_NOTIFICATION_ID" ] && [ "$IN_APP_NOTIFICATION_ID" != "null" ]; then
    print_section "Test 13: Mark Notification as Archived"
    echo "POST ${API_BASE}/in-app/${IN_APP_NOTIFICATION_ID}/archive?user_id=${TEST_USER_ID}"
    
    MARK_ARCHIVED_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/in-app/${IN_APP_NOTIFICATION_ID}/archive?user_id=${TEST_USER_ID}")
    HTTP_CODE=$(echo "$MARK_ARCHIVED_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$MARK_ARCHIVED_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_result 0 "Notification marked as archived"
    else
        print_result 1 "Failed to mark notification as archived"
    fi
else
    echo -e "${YELLOW}Skipping Test 13: No in-app notification ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 14: Register Push Subscription
print_section "Test 14: Register Push Subscription"
echo "POST ${API_BASE}/push/subscribe"
PUSH_SUBSCRIBE_PAYLOAD='{
  "user_id": "user_test_123",
  "device_token": "test_device_token_abc123",
  "platform": "web",
  "endpoint": "https://fcm.googleapis.com/fcm/send/test_endpoint",
  "auth_key": "test_auth_key",
  "p256dh_key": "test_p256dh_key",
  "device_name": "Chrome Browser",
  "device_model": "Desktop",
  "app_version": "1.0.0"
}'
echo "Request Body:"
pretty_json "$PUSH_SUBSCRIBE_PAYLOAD"

PUSH_SUBSCRIBE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/push/subscribe" \
  -H "Content-Type: application/json" \
  -d "$PUSH_SUBSCRIBE_PAYLOAD")
HTTP_CODE=$(echo "$PUSH_SUBSCRIBE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$PUSH_SUBSCRIBE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Push subscription registered successfully"
else
    print_result 1 "Failed to register push subscription"
fi

# Test 15: Get User's Push Subscriptions
print_section "Test 15: Get User's Push Subscriptions"
echo "GET ${API_BASE}/push/subscriptions/${TEST_USER_ID}"
GET_SUBSCRIPTIONS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/push/subscriptions/${TEST_USER_ID}")
HTTP_CODE=$(echo "$GET_SUBSCRIPTIONS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$GET_SUBSCRIPTIONS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Push subscriptions retrieved successfully"
else
    print_result 1 "Failed to get push subscriptions"
fi

# Test 16: Batch Send Notifications
if [ -n "$TEMPLATE_ID" ] && [ "$TEMPLATE_ID" != "null" ]; then
    print_section "Test 16: Batch Send Notifications"
    echo "POST ${API_BASE}/batch"
    BATCH_SEND_PAYLOAD="{
      \"name\": \"Welcome Campaign\",
      \"template_id\": \"${TEMPLATE_ID}\",
      \"type\": \"email\",
      \"priority\": \"normal\",
      \"recipients\": [
        {
          \"email\": \"user1@example.com\",
          \"variables\": {
            \"user_name\": \"Alice\",
            \"app_name\": \"iaPro\"
          }
        },
        {
          \"email\": \"user2@example.com\",
          \"variables\": {
            \"user_name\": \"Bob\",
            \"app_name\": \"iaPro\"
          }
        },
        {
          \"email\": \"user3@example.com\",
          \"variables\": {
            \"user_name\": \"Charlie\",
            \"app_name\": \"iaPro\"
          }
        }
      ],
      \"metadata\": {
        \"campaign_id\": \"welcome_2024\"
      }
    }"
    echo "Request Body:"
    pretty_json "$BATCH_SEND_PAYLOAD"
    
    BATCH_SEND_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/batch" \
      -H "Content-Type: application/json" \
      -d "$BATCH_SEND_PAYLOAD")
    HTTP_CODE=$(echo "$BATCH_SEND_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$BATCH_SEND_RESPONSE" | sed '$d')
    
    echo "Response:"
    pretty_json "$RESPONSE_BODY"
    echo "HTTP Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        BATCH_ID=$(json_value "$RESPONSE_BODY" "batch.batch_id")
        print_result 0 "Batch notifications sent successfully"
        echo -e "${YELLOW}Batch ID: ${BATCH_ID}${NC}"
    else
        print_result 1 "Failed to send batch notifications"
    fi
else
    echo -e "${YELLOW}Skipping Test 16: No template ID available${NC}"
    ((TESTS_FAILED++))
fi

# Test 17: Get Notification Statistics
print_section "Test 17: Get Notification Statistics"
echo "GET ${API_BASE}/stats?period=all_time"
STATS_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/stats?period=all_time")
HTTP_CODE=$(echo "$STATS_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$STATS_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Notification statistics retrieved successfully"
else
    print_result 1 "Failed to get notification statistics"
fi

# Test 18: Test Email Endpoint
print_section "Test 18: Test Email Sending (Development)"
echo "POST ${API_BASE}/test/email?to=testuser@example.com&subject=Test%20Email"
TEST_EMAIL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/test/email?to=testuser@example.com&subject=Test%20Email")
HTTP_CODE=$(echo "$TEST_EMAIL_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TEST_EMAIL_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Test email sent successfully"
else
    print_result 1 "Failed to send test email"
fi

# Test 19: Test In-App Notification Endpoint
print_section "Test 19: Test In-App Notification (Development)"
echo "POST ${API_BASE}/test/in-app?user_id=test_user_456&title=Test%20Notification"
TEST_IN_APP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/test/in-app?user_id=test_user_456&title=Test%20Notification")
HTTP_CODE=$(echo "$TEST_IN_APP_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$TEST_IN_APP_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Test in-app notification created successfully"
else
    print_result 1 "Failed to create test in-app notification"
fi

# Test 20: Unsubscribe Push Notification
print_section "Test 20: Unsubscribe Push Notification"
echo "DELETE ${API_BASE}/push/unsubscribe?user_id=${TEST_USER_ID}&device_token=test_device_token_abc123"
UNSUBSCRIBE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${API_BASE}/push/unsubscribe?user_id=${TEST_USER_ID}&device_token=test_device_token_abc123")
HTTP_CODE=$(echo "$UNSUBSCRIBE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$UNSUBSCRIBE_RESPONSE" | sed '$d')

echo "Response:"
pretty_json "$RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Push subscription removed successfully"
else
    print_result 1 "Failed to unsubscribe push notification"
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
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Please review the output above.${NC}"
    exit 1
fi

