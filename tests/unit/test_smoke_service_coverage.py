from __future__ import annotations

from pathlib import Path

TARGETED_SMOKE_FILES = {
    "account_service": "test_account_smoke.py",
    "album_service": "test_album_smoke.py",
    "audit_service": "test_audit_smoke.py",
    "authorization_service": "test_authorization_smoke.py",
    "billing_service": "test_billing_smoke.py",
    "campaign_service": "test_campaign_smoke.py",
    "compliance_service": "test_compliance_smoke.py",
    "device_service": "test_device_smoke.py",
    "invitation_service": "test_invitation_smoke.py",
    "location_service": "test_location_smoke.py",
    "media_service": "test_media_smoke.py",
    "memory_service": "test_memory_smoke.py",
    "notification_service": "test_notification_smoke.py",
    "ota_service": "test_ota_smoke.py",
    "product_service": "test_product_smoke.py",
    "project_service": "test_project_smoke.py",
    "sharing_service": "test_sharing_smoke.py",
    "storage_service": "test_storage_smoke.py",
    "subscription_service": "test_subscription_smoke.py",
    "weather_service": "test_weather_smoke.py",
}


def test_every_microservice_has_a_python_smoke_test():
    repo_root = Path(__file__).resolve().parents[2]
    services = sorted(
        path.name
        for path in (repo_root / "microservices").iterdir()
        if path.is_dir() and path.name.endswith("_service")
    )

    missing = []
    for service_name in services:
        smoke_dir = repo_root / "tests" / "smoke" / service_name
        smoke_files = (
            sorted(smoke_dir.glob("test_*_smoke.py")) if smoke_dir.exists() else []
        )
        if not smoke_files:
            missing.append(service_name)

    assert not missing, f"Missing Python smoke tests for: {missing}"


def test_targeted_services_use_canonical_smoke_filenames():
    repo_root = Path(__file__).resolve().parents[2]

    missing = []
    for service_name, filename in TARGETED_SMOKE_FILES.items():
        smoke_file = repo_root / "tests" / "smoke" / service_name / filename
        if not smoke_file.exists():
            missing.append(str(smoke_file.relative_to(repo_root)))

    assert not missing, f"Missing canonical smoke files: {missing}"
