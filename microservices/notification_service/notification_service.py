"""
Notification Service Business Logic Layer

业务逻辑层，处理通知发送、模板管理、邮件发送等

Uses dependency injection for testability:
- Repository is injected, not created at import time
- Event publishers are lazily loaded
- Service clients are injected
"""

import json
import httpx
import os
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import re
import asyncio

# Import only models (no I/O dependencies)
from .models import (
    Notification, NotificationTemplate, InAppNotification,
    NotificationBatch, SendNotificationRequest, SendBatchRequest,
    CreateTemplateRequest, UpdateTemplateRequest,
    NotificationResponse, TemplateResponse, BatchResponse,
    NotificationStatus, NotificationType, TemplateStatus,
    NotificationPriority, NotificationStatsResponse,
    RecipientType, PushSubscription, PushPlatform,
    RegisterPushSubscriptionRequest
)

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from core.config_manager import ConfigManager
    from .notification_repository import NotificationRepository
    from .events.publishers import NotificationEventPublishers
    from .clients import AccountServiceClient, OrganizationServiceClient


logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务业务逻辑层"""

    def __init__(
        self,
        event_bus=None,
        config_manager=None,
        repository=None,
        account_client=None,
        organization_client=None,
        email_client=None,
    ):
        """
        Initialize notification service.

        Args:
            event_bus: Event bus for publishing events
            config_manager: ConfigManager instance for service discovery
            repository: Optional NotificationRepository (for DI/testing)
            account_client: Optional AccountServiceClient (for DI/testing)
            organization_client: Optional OrganizationServiceClient (for DI/testing)
            email_client: Optional email client (for DI/testing)
        """
        self.event_bus = event_bus
        self.config_manager = config_manager
        self._event_publishers_loaded = False

        # Support dependency injection - lazy import real dependencies only if not provided
        if repository is not None:
            self.repository = repository
        else:
            from .notification_repository import NotificationRepository
            self.repository = NotificationRepository(config=config_manager)

        # Lazy load event publishers
        self.event_publishers = None
        self._lazy_load_event_publishers()

        # Initialize service clients with lazy imports
        if account_client is not None:
            self.account_client = account_client
        else:
            from .clients import AccountServiceClient
            self.account_client = AccountServiceClient(config_manager)

        if organization_client is not None:
            self.organization_client = organization_client
        else:
            from .clients import OrganizationServiceClient
            self.organization_client = OrganizationServiceClient(config_manager)

        # Resend API配置
        self.resend_api_key = os.environ.get("RESEND_API_KEY")
        self.resend_base_url = "https://api.resend.com"
        self.default_from_email = "noreply@iapro.ai"

        # HTTP客户端（用于发送邮件）- support DI
        if email_client is not None:
            self.email_client = email_client
        elif self.resend_api_key:
            self.email_client = httpx.AsyncClient(
                base_url=self.resend_base_url,
                headers={
                    "Authorization": f"Bearer {self.resend_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
        else:
            self.email_client = None
            logger.warning("Resend API key not configured. Email sending disabled.")

    def _lazy_load_event_publishers(self):
        """Lazy load event publishers to avoid import-time I/O"""
        if not self._event_publishers_loaded:
            if self.event_bus:
                try:
                    from .events.publishers import NotificationEventPublishers
                    self.event_publishers = NotificationEventPublishers(self.event_bus)
                except ImportError:
                    logger.warning("Event publishers not available")
                    self.event_publishers = None
            self._event_publishers_loaded = True

    # ====================
    # 通知模板管理
    # ====================
    
    async def create_template(self, request: CreateTemplateRequest) -> TemplateResponse:
        """创建通知模板"""
        try:
            # 生成模板ID
            template_id = f"tpl_{request.type.value}_{datetime.utcnow().timestamp()}"
            
            # 创建模板对象
            template = NotificationTemplate(
                template_id=template_id,
                name=request.name,
                description=request.description,
                type=request.type,
                subject=request.subject,
                content=request.content,
                html_content=request.html_content,
                variables=request.variables,
                metadata=request.metadata,
                status=TemplateStatus.ACTIVE
            )
            
            # 保存到数据库
            created_template = await self.repository.create_template(template)
            
            return TemplateResponse(
                template=created_template,
                message="Template created successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to create template: {str(e)}")
            raise
    
    async def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """获取通知模板"""
        return await self.repository.get_template(template_id)
    
    async def list_templates(
        self,
        type: Optional[NotificationType] = None,
        status: Optional[TemplateStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[NotificationTemplate]:
        """列出通知模板"""
        return await self.repository.list_templates(type, status, limit, offset)
    
    async def update_template(
        self,
        template_id: str,
        request: UpdateTemplateRequest
    ) -> TemplateResponse:
        """更新通知模板"""
        try:
            # 构建更新字典
            updates = {}
            if request.name is not None:
                updates["name"] = request.name
            if request.description is not None:
                updates["description"] = request.description
            if request.subject is not None:
                updates["subject"] = request.subject
            if request.content is not None:
                updates["content"] = request.content
            if request.html_content is not None:
                updates["html_content"] = request.html_content
            if request.variables is not None:
                updates["variables"] = request.variables
            if request.status is not None:
                updates["status"] = request.status
            if request.metadata is not None:
                updates["metadata"] = request.metadata
            
            # 更新模板
            success = await self.repository.update_template(template_id, updates)
            
            if success:
                # 获取更新后的模板
                template = await self.repository.get_template(template_id)
                return TemplateResponse(
                    template=template,
                    message="Template updated successfully"
                )
            else:
                raise Exception("Failed to update template")
            
        except Exception as e:
            logger.error(f"Failed to update template {template_id}: {str(e)}")
            raise
    
    # ====================
    # 发送通知
    # ====================
    
    async def send_notification(self, request: SendNotificationRequest) -> NotificationResponse:
        """发送单个通知"""
        try:
            # 生成通知ID
            notification_id = f"ntf_{request.type.value}_{datetime.utcnow().timestamp()}"
            
            # 如果指定了模板，加载模板内容
            if request.template_id:
                template = await self.repository.get_template(request.template_id)
                if template:
                    # 使用模板内容，替换变量
                    content = self._replace_template_variables(
                        template.content,
                        request.variables
                    )
                    html_content = None
                    if template.html_content:
                        html_content = self._replace_template_variables(
                            template.html_content,
                            request.variables
                        )
                    
                    # 如果请求中没有指定主题，使用模板主题
                    if not request.subject and template.subject:
                        request.subject = self._replace_template_variables(
                            template.subject,
                            request.variables
                        )
                else:
                    content = request.content or ""
                    html_content = request.html_content
            else:
                content = request.content or ""
                html_content = request.html_content
            
            # 创建通知对象
            notification = Notification(
                notification_id=notification_id,
                type=request.type,
                priority=request.priority,
                recipient_type=RecipientType.EMAIL if request.recipient_email else RecipientType.USER,
                recipient_id=request.recipient_id,
                recipient_email=request.recipient_email,
                recipient_phone=request.recipient_phone,
                template_id=request.template_id,
                subject=request.subject,
                content=content,
                html_content=html_content,
                variables=request.variables,
                scheduled_at=request.scheduled_at,
                metadata=request.metadata,
                tags=request.tags,
                status=NotificationStatus.PENDING
            )
            
            # 保存到数据库
            created_notification = await self.repository.create_notification(notification)
            
            # 如果没有设置计划时间，立即发送
            if not request.scheduled_at or request.scheduled_at <= datetime.utcnow():
                await self._process_notification(created_notification)
            
            return NotificationResponse(
                notification=created_notification,
                message="Notification created and queued for sending"
            )
            
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            raise
    
    async def send_batch(self, request: SendBatchRequest) -> BatchResponse:
        """批量发送通知"""
        try:
            # 生成批次ID
            batch_id = f"batch_{datetime.utcnow().timestamp()}"
            
            # 创建批次对象
            batch = NotificationBatch(
                batch_id=batch_id,
                name=request.name,
                template_id=request.template_id,
                type=request.type,
                priority=request.priority,
                recipients=request.recipients,
                total_recipients=len(request.recipients),
                scheduled_at=request.scheduled_at,
                metadata=request.metadata
            )
            
            # 保存批次
            created_batch = await self.repository.create_batch(batch)
            
            # 如果没有设置计划时间，立即处理
            if not request.scheduled_at or request.scheduled_at <= datetime.utcnow():
                # 异步处理批量发送
                asyncio.create_task(self._process_batch(created_batch))
            
            return BatchResponse(
                batch=created_batch,
                message=f"Batch created with {len(request.recipients)} recipients"
            )
            
        except Exception as e:
            logger.error(f"Failed to send batch: {str(e)}")
            raise
    
    async def _process_batch(self, batch: NotificationBatch):
        """处理批量发送"""
        try:
            # 更新批次状态为开始
            await self.repository.update_batch_stats(
                batch.batch_id,
                sent_count=0
            )
            
            # 获取模板
            template = await self.repository.get_template(batch.template_id)
            if not template:
                logger.error(f"Template {batch.template_id} not found for batch {batch.batch_id}")
                return
            
            sent_count = 0
            delivered_count = 0
            failed_count = 0
            
            # 处理每个接收者
            for recipient in batch.recipients:
                try:
                    # 创建通知请求
                    notification_request = SendNotificationRequest(
                        type=batch.type,
                        priority=batch.priority,
                        template_id=batch.template_id,
                        recipient_id=recipient.get("user_id"),
                        recipient_email=recipient.get("email"),
                        recipient_phone=recipient.get("phone"),
                        variables=recipient.get("variables", {}),
                        metadata={
                            "batch_id": batch.batch_id,
                            **batch.metadata
                        }
                    )
                    
                    # 发送通知
                    response = await self.send_notification(notification_request)
                    sent_count += 1
                    
                    # 检查发送状态
                    if response.notification.status == NotificationStatus.SENT:
                        delivered_count += 1
                    elif response.notification.status == NotificationStatus.FAILED:
                        failed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send to recipient in batch {batch.batch_id}: {str(e)}")
                    failed_count += 1
                
                # 定期更新批次统计
                if (sent_count + failed_count) % 10 == 0:
                    await self.repository.update_batch_stats(
                        batch.batch_id,
                        sent_count=sent_count,
                        delivered_count=delivered_count,
                        failed_count=failed_count
                    )
            
            # 最终更新批次统计
            await self.repository.update_batch_stats(
                batch.batch_id,
                sent_count=sent_count,
                delivered_count=delivered_count,
                failed_count=failed_count,
                completed=True
            )
            
        except Exception as e:
            logger.error(f"Failed to process batch {batch.batch_id}: {str(e)}")
    
    async def _process_notification(self, notification: Notification):
        """处理单个通知发送"""
        try:
            # 更新状态为发送中
            await self.repository.update_notification_status(
                notification.notification_id,
                NotificationStatus.SENDING
            )
            
            # 根据类型发送通知
            if notification.type == NotificationType.EMAIL:
                await self._send_email_notification(notification)
            elif notification.type == NotificationType.IN_APP:
                await self._send_in_app_notification(notification)
            elif notification.type == NotificationType.SMS:
                # SMS功能暂未实现
                logger.warning(f"SMS notification not implemented: {notification.notification_id}")
                await self.repository.update_notification_status(
                    notification.notification_id,
                    NotificationStatus.FAILED,
                    error_message="SMS provider not configured"
                )
            elif notification.type == NotificationType.PUSH:
                await self._send_push_notification(notification)
            elif notification.type == NotificationType.WEBHOOK:
                await self._send_webhook_notification(notification)
            
        except Exception as e:
            logger.error(f"Failed to process notification {notification.notification_id}: {str(e)}")
            await self.repository.update_notification_status(
                notification.notification_id,
                NotificationStatus.FAILED,
                error_message=str(e)
            )
    
    async def _send_email_notification(self, notification: Notification):
        """发送邮件通知"""
        try:
            if not self.email_client:
                raise Exception("Email client not configured")
            
            if not notification.recipient_email:
                raise Exception("Recipient email not provided")
            
            # 准备邮件数据
            email_data = {
                "from": self.default_from_email,
                "to": [notification.recipient_email],
                "subject": notification.subject or "Notification",
                "html": notification.html_content or notification.content
            }
            
            # 如果有纯文本内容，也添加
            if notification.content and not notification.html_content:
                email_data["text"] = notification.content
            
            # 发送邮件
            response = await self.email_client.post("/emails", json=email_data)
            
            if response.status_code == 200:
                result_data = response.json()
                # 更新状态为已发送
                await self.repository.update_notification_status(
                    notification.notification_id,
                    NotificationStatus.SENT,
                    provider_message_id=result_data.get("id")
                )
                logger.info(f"Email sent successfully: {notification.notification_id}")

                # Publish notification.sent event using publishers
                if self.event_publishers:
                    await self.event_publishers.publish_notification_sent(
                        notification_id=notification.notification_id,
                        notification_type=notification.type.value,
                        recipient_id=notification.recipient_id,
                        recipient_email=notification.recipient_email,
                        status=notification.status.value,
                        subject=notification.subject,
                        priority=notification.priority.value
                    )
            else:
                error_message = f"Email API error: {response.status_code} - {response.text}"
                await self.repository.update_notification_status(
                    notification.notification_id,
                    NotificationStatus.FAILED,
                    error_message=error_message
                )
                logger.error(error_message)
            
        except Exception as e:
            logger.error(f"Failed to send email notification {notification.notification_id}: {str(e)}")
            await self.repository.update_notification_status(
                notification.notification_id,
                NotificationStatus.FAILED,
                error_message=str(e)
            )
    
    async def _send_in_app_notification(self, notification: Notification):
        """发送应用内通知"""
        try:
            if not notification.recipient_id:
                raise Exception("Recipient user ID not provided for in-app notification")
            
            # 创建应用内通知
            in_app_notification = InAppNotification(
                notification_id=notification.notification_id,
                user_id=notification.recipient_id,
                title=notification.subject or "Notification",
                message=notification.content,
                priority=notification.priority
            )
            
            # 保存到数据库
            await self.repository.create_in_app_notification(in_app_notification)
            
            # 更新状态为已发送
            await self.repository.update_notification_status(
                notification.notification_id,
                NotificationStatus.DELIVERED
            )

            logger.info(f"In-app notification created: {notification.notification_id}")

            # Publish notification.sent event using publishers
            if self.event_publishers:
                await self.event_publishers.publish_notification_sent(
                    notification_id=notification.notification_id,
                    notification_type=notification.type.value,
                    recipient_id=notification.recipient_id,
                    recipient_email=notification.recipient_email,
                    status=notification.status.value,
                    subject=notification.subject,
                    priority=notification.priority.value
                )
            
        except Exception as e:
            logger.error(f"Failed to send in-app notification {notification.notification_id}: {str(e)}")
            await self.repository.update_notification_status(
                notification.notification_id,
                NotificationStatus.FAILED,
                error_message=str(e)
            )
    
    async def _send_webhook_notification(self, notification: Notification):
        """发送Webhook通知"""
        try:
            # 从元数据中获取webhook URL
            webhook_url = notification.metadata.get("webhook_url")
            if not webhook_url:
                raise Exception("Webhook URL not provided in metadata")
            
            # 准备webhook数据
            webhook_data = {
                "notification_id": notification.notification_id,
                "type": notification.type.value,
                "subject": notification.subject,
                "content": notification.content,
                "variables": notification.variables,
                "metadata": notification.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 发送webhook
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=webhook_data,
                    timeout=30.0
                )
                
                if response.status_code in [200, 201, 202, 204]:
                    # 更新状态为已发送
                    await self.repository.update_notification_status(
                        notification.notification_id,
                        NotificationStatus.DELIVERED,
                        provider_message_id=f"webhook_{response.status_code}"
                    )
                    logger.info(f"Webhook sent successfully: {notification.notification_id}")

                    # Publish notification.sent event using publishers
                    if self.event_publishers:
                        await self.event_publishers.publish_notification_sent(
                            notification_id=notification.notification_id,
                            notification_type=notification.type.value,
                            recipient_id=notification.recipient_id,
                            recipient_email=notification.recipient_email,
                            status=notification.status.value,
                            subject=notification.subject,
                            priority=notification.priority.value
                        )
                else:
                    error_message = f"Webhook error: {response.status_code}"
                    await self.repository.update_notification_status(
                        notification.notification_id,
                        NotificationStatus.FAILED,
                        error_message=error_message
                    )
                    logger.error(error_message)
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification {notification.notification_id}: {str(e)}")
            await self.repository.update_notification_status(
                notification.notification_id,
                NotificationStatus.FAILED,
                error_message=str(e)
            )
    
    # ====================
    # 应用内通知管理
    # ====================
    
    async def list_user_notifications(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[InAppNotification]:
        """列出用户的应用内通知"""
        return await self.repository.list_user_in_app_notifications(
            user_id, is_read, is_archived, category, limit, offset
        )
    
    async def mark_notification_read(
        self,
        notification_id: str,
        user_id: str
    ) -> bool:
        """标记通知为已读"""
        return await self.repository.mark_notification_as_read(notification_id, user_id)
    
    async def mark_notification_archived(
        self,
        notification_id: str,
        user_id: str
    ) -> bool:
        """标记通知为已归档"""
        return await self.repository.mark_notification_as_archived(notification_id, user_id)
    
    async def get_unread_count(self, user_id: str) -> int:
        """获取未读通知数量"""
        return await self.repository.get_unread_count(user_id)
    
    async def _send_push_notification(self, notification: Notification):
        """发送推送通知"""
        try:
            if not notification.recipient_id:
                raise Exception("Recipient user ID not provided for push notification")
            
            # 获取用户的所有活跃推送订阅
            subscriptions = await self.repository.get_user_push_subscriptions(
                notification.recipient_id,
                is_active=True
            )
            
            if not subscriptions:
                await self.repository.update_notification_status(
                    notification.notification_id,
                    NotificationStatus.FAILED,
                    error_message="No active push subscriptions found for user"
                )
                return
            
            success_count = 0
            failed_count = 0
            
            for subscription in subscriptions:
                try:
                    if subscription.platform == PushPlatform.WEB:
                        await self._send_web_push(notification, subscription)
                    elif subscription.platform == PushPlatform.IOS:
                        await self._send_ios_push(notification, subscription)
                    elif subscription.platform == PushPlatform.ANDROID:
                        await self._send_android_push(notification, subscription)
                    
                    success_count += 1
                    # 更新最后使用时间
                    await self.repository.update_push_last_used(
                        subscription.user_id,
                        subscription.device_token
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send push to {subscription.platform.value}: {str(e)}")
                    failed_count += 1
            
            # 更新通知状态
            if success_count > 0:
                await self.repository.update_notification_status(
                    notification.notification_id,
                    NotificationStatus.DELIVERED,
                    provider_message_id=f"push_{success_count}_devices"
                )

                # Publish notification.sent event using publishers
                if self.event_publishers:
                    await self.event_publishers.publish_notification_sent(
                        notification_id=notification.notification_id,
                        notification_type=notification.type.value,
                        recipient_id=notification.recipient_id,
                        recipient_email=notification.recipient_email,
                        status=notification.status.value,
                        subject=notification.subject,
                        priority=notification.priority.value
                    )
            else:
                await self.repository.update_notification_status(
                    notification.notification_id,
                    NotificationStatus.FAILED,
                    error_message=f"Failed to send to all {failed_count} devices"
                )
            
        except Exception as e:
            logger.error(f"Failed to send push notification {notification.notification_id}: {str(e)}")
            await self.repository.update_notification_status(
                notification.notification_id,
                NotificationStatus.FAILED,
                error_message=str(e)
            )
    
    async def _send_web_push(self, notification: Notification, subscription: PushSubscription):
        """发送Web推送通知"""
        try:
            # Web Push需要使用pywebpush库
            # pip install pywebpush
            from pywebpush import webpush, WebPushException
            
            # 准备推送数据
            push_data = {
                "title": notification.subject or "New Notification",
                "body": notification.content,
                "icon": "/icon-192x192.png",
                "badge": "/badge-72x72.png",
                "data": {
                    "notification_id": notification.notification_id,
                    "url": notification.metadata.get("action_url", "/")
                }
            }
            
            # 发送Web Push
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "auth": subscription.auth_key,
                        "p256dh": subscription.p256dh_key
                    }
                },
                data=json.dumps(push_data),
                vapid_private_key=os.environ.get("VAPID_PRIVATE_KEY"),
                vapid_claims={
                    "sub": f"mailto:{self.default_from_email}"
                }
            )
            
            logger.info(f"Web push sent successfully: {notification.notification_id}")
            
        except ImportError:
            logger.error("pywebpush not installed. Install with: pip install pywebpush")
            raise Exception("Web push library not available")
        except WebPushException as e:
            logger.error(f"Web push error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to send web push: {str(e)}")
            raise
    
    async def _send_ios_push(self, notification: Notification, subscription: PushSubscription):
        """发送iOS推送通知（使用APNs）"""
        try:
            # iOS推送需要使用apns2库
            # pip install apns2
            # 这里是示例实现，实际需要配置APNs证书
            
            # 准备推送payload
            payload = {
                "aps": {
                    "alert": {
                        "title": notification.subject or "New Notification",
                        "body": notification.content
                    },
                    "badge": 1,
                    "sound": "default"
                },
                "notification_id": notification.notification_id
            }
            
            # TODO: 实际实现需要配置APNs
            # from apns2.client import APNsClient
            # from apns2.payload import Payload
            # client = APNsClient('cert.pem', use_sandbox=True)
            # client.send_notification(subscription.device_token, Payload(custom=payload))
            
            logger.info(f"iOS push would be sent to: {subscription.device_token}")
            
        except Exception as e:
            logger.error(f"Failed to send iOS push: {str(e)}")
            raise
    
    async def _send_android_push(self, notification: Notification, subscription: PushSubscription):
        """发送Android推送通知（使用FCM）"""
        try:
            # Android推送使用Firebase Cloud Messaging (FCM)
            # 需要配置FCM服务器密钥
            
            fcm_server_key = os.environ.get("FCM_SERVER_KEY")
            if not fcm_server_key:
                raise Exception("FCM server key not configured")
            
            # 准备FCM消息
            fcm_message = {
                "to": subscription.device_token,
                "notification": {
                    "title": notification.subject or "New Notification",
                    "body": notification.content,
                    "icon": "notification_icon"
                },
                "data": {
                    "notification_id": notification.notification_id,
                    "click_action": notification.metadata.get("action_url", "")
                }
            }
            
            # 发送到FCM
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://fcm.googleapis.com/fcm/send",
                    headers={
                        "Authorization": f"key={fcm_server_key}",
                        "Content-Type": "application/json"
                    },
                    json=fcm_message,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Android push sent successfully: {notification.notification_id}")
                else:
                    raise Exception(f"FCM error: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Failed to send Android push: {str(e)}")
            raise
    
    # ====================
    # Push订阅管理
    # ====================
    
    async def register_push_subscription(
        self,
        request: RegisterPushSubscriptionRequest
    ) -> PushSubscription:
        """注册推送订阅"""
        try:
            subscription = PushSubscription(
                user_id=request.user_id,
                device_token=request.device_token,
                platform=request.platform,
                endpoint=request.endpoint,
                auth_key=request.auth_key,
                p256dh_key=request.p256dh_key,
                device_name=request.device_name,
                device_model=request.device_model,
                app_version=request.app_version,
                is_active=True
            )
            
            return await self.repository.register_push_subscription(subscription)
            
        except Exception as e:
            logger.error(f"Failed to register push subscription: {str(e)}")
            raise
    
    async def get_user_push_subscriptions(
        self,
        user_id: str,
        platform: Optional[PushPlatform] = None
    ) -> List[PushSubscription]:
        """获取用户的推送订阅"""
        return await self.repository.get_user_push_subscriptions(
            user_id, platform, is_active=True
        )
    
    async def unsubscribe_push(
        self,
        user_id: str,
        device_token: str
    ) -> bool:
        """取消推送订阅"""
        return await self.repository.unsubscribe_push(user_id, device_token)
    
    # ====================
    # 统计和查询
    # ====================
    
    async def get_notification_stats(
        self,
        user_id: Optional[str] = None,
        period: str = "all_time"
    ) -> NotificationStatsResponse:
        """获取通知统计"""
        try:
            # 计算时间范围
            end_date = datetime.utcnow()
            start_date = None
            
            if period == "today":
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "week":
                start_date = end_date - timedelta(days=7)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            elif period == "year":
                start_date = end_date - timedelta(days=365)
            
            # 获取统计数据
            stats = await self.repository.get_notification_stats(
                user_id, start_date, end_date
            )
            
            return NotificationStatsResponse(
                total_sent=stats["total_sent"],
                total_delivered=stats["total_delivered"],
                total_failed=stats["total_failed"],
                total_pending=stats["total_pending"],
                by_type=stats["by_type"],
                by_status=stats["by_status"],
                period=period
            )
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {str(e)}")
            raise
    
    async def process_pending_notifications(self):
        """处理待发送的通知（后台任务）"""
        try:
            # 获取待发送的通知
            pending_notifications = await self.repository.get_pending_notifications(limit=50)
            
            # 并发处理通知
            tasks = []
            for notification in pending_notifications:
                # 检查是否过期
                if notification.expires_at and notification.expires_at < datetime.utcnow():
                    await self.repository.update_notification_status(
                        notification.notification_id,
                        NotificationStatus.CANCELLED,
                        error_message="Notification expired"
                    )
                    continue
                
                # 创建发送任务
                tasks.append(self._process_notification(notification))
            
            # 执行所有任务
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            return len(pending_notifications)
            
        except Exception as e:
            logger.error(f"Failed to process pending notifications: {str(e)}")
            return 0
    
    # ====================
    # 辅助方法
    # ====================

    def _replace_template_variables(
        self,
        content: str,
        variables: Dict[str, Any]
    ) -> str:
        """替换模板变量"""
        if not variables:
            return content

        # 使用正则表达式替换变量 {{variable_name}}
        pattern = r'\{\{(\w+)\}\}'

        def replace_var(match):
            var_name = match.group(1)
            return str(variables.get(var_name, match.group(0)))

        return re.sub(pattern, replace_var, content)
    
    async def cleanup(self):
        """清理资源"""
        if self.email_client:
            await self.email_client.aclose()

        # Close service clients
        if self.account_client:
            await self.account_client.close()
        if self.organization_client:
            await self.organization_client.close()