#!/bin/bash

# GDPR Compliance Test Script
# Test user data control features

BASE_URL="http://localhost:8226"
TEST_USER="gdpr_test_user_$(date +%s)"

echo "=========================================="
echo "GDPR Compliance Test Script"
echo "Test User: $TEST_USER"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test 1: Create some test data
echo "Test 1: Create Test Data"
echo "Creating compliance checks for test user..."
for i in {1..3}; do
    curl -s -X POST "${BASE_URL}/api/v1/compliance/check" \
      -H "Content-Type: application/json" \
      -d "{
        \"user_id\": \"${TEST_USER}\",
        \"content_type\": \"text\",
        \"content\": \"Test message ${i}\",
        \"check_types\": [\"content_moderation\"]
      }" > /dev/null
done
echo -e "${GREEN}✓ Created test data${NC}"
echo ""

# Test 2: Get Data Summary (GDPR Article 15)
echo "Test 2: Get Data Summary (GDPR Article 15 - Right to Access)"
response=$(curl -s "${BASE_URL}/api/v1/compliance/user/${TEST_USER}/data-summary")
echo "Response: $response"
if echo "$response" | grep -q '"user_id"'; then
    echo -e "${GREEN}✓ Data summary accessible${NC}"
else
    echo -e "${RED}✗ Data summary failed${NC}"
fi
echo ""

# Test 3: Export Data as JSON (GDPR Article 20)
echo "Test 3: Export Data as JSON (GDPR Article 20 - Data Portability)"
response=$(curl -s "${BASE_URL}/api/v1/compliance/user/${TEST_USER}/data-export?format=json")
echo "Response (truncated): $(echo $response | cut -c1-200)..."
if echo "$response" | grep -q '"export_type":"gdpr_data_export"'; then
    echo -e "${GREEN}✓ JSON export working${NC}"
else
    echo -e "${RED}✗ JSON export failed${NC}"
fi
echo ""

# Test 4: Export Data as CSV
echo "Test 4: Export Data as CSV"
response=$(curl -s "${BASE_URL}/api/v1/compliance/user/${TEST_USER}/data-export?format=csv")
echo "Response (first line): $(echo "$response" | head -n 1)"
if echo "$response" | grep -q "check_id"; then
    echo -e "${GREEN}✓ CSV export working${NC}"
else
    echo -e "${RED}✗ CSV export failed${NC}"
fi
echo ""

# Test 5: Get Audit Log (GDPR Article 30)
echo "Test 5: Get Audit Log (GDPR Article 30 - Processing Records)"
response=$(curl -s "${BASE_URL}/api/v1/compliance/user/${TEST_USER}/audit-log")
echo "Response: $response"
if echo "$response" | grep -q '"audit_entries"'; then
    echo -e "${GREEN}✓ Audit log accessible${NC}"
else
    echo -e "${RED}✗ Audit log failed${NC}"
fi
echo ""

# Test 6: Consent Management (GDPR Article 7)
echo "Test 6: Consent Management (GDPR Article 7 - Consent)"
echo "Revoking analytics consent..."
response=$(curl -s -X POST "${BASE_URL}/api/v1/compliance/user/${TEST_USER}/consent?consent_type=analytics&granted=false")
echo "Response: $response"
if echo "$response" | grep -q '"granted":false'; then
    echo -e "${GREEN}✓ Consent revocation working${NC}"
else
    echo -e "${RED}✗ Consent revocation failed${NC}"
fi
echo ""

# Test 7: Delete User Data (GDPR Article 17) - LAST TEST
echo "Test 7: Delete User Data (GDPR Article 17 - Right to Erasure)"
echo -e "${YELLOW}⚠ This will permanently delete test data${NC}"
response=$(curl -s -X DELETE "${BASE_URL}/api/v1/compliance/user/${TEST_USER}/data?confirmation=CONFIRM_DELETE")
echo "Response: $response"
if echo "$response" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✓ Data deletion working${NC}"
    deleted=$(echo "$response" | grep -oP '"deleted_records":\K[0-9]+' || echo "0")
    echo "  Deleted records: $deleted"
else
    echo -e "${RED}✗ Data deletion failed${NC}"
fi
echo ""

# Test 8: Verify Deletion
echo "Test 8: Verify Data Deletion"
response=$(curl -s "${BASE_URL}/api/v1/compliance/user/${TEST_USER}/data-summary")
echo "Response: $response"
if echo "$response" | grep -q '"total_records":0'; then
    echo -e "${GREEN}✓ Data successfully deleted${NC}"
else
    echo -e "${YELLOW}⚠ Some data may still exist${NC}"
fi
echo ""

echo "=========================================="
echo "GDPR Compliance Tests Complete"
echo "=========================================="

