#!/bin/bash

# PCI-DSS Compliance Test Script
# Test credit card data detection

BASE_URL="http://localhost:8250"

echo "=========================================="
echo "PCI-DSS Compliance Test Script"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Test 1: Visa Card Detection
echo "Test 1: Visa Card Detection"
response=$(curl -s -X POST "${BASE_URL}/api/compliance/pci/card-data-check" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "My Visa card is 4532-1234-5678-9010",
    "user_id": "test_user"
  }')
echo "Response: $response"
if echo "$response" | grep -q '"pci_compliant":false'; then
    echo -e "${GREEN}✓ Visa detection working${NC}"
else
    echo -e "${RED}✗ Visa detection failed${NC}"
fi
echo ""

# Test 2: Mastercard Detection
echo "Test 2: Mastercard Detection"
response=$(curl -s -X POST "${BASE_URL}/api/compliance/pci/card-data-check" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Mastercard: 5412-3456-7890-1234",
    "user_id": "test_user"
  }')
echo "Response: $response"
if echo "$response" | grep -q '"type":"mastercard"'; then
    echo -e "${GREEN}✓ Mastercard detection working${NC}"
else
    echo -e "${RED}✗ Mastercard detection failed${NC}"
fi
echo ""

# Test 3: Amex Detection
echo "Test 3: American Express Detection"
response=$(curl -s -X POST "${BASE_URL}/api/compliance/pci/card-data-check" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "My Amex: 3782 822463 10005",
    "user_id": "test_user"
  }')
echo "Response: $response"
if echo "$response" | grep -q '"type":"amex"'; then
    echo -e "${GREEN}✓ Amex detection working${NC}"
else
    echo -e "${RED}✗ Amex detection failed${NC}"
fi
echo ""

# Test 4: Clean Content (No Card)
echo "Test 4: Clean Content (No Card)"
response=$(curl -s -X POST "${BASE_URL}/api/compliance/pci/card-data-check" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a normal message without card data",
    "user_id": "test_user"
  }')
echo "Response: $response"
if echo "$response" | grep -q '"pci_compliant":true'; then
    echo -e "${GREEN}✓ Clean content passed${NC}"
else
    echo -e "${RED}✗ Clean content should pass${NC}"
fi
echo ""

# Test 5: Multiple Cards
echo "Test 5: Multiple Cards Detection"
response=$(curl -s -X POST "${BASE_URL}/api/compliance/pci/card-data-check" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "I have two cards: 4532-1234-5678-9010 and 5412-3456-7890-1234",
    "user_id": "test_user"
  }')
echo "Response: $response"
card_count=$(echo "$response" | grep -o '"type"' | wc -l)
if [ "$card_count" -ge 2 ]; then
    echo -e "${GREEN}✓ Multiple cards detected (found: $card_count)${NC}"
else
    echo -e "${RED}✗ Should detect multiple cards${NC}"
fi
echo ""

echo "=========================================="
echo "PCI-DSS Tests Complete"
echo "=========================================="

