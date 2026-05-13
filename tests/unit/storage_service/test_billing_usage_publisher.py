from unittest.mock import AsyncMock

import pytest

from microservices.storage_service.events.publishers import StorageEventPublisher


@pytest.mark.asyncio
async def test_storage_upload_billing_usage_event_is_canonical():
    event_bus = AsyncMock()
    event_bus.publish_event.return_value = True
    publisher = StorageEventPublisher(event_bus)

    result = await publisher.publish_billing_usage_recorded(
        user_id="user_123",
        organization_id="org_123",
        product_id="minio_storage",
        usage_amount=4096,
        unit_type="byte",
        operation_type="storage_bytes_written",
        resource_name="file_123",
        usage_details={"file_id": "file_123"},
        idempotency_key="storage:upload:file_123",
    )

    assert result is True
    event = event_bus.publish_event.call_args.args[0]
    assert event.type == "billing.usage.recorded.storage_bytes_written"
    assert event.source == "storage_service"
    assert event.data["service_type"] == "storage_minio"
    assert event.data["product_id"] == "minio_storage"
    assert event.data["usage_amount"] == 4096
    assert event.data["unit_type"] == "byte"
    assert event.data["organization_id"] == "org_123"
    assert event.data["cost_components"][0]["component_id"] == "object_storage_capacity"


@pytest.mark.asyncio
async def test_storage_download_billing_usage_event_uses_egress_meter():
    event_bus = AsyncMock()
    event_bus.publish_event.return_value = True
    publisher = StorageEventPublisher(event_bus)

    await publisher.publish_billing_usage_recorded(
        user_id="user_123",
        product_id="minio_storage",
        usage_amount=8192,
        unit_type="byte",
        operation_type="egress_bytes",
        resource_name="file_123",
    )

    event = event_bus.publish_event.call_args.args[0]
    assert event.type == "billing.usage.recorded.egress_bytes"
    assert event.data["operation_type"] == "egress_bytes"
    assert event.data["cost_components"][0]["component_id"] == "storage_egress"
    assert event.data["cost_components"][0]["component_type"] == "network"
