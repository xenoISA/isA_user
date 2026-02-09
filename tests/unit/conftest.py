"""
Unit Test Layer Configuration (Layer 4)

Structure:
    tests/unit/
    ├── golden/      🔒 Characterization (never modify)
    ├── services/    🆕 TDD (new features)
    ├── logic/       Pure business logic
    └── models/      Types, enums, schemas

Usage:
    pytest tests/unit -v                 # All unit tests
    pytest tests/unit/golden -v          # Only golden tests
    pytest tests/unit -m golden -v       # By marker
"""
import os
import sys

import pytest

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "golden: safety net tests - DO NOT MODIFY"
    )
