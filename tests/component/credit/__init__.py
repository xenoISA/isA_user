"""
Credit Service Component Tests

Component tests for credit_service testing the service class with mocked dependencies.
Following TDD principles with comprehensive coverage of all business rules.

Structure:
- conftest.py: Fixtures and mocks for credit service testing
- test_credit_service_component.py: 80 component tests covering all business rules

Test Coverage:
1. Account Rules (BR-ACC-001 to BR-ACC-010) - 10 tests
2. Allocation Rules (BR-ALC-001 to BR-ALC-010) - 10 tests
3. Consumption Rules with FIFO (BR-CON-001 to BR-CON-010) - 15 tests
4. Expiration Rules (BR-EXP-001 to BR-EXP-010) - 10 tests
5. Transfer Rules (BR-TRF-001 to BR-TRF-010) - 10 tests
6. Campaign Rules (BR-CMP-001 to BR-CMP-010) - 10 tests
7. Edge Cases (EC-001 to EC-015) - 15 tests

Markers:
- @pytest.mark.component: Component test marker
- @pytest.mark.asyncio: Async test marker

Usage:
    pytest tests/component/credit -v
    pytest tests/component/credit -k "test_account" -v
"""
