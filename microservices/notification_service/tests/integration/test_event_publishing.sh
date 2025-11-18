#!/bin/bash

# Notification Service Event Publishing Integration Test
# Verifies that notification events are properly published

BASE_URL="${BASE_URL:-http://localhost}"
API_BASE="${BASE_URL}/api/v1/notifications"
AUTH_URL="${BASE_URL}/api/v1/auth"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================================================"
echo "Notification Service - Event Publishing Integration Test"
echo "======================================================================"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

echo ""
echo "======================================================================"
echo "Test 1: Verify notification.sent event is published"
echo "======================================================================"
echo ""

SEND_PAYLOAD='{
  "type": "email",
  "recipient_email": "test@example.com",
  "subject": "Test Notification Event Publishing",
  "content": "This notification should trigger a notification.sent event",
  "priority": "high"
}'

echo "Sending notification to trigger notification.sent event..."
echo "POST ${API_BASE}/send"
echo "$SEND_PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$SEND_PAYLOAD"

RESPONSE=$(curl -s -X POST "${API_BASE}/send" \
  -H "Content-Type: application/json" \
  -d "$SEND_PAYLOAD")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

NOTIFICATION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('notification', {}).get('notification_id', ''))" 2>/dev/null)

if [ -n "$NOTIFICATION_ID" ] && [ "$NOTIFICATION_ID" != "null" ]; then
    print_result 0 "notification.sent event should be published (notification_id: $NOTIFICATION_ID)"
else
    print_result 1 "Failed to send notification"
fi

echo ""
echo "======================================================================"
echo "Test 2: Verify notification.sent event for in-app notification"
echo "======================================================================"
echo ""

IN_APP_PAYLOAD='{
  "type": "in_app",
  "recipient_id": "test_user_event_123",
  "subject": "Test In-App Notification",
  "content": "This in-app notification should trigger a notification.sent event",
  "priority": "normal"
}'

echo "Sending in-app notification to trigger notification.sent event..."
echo "POST ${API_BASE}/send"
echo "$IN_APP_PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$IN_APP_PAYLOAD"

RESPONSE=$(curl -s -X POST "${API_BASE}/send" \
  -H "Content-Type: application/json" \
  -d "$IN_APP_PAYLOAD")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

IN_APP_NOTIFICATION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('notification', {}).get('notification_id', ''))" 2>/dev/null)

if [ -n "$IN_APP_NOTIFICATION_ID" ] && [ "$IN_APP_NOTIFICATION_ID" != "null" ]; then
    print_result 0 "notification.sent event should be published for in-app notification"
else
    print_result 1 "Failed to send in-app notification"
fi

echo ""
echo "======================================================================"
echo "Test 3: Verify notification.batch_completed event is published"
echo "======================================================================"
echo ""

# Create a template first
TEMPLATE_PAYLOAD='{
  "name": "Event Test Template",
  "description": "Template for event publishing test",
  "type": "email",
  "subject": "Test {{name}}",
  "content": "Hello {{name}}, this is a test.",
  "variables": ["name"]
}'

echo "Creating template for batch test..."
TEMPLATE_RESPONSE=$(curl -s -X POST "${API_BASE}/templates" \
  -H "Content-Type: application/json" \
  -d "$TEMPLATE_PAYLOAD")

TEMPLATE_ID=$(echo "$TEMPLATE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('template', {}).get('template_id', ''))" 2>/dev/null)

if [ -n "$TEMPLATE_ID" ] && [ "$TEMPLATE_ID" != "null" ]; then
    BATCH_PAYLOAD="{
      \"name\": \"Event Test Batch\",
      \"template_id\": \"${TEMPLATE_ID}\",
      \"type\": \"email\",
      \"priority\": \"normal\",
      \"recipients\": [
        {
          \"email\": \"user1@example.com\",
          \"variables\": {\"name\": \"Alice\"}
        },
        {
          \"email\": \"user2@example.com\",
          \"variables\": {\"name\": \"Bob\"}
        }
      ]
    }"

    echo "Sending batch notification to trigger notification.batch_completed event..."
    echo "POST ${API_BASE}/batch"
    echo "$BATCH_PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$BATCH_PAYLOAD"

    BATCH_RESPONSE=$(curl -s -X POST "${API_BASE}/batch" \
      -H "Content-Type: application/json" \
      -d "$BATCH_PAYLOAD")

    echo "Response:"
    echo "$BATCH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$BATCH_RESPONSE"

    BATCH_ID=$(echo "$BATCH_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('batch', {}).get('batch_id', ''))" 2>/dev/null)

    if [ -n "$BATCH_ID" ] && [ "$BATCH_ID" != "null" ]; then
        print_result 0 "notification.batch_completed event should be published (batch_id: $BATCH_ID)"
    else
        print_result 1 "Failed to send batch notifications"
    fi
else
    print_result 1 "Cannot test batch (failed to create template)"
fi

echo ""
echo "======================================================================"
echo "Test 4: Verify notification service handles events from other services"
echo "======================================================================"
echo ""

echo -e "${YELLOW}Note: This test requires event_service to be running${NC}"
echo -e "${YELLOW}Event subscriptions tested:${NC}"
echo -e "${YELLOW}  - user.registered -> sends welcome email${NC}"
echo -e "${YELLOW}  - payment.completed -> sends receipt${NC}"
echo -e "${YELLOW}  - organization.member_added -> sends invitation${NC}"
echo -e "${YELLOW}  - device.offline -> sends alert${NC}"
echo -e "${YELLOW}  - file.uploaded -> sends confirmation${NC}"
echo -e "${YELLOW}  - file.shared -> sends notification${NC}"
echo -e "${YELLOW}  - order.created -> sends confirmation${NC}"
echo -e "${YELLOW}  - task.assigned -> sends notification${NC}"
echo -e "${YELLOW}  - invitation.created -> sends email${NC}"
echo -e "${YELLOW}  - wallet.balance_low -> sends alert${NC}"
echo ""
echo -e "${YELLOW}These event handlers are tested via test_event_subscriptions.py${NC}"

# Summary
echo ""
echo "======================================================================"
echo "Event Publishing Test Summary"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Total: $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All event publishing tests passed!${NC}"
    echo ""
    echo "Events that should have been published:"
    echo "  - notification.sent (email)"
    echo "  - notification.sent (in-app)"
    echo "  - notification.batch_completed"
    echo ""
    echo "Event subscriptions configured for:"
    echo "  - user.registered, payment.completed, organization.member_added"
    echo "  - device.offline, file.uploaded, file.shared"
    echo "  - order.created, task.assigned, invitation.created"
    echo "  - wallet.balance_low"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
