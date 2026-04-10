from __future__ import annotations

import pytest

from microservices.subscription_service.subscription_repository import SubscriptionRepository


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def query(self, query, params=None):
        return self.rows


@pytest.mark.asyncio
async def test_initialize_raises_when_canonical_reservation_columns_are_missing():
    repository = object.__new__(SubscriptionRepository)
    repository.db = FakeDB(
        [
            {"column_name": "reservation_id"},
            {"column_name": "subscription_id"},
            {"column_name": "user_id"},
        ]
    )
    repository.schema = "subscription"
    repository.reservations_table = "credit_reservations"

    with pytest.raises(
        RuntimeError,
        match="003_add_canonical_payer_fields_to_credit_reservations.sql",
    ):
        await SubscriptionRepository.initialize(repository)


@pytest.mark.asyncio
async def test_initialize_accepts_canonical_reservation_columns():
    repository = object.__new__(SubscriptionRepository)
    repository.db = FakeDB(
        [
            {"column_name": "reservation_id"},
            {"column_name": "subscription_id"},
            {"column_name": "user_id"},
            {"column_name": "actor_user_id"},
            {"column_name": "billing_account_type"},
            {"column_name": "billing_account_id"},
        ]
    )
    repository.schema = "subscription"
    repository.reservations_table = "credit_reservations"

    await SubscriptionRepository.initialize(repository)
