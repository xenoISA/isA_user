from __future__ import annotations

import pytest

from microservices.billing_service.billing_repository import BillingRepository


class FakeDB:
    def __init__(self, responses):
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def query(self, query, params=None):
        if not self._responses:
            raise AssertionError("Unexpected query with no remaining fake responses")
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_initialize_raises_when_billing_record_columns_are_missing():
    repository = object.__new__(BillingRepository)
    repository.db = FakeDB(
        [
            [
                {"column_name": "billing_id"},
                {"column_name": "user_id"},
                {"column_name": "organization_id"},
            ]
        ]
    )
    repository.schema = "billing"
    repository.billing_records_table = "billing_records"
    repository.billing_events_table = "billing_events"

    with pytest.raises(
        RuntimeError,
        match="003_add_agent_attribution_to_billing.sql and 004_add_canonical_payer_fields.sql",
    ):
        await BillingRepository.initialize(repository)


@pytest.mark.asyncio
async def test_initialize_raises_when_event_processing_claims_table_is_missing():
    repository = object.__new__(BillingRepository)
    repository.db = FakeDB(
        [
            [
                {"column_name": "billing_id"},
                {"column_name": "user_id"},
                {"column_name": "organization_id"},
                {"column_name": "service_type"},
                {"column_name": "actor_user_id"},
                {"column_name": "billing_account_type"},
                {"column_name": "billing_account_id"},
                {"column_name": "agent_id"},
            ],
            [
                {"column_name": "event_id"},
                {"column_name": "user_id"},
                {"column_name": "organization_id"},
                {"column_name": "service_type"},
                {"column_name": "actor_user_id"},
                {"column_name": "billing_account_type"},
                {"column_name": "billing_account_id"},
                {"column_name": "agent_id"},
            ],
            [],
        ]
    )
    repository.schema = "billing"
    repository.billing_records_table = "billing_records"
    repository.billing_events_table = "billing_events"

    with pytest.raises(
        RuntimeError,
        match="005_add_event_processing_claims.sql",
    ):
        await BillingRepository.initialize(repository)


@pytest.mark.asyncio
async def test_initialize_accepts_canonical_billing_schema():
    repository = object.__new__(BillingRepository)
    repository.db = FakeDB(
        [
            [
                {"column_name": "billing_id"},
                {"column_name": "user_id"},
                {"column_name": "organization_id"},
                {"column_name": "service_type"},
                {"column_name": "actor_user_id"},
                {"column_name": "billing_account_type"},
                {"column_name": "billing_account_id"},
                {"column_name": "agent_id"},
            ],
            [
                {"column_name": "event_id"},
                {"column_name": "user_id"},
                {"column_name": "organization_id"},
                {"column_name": "service_type"},
                {"column_name": "actor_user_id"},
                {"column_name": "billing_account_type"},
                {"column_name": "billing_account_id"},
                {"column_name": "agent_id"},
            ],
            [{"?column?": 1}],
        ]
    )
    repository.schema = "billing"
    repository.billing_records_table = "billing_records"
    repository.billing_events_table = "billing_events"

    await BillingRepository.initialize(repository)
