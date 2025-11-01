"""
Invitation Repository

邀请数据访问层 - PostgreSQL + gRPC
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import uuid
import secrets

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from .models import (
    InvitationStatus, OrganizationRole,
    InvitationResponse, InvitationDetailResponse
)

logger = logging.getLogger(__name__)


class InvitationRepository:
    """邀请数据仓库 - PostgreSQL"""

    def __init__(self):
        self.db = PostgresClient(
            host=os.getenv("POSTGRES_GRPC_HOST", "isa-postgres-grpc"),
            port=int(os.getenv("POSTGRES_GRPC_PORT", "50061")),
            user_id="invitation_service"
        )
        self.schema = "invitation"
        self.invitations_table = "organization_invitations"

    # ============ Invitation CRUD Operations ============

    async def create_invitation(
        self,
        organization_id: str,
        email: str,
        role: OrganizationRole,
        invited_by: str
    ) -> Optional[InvitationResponse]:
        """创建邀请"""
        try:
            # 生成邀请ID和令牌
            invitation_id = str(uuid.uuid4())
            invitation_token = secrets.token_urlsafe(32)

            # 设置过期时间（7天）
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            now = datetime.now(timezone.utc)

            query = f'''
                INSERT INTO {self.schema}.{self.invitations_table} (
                    invitation_id, organization_id, email, role, invited_by,
                    invitation_token, status, expires_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
            '''

            params = [
                invitation_id,
                organization_id,
                email,
                role.value,
                invited_by,
                invitation_token,
                InvitationStatus.PENDING.value,
                expires_at,
                now,
                now
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                return InvitationResponse(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error creating invitation: {e}", exc_info=True)
            return None

    async def get_invitation_by_id(self, invitation_id: str) -> Optional[InvitationResponse]:
        """根据ID获取邀请"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.invitations_table}
                WHERE invitation_id = $1
            '''

            with self.db:
                results = self.db.query(query, [invitation_id], schema=self.schema)

            if results and len(results) > 0:
                return InvitationResponse(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting invitation by id: {e}")
            return None

    async def get_invitation_by_token(self, invitation_token: str) -> Optional[InvitationResponse]:
        """根据令牌获取邀请"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.invitations_table}
                WHERE invitation_token = $1
            '''

            with self.db:
                results = self.db.query(query, [invitation_token], schema=self.schema)

            if results and len(results) > 0:
                return InvitationResponse(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting invitation by token: {e}")
            return None

    async def get_invitation_with_organization_info(self, invitation_token: str) -> Optional[Dict[str, Any]]:
        """获取邀请及组织信息 - 注意：需要跨服务调用获取组织和用户信息"""
        try:
            # 首先获取邀请信息
            invitation = await self.get_invitation_by_token(invitation_token)

            if not invitation:
                return None

            # 将Pydantic模型转换为字典
            result = invitation.dict()

            # TODO: 使用服务发现获取组织和用户信息
            # 当前返回基本邀请信息，组织和用户信息需要通过其他微服务获取
            logger.warning("Organization and user info require cross-service calls - returning invitation only")

            return result

        except Exception as e:
            logger.error(f"Error getting invitation with organization info: {e}")
            return None

    async def get_pending_invitation_by_email_and_organization(
        self,
        email: str,
        organization_id: str
    ) -> Optional[InvitationResponse]:
        """根据邮箱和组织ID获取待处理邀请"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.invitations_table}
                WHERE email = $1 AND organization_id = $2 AND status = $3
                ORDER BY created_at DESC
                LIMIT 1
            '''

            with self.db:
                results = self.db.query(
                    query,
                    [email, organization_id, InvitationStatus.PENDING.value],
                    schema=self.schema
                )

            if results and len(results) > 0:
                return InvitationResponse(**results[0])
            return None

        except Exception as e:
            logger.error(f"Error getting pending invitation by email and organization: {e}")
            return None

    async def get_organization_invitations(
        self,
        organization_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[InvitationResponse]:
        """获取组织的邀请列表"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.invitations_table}
                WHERE organization_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            '''

            with self.db:
                results = self.db.query(query, [organization_id, limit, offset], schema=self.schema)

            if results:
                # 返回基本邀请响应
                # 注意：InvitationDetailResponse需要组织和用户信息，需要跨服务调用
                return [InvitationResponse(**inv) for inv in results]
            return []

        except Exception as e:
            logger.error(f"Error getting organization invitations: {e}")
            return []

    async def update_invitation(self, invitation_id: str, update_data: Dict[str, Any]) -> bool:
        """更新邀请"""
        try:
            # Build SET clause dynamically
            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                if key == "updated_at":
                    continue
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            # Add updated_at
            param_count += 1
            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc))

            # Add invitation_id for WHERE clause
            param_count += 1
            params.append(invitation_id)

            query = f'''
                UPDATE {self.schema}.{self.invitations_table}
                SET {", ".join(set_clauses)}
                WHERE invitation_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating invitation: {e}")
            return False

    async def accept_invitation(self, invitation_token: str) -> bool:
        """接受邀请"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.invitations_table}
                SET status = $1, accepted_at = $2, updated_at = $3
                WHERE invitation_token = $4 AND status = $5
            '''

            params = [
                InvitationStatus.ACCEPTED.value,
                now,
                now,
                invitation_token,
                InvitationStatus.PENDING.value
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error accepting invitation: {e}")
            return False

    async def cancel_invitation(self, invitation_id: str) -> bool:
        """取消邀请"""
        try:
            return await self.update_invitation(invitation_id, {
                'status': InvitationStatus.CANCELLED.value
            })

        except Exception as e:
            logger.error(f"Error cancelling invitation: {e}")
            return False

    async def expire_old_invitations(self) -> int:
        """过期旧邀请"""
        try:
            now = datetime.now(timezone.utc)

            query = f'''
                UPDATE {self.schema}.{self.invitations_table}
                SET status = $1, updated_at = $2
                WHERE status = $3 AND expires_at < $4
            '''

            params = [
                InvitationStatus.EXPIRED.value,
                now,
                InvitationStatus.PENDING.value,
                now
            ]

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count if count is not None else 0

        except Exception as e:
            logger.error(f"Error expiring old invitations: {e}")
            return 0

    async def delete_invitation(self, invitation_id: str) -> bool:
        """删除邀请"""
        try:
            query = f'''
                DELETE FROM {self.schema}.{self.invitations_table}
                WHERE invitation_id = $1
            '''

            with self.db:
                count = self.db.execute(query, [invitation_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error deleting invitation: {e}")
            return False

    # ============ Statistics ============

    async def get_invitation_stats(self, organization_id: Optional[str] = None) -> Dict[str, int]:
        """获取邀请统计"""
        try:
            conditions = []
            params = []
            param_count = 0

            if organization_id:
                param_count += 1
                conditions.append(f"organization_id = ${param_count}")
                params.append(organization_id)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f'''
                SELECT status, COUNT(*) as count
                FROM {self.schema}.{self.invitations_table}
                {where_clause}
                GROUP BY status
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            stats = {"total": 0, "pending": 0, "accepted": 0, "expired": 0, "cancelled": 0}

            for row in results:
                status = row.get("status")
                count = row.get("count", 0)
                if status in stats:
                    stats[status] = count
                stats["total"] += count

            return stats

        except Exception as e:
            logger.error(f"Error getting invitation stats: {e}")
            return {"total": 0, "pending": 0, "accepted": 0, "expired": 0, "cancelled": 0}

    # ============ Event Handler Methods ============

    async def cancel_organization_invitations(self, organization_id: str) -> int:
        """
        Cancel all pending invitations for an organization (for organization.deleted event)

        Args:
            organization_id: Organization ID

        Returns:
            int: Number of invitations cancelled
        """
        try:
            query = f'''
                UPDATE {self.schema}.{self.invitations_table}
                SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = $2
                AND status = $3
            '''

            with self.db:
                count = self.db.execute(
                    query,
                    [InvitationStatus.CANCELLED.value, organization_id, InvitationStatus.PENDING.value],
                    schema=self.schema
                )

            logger.info(f"Cancelled {count} invitations for organization {organization_id}")
            return count if count else 0

        except Exception as e:
            logger.error(f"Error cancelling organization invitations: {e}")
            return 0

    async def cancel_invitations_by_inviter(self, user_id: str) -> int:
        """
        Cancel all pending invitations sent by a user (for user.deleted event)

        Args:
            user_id: User ID who sent the invitations

        Returns:
            int: Number of invitations cancelled
        """
        try:
            query = f'''
                UPDATE {self.schema}.{self.invitations_table}
                SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE invited_by = $2
                AND status = $3
            '''

            with self.db:
                count = self.db.execute(
                    query,
                    [InvitationStatus.CANCELLED.value, user_id, InvitationStatus.PENDING.value],
                    schema=self.schema
                )

            logger.info(f"Cancelled {count} invitations sent by user {user_id}")
            return count if count else 0

        except Exception as e:
            logger.error(f"Error cancelling invitations by inviter: {e}")
            return 0


__all__ = ["InvitationRepository"]
