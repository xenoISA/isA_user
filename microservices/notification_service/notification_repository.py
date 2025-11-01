"""
Notification Service Repository Layer

数据访问层，负责与数据库交互
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import logging
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct, ListValue

from isa_common.postgres_client import PostgresClient
from .models import (
    Notification, NotificationTemplate, InAppNotification,
    NotificationBatch, NotificationStatus, NotificationType,
    TemplateStatus, NotificationPriority, PushSubscription, PushPlatform
)


logger = logging.getLogger(__name__)


def _convert_protobuf_to_native(value: Any) -> Any:
    """Convert Protobuf types to Python native types"""
    if isinstance(value, ListValue):
        return list(value)
    elif isinstance(value, Struct):
        return MessageToDict(value)
    elif isinstance(value, (list, tuple)):
        return [_convert_protobuf_to_native(item) for item in value]
    elif isinstance(value, dict):
        return {k: _convert_protobuf_to_native(v) for k, v in value.items()}
    else:
        return value


class NotificationRepository:
    """通知数据访问层"""

    def __init__(self):
        self.db = PostgresClient(
            host=os.getenv("POSTGRES_GRPC_HOST", "isa-postgres-grpc"),
            port=int(os.getenv("POSTGRES_GRPC_PORT", "50061")),
            user_id="notification_service"
        )
        self.schema = "notification"

    # ====================
    # 通知模板管理
    # ====================

    async def create_template(self, template: NotificationTemplate) -> NotificationTemplate:
        """创建通知模板"""
        try:
            now = datetime.now(timezone.utc)
            template_data = {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "type": template.type.value,
                "subject": template.subject,
                "content": template.content,
                "html_content": template.html_content,
                "variables": template.variables or [],  # Direct list
                "metadata": template.metadata or {},  # Direct dict
                "status": template.status.value,
                "version": template.version,
                "created_by": template.created_by,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            with self.db:
                count = self.db.insert_into("notification_templates", [template_data], schema=self.schema)

            if count is not None and count > 0:
                # Query back to get the generated id
                query = f'SELECT * FROM {self.schema}.notification_templates WHERE template_id = $1'
                with self.db:
                    results = self.db.query(query, [template.template_id], schema=self.schema)

                if results and len(results) > 0:
                    created_template = results[0]
                    template.id = created_template["id"]
                    template.created_at = datetime.fromisoformat(created_template["created_at"])
                    template.updated_at = datetime.fromisoformat(created_template["updated_at"])
                return template

            raise Exception("Failed to create template")

        except Exception as e:
            logger.error(f"Failed to create template: {str(e)}")
            raise

    async def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """获取通知模板"""
        try:
            query = f'SELECT * FROM {self.schema}.notification_templates WHERE template_id = $1 LIMIT 1'

            with self.db:
                results = self.db.query(query, [template_id], schema=self.schema)

            if results and len(results) > 0:
                return self._parse_template(results[0])

            return None

        except Exception as e:
            logger.error(f"Failed to get template {template_id}: {str(e)}")
            return None

    async def list_templates(
        self,
        type: Optional[NotificationType] = None,
        status: Optional[TemplateStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[NotificationTemplate]:
        """列出通知模板"""
        try:
            conditions = []
            params = []
            param_count = 0

            if type:
                param_count += 1
                conditions.append(f"type = ${param_count}")
                params.append(type.value)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status.value)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f'''
                SELECT * FROM {self.schema}.notification_templates
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            templates = []
            for data in results:
                template = self._parse_template(data)
                if template:
                    templates.append(template)

            return templates

        except Exception as e:
            logger.error(f"Failed to list templates: {str(e)}")
            return []

    async def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """更新通知模板"""
        try:
            update_parts = []
            params = []
            param_count = 0

            # 处理更新字段
            if "name" in updates:
                param_count += 1
                update_parts.append(f"name = ${param_count}")
                params.append(updates["name"])

            if "description" in updates:
                param_count += 1
                update_parts.append(f"description = ${param_count}")
                params.append(updates["description"])

            if "subject" in updates:
                param_count += 1
                update_parts.append(f"subject = ${param_count}")
                params.append(updates["subject"])

            if "content" in updates:
                param_count += 1
                update_parts.append(f"content = ${param_count}")
                params.append(updates["content"])

            if "html_content" in updates:
                param_count += 1
                update_parts.append(f"html_content = ${param_count}")
                params.append(updates["html_content"])

            if "variables" in updates:
                param_count += 1
                update_parts.append(f"variables = ${param_count}")
                params.append(updates["variables"])  # Direct list

            if "status" in updates:
                param_count += 1
                update_parts.append(f"status = ${param_count}")
                status_value = updates["status"].value if hasattr(updates["status"], "value") else updates["status"]
                params.append(status_value)

            if "metadata" in updates:
                param_count += 1
                update_parts.append(f"metadata = ${param_count}")
                params.append(updates["metadata"])  # Direct dict

            if not update_parts:
                return True

            # Add updated_at
            param_count += 1
            update_parts.append(f"updated_at = ${param_count}")
            params.append(datetime.now(timezone.utc).isoformat())

            # Add template_id for WHERE clause
            param_count += 1
            params.append(template_id)

            set_clause = ", ".join(update_parts)
            query = f'''
                UPDATE {self.schema}.notification_templates
                SET {set_clause}
                WHERE template_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to update template {template_id}: {str(e)}")
            return False

    # ====================
    # 通知管理
    # ====================

    async def create_notification(self, notification: Notification) -> Notification:
        """创建通知"""
        try:
            now = datetime.now(timezone.utc)

            # Determine user_id - fallback to email or phone if no recipient_id provided
            user_id = notification.recipient_id
            if not user_id:
                # For email notifications without user_id, use email as identifier
                if notification.recipient_email:
                    user_id = f"email:{notification.recipient_email}"
                elif notification.recipient_phone:
                    user_id = f"phone:{notification.recipient_phone}"
                else:
                    user_id = "system"  # Fallback for system notifications

            notification_data = {
                "notification_id": notification.notification_id,
                "user_id": user_id,
                "type": notification.type.value,
                "channel": getattr(notification, 'channel', None),
                "recipient": getattr(notification, 'recipient', notification.recipient_email or notification.recipient_phone or ''),
                "priority": notification.priority.value,
                "subject": notification.subject,
                "content": notification.content,
                "html_content": notification.html_content,
                "template_id": notification.template_id,
                "variables": notification.variables or {},  # Direct dict
                "metadata": notification.metadata or {},  # Direct dict
                "scheduled_at": notification.scheduled_at.isoformat() if notification.scheduled_at else None,
                "retry_count": notification.retry_count,
                "max_retries": notification.max_retries,
                "status": notification.status.value,
                "error_message": notification.error_message,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            with self.db:
                count = self.db.insert_into("notifications", [notification_data], schema=self.schema)

            if count is not None and count > 0:
                notification.created_at = now
                return notification

            raise Exception("Failed to create notification")

        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            raise

    async def get_notification(self, notification_id: str) -> Optional[Notification]:
        """获取通知"""
        try:
            query = f'SELECT * FROM {self.schema}.notifications WHERE notification_id = $1 LIMIT 1'

            with self.db:
                results = self.db.query(query, [notification_id], schema=self.schema)

            if results and len(results) > 0:
                return self._parse_notification(results[0])

            return None

        except Exception as e:
            logger.error(f"Failed to get notification {notification_id}: {str(e)}")
            return None

    async def list_notifications(
        self,
        user_id: Optional[str] = None,
        type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        priority: Optional[NotificationPriority] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Notification]:
        """列出通知"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if type:
                param_count += 1
                conditions.append(f"type = ${param_count}")
                params.append(type.value)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status.value)

            if priority:
                param_count += 1
                conditions.append(f"priority = ${param_count}")
                params.append(priority.value)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f'''
                SELECT * FROM {self.schema}.notifications
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            notifications = []
            for data in results:
                notification = self._parse_notification(data)
                if notification:
                    notifications.append(notification)

            return notifications

        except Exception as e:
            logger.error(f"Failed to list notifications: {str(e)}")
            return []

    async def update_notification_status(
        self,
        notification_id: str,
        status: NotificationStatus,
        error_message: Optional[str] = None,
        provider_message_id: Optional[str] = None
    ) -> bool:
        """更新通知状态"""
        try:
            now = datetime.now(timezone.utc)
            update_parts = ["status = $1"]
            params = [status.value]
            param_count = 1

            # 根据状态更新相应的时间戳
            if status == NotificationStatus.SENT:
                param_count += 1
                update_parts.append(f"sent_at = ${param_count}")
                params.append(now.isoformat())
            elif status == NotificationStatus.DELIVERED:
                param_count += 1
                update_parts.append(f"delivered_at = ${param_count}")
                params.append(now.isoformat())
            elif status == NotificationStatus.FAILED:
                if error_message:
                    param_count += 1
                    update_parts.append(f"error_message = ${param_count}")
                    params.append(error_message)

            if provider_message_id:
                param_count += 1
                update_parts.append(f"provider_message_id = ${param_count}")
                params.append(provider_message_id)

            param_count += 1
            params.append(notification_id)

            set_clause = ", ".join(update_parts)
            query = f'''
                UPDATE {self.schema}.notifications
                SET {set_clause}
                WHERE notification_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to update notification status {notification_id}: {str(e)}")
            return False

    async def get_pending_notifications(self, limit: int = 100) -> List[Notification]:
        """获取待发送的通知"""
        try:
            now = datetime.now(timezone.utc).isoformat()

            query = f'''
                SELECT * FROM {self.schema}.notifications
                WHERE status = $1
                AND (scheduled_at IS NULL OR scheduled_at <= $2)
                ORDER BY priority, created_at
                LIMIT {limit}
            '''

            with self.db:
                results = self.db.query(query, [NotificationStatus.PENDING.value, now], schema=self.schema)

            notifications = []
            for data in results:
                notification = self._parse_notification(data)
                if notification:
                    notifications.append(notification)

            return notifications

        except Exception as e:
            logger.error(f"Failed to get pending notifications: {str(e)}")
            return []

    # ====================
    # 应用内通知管理
    # ====================

    async def create_in_app_notification(self, notification: InAppNotification) -> InAppNotification:
        """创建应用内通知"""
        try:
            now = datetime.now(timezone.utc)
            notification_data = {
                "notification_id": notification.notification_id,
                "user_id": notification.user_id,
                "title": notification.title,
                "message": notification.message,
                "type": getattr(notification, 'type', 'info'),
                "category": notification.category,
                "priority": notification.priority.value,
                "action_type": getattr(notification, 'action_type', None),
                "action_url": notification.action_url,
                "action_data": getattr(notification, 'action_data', {}),  # Direct dict
                "icon": notification.icon,
                "avatar_url": getattr(notification, 'avatar_url', None),
                "is_read": notification.is_read,
                "is_archived": notification.is_archived,
                "metadata": getattr(notification, 'metadata', {}),  # Direct dict
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            with self.db:
                count = self.db.insert_into("in_app_notifications", [notification_data], schema=self.schema)

            if count is not None and count > 0:
                notification.created_at = now
                return notification

            raise Exception("Failed to create in-app notification")

        except Exception as e:
            logger.error(f"Failed to create in-app notification: {str(e)}")
            raise

    async def list_user_in_app_notifications(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[InAppNotification]:
        """列出用户的应用内通知"""
        try:
            conditions = ["user_id = $1"]
            params = [user_id]
            param_count = 1

            if is_read is not None:
                param_count += 1
                conditions.append(f"is_read = ${param_count}")
                params.append(is_read)

            if is_archived is not None:
                param_count += 1
                conditions.append(f"is_archived = ${param_count}")
                params.append(is_archived)

            if category:
                param_count += 1
                conditions.append(f"category = ${param_count}")
                params.append(category)

            where_clause = " AND ".join(conditions)
            query = f'''
                SELECT * FROM {self.schema}.in_app_notifications
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            notifications = []
            for data in results:
                notification = self._parse_in_app_notification(data)
                if notification:
                    notifications.append(notification)

            return notifications

        except Exception as e:
            logger.error(f"Failed to list user in-app notifications: {str(e)}")
            return []

    async def mark_notification_as_read(self, notification_id: str, user_id: str) -> bool:
        """标记通知为已读"""
        try:
            now = datetime.now(timezone.utc).isoformat()

            query = f'''
                UPDATE {self.schema}.in_app_notifications
                SET is_read = TRUE, read_at = $1
                WHERE notification_id = $2 AND user_id = $3
            '''

            with self.db:
                count = self.db.execute(query, [now, notification_id, user_id], schema=self.schema)

            # 同时更新主通知表的已读时间
            if count is not None and count > 0:
                update_query = f'''
                    UPDATE {self.schema}.notifications
                    SET read_at = $1
                    WHERE notification_id = $2
                '''
                with self.db:
                    self.db.execute(update_query, [now, notification_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to mark notification as read {notification_id}: {str(e)}")
            return False

    async def mark_notification_as_archived(self, notification_id: str, user_id: str) -> bool:
        """标记通知为已归档"""
        try:
            now = datetime.now(timezone.utc).isoformat()

            query = f'''
                UPDATE {self.schema}.in_app_notifications
                SET is_archived = TRUE, archived_at = $1
                WHERE notification_id = $2 AND user_id = $3
            '''

            with self.db:
                count = self.db.execute(query, [now, notification_id, user_id], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to mark notification as archived {notification_id}: {str(e)}")
            return False

    async def get_unread_count(self, user_id: str) -> int:
        """获取未读通知数量"""
        try:
            query = f'''
                SELECT COUNT(*) as count
                FROM {self.schema}.in_app_notifications
                WHERE user_id = $1 AND is_read = FALSE AND is_archived = FALSE
            '''

            with self.db:
                results = self.db.query(query, [user_id], schema=self.schema)

            if results and len(results) > 0:
                return results[0].get("count", 0)

            return 0

        except Exception as e:
            logger.error(f"Failed to get unread count for user {user_id}: {str(e)}")
            return 0

    # ====================
    # 批量通知管理
    # ====================

    async def create_batch(self, batch: NotificationBatch) -> NotificationBatch:
        """创建批量通知"""
        try:
            now = datetime.now(timezone.utc)
            batch_data = {
                "batch_id": batch.batch_id,
                "name": batch.name,
                "template_id": batch.template_id,
                "type": batch.type.value,
                "total_count": getattr(batch, 'total_recipients', 0),
                "sent_count": batch.sent_count,
                "delivered_count": batch.delivered_count,
                "failed_count": batch.failed_count,
                "status": getattr(batch, 'status', 'pending'),
                "scheduled_at": batch.scheduled_at.isoformat() if batch.scheduled_at else None,
                "metadata": batch.metadata or {},  # Direct dict
                "created_by": batch.created_by,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            with self.db:
                count = self.db.insert_into("notification_batches", [batch_data], schema=self.schema)

            if count is not None and count > 0:
                batch.created_at = now
                return batch

            raise Exception("Failed to create batch")

        except Exception as e:
            logger.error(f"Failed to create batch: {str(e)}")
            raise

    async def update_batch_stats(
        self,
        batch_id: str,
        sent_count: Optional[int] = None,
        delivered_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        completed: bool = False
    ) -> bool:
        """更新批量通知统计"""
        try:
            update_parts = []
            params = []
            param_count = 0

            if sent_count is not None:
                param_count += 1
                update_parts.append(f"sent_count = ${param_count}")
                params.append(sent_count)

            if delivered_count is not None:
                param_count += 1
                update_parts.append(f"delivered_count = ${param_count}")
                params.append(delivered_count)

            if failed_count is not None:
                param_count += 1
                update_parts.append(f"failed_count = ${param_count}")
                params.append(failed_count)

            if completed:
                param_count += 1
                update_parts.append(f"completed_at = ${param_count}")
                params.append(datetime.now(timezone.utc).isoformat())

                param_count += 1
                update_parts.append(f"status = ${param_count}")
                params.append('completed')

            if not update_parts:
                return True

            param_count += 1
            params.append(batch_id)

            set_clause = ", ".join(update_parts)
            query = f'''
                UPDATE {self.schema}.notification_batches
                SET {set_clause}
                WHERE batch_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to update batch stats {batch_id}: {str(e)}")
            return False

    # ====================
    # Push订阅管理
    # ====================

    async def register_push_subscription(self, subscription: PushSubscription) -> PushSubscription:
        """注册推送订阅"""
        try:
            now = datetime.now(timezone.utc)
            subscription_data = {
                "subscription_id": getattr(subscription, 'subscription_id', f"{subscription.user_id}_{subscription.device_token}"),
                "user_id": subscription.user_id,
                "device_token": subscription.device_token,
                "platform": subscription.platform.value,
                "device_id": getattr(subscription, 'device_id', None),
                "device_name": subscription.device_name,
                "app_version": subscription.app_version,
                "os_version": getattr(subscription, 'os_version', None),
                "endpoint": subscription.endpoint,
                "p256dh": getattr(subscription, 'p256dh_key', None),
                "auth": getattr(subscription, 'auth_key', None),
                "topics": getattr(subscription, 'topics', []),  # Direct list -> TEXT[]
                "is_active": subscription.is_active,
                "metadata": getattr(subscription, 'metadata', {}),  # Direct dict
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }

            # Use INSERT ... ON CONFLICT to upsert
            query = f'''
                INSERT INTO {self.schema}.push_subscriptions (
                    subscription_id, user_id, device_token, platform, device_id, device_name,
                    app_version, os_version, endpoint, p256dh, auth, topics, is_active,
                    metadata, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (user_id, device_token, platform)
                DO UPDATE SET
                    device_name = EXCLUDED.device_name,
                    app_version = EXCLUDED.app_version,
                    os_version = EXCLUDED.os_version,
                    endpoint = EXCLUDED.endpoint,
                    p256dh = EXCLUDED.p256dh,
                    auth = EXCLUDED.auth,
                    topics = EXCLUDED.topics,
                    is_active = EXCLUDED.is_active,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
                RETURNING *
            '''

            params = [
                subscription_data["subscription_id"],
                subscription_data["user_id"],
                subscription_data["device_token"],
                subscription_data["platform"],
                subscription_data["device_id"],
                subscription_data["device_name"],
                subscription_data["app_version"],
                subscription_data["os_version"],
                subscription_data["endpoint"],
                subscription_data["p256dh"],
                subscription_data["auth"],
                subscription_data["topics"],
                subscription_data["is_active"],
                subscription_data["metadata"],
                subscription_data["created_at"],
                subscription_data["updated_at"]
            ]

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            if results and len(results) > 0:
                created_subscription = results[0]
                subscription.id = created_subscription["id"]
                subscription.created_at = datetime.fromisoformat(created_subscription["created_at"])
                subscription.updated_at = datetime.fromisoformat(created_subscription["updated_at"])
                return subscription

            raise Exception("Failed to register push subscription")

        except Exception as e:
            logger.error(f"Failed to register push subscription: {str(e)}")
            raise

    async def get_user_push_subscriptions(
        self,
        user_id: str,
        platform: Optional[PushPlatform] = None,
        is_active: bool = True
    ) -> List[PushSubscription]:
        """获取用户的推送订阅"""
        try:
            conditions = ["user_id = $1", "is_active = $2"]
            params = [user_id, is_active]
            param_count = 2

            if platform:
                param_count += 1
                conditions.append(f"platform = ${param_count}")
                params.append(platform.value)

            where_clause = " AND ".join(conditions)
            query = f'SELECT * FROM {self.schema}.push_subscriptions WHERE {where_clause}'

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            subscriptions = []
            for data in results:
                subscription = self._parse_push_subscription(data)
                if subscription:
                    subscriptions.append(subscription)

            return subscriptions

        except Exception as e:
            logger.error(f"Failed to get user push subscriptions: {str(e)}")
            return []

    async def unsubscribe_push(self, user_id: str, device_token: str) -> bool:
        """取消推送订阅"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            query = f'''
                UPDATE {self.schema}.push_subscriptions
                SET is_active = FALSE, updated_at = $1
                WHERE user_id = $2 AND device_token = $3
            '''

            with self.db:
                count = self.db.execute(query, [now, user_id, device_token], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to unsubscribe push: {str(e)}")
            return False

    async def update_push_last_used(self, user_id: str, device_token: str) -> bool:
        """更新推送订阅最后使用时间"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            query = f'''
                UPDATE {self.schema}.push_subscriptions
                SET last_used_at = $1
                WHERE user_id = $2 AND device_token = $3
            '''

            with self.db:
                count = self.db.execute(query, [now, user_id, device_token], schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Failed to update push last used: {str(e)}")
            return False

    # ====================
    # 统计查询
    # ====================

    async def get_notification_stats(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取通知统计"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if start_date:
                param_count += 1
                conditions.append(f"created_at >= ${param_count}")
                params.append(start_date.isoformat())

            if end_date:
                param_count += 1
                conditions.append(f"created_at <= ${param_count}")
                params.append(end_date.isoformat())

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f'SELECT * FROM {self.schema}.notifications WHERE {where_clause}'

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            stats = {
                "total_sent": 0,
                "total_delivered": 0,
                "total_failed": 0,
                "total_pending": 0,
                "by_type": {},
                "by_status": {}
            }

            for notification in results:
                stats["total_sent"] += 1

                status = notification["status"]
                if status == NotificationStatus.DELIVERED.value:
                    stats["total_delivered"] += 1
                elif status == NotificationStatus.FAILED.value:
                    stats["total_failed"] += 1
                elif status == NotificationStatus.PENDING.value:
                    stats["total_pending"] += 1

                # 按类型统计
                type_val = notification["type"]
                if type_val not in stats["by_type"]:
                    stats["by_type"][type_val] = 0
                stats["by_type"][type_val] += 1

                # 按状态统计
                if status not in stats["by_status"]:
                    stats["by_status"][status] = 0
                stats["by_status"][status] += 1

            return stats

        except Exception as e:
            logger.error(f"Failed to get notification stats: {str(e)}")
            return {
                "total_sent": 0,
                "total_delivered": 0,
                "total_failed": 0,
                "total_pending": 0,
                "by_type": {},
                "by_status": {}
            }

    # ====================
    # 辅助方法
    # ====================

    def _parse_template(self, data: Dict[str, Any]) -> Optional[NotificationTemplate]:
        """解析模板数据"""
        try:
            template = NotificationTemplate(
                template_id=data["template_id"],
                name=data["name"],
                type=NotificationType(data["type"]),
                content=data["content"]
            )

            template.id = data.get("id")
            template.description = data.get("description")
            template.subject = data.get("subject")
            template.html_content = data.get("html_content")

            # JSONB fields need to be converted from Protobuf types
            template.variables = _convert_protobuf_to_native(data.get("variables", []))
            template.metadata = _convert_protobuf_to_native(data.get("metadata", {}))

            template.status = TemplateStatus(data.get("status", "active"))
            template.version = data.get("version", 1)
            template.created_by = data.get("created_by")

            if data.get("created_at"):
                template.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("updated_at"):
                template.updated_at = datetime.fromisoformat(data["updated_at"])

            return template

        except Exception as e:
            logger.error(f"Failed to parse template: {str(e)}")
            return None

    def _parse_notification(self, data: Dict[str, Any]) -> Optional[Notification]:
        """解析通知数据"""
        try:
            from .models import RecipientType

            notification = Notification(
                notification_id=data["notification_id"],
                type=NotificationType(data["type"]),
                content=data.get("content", "")
            )

            notification.id = data.get("id")
            notification.priority = NotificationPriority(data.get("priority", "normal"))
            notification.recipient_type = RecipientType.USER  # Default
            notification.recipient_id = data.get("user_id")  # Map user_id to recipient_id
            notification.recipient_email = data.get("recipient") if "@" in (data.get("recipient") or "") else None
            notification.recipient_phone = data.get("recipient") if data.get("recipient") and "@" not in data.get("recipient", "") else None

            notification.template_id = data.get("template_id")
            notification.subject = data.get("subject")
            notification.html_content = data.get("html_content")

            # JSONB fields need to be converted from Protobuf types
            notification.variables = _convert_protobuf_to_native(data.get("variables", {}))
            notification.metadata = _convert_protobuf_to_native(data.get("metadata", {}))

            notification.retry_count = data.get("retry_count", 0)
            notification.max_retries = data.get("max_retries", 3)
            notification.status = NotificationStatus(data.get("status", "pending"))
            notification.error_message = data.get("error_message")
            # Note: batch_id is in DB but not in Notification model
            notification.provider = data.get("provider")
            notification.provider_message_id = data.get("provider_message_id")

            # 解析时间字段
            if data.get("scheduled_at"):
                notification.scheduled_at = datetime.fromisoformat(data["scheduled_at"])
            if data.get("created_at"):
                notification.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("sent_at"):
                notification.sent_at = datetime.fromisoformat(data["sent_at"])
            if data.get("delivered_at"):
                notification.delivered_at = datetime.fromisoformat(data["delivered_at"])
            if data.get("read_at"):
                notification.read_at = datetime.fromisoformat(data["read_at"])

            return notification

        except Exception as e:
            logger.error(f"Failed to parse notification: {str(e)}")
            return None

    def _parse_in_app_notification(self, data: Dict[str, Any]) -> Optional[InAppNotification]:
        """解析应用内通知数据"""
        try:
            notification = InAppNotification(
                notification_id=data["notification_id"],
                user_id=data["user_id"],
                title=data["title"],
                message=data["message"]
            )

            notification.id = data.get("id")
            notification.type = data.get("type", "info")
            notification.icon = data.get("icon")
            notification.avatar_url = data.get("avatar_url")
            notification.action_type = data.get("action_type")
            notification.action_url = data.get("action_url")
            notification.action_data = _convert_protobuf_to_native(data.get("action_data", {}))
            notification.category = data.get("category")
            notification.priority = NotificationPriority(data.get("priority", "normal"))
            notification.is_read = data.get("is_read", False)
            notification.is_archived = data.get("is_archived", False)
            notification.metadata = _convert_protobuf_to_native(data.get("metadata", {}))

            if data.get("created_at"):
                notification.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("read_at"):
                notification.read_at = datetime.fromisoformat(data["read_at"])
            if data.get("archived_at"):
                notification.archived_at = datetime.fromisoformat(data["archived_at"])
            if data.get("expires_at"):
                notification.expires_at = datetime.fromisoformat(data["expires_at"])

            return notification

        except Exception as e:
            logger.error(f"Failed to parse in-app notification: {str(e)}")
            return None

    def _parse_push_subscription(self, data: Dict[str, Any]) -> Optional[PushSubscription]:
        """解析推送订阅数据"""
        try:
            subscription = PushSubscription(
                user_id=data["user_id"],
                device_token=data["device_token"],
                platform=PushPlatform(data["platform"])
            )

            subscription.id = data.get("id")
            subscription.subscription_id = data.get("subscription_id")
            subscription.device_id = data.get("device_id")
            subscription.endpoint = data.get("endpoint")
            subscription.auth_key = data.get("auth")
            subscription.p256dh_key = data.get("p256dh")
            subscription.device_name = data.get("device_name")
            subscription.device_model = data.get("device_model")
            subscription.app_version = data.get("app_version")
            subscription.os_version = data.get("os_version")
            subscription.topics = _convert_protobuf_to_native(data.get("topics", []))  # TEXT[] returned as list
            subscription.is_active = data.get("is_active", True)
            subscription.metadata = _convert_protobuf_to_native(data.get("metadata", {}))

            if data.get("created_at"):
                subscription.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("updated_at"):
                subscription.updated_at = datetime.fromisoformat(data["updated_at"])
            if data.get("last_used_at"):
                subscription.last_used_at = datetime.fromisoformat(data["last_used_at"])
            if data.get("expires_at"):
                subscription.expires_at = datetime.fromisoformat(data["expires_at"])

            return subscription

        except Exception as e:
            logger.error(f"Failed to parse push subscription: {str(e)}")
            return None
