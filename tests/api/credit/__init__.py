"""
Credit Service API Tests

Layer 4: API Contract Tests with real HTTP calls.
Tests validate HTTP contracts, status codes, and response schemas.

Purpose:
- Test actual HTTP endpoints against running credit_service
- Validate request/response schemas
- Test status code contracts (200, 201, 400, 404, 422)
- Test credit allocation, consumption, campaigns, and transfers

Usage:
    pytest tests/api/credit -v
    pytest tests/api/credit -v -k "health"
    pytest tests/api/credit -v -k "allocate"
"""
