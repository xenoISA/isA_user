from microservices.auth_service.api_key_repository import (
    api_key_matches_project,
    build_api_key_metadata,
    clean_api_key_for_listing,
)


def test_legacy_api_key_metadata_defaults_to_organization_owner():
    metadata = build_api_key_metadata(
        {
            "permissions": ["read:data"],
            "created_by": "usr_1",
        }
    )

    assert metadata == {
        "project_id": None,
        "owner_type": "organization",
        "service_account_id": None,
        "scopes": ["read:data"],
        "ip_allowlist": [],
        "rate_limits": {},
        "spend_limit": None,
        "created_by": "usr_1",
        "expires_at": None,
    }


def test_project_scoped_metadata_preserves_service_account_fields():
    metadata = build_api_key_metadata(
        {
            "project_id": "proj_1",
            "owner_type": "service_account",
            "service_account_id": "sa_1",
            "scopes": ["models.invoke"],
            "ip_allowlist": ["10.0.0.1"],
            "rate_limits": {"requests_per_minute": 120},
            "spend_limit": 25.5,
            "expires_at": "2026-06-01T00:00:00+00:00",
        }
    )

    assert metadata["project_id"] == "proj_1"
    assert metadata["owner_type"] == "service_account"
    assert metadata["service_account_id"] == "sa_1"
    assert metadata["scopes"] == ["models.invoke"]
    assert metadata["ip_allowlist"] == ["10.0.0.1"]
    assert metadata["rate_limits"] == {"requests_per_minute": 120}
    assert metadata["spend_limit"] == 25.5
    assert metadata["expires_at"] == "2026-06-01T00:00:00+00:00"


def test_clean_api_key_for_listing_never_exposes_secret_material():
    cleaned = clean_api_key_for_listing(
        {
            "key_id": "key_1",
            "name": "Project key",
            "api_key": "isa_plain_secret",
            "key_hash": "abcdef1234567890",
            "project_id": "proj_1",
            "owner_type": "service_account",
            "service_account_id": "sa_1",
            "scopes": ["models.invoke"],
            "ip_allowlist": ["10.0.0.1"],
            "rate_limits": {"requests_per_minute": 60},
            "spend_limit": 10,
        }
    )

    assert "api_key" not in cleaned
    assert "key_hash" not in cleaned
    assert cleaned["key_preview"] == "isa_...34567890"
    assert cleaned["project_id"] == "proj_1"
    assert cleaned["owner_type"] == "service_account"
    assert cleaned["service_account_id"] == "sa_1"
    assert cleaned["scopes"] == ["models.invoke"]
    assert cleaned["ip_allowlist"] == ["10.0.0.1"]
    assert cleaned["rate_limits"] == {"requests_per_minute": 60}
    assert cleaned["spend_limit"] == 10


def test_api_key_matches_project_only_when_filter_matches_scope():
    assert api_key_matches_project({"project_id": "proj_1"}, "proj_1") is True
    assert api_key_matches_project({"project_id": "proj_1"}, "proj_2") is False
    assert api_key_matches_project({"project_id": None}, "proj_1") is False
    assert api_key_matches_project({"project_id": None}, None) is True
