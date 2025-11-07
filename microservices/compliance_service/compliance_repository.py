"""
Compliance Repository

数据访问层 - PostgreSQL + gRPC
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from core.config_manager import ConfigManager
from .models import (
    ComplianceCheck, CompliancePolicy, ComplianceStatus,
    RiskLevel, ComplianceCheckType, ContentType
)

logger = logging.getLogger(__name__)


class ComplianceRepository:
    """合规数据访问层 - PostgreSQL"""

    def __init__(self, config: Optional[ConfigManager] = None):
        # Use config_manager for service discovery
        if config is None:
            config = ConfigManager("compliance_service")

        # Discover PostgreSQL service
        # Priority: environment variables → Consul → localhost fallback
        host, port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        logger.info(f"Connecting to PostgreSQL at {host}:{port}")
        self.db = PostgresClient(
            host=host,
            port=port,
            user_id="compliance_service"
        )
        self.schema = "compliance"
        self.checks_table = "compliance_checks"
        self.policies_table = "compliance_policies"

    # ====================
    # 合规检查记录管理
    # ====================

    async def create_check(self, check: ComplianceCheck) -> Optional[ComplianceCheck]:
        """创建合规检查记录"""
        try:
            query = f'''
                INSERT INTO {self.schema}.{self.checks_table} (
                    check_id, check_type, content_type, status, risk_level,
                    user_id, organization_id, session_id, request_id, content_id,
                    content_hash, content_size, confidence_score,
                    violations, warnings, detected_issues, moderation_categories, detected_pii,
                    action_taken, blocked_reason, human_review_required,
                    reviewed_by, review_notes, metadata, provider,
                    checked_at, reviewed_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                          $11, $12, $13, $14, $15, $16, $17, $18,
                          $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29)
                RETURNING *
            '''

            import json
            now = datetime.now(timezone.utc)

            params = [
                check.check_id,
                check.check_type.value,
                check.content_type.value,
                check.status.value,
                check.risk_level.value,
                check.user_id,
                check.organization_id,
                check.session_id,
                check.request_id,
                check.content_id,
                check.content_hash,
                check.content_size,
                check.confidence_score,
                json.dumps(check.violations) if check.violations else "[]",
                json.dumps(check.warnings) if check.warnings else "[]",
                json.dumps(check.detected_issues) if check.detected_issues else "{}",
                json.dumps(check.moderation_categories) if check.moderation_categories else "[]",
                json.dumps(check.detected_pii) if check.detected_pii else "[]",
                check.action_taken,
                check.blocked_reason,
                check.human_review_required,
                check.reviewed_by,
                check.review_notes,
                json.dumps(check.metadata) if check.metadata else "{}",
                check.provider,
                check.checked_at,
                check.reviewed_at,
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                logger.info(f"Created compliance check: {check.check_id}")
                return ComplianceCheck(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error creating compliance check: {e}", exc_info=True)
            return None

    async def get_check_by_id(self, check_id: str) -> Optional[ComplianceCheck]:
        """根据ID获取合规检查记录"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.checks_table}
                WHERE check_id = $1
            '''

            with self.db:
                results = self.db.query(query, [check_id], schema=self.schema)

            if results and len(results) > 0:
                return ComplianceCheck(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting compliance check {check_id}: {e}")
            return None

    async def get_checks_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        status: Optional[ComplianceStatus] = None,
        risk_level: Optional[RiskLevel] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ComplianceCheck]:
        """获取用户的合规检查记录"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status.value)

            if risk_level:
                param_count += 1
                conditions.append(f"risk_level = ${param_count}")
                params.append(risk_level.value)

            if start_date:
                param_count += 1
                conditions.append(f"checked_at >= ${param_count}")
                params.append(start_date)

            if end_date:
                param_count += 1
                conditions.append(f"checked_at <= ${param_count}")
                params.append(end_date)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT * FROM {self.schema}.{self.checks_table}
                WHERE {where_clause}
                ORDER BY checked_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            '''

            params.extend([limit, offset])

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return [ComplianceCheck(**item) for item in results] if results else []

        except Exception as e:
            logger.error(f"Error getting checks for user {user_id}: {e}")
            return []

    async def get_checks_by_organization(
        self,
        organization_id: str,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[ComplianceCheck]:
        """获取组织的合规检查记录"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.checks_table}
                WHERE organization_id = $1
                ORDER BY checked_at DESC
                LIMIT $2 OFFSET $3
            '''

            with self.db:
                results = self.db.query(query, [organization_id, limit, offset], schema=self.schema)

            return [ComplianceCheck(**item) for item in results] if results else []

        except Exception as e:
            logger.error(f"Error getting checks for org {organization_id}: {e}")
            return []

    async def get_pending_reviews(self, limit: int = 50) -> List[ComplianceCheck]:
        """获取需要人工审核的记录"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.checks_table}
                WHERE human_review_required = TRUE
                  AND status = $1
                  AND reviewed_by IS NULL
                ORDER BY checked_at ASC
                LIMIT $2
            '''

            with self.db:
                results = self.db.query(query, [ComplianceStatus.PENDING.value, limit], schema=self.schema)

            return [ComplianceCheck(**item) for item in results] if results else []

        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            return []

    async def update_review_status(
        self,
        check_id: str,
        reviewed_by: str,
        status: ComplianceStatus,
        review_notes: Optional[str] = None
    ) -> bool:
        """更新审核状态"""
        try:
            query = f'''
                UPDATE {self.schema}.{self.checks_table}
                SET status = $1,
                    reviewed_by = $2,
                    reviewed_at = $3,
                    review_notes = $4,
                    updated_at = $5
                WHERE check_id = $6
            '''

            now = datetime.now(timezone.utc)
            params = [status.value, reviewed_by, now, review_notes, now, check_id]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating review status: {e}")
            return False

    # ====================
    # 统计和报告
    # ====================

    async def get_statistics(
        self,
        organization_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取统计数据"""
        try:
            conditions = []
            params = []
            param_count = 0

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            if start_date:
                param_count += 1
                conditions.append(f"checked_at >= ${param_count}")
                params.append(start_date)

            if end_date:
                param_count += 1
                conditions.append(f"checked_at <= ${param_count}")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT
                    COUNT(*) as total_checks,
                    COUNT(CASE WHEN status = 'pass' THEN 1 END) as passed_checks,
                    COUNT(CASE WHEN status = 'fail' THEN 1 END) as failed_checks,
                    COUNT(CASE WHEN status = 'flagged' THEN 1 END) as flagged_checks
                FROM {self.schema}.{self.checks_table}
                {where_clause}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                stats = results[0]
                return {
                    "total_checks": stats.get("total_checks", 0),
                    "passed_checks": stats.get("passed_checks", 0),
                    "failed_checks": stats.get("failed_checks", 0),
                    "flagged_checks": stats.get("flagged_checks", 0),
                    "violations_by_type": {},  # TODO: Aggregate from JSONB
                    "violations_by_risk": {}
                }

            return {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "flagged_checks": 0,
                "violations_by_type": {},
                "violations_by_risk": {}
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "flagged_checks": 0,
                "violations_by_type": {},
                "violations_by_risk": {}
            }

    async def get_violations_summary(
        self,
        organization_id: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """获取违规摘要"""
        try:
            from datetime import timedelta
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            conditions = [f"checked_at >= $1"]
            params = [start_date]
            param_count = 1

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            where_clause = " AND ".join(conditions)

            query = f'''
                SELECT
                    check_type,
                    risk_level,
                    COUNT(*) as count
                FROM {self.schema}.{self.checks_table}
                WHERE {where_clause} AND status != 'pass'
                GROUP BY check_type, risk_level
                ORDER BY count DESC
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            return results if results else []

        except Exception as e:
            logger.error(f"Error getting violations summary: {e}")
            return []

    # ====================
    # 合规策略管理
    # ====================

    async def create_policy(self, policy: CompliancePolicy) -> Optional[CompliancePolicy]:
        """创建合规策略"""
        try:
            import json

            query = f'''
                INSERT INTO {self.schema}.{self.policies_table} (
                    policy_id, organization_id, policy_name, description, enabled,
                    check_types, content_types, rules, thresholds,
                    auto_block, require_review, notify_admin,
                    created_by, metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING *
            '''

            now = datetime.now(timezone.utc)
            params = [
                policy.policy_id,
                policy.organization_id,
                policy.policy_name,
                policy.description,
                policy.enabled,
                policy.check_types,  # Array
                policy.content_types,  # Array
                json.dumps(policy.rules),
                json.dumps(policy.thresholds) if policy.thresholds else "{}",
                policy.auto_block,
                policy.require_review,
                policy.notify_admin,
                policy.created_by,
                json.dumps(policy.metadata) if policy.metadata else "{}",
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return CompliancePolicy(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error creating compliance policy: {e}", exc_info=True)
            return None

    async def get_policy_by_id(self, policy_id: str) -> Optional[CompliancePolicy]:
        """根据ID获取合规策略"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.policies_table}
                WHERE policy_id = $1
            '''

            with self.db:
                results = self.db.query(query, [policy_id], schema=self.schema)

            if results and len(results) > 0:
                return CompliancePolicy(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting policy {policy_id}: {e}")
            return None

    async def get_active_policies(
        self,
        organization_id: str
    ) -> List[CompliancePolicy]:
        """获取组织的活跃策略"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.policies_table}
                WHERE organization_id = $1 AND enabled = TRUE
                ORDER BY created_at DESC
            '''

            with self.db:
                results = self.db.query(query, [organization_id], schema=self.schema)

            return [CompliancePolicy(**item) for item in results] if results else []

        except Exception as e:
            logger.error(f"Error getting active policies for org {organization_id}: {e}")
            return []

    # ====================
    # GDPR 数据管理
    # ====================

    async def delete_user_data(self, user_id: str) -> int:
        """删除用户数据（GDPR Article 17: Right to Erasure）"""
        try:
            query = f'''
                DELETE FROM {self.schema}.{self.checks_table}
                WHERE user_id = $1
            '''

            with self.db:
                count = self.db.execute(query, [user_id], schema=self.schema)

            logger.info(f"Deleted {count} compliance records for user {user_id}")
            return count if count is not None else 0

        except Exception as e:
            logger.error(f"Error deleting user data for {user_id}: {e}")
            raise

    async def update_user_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """更新用户同意记录（GDPR Article 7: Conditions for consent）

        Note: This is a simplified implementation.
        In production, you should create a dedicated consent_records table.
        """
        try:
            # For now, we log consent in metadata
            # In production, create a separate consent_records table
            logger.info(
                f"Consent {'granted' if granted else 'revoked'} for user {user_id}: "
                f"{consent_type} (ip: {ip_address}, agent: {user_agent})"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating consent for {user_id}: {e}")
            return False

    async def initialize(self):
        """初始化合规服务（如需要）"""
        logger.info("Compliance repository initialized with PostgreSQL")


__all__ = ["ComplianceRepository"]
