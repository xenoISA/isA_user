from unittest.mock import AsyncMock

import pytest

from microservices.billing_service.client import BillingServiceClient


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_export_user_data_collects_billing_records_and_usage():
    client = BillingServiceClient(base_url="http://billing.local")
    client.get_user_billing_records = AsyncMock(
        return_value={
            "records": [
                {
                    "billing_id": "bill-1",
                    "billing_period": "2026-05",
                    "total_amount": "12.50",
                }
            ],
            "total_count": 1,
        }
    )
    client.get_usage_aggregations = AsyncMock(
        return_value={
            "items": [
                {
                    "service_name": "storage_service",
                    "usage_type": "storage",
                    "quantity": 2.5,
                    "unit": "GB",
                },
                {
                    "service_name": "model_gateway",
                    "usage_type": "tokens",
                    "quantity": 1200,
                    "unit": "tokens",
                },
            ]
        }
    )

    result = await client.export_user_data(
        user_id="user-1",
        organization_id="org-1",
        request_id="gdpr_req_1",
    )

    assert result["schema_version"] == "billing-export-v1"
    assert result["service"] == "billing_service"
    assert result["user_id"] == "user-1"
    assert result["organization_id"] == "org-1"
    assert result["gdpr_request_id"] == "gdpr_req_1"
    assert result["billing_records"]["records"][0]["billing_id"] == "bill-1"
    assert result["usage_aggregations"]["items"][0]["usage_type"] == "storage"
    assert result["counts"] == {
        "records": 3,
        "sections": {"billing_records": 1, "usage_aggregations": 2},
    }
    client.get_user_billing_records.assert_awaited_once_with(
        user_id="user-1",
        organization_id="org-1",
        limit=1000,
        offset=0,
    )
    client.get_usage_aggregations.assert_awaited_once_with(
        user_id="user-1",
        organization_id="org-1",
        group_by="day",
    )
    await client.close()


async def test_export_user_data_returns_empty_payload_when_billing_has_no_data():
    client = BillingServiceClient(base_url="http://billing.local")
    client.get_user_billing_records = AsyncMock(return_value=None)
    client.get_usage_aggregations = AsyncMock(return_value=None)

    result = await client.export_user_data(
        user_id="missing-user",
        organization_id=None,
        request_id="gdpr_req_missing",
    )

    assert result["user_id"] == "missing-user"
    assert result["organization_id"] is None
    assert result["gdpr_request_id"] == "gdpr_req_missing"
    assert result["billing_records"] == {}
    assert result["usage_aggregations"] == {}
    assert result["counts"] == {
        "records": 0,
        "sections": {"billing_records": 0, "usage_aggregations": 0},
    }
    await client.close()
