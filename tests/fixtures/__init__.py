"""
Shared Test Fixtures

Centralized factories, generators, and mock responses
used across all test layers.

Structure:
    - common.py: Base ID generators, timestamps
    - generators.py: Random data generators
    - {service}_fixtures.py: Per-service factories
"""

# Common utilities
from .common import (
    make_user_id,
    make_device_id,
    make_org_id,
    make_email,
    make_timestamp,
)

# Random generators
from .generators import (
    random_string,
    random_email,
    random_phone,
    random_user_ids,
    random_amount,
)

# Account service fixtures
from .account_fixtures import (
    make_account,
    make_account_ensure_request,
    make_account_update_request,
    make_preferences_update,
)

# Album service fixtures
from .album_fixtures import (
    make_album_id,
    make_photo_id,
    make_album,
    make_album_create_request,
    make_album_update_request,
    make_add_photos_request,
    make_remove_photos_request,
    make_album_photo,
)

# Audit service fixtures
from .audit_fixtures import (
    make_event_id,
    make_audit_event,
    make_audit_event_request,
    make_audit_query_request,
    make_security_alert_request,
    make_compliance_report_request,
)

# Auth service fixtures
from .auth_fixtures import (
    make_api_key_id,
    make_api_key,
    make_token_verification_request,
    make_dev_token_request,
    make_token_pair_request,
    make_refresh_token_request,
    make_api_key_verification_request,
    make_api_key_create_request,
    make_device_registration_request,
    make_device_auth_request,
    make_registration_request,
    make_registration_verify_request,
)

# Legacy exports (for backwards compatibility)
make_user = make_account  # Alias
