"""
Subscription Repository

Data access layer for subscription management - PostgreSQL + gRPC
"""

import logging
import os
import sys
import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from enum import Enum
from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    UserSubscription, SubscriptionHistory, SubscriptionStatus,
    BillingCycle, SubscriptionAction, InitiatedBy,
    BillingAccountType, CreditReservation, ReservationStatus,
)

logger = logging.getLogger(__name__)


class SubscriptionRepository:
    """Subscription data access repository - PostgreSQL"""

    @staticmethod
    def _resolve_billing_scope(
        *,
        user_id: str,
        organization_id: Optional[str] = None,
        billing_account_type: Optional[str] = None,
        billing_account_id: Optional[str] = None,
        actor_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve explicit payer fields while keeping legacy user/org inputs working."""
        resolved_actor_user_id = actor_user_id or user_id or billing_account_id or ""
        resolved_type = (
            BillingAccountType(billing_account_type)
            if isinstance(billing_account_type, str)
            else billing_account_type
        )
        resolved_account_id = billing_account_id

        if resolved_type is None:
            if organization_id:
                resolved_type = BillingAccountType.ORGANIZATION
                resolved_account_id = organization_id
            else:
                resolved_type = BillingAccountType.USER
                resolved_account_id = user_id or resolved_actor_user_id
        elif resolved_account_id is None:
            if resolved_type == BillingAccountType.ORGANIZATION:
                resolved_account_id = organization_id
            else:
                resolved_account_id = user_id or resolved_actor_user_id

        resolved_organization_id = organization_id
        if resolved_type == BillingAccountType.ORGANIZATION:
            resolved_organization_id = resolved_organization_id or resolved_account_id

        return {
            "user_id": user_id or resolved_actor_user_id,
            "actor_user_id": resolved_actor_user_id,
            "organization_id": resolved_organization_id,
            "billing_account_type": resolved_type,
            "billing_account_id": resolved_account_id,
        }

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize subscription repository with service discovery."""
        if config is None:
            config = ConfigManager("subscription_service")

        # Discover PostgreSQL service
        postgres_host, postgres_port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {postgres_host}:{postgres_port}")
        self.db = AsyncPostgresClient(
            host=postgres_host,
            port=postgres_port,
            user_id="subscription_service",
        min_pool_size=1,
        max_pool_size=2,
        )
        self.schema = "subscription"
        self.subscriptions_table = "user_subscriptions"
        self.history_table = "subscription_history"
        self.reservations_table = "credit_reservations"

    async def initialize(self):
        """Initialize repository and validate required schema."""
        required_reservation_columns = {
            "actor_user_id",
            "billing_account_type",
            "billing_account_id",
        }
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = $1
              AND table_name = $2
        """

        async with self.db:
            results = await self.db.query(
                query,
                params=[self.schema, self.reservations_table],
            )

        available_columns = {
            row["column_name"] if isinstance(row, dict) else row[0]
            for row in (results or [])
        }
        missing_columns = sorted(required_reservation_columns - available_columns)
        if missing_columns:
            raise RuntimeError(
                "subscription.credit_reservations schema is missing canonical payer "
                f"columns: {', '.join(missing_columns)}. "
                "Apply migration 003_add_canonical_payer_fields_to_credit_reservations.sql."
            )

        logger.info("Subscription repository initialized")

    async def close(self):
        """Close repository connections"""
        logger.info("Subscription repository connections closed")

    # ====================
    # Subscription CRUD
    # ====================

    async def create_subscription(self, subscription: UserSubscription) -> Optional[UserSubscription]:
        """Create a new subscription"""
        try:
            import json
            query = f'''
                INSERT INTO {self.schema}.{self.subscriptions_table} (
                    subscription_id, user_id, organization_id,
                    tier_id, tier_code, status,
                    billing_cycle, price_paid, currency,
                    credits_allocated, credits_used, credits_remaining, credits_rolled_over,
                    current_period_start, current_period_end,
                    trial_start, trial_end, is_trial,
                    seats_purchased, seats_used,
                    cancel_at_period_end, canceled_at, cancellation_reason,
                    payment_method_id, external_subscription_id,
                    auto_renew, next_billing_date, last_billing_date,
                    metadata, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                    $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31
                )
                RETURNING *
            '''

            now = datetime.now(timezone.utc)
            params = [
                subscription.subscription_id,
                subscription.user_id,
                subscription.organization_id,
                subscription.tier_id,
                subscription.tier_code,
                subscription.status.value,
                subscription.billing_cycle.value,
                float(subscription.price_paid),
                subscription.currency,
                subscription.credits_allocated,
                subscription.credits_used,
                subscription.credits_remaining,
                subscription.credits_rolled_over,
                subscription.current_period_start,
                subscription.current_period_end,
                subscription.trial_start,
                subscription.trial_end,
                subscription.is_trial,
                subscription.seats_purchased,
                subscription.seats_used,
                subscription.cancel_at_period_end,
                subscription.canceled_at,
                subscription.cancellation_reason,
                subscription.payment_method_id,
                subscription.external_subscription_id,
                subscription.auto_renew,
                subscription.next_billing_date,
                subscription.last_billing_date,
                json.dumps(subscription.metadata) if subscription.metadata else "{}",
                now,
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_subscription(results[0])
            return None

        except Exception as e:
            logger.error(f"Error creating subscription: {e}", exc_info=True)
            return None

    async def get_subscription(self, subscription_id: str) -> Optional[UserSubscription]:
        """Get subscription by ID"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.subscriptions_table}
                WHERE subscription_id = $1
            '''

            async with self.db:
                results = await self.db.query(query, params=[subscription_id])

            if results and len(results) > 0:
                return self._row_to_subscription(results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            return None

    async def get_user_subscription(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        billing_account_type: Optional[str] = None,
        billing_account_id: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        active_only: bool = True
    ) -> Optional[UserSubscription]:
        """Get the active subscription for the resolved billing account."""
        try:
            scope = self._resolve_billing_scope(
                user_id=user_id,
                organization_id=organization_id,
                billing_account_type=billing_account_type,
                billing_account_id=billing_account_id,
                actor_user_id=actor_user_id,
            )

            if scope["billing_account_type"] == BillingAccountType.ORGANIZATION:
                query = f'''
                    SELECT * FROM {self.schema}.{self.subscriptions_table}
                    WHERE organization_id = $1
                    {'AND status = $2' if active_only else ''}
                    ORDER BY created_at DESC
                    LIMIT 1
                '''
                params = [scope["billing_account_id"]]
                if active_only:
                    params.append('active')
            else:
                query = f'''
                    SELECT * FROM {self.schema}.{self.subscriptions_table}
                    WHERE user_id = $1 AND organization_id IS NULL
                    {'AND status = $2' if active_only else ''}
                    ORDER BY created_at DESC
                    LIMIT 1
                '''
                params = [scope["billing_account_id"]]
                if active_only:
                    params.append('active')

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_subscription(results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting user subscription: {e}")
            return None

    async def get_subscriptions(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status: Optional[SubscriptionStatus] = None,
        tier_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[UserSubscription]:
        """Get subscriptions with filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status.value)

            if tier_code:
                param_count += 1
                conditions.append(f"tier_code = ${param_count}")
                params.append(tier_code)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.subscriptions_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''
            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_subscription(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting subscriptions: {e}")
            return []

    async def update_subscription(
        self,
        subscription_id: str,
        updates: Dict[str, Any]
    ) -> Optional[UserSubscription]:
        """Update a subscription"""
        try:
            import json
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                if key == "metadata":
                    value = json.dumps(value)
                elif isinstance(value, Enum):
                    value = value.value
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            param_count += 1
            params.append(subscription_id)

            query = f'''
                UPDATE {self.schema}.{self.subscriptions_table}
                SET {", ".join(set_clauses)}
                WHERE subscription_id = ${param_count}
                RETURNING *
            '''

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_subscription(results[0])
            return None

        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return None

    async def consume_credits(
        self,
        subscription_id: str,
        credits_to_consume: int
    ) -> Optional[UserSubscription]:
        """Consume credits from a subscription (atomic operation)"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.subscriptions_table}
                SET
                    credits_used = credits_used + $1,
                    credits_remaining = credits_remaining - $1,
                    updated_at = $2
                WHERE subscription_id = $3
                AND credits_remaining >= $1
                RETURNING *
            '''

            params = [credits_to_consume, datetime.now(timezone.utc), subscription_id]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_subscription(results[0])
            return None

        except Exception as e:
            logger.error(f"Error consuming credits: {e}")
            return None

    async def allocate_credits(
        self,
        subscription_id: str,
        credits_to_allocate: int,
        rollover_credits: int = 0
    ) -> Optional[UserSubscription]:
        """Allocate credits to a subscription (for new period)"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.subscriptions_table}
                SET
                    credits_allocated = $1,
                    credits_remaining = $1 + $2,
                    credits_used = 0,
                    credits_rolled_over = $2,
                    updated_at = $3
                WHERE subscription_id = $4
                RETURNING *
            '''

            params = [
                credits_to_allocate,
                rollover_credits,
                datetime.now(timezone.utc),
                subscription_id
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_subscription(results[0])
            return None

        except Exception as e:
            logger.error(f"Error allocating credits: {e}")
            return None

    async def reserve_credits(
        self,
        user_id: str,
        estimated_credits: int,
        organization_id: Optional[str] = None,
        billing_account_type: Optional[str] = None,
        billing_account_id: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        model: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CreditReservation]:
        """Reserve credits idempotently for a request."""
        try:
            await self.db._ensure_connected()
            now = datetime.now(timezone.utc)
            scope = self._resolve_billing_scope(
                user_id=user_id,
                organization_id=organization_id,
                billing_account_type=billing_account_type,
                billing_account_id=billing_account_id,
                actor_user_id=actor_user_id,
            )

            async with self.db._pool.acquire() as conn:
                async with conn.transaction():
                    if request_id:
                        existing = await conn.fetchrow(
                            f"""
                            SELECT * FROM {self.schema}.{self.reservations_table}
                            WHERE request_id = $1
                            """,
                            request_id,
                        )
                        if existing:
                            return self._row_to_credit_reservation(dict(existing))

                    if scope["billing_account_type"] == BillingAccountType.ORGANIZATION:
                        subscription = await conn.fetchrow(
                            f"""
                            SELECT * FROM {self.schema}.{self.subscriptions_table}
                            WHERE organization_id = $1
                              AND status = 'active'
                            ORDER BY created_at DESC
                            LIMIT 1
                            FOR UPDATE
                            """,
                            scope["billing_account_id"],
                        )
                    else:
                        subscription = await conn.fetchrow(
                            f"""
                            SELECT * FROM {self.schema}.{self.subscriptions_table}
                            WHERE user_id = $1
                              AND organization_id IS NULL
                              AND status = 'active'
                            ORDER BY created_at DESC
                            LIMIT 1
                            FOR UPDATE
                            """,
                            scope["billing_account_id"],
                        )

                    if not subscription:
                        return None

                    updated_subscription = await conn.fetchrow(
                        f"""
                        UPDATE {self.schema}.{self.subscriptions_table}
                        SET
                            credits_used = credits_used + $1,
                            credits_remaining = credits_remaining - $1,
                            updated_at = $2
                        WHERE subscription_id = $3
                          AND credits_remaining >= $1
                        RETURNING *
                        """,
                        estimated_credits,
                        now,
                        subscription["subscription_id"],
                    )

                    if not updated_subscription:
                        return None

                    reservation_row = await conn.fetchrow(
                        f"""
                        INSERT INTO {self.schema}.{self.reservations_table} (
                            reservation_id,
                            request_id,
                            subscription_id,
                            user_id,
                            actor_user_id,
                            billing_account_type,
                            billing_account_id,
                            organization_id,
                            model,
                            estimated_credits,
                            credits_remaining_after_reserve,
                            status,
                            metadata,
                            created_at,
                            updated_at
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $14
                        )
                        RETURNING *
                        """,
                        f"res_{uuid.uuid4().hex[:16]}",
                        request_id,
                        updated_subscription["subscription_id"],
                        scope["user_id"],
                        scope["actor_user_id"],
                        scope["billing_account_type"].value
                        if scope["billing_account_type"]
                        else None,
                        scope["billing_account_id"],
                        scope["organization_id"],
                        model,
                        estimated_credits,
                        updated_subscription["credits_remaining"],
                        ReservationStatus.PENDING.value,
                        json.dumps(metadata or {}),
                        now,
                    )

                    if not reservation_row:
                        return None

                    return self._row_to_credit_reservation(dict(reservation_row))

        except Exception as e:
            logger.error(f"Error reserving credits: {e}", exc_info=True)
            raise

    async def get_credit_reservation(
        self,
        reservation_id: str,
    ) -> Optional[CreditReservation]:
        """Get a reservation by ID."""
        try:
            query = f"""
                SELECT * FROM {self.schema}.{self.reservations_table}
                WHERE reservation_id = $1
            """

            async with self.db:
                results = await self.db.query(query, params=[reservation_id])

            if results and len(results) > 0:
                return self._row_to_credit_reservation(results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting credit reservation: {e}", exc_info=True)
            return None

    async def reconcile_credit_reservation(
        self,
        reservation_id: str,
        actual_credits: int,
    ) -> Optional[Dict[str, Any]]:
        """Finalize a reservation against actual usage."""
        try:
            await self.db._ensure_connected()
            now = datetime.now(timezone.utc)

            async with self.db._pool.acquire() as conn:
                async with conn.transaction():
                    reservation_row = await conn.fetchrow(
                        f"""
                        SELECT * FROM {self.schema}.{self.reservations_table}
                        WHERE reservation_id = $1
                        FOR UPDATE
                        """,
                        reservation_id,
                    )
                    if not reservation_row:
                        return None

                    reservation = self._row_to_credit_reservation(dict(reservation_row))
                    subscription_row = await conn.fetchrow(
                        f"""
                        SELECT * FROM {self.schema}.{self.subscriptions_table}
                        WHERE subscription_id = $1
                        FOR UPDATE
                        """,
                        reservation.subscription_id,
                    )
                    if not subscription_row:
                        return None

                    if reservation.status != ReservationStatus.PENDING:
                        return {
                            "reservation": reservation,
                            "credits_remaining": int(subscription_row["credits_remaining"]),
                            "message": f"Reservation already {reservation.status.value}",
                        }

                    credits_refunded = max(reservation.estimated_credits - actual_credits, 0)
                    extra_credits = max(actual_credits - reservation.estimated_credits, 0)

                    if credits_refunded > 0:
                        updated_subscription = await conn.fetchrow(
                            f"""
                            UPDATE {self.schema}.{self.subscriptions_table}
                            SET
                                credits_used = GREATEST(credits_used - $1, 0),
                                credits_remaining = credits_remaining + $1,
                                updated_at = $2
                            WHERE subscription_id = $3
                            RETURNING *
                            """,
                            credits_refunded,
                            now,
                            reservation.subscription_id,
                        )
                        if not updated_subscription:
                            return None
                        subscription_row = updated_subscription
                    elif extra_credits > 0:
                        updated_subscription = await conn.fetchrow(
                            f"""
                            UPDATE {self.schema}.{self.subscriptions_table}
                            SET
                                credits_used = credits_used + $1,
                                credits_remaining = credits_remaining - $1,
                                updated_at = $2
                            WHERE subscription_id = $3
                              AND credits_remaining >= $1
                            RETURNING *
                            """,
                            extra_credits,
                            now,
                            reservation.subscription_id,
                        )
                        if not updated_subscription:
                            return {
                                "reservation": reservation,
                                "credits_remaining": int(subscription_row["credits_remaining"]),
                                "message": "Insufficient credits to reconcile reservation overage",
                            }
                        subscription_row = updated_subscription

                    updated_reservation = await conn.fetchrow(
                        f"""
                        UPDATE {self.schema}.{self.reservations_table}
                        SET
                            status = $1,
                            actual_credits = $2,
                            credits_refunded = $3,
                            extra_credits_consumed = $4,
                            credits_remaining_after_finalize = $5,
                            reconciled_at = $6,
                            updated_at = $6
                        WHERE reservation_id = $7
                        RETURNING *
                        """,
                        ReservationStatus.RECONCILED.value,
                        actual_credits,
                        credits_refunded,
                        extra_credits,
                        int(subscription_row["credits_remaining"]),
                        now,
                        reservation_id,
                    )

                    if not updated_reservation:
                        return None

                    return {
                        "reservation": self._row_to_credit_reservation(dict(updated_reservation)),
                        "credits_remaining": int(subscription_row["credits_remaining"]),
                        "message": "Reservation reconciled successfully",
                    }

        except Exception as e:
            logger.error(f"Error reconciling credit reservation: {e}", exc_info=True)
            return None

    async def release_credit_reservation(
        self,
        reservation_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Release a pending reservation and refund held credits."""
        try:
            await self.db._ensure_connected()
            now = datetime.now(timezone.utc)

            async with self.db._pool.acquire() as conn:
                async with conn.transaction():
                    reservation_row = await conn.fetchrow(
                        f"""
                        SELECT * FROM {self.schema}.{self.reservations_table}
                        WHERE reservation_id = $1
                        FOR UPDATE
                        """,
                        reservation_id,
                    )
                    if not reservation_row:
                        return None

                    reservation = self._row_to_credit_reservation(dict(reservation_row))
                    subscription_row = await conn.fetchrow(
                        f"""
                        SELECT * FROM {self.schema}.{self.subscriptions_table}
                        WHERE subscription_id = $1
                        FOR UPDATE
                        """,
                        reservation.subscription_id,
                    )
                    if not subscription_row:
                        return None

                    if reservation.status == ReservationStatus.RELEASED:
                        return {
                            "reservation": reservation,
                            "credits_remaining": int(subscription_row["credits_remaining"]),
                            "message": "Reservation already released",
                        }

                    if reservation.status == ReservationStatus.RECONCILED:
                        return {
                            "reservation": reservation,
                            "credits_remaining": int(subscription_row["credits_remaining"]),
                            "message": "Reservation already reconciled",
                        }

                    updated_subscription = await conn.fetchrow(
                        f"""
                        UPDATE {self.schema}.{self.subscriptions_table}
                        SET
                            credits_used = GREATEST(credits_used - $1, 0),
                            credits_remaining = credits_remaining + $1,
                            updated_at = $2
                        WHERE subscription_id = $3
                        RETURNING *
                        """,
                        reservation.estimated_credits,
                        now,
                        reservation.subscription_id,
                    )
                    if not updated_subscription:
                        return None

                    updated_reservation = await conn.fetchrow(
                        f"""
                        UPDATE {self.schema}.{self.reservations_table}
                        SET
                            status = $1,
                            credits_refunded = $2,
                            credits_remaining_after_finalize = $3,
                            released_at = $4,
                            updated_at = $4
                        WHERE reservation_id = $5
                        RETURNING *
                        """,
                        ReservationStatus.RELEASED.value,
                        reservation.estimated_credits,
                        int(updated_subscription["credits_remaining"]),
                        now,
                        reservation_id,
                    )
                    if not updated_reservation:
                        return None

                    return {
                        "reservation": self._row_to_credit_reservation(dict(updated_reservation)),
                        "credits_remaining": int(updated_subscription["credits_remaining"]),
                        "message": "Reservation released successfully",
                    }

        except Exception as e:
            logger.error(f"Error releasing credit reservation: {e}", exc_info=True)
            return None

    # ====================
    # History Operations
    # ====================

    async def add_history(self, history: SubscriptionHistory) -> Optional[SubscriptionHistory]:
        """Add a subscription history entry"""
        try:
            import json
            query = f'''
                INSERT INTO {self.schema}.{self.history_table} (
                    history_id, subscription_id, user_id, organization_id,
                    action, previous_tier_code, new_tier_code,
                    previous_status, new_status,
                    credits_change, credits_balance_after,
                    price_change, period_start, period_end,
                    reason, initiated_by, metadata, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18
                )
                RETURNING *
            '''

            now = datetime.now(timezone.utc)
            params = [
                history.history_id or f"hist_{uuid.uuid4().hex[:16]}",
                history.subscription_id,
                history.user_id,
                history.organization_id,
                history.action.value,
                history.previous_tier_code,
                history.new_tier_code,
                history.previous_status,
                history.new_status,
                history.credits_change,
                history.credits_balance_after,
                float(history.price_change),
                history.period_start,
                history.period_end,
                history.reason,
                history.initiated_by.value,
                json.dumps(history.metadata) if history.metadata else "{}",
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_history(results[0])
            return None

        except Exception as e:
            logger.error(f"Error adding history: {e}", exc_info=True)
            return None

    async def get_subscription_history(
        self,
        subscription_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[SubscriptionHistory]:
        """Get history for a subscription"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.history_table}
                WHERE subscription_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            '''

            async with self.db:
                results = await self.db.query(query, params=[subscription_id, limit, offset])

            return [self._row_to_history(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting subscription history: {e}")
            return []

    # ====================
    # Helper Methods
    # ====================

    @staticmethod
    def _coerce_json_dict(value: Any) -> Dict[str, Any]:
        """Normalize DB JSON/text fields to dict for Pydantic models."""
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return {}
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def _row_to_subscription(self, row: Dict[str, Any]) -> UserSubscription:
        """Convert database row to UserSubscription model"""
        return UserSubscription(
            id=int(row.get("id")) if row.get("id") else None,
            subscription_id=row.get("subscription_id"),
            user_id=row.get("user_id"),
            organization_id=row.get("organization_id"),
            tier_id=row.get("tier_id"),
            tier_code=row.get("tier_code"),
            status=SubscriptionStatus(row.get("status")),
            billing_cycle=BillingCycle(row.get("billing_cycle")),
            price_paid=Decimal(str(row.get("price_paid", 0))),
            currency=row.get("currency", "USD"),
            credits_allocated=int(row.get("credits_allocated", 0)),
            credits_used=int(row.get("credits_used", 0)),
            credits_remaining=int(row.get("credits_remaining", 0)),
            credits_rolled_over=int(row.get("credits_rolled_over", 0)),
            current_period_start=row.get("current_period_start"),
            current_period_end=row.get("current_period_end"),
            trial_start=row.get("trial_start"),
            trial_end=row.get("trial_end"),
            is_trial=row.get("is_trial", False),
            seats_purchased=int(row.get("seats_purchased", 1)),
            seats_used=int(row.get("seats_used", 1)),
            cancel_at_period_end=row.get("cancel_at_period_end", False),
            canceled_at=row.get("canceled_at"),
            cancellation_reason=row.get("cancellation_reason"),
            payment_method_id=row.get("payment_method_id"),
            external_subscription_id=row.get("external_subscription_id"),
            auto_renew=row.get("auto_renew", True),
            next_billing_date=row.get("next_billing_date"),
            last_billing_date=row.get("last_billing_date"),
            metadata=self._coerce_json_dict(row.get("metadata")),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )

    def _row_to_history(self, row: Dict[str, Any]) -> SubscriptionHistory:
        """Convert database row to SubscriptionHistory model"""
        return SubscriptionHistory(
            id=int(row.get("id")) if row.get("id") else None,
            history_id=row.get("history_id"),
            subscription_id=row.get("subscription_id"),
            user_id=row.get("user_id"),
            organization_id=row.get("organization_id"),
            action=SubscriptionAction(row.get("action")),
            previous_tier_code=row.get("previous_tier_code"),
            new_tier_code=row.get("new_tier_code"),
            previous_status=row.get("previous_status"),
            new_status=row.get("new_status"),
            credits_change=int(row.get("credits_change", 0)),
            credits_balance_after=int(row.get("credits_balance_after")) if row.get("credits_balance_after") else None,
            price_change=Decimal(str(row.get("price_change", 0))),
            period_start=row.get("period_start"),
            period_end=row.get("period_end"),
            reason=row.get("reason"),
            initiated_by=InitiatedBy(row.get("initiated_by", "system")),
            metadata=self._coerce_json_dict(row.get("metadata")),
            created_at=row.get("created_at")
        )

    def _row_to_credit_reservation(self, row: Dict[str, Any]) -> CreditReservation:
        """Convert database row to CreditReservation model."""
        return CreditReservation(
            id=int(row.get("id")) if row.get("id") else None,
            reservation_id=row.get("reservation_id"),
            subscription_id=row.get("subscription_id"),
            user_id=row.get("user_id"),
            actor_user_id=row.get("actor_user_id") or row.get("user_id"),
            billing_account_type=(
                BillingAccountType(row.get("billing_account_type"))
                if row.get("billing_account_type")
                else None
            ),
            billing_account_id=row.get("billing_account_id"),
            organization_id=row.get("organization_id"),
            request_id=row.get("request_id"),
            model=row.get("model"),
            estimated_credits=int(row.get("estimated_credits", 0)),
            actual_credits=int(row.get("actual_credits")) if row.get("actual_credits") is not None else None,
            credits_refunded=int(row.get("credits_refunded", 0)),
            extra_credits_consumed=int(row.get("extra_credits_consumed", 0)),
            credits_remaining_after_reserve=(
                int(row.get("credits_remaining_after_reserve"))
                if row.get("credits_remaining_after_reserve") is not None
                else None
            ),
            credits_remaining_after_finalize=(
                int(row.get("credits_remaining_after_finalize"))
                if row.get("credits_remaining_after_finalize") is not None
                else None
            ),
            status=ReservationStatus(row.get("status", ReservationStatus.PENDING.value)),
            metadata=self._coerce_json_dict(row.get("metadata")),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            reconciled_at=row.get("reconciled_at"),
            released_at=row.get("released_at"),
        )


__all__ = ["SubscriptionRepository"]
