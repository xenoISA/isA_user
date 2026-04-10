from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from microservices.subscription_service.models import (
    BillingAccountType,
    BillingCycle,
    CreditReservation,
    ReleaseReservationRequest,
    ReservationStatus,
    ReserveCreditsRequest,
    ReconcileReservationRequest,
    SubscriptionStatus,
    UserSubscription,
)
from microservices.subscription_service.subscription_service import SubscriptionService


def _make_subscription(organization_id: str | None = None) -> UserSubscription:
    now = datetime.now(timezone.utc)
    return UserSubscription(
        subscription_id="sub_test_001",
        user_id="usr_test_001",
        organization_id=organization_id,
        tier_id="tier_pro_001",
        tier_code="pro",
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        credits_allocated=100,
        credits_used=0,
        credits_remaining=100,
        credits_rolled_over=0,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )


class FakeReservationRepository:
    def __init__(self, organization_id: str | None = None) -> None:
        self.subscription = _make_subscription(organization_id=organization_id)
        self.reservations: dict[str, CreditReservation] = {}
        self.request_index: dict[str, str] = {}

    async def get_user_subscription(
        self,
        user_id: str,
        organization_id=None,
        billing_account_type=None,
        billing_account_id=None,
        actor_user_id=None,
        active_only=True,
    ):
        payer_type = (
            billing_account_type.value
            if hasattr(billing_account_type, "value")
            else billing_account_type
        )
        if payer_type == BillingAccountType.ORGANIZATION.value:
            if self.subscription.organization_id != billing_account_id:
                return None
            return self.subscription
        if self.subscription.user_id != (billing_account_id or user_id):
            return None
        return self.subscription

    async def reserve_credits(
        self,
        user_id: str,
        estimated_credits: int,
        organization_id=None,
        billing_account_type=None,
        billing_account_id=None,
        actor_user_id=None,
        model=None,
        request_id=None,
        metadata=None,
    ):
        if request_id and request_id in self.request_index:
            return self.reservations[self.request_index[request_id]]
        if self.subscription.credits_remaining < estimated_credits:
            return None

        self.subscription.credits_used += estimated_credits
        self.subscription.credits_remaining -= estimated_credits

        reservation_id = f"res_{len(self.reservations) + 1:03d}"
        reservation = CreditReservation(
            reservation_id=reservation_id,
            subscription_id=self.subscription.subscription_id,
            user_id=user_id,
            actor_user_id=actor_user_id or user_id,
            billing_account_type=(
                BillingAccountType(billing_account_type)
                if isinstance(billing_account_type, str)
                else billing_account_type
            ),
            billing_account_id=billing_account_id or organization_id or user_id,
            organization_id=organization_id,
            request_id=request_id,
            model=model,
            estimated_credits=estimated_credits,
            credits_remaining_after_reserve=self.subscription.credits_remaining,
            status=ReservationStatus.PENDING,
            metadata=metadata or {},
        )
        self.reservations[reservation_id] = reservation
        if request_id:
            self.request_index[request_id] = reservation_id
        return reservation

    async def reconcile_credit_reservation(self, reservation_id: str, actual_credits: int):
        reservation = self.reservations.get(reservation_id)
        if not reservation:
            return None
        if reservation.status != ReservationStatus.PENDING:
            return {
                "reservation": reservation,
                "credits_remaining": self.subscription.credits_remaining,
                "message": f"Reservation already {reservation.status.value}",
            }

        refund = max(reservation.estimated_credits - actual_credits, 0)
        extra = max(actual_credits - reservation.estimated_credits, 0)

        self.subscription.credits_used -= refund
        self.subscription.credits_remaining += refund

        if extra > 0:
            if self.subscription.credits_remaining < extra:
                return {
                    "reservation": reservation,
                    "credits_remaining": self.subscription.credits_remaining,
                    "message": "Insufficient credits to reconcile reservation overage",
                }
            self.subscription.credits_used += extra
            self.subscription.credits_remaining -= extra

        reservation.status = ReservationStatus.RECONCILED
        reservation.actual_credits = actual_credits
        reservation.credits_refunded = refund
        reservation.extra_credits_consumed = extra
        reservation.credits_remaining_after_finalize = self.subscription.credits_remaining

        return {
            "reservation": reservation,
            "credits_remaining": self.subscription.credits_remaining,
            "message": "Reservation reconciled successfully",
        }

    async def release_credit_reservation(self, reservation_id: str):
        reservation = self.reservations.get(reservation_id)
        if not reservation:
            return None
        if reservation.status != ReservationStatus.PENDING:
            return {
                "reservation": reservation,
                "credits_remaining": self.subscription.credits_remaining,
                "message": f"Reservation already {reservation.status.value}",
            }

        self.subscription.credits_used -= reservation.estimated_credits
        self.subscription.credits_remaining += reservation.estimated_credits
        reservation.status = ReservationStatus.RELEASED
        reservation.credits_refunded = reservation.estimated_credits
        reservation.credits_remaining_after_finalize = self.subscription.credits_remaining

        return {
            "reservation": reservation,
            "credits_remaining": self.subscription.credits_remaining,
            "message": "Reservation released successfully",
        }


class BrokenReservationRepository(FakeReservationRepository):
    async def reserve_credits(
        self,
        user_id: str,
        estimated_credits: int,
        organization_id=None,
        billing_account_type=None,
        billing_account_id=None,
        actor_user_id=None,
        model=None,
        request_id=None,
        metadata=None,
    ):
        raise RuntimeError(
            'column "actor_user_id" of relation "credit_reservations" does not exist'
        )


@pytest.mark.asyncio
async def test_reserve_is_idempotent_by_request_id():
    repository = FakeReservationRepository()
    service = SubscriptionService(repository=repository, event_bus=None)

    first = await service.reserve_credits(
        ReserveCreditsRequest(
            user_id="usr_test_001",
            estimated_credits=25,
            model="gpt-4o-mini",
            request_id="req_001",
        )
    )
    second = await service.reserve_credits(
        ReserveCreditsRequest(
            user_id="usr_test_001",
            estimated_credits=25,
            model="gpt-4o-mini",
            request_id="req_001",
        )
    )

    assert first.success is True
    assert second.success is True
    assert second.reservation_id == first.reservation_id
    assert repository.subscription.credits_used == 25
    assert repository.subscription.credits_remaining == 75


@pytest.mark.asyncio
async def test_reconcile_refunds_difference_back_to_subscription():
    repository = FakeReservationRepository()
    service = SubscriptionService(repository=repository, event_bus=None)

    reserve = await service.reserve_credits(
        ReserveCreditsRequest(
            user_id="usr_test_001",
            estimated_credits=30,
            model="gpt-4o-mini",
            request_id="req_002",
        )
    )
    reconcile = await service.reconcile_reservation(
        ReconcileReservationRequest(
            reservation_id=reserve.reservation_id,
            actual_credits=24,
        )
    )

    assert reconcile.success is True
    assert reconcile.credits_consumed == 24
    assert reconcile.credits_refunded == 6
    assert reconcile.credits_remaining == 76
    assert repository.subscription.credits_used == 24
    assert repository.subscription.credits_remaining == 76


@pytest.mark.asyncio
async def test_release_restores_reserved_credits():
    repository = FakeReservationRepository()
    service = SubscriptionService(repository=repository, event_bus=None)

    reserve = await service.reserve_credits(
        ReserveCreditsRequest(
            user_id="usr_test_001",
            estimated_credits=18,
            model="gpt-4o-mini",
            request_id="req_003",
        )
    )
    release = await service.release_reservation(
        ReleaseReservationRequest(reservation_id=reserve.reservation_id)
    )

    assert release.success is True
    assert release.credits_released == 18
    assert release.credits_remaining == 100
    assert repository.subscription.credits_used == 0
    assert repository.subscription.credits_remaining == 100


@pytest.mark.asyncio
async def test_reserve_uses_explicit_org_payer_fields():
    repository = FakeReservationRepository(organization_id="org_test_001")
    service = SubscriptionService(repository=repository, event_bus=None)

    reserve = await service.reserve_credits(
        ReserveCreditsRequest(
            user_id="usr_test_001",
            actor_user_id="usr_test_001",
            billing_account_type=BillingAccountType.ORGANIZATION,
            billing_account_id="org_test_001",
            organization_id="org_test_001",
            estimated_credits=20,
            model="gpt-4o-mini",
            request_id="req_org_001",
        )
    )

    assert reserve.success is True
    assert reserve.billing_account_type == BillingAccountType.ORGANIZATION
    assert reserve.billing_account_id == "org_test_001"
    assert reserve.actor_user_id == "usr_test_001"
    stored = repository.reservations[reserve.reservation_id]
    assert stored.billing_account_type == BillingAccountType.ORGANIZATION
    assert stored.billing_account_id == "org_test_001"
    assert stored.actor_user_id == "usr_test_001"


@pytest.mark.asyncio
async def test_reconcile_overage_fails_when_extra_credits_are_not_available():
    repository = FakeReservationRepository()
    service = SubscriptionService(repository=repository, event_bus=None)

    reserve = await service.reserve_credits(
        ReserveCreditsRequest(
            user_id="usr_test_001",
            estimated_credits=95,
            model="gpt-4o-mini",
            request_id="req_004",
        )
    )
    reconcile = await service.reconcile_reservation(
        ReconcileReservationRequest(
            reservation_id=reserve.reservation_id,
            actual_credits=110,
        )
    )

    assert reconcile.success is False
    assert reconcile.message == "Insufficient credits to reconcile reservation overage"
    assert repository.subscription.credits_used == 95
    assert repository.subscription.credits_remaining == 5


@pytest.mark.asyncio
async def test_reserve_surfaces_unexpected_repository_failures():
    repository = BrokenReservationRepository()
    service = SubscriptionService(repository=repository, event_bus=None)

    reserve = await service.reserve_credits(
        ReserveCreditsRequest(
            user_id="usr_test_001",
            estimated_credits=25,
            model="gpt-4o-mini",
            request_id="req_broken_001",
        )
    )

    assert reserve.success is False
    assert reserve.message.startswith("Reservation failed:")
    assert "actor_user_id" in reserve.message
