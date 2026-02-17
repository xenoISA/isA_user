"""
Membership Service Data Repository

Data access layer - PostgreSQL + gRPC (Async)
"""

import logging
import os
import sys
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager
from .models import (
    Membership, MembershipHistory, Tier, TierBenefit,
    MembershipStatus, MembershipTier, PointAction, InitiatedBy
)

logger = logging.getLogger(__name__)


class MembershipRepository:
    """Membership service data repository - PostgreSQL (Async)"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("membership_service")

        # Discover PostgreSQL service
        host, port = config.discover_service(
            service_name='postgres_service',
            default_host='localhost',
            default_port=5432,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            user_id="membership_service"
        )
        self.schema = "membership"
        self.memberships_table = "memberships"
        self.history_table = "membership_history"
        self.tiers_table = "tiers"
        self.tier_benefits_table = "tier_benefits"
        self.benefit_usage_table = "benefit_usage"

        # Tier cache
        self._tier_cache: Dict[str, Tier] = {}

    async def initialize(self):
        """Initialize database connection and load tier cache"""
        logger.info("Membership repository initialized with PostgreSQL")
        await self._load_tier_cache()

    async def close(self):
        """Close database connection"""
        logger.info("Membership repository database connection closed")

    async def _load_tier_cache(self):
        """Load tier definitions into memory cache"""
        try:
            tiers = await self.get_all_tiers()
            self._tier_cache = {t.tier_code.value: t for t in tiers}
            logger.info(f"Loaded {len(self._tier_cache)} tiers into cache")
        except Exception as e:
            logger.warning(f"Failed to load tier cache: {e}")
            # Initialize with default tiers
            self._tier_cache = {
                "bronze": Tier(tier_code=MembershipTier.BRONZE, tier_name="Bronze", qualification_threshold=0, point_multiplier=Decimal("1.0")),
                "silver": Tier(tier_code=MembershipTier.SILVER, tier_name="Silver", qualification_threshold=5000, point_multiplier=Decimal("1.25")),
                "gold": Tier(tier_code=MembershipTier.GOLD, tier_name="Gold", qualification_threshold=20000, point_multiplier=Decimal("1.5")),
                "platinum": Tier(tier_code=MembershipTier.PLATINUM, tier_name="Platinum", qualification_threshold=50000, point_multiplier=Decimal("2.0")),
                "diamond": Tier(tier_code=MembershipTier.DIAMOND, tier_name="Diamond", qualification_threshold=100000, point_multiplier=Decimal("3.0")),
            }

    # ====================
    # Membership CRUD
    # ====================

    async def create_membership(
        self,
        user_id: str,
        tier_code: str,
        points_balance: int = 0,
        **kwargs
    ) -> Membership:
        """Create new membership"""
        try:
            membership_id = f"mem_{uuid.uuid4().hex[:16]}"
            now = datetime.now(timezone.utc)
            expiration_date = now + timedelta(days=365)

            query = f'''
                INSERT INTO {self.schema}.{self.memberships_table} (
                    membership_id, user_id, organization_id, tier_code, status,
                    points_balance, tier_points, lifetime_points, pending_points,
                    enrolled_at, expiration_date, last_activity_at, auto_renew,
                    enrollment_source, promo_code, metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                RETURNING *
            '''

            params = [
                membership_id,
                user_id,
                kwargs.get("organization_id"),
                tier_code,
                MembershipStatus.ACTIVE.value,
                points_balance,
                kwargs.get("tier_points", 0),
                kwargs.get("lifetime_points", points_balance),
                kwargs.get("pending_points", 0),
                now,
                expiration_date,
                now,
                kwargs.get("auto_renew", True),
                kwargs.get("enrollment_source", "api"),
                kwargs.get("promo_code"),
                json.dumps(kwargs.get("metadata", {})),
                now,
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_membership(results[0])
            else:
                raise Exception("Failed to create membership")

        except Exception as e:
            logger.error(f"Error creating membership: {e}", exc_info=True)
            raise

    async def get_membership(self, membership_id: str) -> Optional[Membership]:
        """Get membership by ID"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.memberships_table}
                WHERE membership_id = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[membership_id])

            if result:
                return self._row_to_membership(result)
            return None

        except Exception as e:
            logger.error(f"Error getting membership {membership_id}: {e}")
            raise

    async def get_membership_by_user(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        active_only: bool = True
    ) -> Optional[Membership]:
        """Get membership for user"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)
            else:
                conditions.append("organization_id IS NULL")

            if active_only:
                conditions.append("status IN ('active', 'pending')")

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.memberships_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT 1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=params)

            if result:
                return self._row_to_membership(result)
            return None

        except Exception as e:
            logger.error(f"Error getting membership for user {user_id}: {e}")
            raise

    async def list_memberships(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status: Optional[MembershipStatus] = None,
        tier_code: Optional[MembershipTier] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Membership]:
        """List memberships with filters"""
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
                params.append(tier_code.value)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT * FROM {self.schema}.{self.memberships_table}
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_membership(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error listing memberships: {e}")
            raise

    async def count_memberships(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        status: Optional[MembershipStatus] = None,
        tier_code: Optional[MembershipTier] = None
    ) -> int:
        """Count memberships with filters"""
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
                params.append(tier_code.value)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT COUNT(*) as count FROM {self.schema}.{self.memberships_table}
                {where_clause}
            '''

            async with self.db:
                result = await self.db.query_row(query, params=params)

            return result.get("count", 0) if result else 0

        except Exception as e:
            logger.error(f"Error counting memberships: {e}")
            return 0

    # ====================
    # Points Operations
    # ====================

    async def add_points(
        self,
        membership_id: str,
        points: int,
        tier_points: int,
        source: str,
        reference_id: Optional[str] = None
    ) -> Membership:
        """Atomically add points"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.memberships_table}
                SET points_balance = points_balance + $1,
                    tier_points = tier_points + $2,
                    lifetime_points = lifetime_points + $1,
                    last_activity_at = $3,
                    updated_at = $3
                WHERE membership_id = $4
                RETURNING *
            '''

            params = [points, tier_points, now, membership_id]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_membership(results[0])
            else:
                raise Exception(f"Membership not found: {membership_id}")

        except Exception as e:
            logger.error(f"Error adding points: {e}")
            raise

    async def deduct_points(
        self,
        membership_id: str,
        points: int,
        reward_code: str,
        description: Optional[str] = None
    ) -> Membership:
        """Atomically deduct points"""
        try:
            now = datetime.now(timezone.utc)

            # First verify sufficient balance
            membership = await self.get_membership(membership_id)
            if not membership:
                raise Exception(f"Membership not found: {membership_id}")
            if membership.points_balance < points:
                raise Exception(f"Insufficient points. Available: {membership.points_balance}, Requested: {points}")

            query = f'''
                UPDATE {self.schema}.{self.memberships_table}
                SET points_balance = points_balance - $1,
                    last_activity_at = $2,
                    updated_at = $2
                WHERE membership_id = $3 AND points_balance >= $1
                RETURNING *
            '''

            params = [points, now, membership_id]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_membership(results[0])
            else:
                raise Exception("Failed to deduct points - insufficient balance or membership not found")

        except Exception as e:
            logger.error(f"Error deducting points: {e}")
            raise

    # ====================
    # Tier Operations
    # ====================

    async def update_tier(
        self,
        membership_id: str,
        new_tier: str
    ) -> Membership:
        """Update membership tier"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.memberships_table}
                SET tier_code = $1,
                    updated_at = $2
                WHERE membership_id = $3
                RETURNING *
            '''

            params = [new_tier, now, membership_id]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_membership(results[0])
            else:
                raise Exception(f"Membership not found: {membership_id}")

        except Exception as e:
            logger.error(f"Error updating tier: {e}")
            raise

    async def get_tier(self, tier_code: str) -> Optional[Tier]:
        """Get tier definition"""
        # Check cache first
        if tier_code in self._tier_cache:
            return self._tier_cache[tier_code]

        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.tiers_table}
                WHERE tier_code = $1
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[tier_code])

            if result:
                tier = self._row_to_tier(result)
                self._tier_cache[tier_code] = tier
                return tier
            return None

        except Exception as e:
            logger.error(f"Error getting tier {tier_code}: {e}")
            return None

    async def get_all_tiers(self) -> List[Tier]:
        """Get all tier definitions"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.tiers_table}
                WHERE is_active = true
                ORDER BY display_order ASC
            '''

            async with self.db:
                results = await self.db.query(query)

            return [self._row_to_tier(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting all tiers: {e}")
            return []

    # ====================
    # Status Operations
    # ====================

    async def update_status(
        self,
        membership_id: str,
        status: MembershipStatus,
        reason: Optional[str] = None
    ) -> Membership:
        """Update membership status"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.memberships_table}
                SET status = $1,
                    updated_at = $2
                WHERE membership_id = $3
                RETURNING *
            '''

            params = [status.value, now, membership_id]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_membership(results[0])
            else:
                raise Exception(f"Membership not found: {membership_id}")

        except Exception as e:
            logger.error(f"Error updating status: {e}")
            raise

    # ====================
    # History
    # ====================

    async def get_history(
        self,
        membership_id: str,
        limit: int = 50,
        offset: int = 0,
        action: Optional[PointAction] = None
    ) -> List[MembershipHistory]:
        """Get membership history"""
        try:
            conditions = ["membership_id = $1"]
            params = [membership_id]
            param_count = 1

            if action:
                param_count += 1
                conditions.append(f"action = ${param_count}")
                params.append(action.value)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.history_table}
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            async with self.db:
                results = await self.db.query(query, params=params)

            return [self._row_to_history(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []

    async def count_history(
        self,
        membership_id: str,
        action: Optional[PointAction] = None
    ) -> int:
        """Count history entries"""
        try:
            conditions = ["membership_id = $1"]
            params = [membership_id]
            param_count = 1

            if action:
                param_count += 1
                conditions.append(f"action = ${param_count}")
                params.append(action.value)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT COUNT(*) as count FROM {self.schema}.{self.history_table}
                WHERE {where_clause}
            '''

            async with self.db:
                result = await self.db.query_row(query, params=params)

            return result.get("count", 0) if result else 0

        except Exception as e:
            logger.error(f"Error counting history: {e}")
            return 0

    async def add_history(
        self,
        membership_id: str,
        action: PointAction,
        points_change: int = 0,
        **kwargs
    ) -> MembershipHistory:
        """Record history entry"""
        try:
            history_id = f"hist_{uuid.uuid4().hex[:16]}"
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.history_table} (
                    history_id, membership_id, action, points_change, balance_after,
                    previous_tier, new_tier, source, reference_id, reward_code,
                    benefit_code, description, initiated_by, metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING *
            '''

            params = [
                history_id,
                membership_id,
                action.value,
                points_change,
                kwargs.get("balance_after"),
                kwargs.get("previous_tier"),
                kwargs.get("new_tier"),
                kwargs.get("source"),
                kwargs.get("reference_id"),
                kwargs.get("reward_code"),
                kwargs.get("benefit_code"),
                kwargs.get("description"),
                kwargs.get("initiated_by", InitiatedBy.SYSTEM.value),
                json.dumps(kwargs.get("metadata", {})),
                now
            ]

            async with self.db:
                results = await self.db.query(query, params=params)

            if results and len(results) > 0:
                return self._row_to_history(results[0])
            else:
                raise Exception("Failed to add history")

        except Exception as e:
            logger.error(f"Error adding history: {e}")
            raise

    # ====================
    # Benefits
    # ====================

    async def get_tier_benefits(
        self,
        tier_code: str
    ) -> List[TierBenefit]:
        """Get benefits for tier"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.tier_benefits_table}
                WHERE tier_code = $1 AND is_active = true
            '''

            async with self.db:
                results = await self.db.query(query, params=[tier_code])

            return [self._row_to_tier_benefit(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting tier benefits: {e}")
            return []

    async def get_benefit_usage(
        self,
        membership_id: str,
        benefit_code: str
    ) -> int:
        """Get benefit usage count"""
        try:
            query = f'''
                SELECT COUNT(*) as count FROM {self.schema}.{self.history_table}
                WHERE membership_id = $1 AND benefit_code = $2 AND action = 'benefit_used'
            '''

            async with self.db:
                result = await self.db.query_row(query, params=[membership_id, benefit_code])

            return result.get("count", 0) if result else 0

        except Exception as e:
            logger.error(f"Error getting benefit usage: {e}")
            return 0

    async def record_benefit_usage(
        self,
        membership_id: str,
        benefit_code: str
    ) -> None:
        """Record benefit usage"""
        await self.add_history(
            membership_id=membership_id,
            action=PointAction.BENEFIT_USED,
            benefit_code=benefit_code,
            initiated_by=InitiatedBy.USER.value
        )

    # ====================
    # GDPR
    # ====================

    async def delete_user_data(self, user_id: str) -> int:
        """Delete all user data (GDPR)"""
        try:
            # Get all membership IDs for user
            memberships = await self.list_memberships(user_id=user_id)
            membership_ids = [m.membership_id for m in memberships]

            deleted_count = 0

            # Delete history for each membership
            for mid in membership_ids:
                query = f'''
                    DELETE FROM {self.schema}.{self.history_table}
                    WHERE membership_id = $1
                '''
                async with self.db:
                    await self.db.query(query, params=[mid])

            # Delete memberships
            query = f'''
                DELETE FROM {self.schema}.{self.memberships_table}
                WHERE user_id = $1
            '''
            async with self.db:
                await self.db.query(query, params=[user_id])
                deleted_count = len(memberships)

            logger.info(f"Deleted {deleted_count} membership records for user {user_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting user data: {e}")
            return 0

    # ====================
    # Statistics
    # ====================

    async def get_stats(self) -> Dict[str, Any]:
        """Get membership statistics"""
        try:
            query = f'''
                SELECT
                    COUNT(*) as total_memberships,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_memberships,
                    COUNT(CASE WHEN status = 'suspended' THEN 1 END) as suspended_memberships,
                    COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_memberships,
                    COUNT(CASE WHEN status = 'canceled' THEN 1 END) as canceled_memberships,
                    COALESCE(SUM(lifetime_points), 0) as total_points_issued,
                    COALESCE(SUM(lifetime_points - points_balance), 0) as total_points_redeemed
                FROM {self.schema}.{self.memberships_table}
            '''

            async with self.db:
                result = await self.db.query_row(query)

            # Get tier distribution
            tier_query = f'''
                SELECT tier_code, COUNT(*) as count
                FROM {self.schema}.{self.memberships_table}
                WHERE status = 'active'
                GROUP BY tier_code
            '''

            async with self.db:
                tier_results = await self.db.query(tier_query)

            tier_distribution = {row.get("tier_code"): row.get("count", 0) for row in tier_results} if tier_results else {}

            return {
                "total_memberships": result.get("total_memberships", 0) if result else 0,
                "active_memberships": result.get("active_memberships", 0) if result else 0,
                "suspended_memberships": result.get("suspended_memberships", 0) if result else 0,
                "expired_memberships": result.get("expired_memberships", 0) if result else 0,
                "canceled_memberships": result.get("canceled_memberships", 0) if result else 0,
                "total_points_issued": int(result.get("total_points_issued", 0)) if result else 0,
                "total_points_redeemed": int(result.get("total_points_redeemed", 0)) if result else 0,
                "tier_distribution": tier_distribution
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    # ====================
    # Helper Methods
    # ====================

    def _row_to_membership(self, row: Dict[str, Any]) -> Membership:
        """Convert database row to Membership model"""
        return Membership(
            id=row.get("id"),
            membership_id=row.get("membership_id"),
            user_id=row.get("user_id"),
            organization_id=row.get("organization_id"),
            tier_code=MembershipTier(row.get("tier_code", "bronze")),
            status=MembershipStatus(row.get("status", "active")),
            points_balance=int(row.get("points_balance", 0)),
            tier_points=int(row.get("tier_points", 0)),
            lifetime_points=int(row.get("lifetime_points", 0)),
            pending_points=int(row.get("pending_points", 0)),
            enrolled_at=row.get("enrolled_at"),
            expiration_date=row.get("expiration_date"),
            last_activity_at=row.get("last_activity_at"),
            auto_renew=row.get("auto_renew", True),
            enrollment_source=row.get("enrollment_source"),
            promo_code=row.get("promo_code"),
            metadata=row.get("metadata", {}),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )

    def _row_to_history(self, row: Dict[str, Any]) -> MembershipHistory:
        """Convert database row to MembershipHistory model"""
        return MembershipHistory(
            id=row.get("id"),
            history_id=row.get("history_id"),
            membership_id=row.get("membership_id"),
            action=PointAction(row.get("action")),
            points_change=int(row.get("points_change", 0)),
            balance_after=int(row.get("balance_after")) if row.get("balance_after") is not None else None,
            previous_tier=row.get("previous_tier"),
            new_tier=row.get("new_tier"),
            source=row.get("source"),
            reference_id=row.get("reference_id"),
            reward_code=row.get("reward_code"),
            benefit_code=row.get("benefit_code"),
            description=row.get("description"),
            initiated_by=InitiatedBy(row.get("initiated_by", "system")),
            metadata=row.get("metadata", {}),
            created_at=row.get("created_at")
        )

    def _row_to_tier(self, row: Dict[str, Any]) -> Tier:
        """Convert database row to Tier model"""
        return Tier(
            id=row.get("id"),
            tier_code=MembershipTier(row.get("tier_code")),
            tier_name=row.get("tier_name"),
            display_order=row.get("display_order", 0),
            qualification_threshold=int(row.get("qualification_threshold", 0)),
            point_multiplier=Decimal(str(row.get("point_multiplier", 1.0))),
            is_active=row.get("is_active", True),
            created_at=row.get("created_at")
        )

    def _row_to_tier_benefit(self, row: Dict[str, Any]) -> TierBenefit:
        """Convert database row to TierBenefit model"""
        return TierBenefit(
            id=row.get("id"),
            benefit_id=row.get("benefit_id"),
            tier_code=MembershipTier(row.get("tier_code")),
            benefit_code=row.get("benefit_code"),
            benefit_name=row.get("benefit_name"),
            benefit_type=row.get("benefit_type"),
            usage_limit=row.get("usage_limit"),
            is_unlimited=row.get("is_unlimited", False),
            is_active=row.get("is_active", True),
            created_at=row.get("created_at")
        )


__all__ = ["MembershipRepository"]
