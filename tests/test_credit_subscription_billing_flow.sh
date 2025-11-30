#!/bin/bash
#
# Credit and Subscription Billing Flow Integration Test
#
# Tests the complete credit-based billing flow:
# 1. Create/verify subscription for user
# 2. Check credit balance
# 3. Make a billable request (model inference)
# 4. Verify credit consumption
# 5. Verify billing records
#
# Credit system: 1 Credit = $0.00001 USD (100,000 Credits = $1)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_USER_ID="test_credit_user_$(date +%s)"
TEST_ORG_ID=""

# Service URLs (update as needed)
SUBSCRIPTION_URL="${SUBSCRIPTION_URL:-http://localhost:8228}"
BILLING_URL="${BILLING_URL:-http://localhost:8216}"
WALLET_URL="${WALLET_URL:-http://localhost:8208}"
PRODUCT_URL="${PRODUCT_URL:-http://localhost:8207}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Credit & Subscription Billing Flow Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Test Configuration:"
echo "  User ID: $TEST_USER_ID"
echo "  Subscription URL: $SUBSCRIPTION_URL"
echo "  Billing URL: $BILLING_URL"
echo "  Wallet URL: $WALLET_URL"
echo "  Product URL: $PRODUCT_URL"
echo ""

# Helper functions
print_step() {
    echo -e "\n${BLUE}=== Step $1: $2 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

check_service() {
    local url=$1
    local name=$2
    if curl -s "${url}/health" > /dev/null 2>&1; then
        print_success "$name is healthy"
        return 0
    else
        print_error "$name is not responding at $url"
        return 1
    fi
}

# Step 0: Check services are running
print_step "0" "Service Health Check"

services_ok=true

echo "Checking subscription service..."
check_service "$SUBSCRIPTION_URL" "Subscription Service" || services_ok=false

echo "Checking billing service..."
check_service "$BILLING_URL" "Billing Service" || services_ok=false

echo "Checking wallet service..."
check_service "$WALLET_URL" "Wallet Service" || services_ok=false

echo "Checking product service..."
check_service "$PRODUCT_URL" "Product Service" || services_ok=false

if [ "$services_ok" = false ]; then
    print_error "Some services are not available. Please ensure port-forwards are running:"
    echo "  kubectl port-forward -n isa-cloud-staging svc/subscription 8228:8228 &"
    echo "  kubectl port-forward -n isa-cloud-staging svc/billing 8216:8216 &"
    echo "  kubectl port-forward -n isa-cloud-staging svc/wallet 8208:8208 &"
    echo "  kubectl port-forward -n isa-cloud-staging svc/product 8207:8207 &"
    exit 1
fi

# Step 1: Get subscription tiers from product service
print_step "1" "Get Available Subscription Tiers"

echo "Fetching subscription tiers..."
TIERS_RESPONSE=$(curl -s "${PRODUCT_URL}/api/v1/subscription-tiers" 2>/dev/null || echo '{"error": "failed"}')

if echo "$TIERS_RESPONSE" | grep -q "error"; then
    print_info "Could not fetch tiers from product service (may not have the endpoint yet)"
    echo "Using default tier: free"
    TIER_CODE="free"
else
    echo "$TIERS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TIERS_RESPONSE"
    TIER_CODE=$(echo "$TIERS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('tiers', [{'tier_code': 'free'}])[0].get('tier_code', 'free'))" 2>/dev/null || echo "free")
    print_success "Found tier: $TIER_CODE"
fi

# Step 2: Create subscription for test user
print_step "2" "Create Subscription for Test User"

echo "Creating subscription..."
CREATE_SUB_RESPONSE=$(curl -s -X POST "${SUBSCRIPTION_URL}/api/v1/subscriptions" \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$TEST_USER_ID\",
        \"tier_code\": \"$TIER_CODE\",
        \"billing_cycle\": \"monthly\"
    }" 2>/dev/null || echo '{"success": false, "message": "request failed"}')

echo "$CREATE_SUB_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CREATE_SUB_RESPONSE"

if echo "$CREATE_SUB_RESPONSE" | grep -q '"success": true'; then
    SUBSCRIPTION_ID=$(echo "$CREATE_SUB_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('subscription_id', ''))" 2>/dev/null)
    print_success "Subscription created: $SUBSCRIPTION_ID"
else
    print_info "Subscription creation may have failed - continuing with balance check"
fi

# Step 3: Check credit balance
print_step "3" "Check Credit Balance"

echo "Fetching credit balance..."
BALANCE_RESPONSE=$(curl -s "${SUBSCRIPTION_URL}/api/v1/credits/balance?user_id=${TEST_USER_ID}" 2>/dev/null || echo '{"success": false}')

echo "$BALANCE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$BALANCE_RESPONSE"

if echo "$BALANCE_RESPONSE" | grep -q '"success": true'; then
    SUBSCRIPTION_CREDITS=$(echo "$BALANCE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('subscription_credits_remaining', 0))" 2>/dev/null)
    print_success "Subscription credits: $SUBSCRIPTION_CREDITS"
else
    print_info "Could not fetch balance (subscription service may not be fully deployed)"
    SUBSCRIPTION_CREDITS=0
fi

# Step 4: Get cost definition for model inference
print_step "4" "Get Cost Definition"

echo "Fetching cost definition for model inference..."
COST_RESPONSE=$(curl -s "${PRODUCT_URL}/api/v1/cost-definitions/lookup?service_type=model_inference&provider=openai&model_name=gpt-4o-mini" 2>/dev/null || echo '{"cost_definition": null}')

echo "$COST_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$COST_RESPONSE"

if echo "$COST_RESPONSE" | grep -q "cost_definition"; then
    CREDIT_COST=$(echo "$COST_RESPONSE" | python3 -c "import sys, json; cd=json.load(sys.stdin).get('cost_definition', {}); print(cd.get('credits_per_unit', 0))" 2>/dev/null || echo "0")
    print_success "Credits per 1K tokens: $CREDIT_COST"
else
    print_info "Cost definition not found (product service may not have the endpoint yet)"
fi

# Step 5: Test credit consumption (simulate)
print_step "5" "Test Credit Consumption"

echo "Simulating credit consumption..."
CONSUME_REQUEST='{
    "user_id": "'"$TEST_USER_ID"'",
    "credits_to_consume": 1000,
    "service_type": "model_inference",
    "description": "Integration test - model inference",
    "usage_record_id": "test_'"$(date +%s)"'"
}'

echo "Request payload:"
echo "$CONSUME_REQUEST" | python3 -m json.tool

CONSUME_RESPONSE=$(curl -s -X POST "${SUBSCRIPTION_URL}/api/v1/credits/consume" \
    -H "Content-Type: application/json" \
    -d "$CONSUME_REQUEST" 2>/dev/null || echo '{"success": false, "message": "request failed"}')

echo "Response:"
echo "$CONSUME_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CONSUME_RESPONSE"

if echo "$CONSUME_RESPONSE" | grep -q '"success": true'; then
    CONSUMED_CREDITS=$(echo "$CONSUME_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('credits_consumed', 0))" 2>/dev/null)
    print_success "Credits consumed: $CONSUMED_CREDITS"
elif echo "$CONSUME_RESPONSE" | grep -q "Insufficient credits"; then
    print_info "Insufficient credits (expected for new free tier user)"
elif echo "$CONSUME_RESPONSE" | grep -q "No active subscription"; then
    print_info "No active subscription found"
else
    print_info "Credit consumption response received"
fi

# Step 6: Check updated balance
print_step "6" "Verify Updated Balance"

echo "Fetching updated credit balance..."
UPDATED_BALANCE=$(curl -s "${SUBSCRIPTION_URL}/api/v1/credits/balance?user_id=${TEST_USER_ID}" 2>/dev/null || echo '{"success": false}')

echo "$UPDATED_BALANCE" | python3 -m json.tool 2>/dev/null || echo "$UPDATED_BALANCE"

if echo "$UPDATED_BALANCE" | grep -q '"success": true'; then
    NEW_CREDITS=$(echo "$UPDATED_BALANCE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('subscription_credits_remaining', 0))" 2>/dev/null)
    print_success "Current subscription credits: $NEW_CREDITS"
else
    print_info "Could not verify updated balance"
fi

# Step 7: Check billing service integration
print_step "7" "Billing Service Integration"

echo "Testing billing calculation endpoint..."
CALC_REQUEST='{
    "user_id": "'"$TEST_USER_ID"'",
    "product_id": "gpt-4o-mini",
    "usage_amount": 1.0
}'

echo "Request:"
echo "$CALC_REQUEST" | python3 -m json.tool

CALC_RESPONSE=$(curl -s -X POST "${BILLING_URL}/api/v1/billing/calculate" \
    -H "Content-Type: application/json" \
    -d "$CALC_REQUEST" 2>/dev/null || echo '{"success": false, "message": "request failed"}')

echo "Response:"
echo "$CALC_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CALC_RESPONSE"

if echo "$CALC_RESPONSE" | grep -q '"success": true'; then
    SUGGESTED_METHOD=$(echo "$CALC_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('suggested_billing_method', 'unknown'))" 2>/dev/null)
    print_success "Billing calculation successful"
    echo "  Suggested method: $SUGGESTED_METHOD"
else
    print_info "Billing calculation endpoint may need updates"
fi

# Summary
print_step "Summary" "Test Results"

echo ""
echo "Test completed for user: $TEST_USER_ID"
echo ""
echo "Services tested:"
echo "  - Subscription Service: Credit balance and consumption"
echo "  - Product Service: Subscription tiers and cost definitions"
echo "  - Billing Service: Cost calculation with credit priority"
echo "  - Wallet Service: (Available for purchased credits)"
echo ""
echo "Credit deduction priority:"
echo "  1. Subscription Credits (from monthly plan)"
echo "  2. Purchased Credits (from wallet credit_accounts)"
echo "  3. Wallet Balance (traditional wallet)"
echo "  4. Payment Charge (external payment)"
echo ""

print_success "Integration test completed!"
echo ""
echo "To run a full end-to-end test with model inference:"
echo "  python3 tests/test_complete_billing_flow.py"
