"""
Event Service Component Golden Tests

This package contains component-level golden tests for the Event Service.
Golden tests document CURRENT behavior with mocked dependencies.

Test Files:
    - test_event_api_golden.py: API endpoint tests with TestClient
    - test_event_integration_golden.py: Service layer tests with mocked repository
    - mocks.py: Mock implementations for testing

Usage:
    # Run all event service golden tests
    pytest tests/component/golden/event_service/ -v

    # Run API tests only
    pytest tests/component/golden/event_service/test_event_api_golden.py -v

    # Run integration tests only
    pytest tests/component/golden/event_service/test_event_integration_golden.py -v
"""
