"""
Notification Service Repository Layer

数据访问层，负责与数据库交互
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from core.database.supabase_client import get_supabase_client
from .models import (
    Notification, NotificationTemplate, InAppNotification,
    NotificationBatch, NotificationStatus, NotificationType,
    TemplateStatus, NotificationPriority, PushSubscription, PushPlatform
)


logger = logging.getLogger(__name__)


class NotificationRepository:
    """通知数据访问层"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.schema = "dev"
        
    # ====================
    # 通知模板管理
    # ====================
    
    async def create_template(self, template: NotificationTemplate) -> NotificationTemplate:
        """创建通知模板"""
        try:
            now = datetime.utcnow()
            template_data = {
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "type": template.type.value,
                "subject": template.subject,
                "content": template.content,
                "html_content": template.html_content,
                "variables": json.dumps(template.variables),
                "metadata": json.dumps(template.metadata),
                "status": template.status.value,
                "version": template.version,
                "created_by": template.created_by,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            result = self.supabase.table('notification_templates').insert(template_data).execute()
            
            if result.data:
                created_template = result.data[0]
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
            result = self.supabase.table('notification_templates')\
                .select("*")\
                .eq("template_id", template_id)\
                .single()\
                .execute()
            
            if result.data:
                return self._parse_template(result.data)
            
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
            query = self.supabase.table('notification_templates').select("*")
            
            if type:
                query = query.eq("type", type.value)
            if status:
                query = query.eq("status", status.value)
            
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            result = query.execute()
            
            templates = []
            for data in result.data:
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
            update_data = {
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 处理更新字段
            if "name" in updates:
                update_data["name"] = updates["name"]
            if "description" in updates:
                update_data["description"] = updates["description"]
            if "subject" in updates:
                update_data["subject"] = updates["subject"]
            if "content" in updates:
                update_data["content"] = updates["content"]
            if "html_content" in updates:
                update_data["html_content"] = updates["html_content"]
            if "variables" in updates:
                update_data["variables"] = json.dumps(updates["variables"])
            if "status" in updates:
                update_data["status"] = updates["status"].value if hasattr(updates["status"], "value") else updates["status"]
            if "metadata" in updates:
                update_data["metadata"] = json.dumps(updates["metadata"])
            
            result = self.supabase.table('notification_templates')\
                .update(update_data)\
                .eq("template_id", template_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update template {template_id}: {str(e)}")
            return False
    
    # ====================
    # 通知管理
    # ====================
    
    async def create_notification(self, notification: Notification) -> Notification:
        """创建通知"""
        try:
            now = datetime.utcnow()
            notification_data = {
                "notification_id": notification.notification_id,
                "type": notification.type.value,
                "priority": notification.priority.value,
                "recipient_type": notification.recipient_type.value,
                "recipient_id": notification.recipient_id,
                "recipient_email": notification.recipient_email,
                "recipient_phone": notification.recipient_phone,
                "template_id": notification.template_id,
                "subject": notification.subject,
                "content": notification.content,
                "html_content": notification.html_content,
                "variables": json.dumps(notification.variables),
                "scheduled_at": notification.scheduled_at.isoformat() if notification.scheduled_at else None,
                "expires_at": notification.expires_at.isoformat() if notification.expires_at else None,
                "retry_count": notification.retry_count,
                "max_retries": notification.max_retries,
                "status": notification.status.value,
                "error_message": notification.error_message,
                "provider": notification.provider,
                "provider_message_id": notification.provider_message_id,
                "metadata": json.dumps(notification.metadata),
                "tags": json.dumps(notification.tags),
                "created_at": now.isoformat()
            }
            
            result = self.supabase.table('notifications').insert(notification_data).execute()
            
            if result.data:
                created_notification = result.data[0]
                notification.id = created_notification["id"]
                notification.created_at = datetime.fromisoformat(created_notification["created_at"])
                return notification
            
            raise Exception("Failed to create notification")
            
        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            raise
    
    async def get_notification(self, notification_id: str) -> Optional[Notification]:
        """获取通知"""
        try:
            result = self.supabase.table('notifications')\
                .select("*")\
                .eq("notification_id", notification_id)\
                .single()\
                .execute()
            
            if result.data:
                return self._parse_notification(result.data)
            
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
            query = self.supabase.table('notifications').select("*")
            
            if user_id:
                query = query.eq("recipient_id", user_id)
            if type:
                query = query.eq("type", type.value)
            if status:
                query = query.eq("status", status.value)
            if priority:
                query = query.eq("priority", priority.value)
            
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            result = query.execute()
            
            notifications = []
            for data in result.data:
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
            now = datetime.utcnow()
            update_data = {
                "status": status.value
            }
            
            # 根据状态更新相应的时间戳
            if status == NotificationStatus.SENT:
                update_data["sent_at"] = now.isoformat()
            elif status == NotificationStatus.DELIVERED:
                update_data["delivered_at"] = now.isoformat()
            elif status == NotificationStatus.FAILED:
                update_data["failed_at"] = now.isoformat()
                if error_message:
                    update_data["error_message"] = error_message
            
            if provider_message_id:
                update_data["provider_message_id"] = provider_message_id
            
            result = self.supabase.table('notifications')\
                .update(update_data)\
                .eq("notification_id", notification_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update notification status {notification_id}: {str(e)}")
            return False
    
    async def get_pending_notifications(self, limit: int = 100) -> List[Notification]:
        """获取待发送的通知"""
        try:
            now = datetime.utcnow()
            
            result = self.supabase.table('notifications')\
                .select("*")\
                .eq("status", NotificationStatus.PENDING.value)\
                .or_(f"scheduled_at.is.null,scheduled_at.lte.{now.isoformat()}")\
                .order("priority", desc=False)\
                .order("created_at")\
                .limit(limit)\
                .execute()
            
            notifications = []
            for data in result.data:
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
            now = datetime.utcnow()
            notification_data = {
                "notification_id": notification.notification_id,
                "user_id": notification.user_id,
                "title": notification.title,
                "message": notification.message,
                "icon": notification.icon,
                "image_url": notification.image_url,
                "action_url": notification.action_url,
                "category": notification.category,
                "priority": notification.priority.value,
                "is_read": notification.is_read,
                "is_archived": notification.is_archived,
                "created_at": now.isoformat()
            }
            
            result = self.supabase.table('in_app_notifications').insert(notification_data).execute()
            
            if result.data:
                created_notification = result.data[0]
                notification.id = created_notification["id"]
                notification.created_at = datetime.fromisoformat(created_notification["created_at"])
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
            query = self.supabase.table('in_app_notifications')\
                .select("*")\
                .eq("user_id", user_id)
            
            if is_read is not None:
                query = query.eq("is_read", is_read)
            if is_archived is not None:
                query = query.eq("is_archived", is_archived)
            if category:
                query = query.eq("category", category)
            
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            result = query.execute()
            
            notifications = []
            for data in result.data:
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
            update_data = {
                "is_read": True,
                "read_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table('in_app_notifications')\
                .update(update_data)\
                .eq("notification_id", notification_id)\
                .eq("user_id", user_id)\
                .execute()
            
            # 同时更新主通知表的已读时间
            if len(result.data) > 0:
                self.supabase.table('notifications')\
                    .update({"read_at": datetime.utcnow().isoformat()})\
                    .eq("notification_id", notification_id)\
                    .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to mark notification as read {notification_id}: {str(e)}")
            return False
    
    async def mark_notification_as_archived(self, notification_id: str, user_id: str) -> bool:
        """标记通知为已归档"""
        try:
            update_data = {
                "is_archived": True,
                "archived_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table('in_app_notifications')\
                .update(update_data)\
                .eq("notification_id", notification_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to mark notification as archived {notification_id}: {str(e)}")
            return False
    
    async def get_unread_count(self, user_id: str) -> int:
        """获取未读通知数量"""
        try:
            result = self.supabase.table('in_app_notifications')\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .eq("is_read", False)\
                .eq("is_archived", False)\
                .execute()
            
            return result.count if result.count else 0
            
        except Exception as e:
            logger.error(f"Failed to get unread count for user {user_id}: {str(e)}")
            return 0
    
    # ====================
    # 批量通知管理
    # ====================
    
    async def create_batch(self, batch: NotificationBatch) -> NotificationBatch:
        """创建批量通知"""
        try:
            now = datetime.utcnow()
            batch_data = {
                "batch_id": batch.batch_id,
                "name": batch.name,
                "template_id": batch.template_id,
                "type": batch.type.value,
                "priority": batch.priority.value,
                "recipients": json.dumps(batch.recipients),
                "total_recipients": batch.total_recipients,
                "sent_count": batch.sent_count,
                "delivered_count": batch.delivered_count,
                "failed_count": batch.failed_count,
                "scheduled_at": batch.scheduled_at.isoformat() if batch.scheduled_at else None,
                "metadata": json.dumps(batch.metadata),
                "created_by": batch.created_by,
                "created_at": now.isoformat()
            }
            
            result = self.supabase.table('notification_batches').insert(batch_data).execute()
            
            if result.data:
                created_batch = result.data[0]
                batch.id = created_batch["id"]
                batch.created_at = datetime.fromisoformat(created_batch["created_at"])
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
            update_data = {}
            
            if sent_count is not None:
                update_data["sent_count"] = sent_count
            if delivered_count is not None:
                update_data["delivered_count"] = delivered_count
            if failed_count is not None:
                update_data["failed_count"] = failed_count
            if completed:
                update_data["completed_at"] = datetime.utcnow().isoformat()
            
            if not update_data:
                return True
            
            result = self.supabase.table('notification_batches')\
                .update(update_data)\
                .eq("batch_id", batch_id)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to update batch stats {batch_id}: {str(e)}")
            return False
    
    # ====================
    # Push订阅管理
    # ====================
    
    async def register_push_subscription(self, subscription: PushSubscription) -> PushSubscription:
        """注册推送订阅"""
        try:
            now = datetime.utcnow()
            subscription_data = {
                "user_id": subscription.user_id,
                "device_token": subscription.device_token,
                "platform": subscription.platform.value,
                "endpoint": subscription.endpoint,
                "auth_key": subscription.auth_key,
                "p256dh_key": subscription.p256dh_key,
                "device_name": subscription.device_name,
                "device_model": subscription.device_model,
                "app_version": subscription.app_version,
                "is_active": subscription.is_active,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            # 尝试更新现有订阅或插入新订阅
            result = self.supabase.table('push_subscriptions').upsert(
                subscription_data,
                on_conflict="user_id,device_token"
            ).execute()
            
            if result.data:
                created_subscription = result.data[0]
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
            query = self.supabase.table('push_subscriptions')\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_active", is_active)
            
            if platform:
                query = query.eq("platform", platform.value)
            
            result = query.execute()
            
            subscriptions = []
            for data in result.data:
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
            result = self.supabase.table('push_subscriptions')\
                .update({"is_active": False, "updated_at": datetime.utcnow().isoformat()})\
                .eq("user_id", user_id)\
                .eq("device_token", device_token)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe push: {str(e)}")
            return False
    
    async def update_push_last_used(self, user_id: str, device_token: str) -> bool:
        """更新推送订阅最后使用时间"""
        try:
            result = self.supabase.table('push_subscriptions')\
                .update({"last_used_at": datetime.utcnow().isoformat()})\
                .eq("user_id", user_id)\
                .eq("device_token", device_token)\
                .execute()
            
            return len(result.data) > 0
            
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
            query = self.supabase.table('notifications').select("*")
            
            if user_id:
                query = query.eq("recipient_id", user_id)
            
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            
            if end_date:
                query = query.lte("created_at", end_date.isoformat())
            
            result = query.execute()
            
            stats = {
                "total_sent": 0,
                "total_delivered": 0,
                "total_failed": 0,
                "total_pending": 0,
                "by_type": {},
                "by_status": {}
            }
            
            for notification in result.data:
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
            
            # 解析JSON字段
            template.variables = self._parse_json_field(data.get("variables"), [])
            template.metadata = self._parse_json_field(data.get("metadata"), {})
            
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
            notification.recipient_type = RecipientType(data.get("recipient_type", "user"))
            notification.recipient_id = data.get("recipient_id")
            notification.recipient_email = data.get("recipient_email")
            notification.recipient_phone = data.get("recipient_phone")
            
            notification.template_id = data.get("template_id")
            notification.subject = data.get("subject")
            notification.html_content = data.get("html_content")
            
            # 解析JSON字段
            notification.variables = self._parse_json_field(data.get("variables"), {})
            notification.metadata = self._parse_json_field(data.get("metadata"), {})
            notification.tags = self._parse_json_field(data.get("tags"), [])
            
            notification.retry_count = data.get("retry_count", 0)
            notification.max_retries = data.get("max_retries", 3)
            notification.status = NotificationStatus(data.get("status", "pending"))
            notification.error_message = data.get("error_message")
            notification.provider = data.get("provider")
            notification.provider_message_id = data.get("provider_message_id")
            
            # 解析时间字段
            if data.get("scheduled_at"):
                notification.scheduled_at = datetime.fromisoformat(data["scheduled_at"])
            if data.get("expires_at"):
                notification.expires_at = datetime.fromisoformat(data["expires_at"])
            if data.get("created_at"):
                notification.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("sent_at"):
                notification.sent_at = datetime.fromisoformat(data["sent_at"])
            if data.get("delivered_at"):
                notification.delivered_at = datetime.fromisoformat(data["delivered_at"])
            if data.get("read_at"):
                notification.read_at = datetime.fromisoformat(data["read_at"])
            if data.get("failed_at"):
                notification.failed_at = datetime.fromisoformat(data["failed_at"])
            
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
            notification.icon = data.get("icon")
            notification.image_url = data.get("image_url")
            notification.action_url = data.get("action_url")
            notification.category = data.get("category")
            notification.priority = NotificationPriority(data.get("priority", "normal"))
            notification.is_read = data.get("is_read", False)
            notification.is_archived = data.get("is_archived", False)
            
            if data.get("created_at"):
                notification.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("read_at"):
                notification.read_at = datetime.fromisoformat(data["read_at"])
            if data.get("archived_at"):
                notification.archived_at = datetime.fromisoformat(data["archived_at"])
            
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
            subscription.endpoint = data.get("endpoint")
            subscription.auth_key = data.get("auth_key")
            subscription.p256dh_key = data.get("p256dh_key")
            subscription.device_name = data.get("device_name")
            subscription.device_model = data.get("device_model")
            subscription.app_version = data.get("app_version")
            subscription.is_active = data.get("is_active", True)
            
            if data.get("created_at"):
                subscription.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("updated_at"):
                subscription.updated_at = datetime.fromisoformat(data["updated_at"])
            if data.get("last_used_at"):
                subscription.last_used_at = datetime.fromisoformat(data["last_used_at"])
            
            return subscription
            
        except Exception as e:
            logger.error(f"Failed to parse push subscription: {str(e)}")
            return None
    
    def _parse_json_field(self, value: Any, default: Any) -> Any:
        """解析JSON字段"""
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return default