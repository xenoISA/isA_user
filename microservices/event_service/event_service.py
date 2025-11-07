"""
Event Service Implementation

事件服务核心实现
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable
import uuid

from .models import (
    Event, EventStream, EventSource, EventCategory, EventStatus,
    EventCreateRequest, EventQueryRequest, EventResponse, EventListResponse,
    EventStatistics, EventProcessingResult, ProcessingStatus,
    EventReplayRequest, EventProjection, EventProcessor, EventSubscription,
    RudderStackEvent
)
from .event_repository import EventRepository
from core.nats_client import Event as NATSEvent, EventType, ServiceSource
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class EventService:
    """事件服务核心类"""

    def __init__(self, event_bus=None, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager if config_manager else ConfigManager("event_service")
        self.repository = EventRepository(config=self.config_manager)
        self.event_bus = event_bus
        self.processors: Dict[str, EventProcessor] = {}
        self.subscriptions: Dict[str, EventSubscription] = {}
        self.projections: Dict[str, EventProjection] = {}
        self.processing_queue = asyncio.Queue()
        self.is_processing = False
        
    async def initialize(self):
        """初始化服务"""
        # 初始化数据库
        await self.repository.initialize()
        
        # 加载处理器和订阅
        await self._load_processors()
        await self._load_subscriptions()
        
        # 启动事件处理循环
        asyncio.create_task(self._process_event_queue())
        
        logger.info("Event Service initialized")
    
    # ==================== 事件创建和存储 ====================
    
    async def create_event(self, request: EventCreateRequest) -> EventResponse:
        """创建事件"""
        # 创建事件对象
        event = Event(
            event_type=request.event_type,
            event_source=request.event_source,
            event_category=request.event_category,
            user_id=request.user_id,
            data=request.data,
            metadata=request.metadata or {},
            context=request.context or {},
            timestamp=datetime.utcnow()
        )
        
        # 存储事件
        stored_event = await self.repository.save_event(event)

        # 添加到处理队列
        await self.processing_queue.put(stored_event)

        # 触发实时处理器
        asyncio.create_task(self._trigger_realtime_processors(stored_event))

        logger.info(f"Event created: {stored_event.event_id} - {stored_event.event_type}")

        # Publish event.stored event
        if self.event_bus:
            try:
                nats_event = NATSEvent(
                    event_type=EventType.EVENT_STORED,
                    source=ServiceSource.EVENT_SERVICE,
                    data={
                        "event_id": stored_event.event_id,
                        "event_type": stored_event.event_type,
                        "event_source": stored_event.event_source.value,
                        "event_category": stored_event.event_category.value,
                        "user_id": stored_event.user_id,
                        "timestamp": stored_event.timestamp.isoformat()
                    }
                )
                await self.event_bus.publish_event(nats_event)
            except Exception as e:
                logger.error(f"Failed to publish event.stored event: {e}")
        
        return EventResponse(
            event_id=stored_event.event_id,
            event_type=stored_event.event_type,
            event_source=stored_event.event_source,
            event_category=stored_event.event_category,
            user_id=stored_event.user_id,
            data=stored_event.data,
            status=stored_event.status,
            timestamp=stored_event.timestamp,
            created_at=stored_event.created_at
        )
    
    async def create_event_from_rudderstack(self, rudderstack_event: RudderStackEvent) -> EventResponse:
        """从 RudderStack 事件创建事件"""
        # 转换 RudderStack 事件为统一事件格式
        event = Event(
            event_type=rudderstack_event.event,
            event_source=EventSource.FRONTEND,
            event_category=self._categorize_rudderstack_event(rudderstack_event),
            user_id=rudderstack_event.userId or rudderstack_event.anonymousId,
            data={
                "properties": rudderstack_event.properties,
                "type": rudderstack_event.type,
            },
            context=rudderstack_event.context,
            metadata={
                "anonymous_id": rudderstack_event.anonymousId,
                "sent_at": rudderstack_event.sentAt,
                "received_at": rudderstack_event.receivedAt,
                "original_timestamp": rudderstack_event.originalTimestamp
            },
            timestamp=datetime.fromisoformat(rudderstack_event.timestamp.replace('Z', '+00:00'))
        )
        
        # 存储事件
        stored_event = await self.repository.save_event(event)
        
        # 添加到处理队列
        await self.processing_queue.put(stored_event)
        
        logger.info(f"RudderStack event created: {stored_event.event_id}")
        
        return EventResponse(
            event_id=stored_event.event_id,
            event_type=stored_event.event_type,
            event_source=stored_event.event_source,
            event_category=stored_event.event_category,
            user_id=stored_event.user_id,
            data=stored_event.data,
            status=stored_event.status,
            timestamp=stored_event.timestamp,
            created_at=stored_event.created_at
        )
    
    async def create_event_from_nats(self, nats_event: Dict[str, Any]) -> EventResponse:
        """从 NATS 事件创建事件"""
        # 转换 NATS 事件为统一事件格式
        event = Event(
            event_type=nats_event.get("type", "unknown"),
            event_source=EventSource.BACKEND,
            event_category=self._categorize_nats_event(nats_event),
            user_id=nats_event.get("data", {}).get("user_id"),
            data=nats_event.get("data", {}),
            metadata={
                "source_service": nats_event.get("source"),
                "event_id": nats_event.get("id"),
                "version": nats_event.get("version")
            },
            context={
                "subject": nats_event.get("subject"),
                "correlation_id": nats_event.get("correlation_id")
            },
            timestamp=datetime.fromisoformat(nats_event.get("timestamp", datetime.utcnow().isoformat()))
        )
        
        # 存储事件
        stored_event = await self.repository.save_event(event)
        
        # 添加到处理队列
        await self.processing_queue.put(stored_event)
        
        logger.info(f"NATS event created: {stored_event.event_id}")
        
        return EventResponse(
            event_id=stored_event.event_id,
            event_type=stored_event.event_type,
            event_source=stored_event.event_source,
            event_category=stored_event.event_category,
            user_id=stored_event.user_id,
            data=stored_event.data,
            status=stored_event.status,
            timestamp=stored_event.timestamp,
            created_at=stored_event.created_at
        )
    
    # ==================== 事件查询 ====================
    
    async def query_events(self, request: EventQueryRequest) -> EventListResponse:
        """查询事件"""
        events, total = await self.repository.query_events(
            user_id=request.user_id,
            event_type=request.event_type,
            event_source=request.event_source,
            event_category=request.event_category,
            status=request.status,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=request.limit,
            offset=request.offset
        )
        
        responses = [
            EventResponse(
                event_id=e.event_id,
                event_type=e.event_type,
                event_source=e.event_source,
                event_category=e.event_category,
                user_id=e.user_id,
                data=e.data,
                status=e.status,
                timestamp=e.timestamp,
                created_at=e.created_at
            ) for e in events
        ]
        
        return EventListResponse(
            events=responses,
            total=total,
            limit=request.limit,
            offset=request.offset,
            has_more=(request.offset + request.limit) < total
        )
    
    async def get_event(self, event_id: str) -> Optional[Event]:
        """获取单个事件"""
        return await self.repository.get_event(event_id)
    
    async def get_event_stream(self, stream_id: str, from_version: Optional[int] = None) -> EventStream:
        """获取事件流"""
        events = await self.repository.get_event_stream(stream_id, from_version)
        
        # 解析流ID
        parts = stream_id.split(":")
        entity_type = parts[0] if parts else "unknown"
        entity_id = parts[1] if len(parts) > 1 else stream_id
        
        return EventStream(
            stream_id=stream_id,
            stream_type=entity_type,
            entity_id=entity_id,
            entity_type=entity_type,
            events=events,
            version=len(events)
        )
    
    async def get_user_events(self, user_id: str, limit: int = 100) -> List[Event]:
        """获取用户事件"""
        return await self.repository.get_user_events(user_id, limit)
    
    async def get_unprocessed_events(self, limit: int = 100) -> List[Event]:
        """获取未处理事件"""
        return await self.repository.get_unprocessed_events(limit)
    
    # ==================== 事件统计 ====================
    
    async def get_statistics(self) -> EventStatistics:
        """获取事件统计"""
        stats = await self.repository.get_statistics()
        
        # 计算处理率和错误率
        total = stats.total_events
        if total > 0:
            stats.processing_rate = (stats.processed_events / total) * 100
            stats.error_rate = (stats.failed_events / total) * 100
        
        # 获取热门数据 (TODO: implement these methods in repository)
        stats.top_users = []  # await self.repository.get_top_users(5) 
        stats.top_event_types = []  # await self.repository.get_top_event_types(10)
        
        return stats
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """获取用户事件统计"""
        return await self.repository.get_user_statistics(user_id)
    
    # ==================== 事件处理 ====================
    
    async def mark_event_processed(
        self, 
        event_id: str, 
        processor_name: str, 
        result: EventProcessingResult
    ) -> bool:
        """标记事件已处理"""
        event = await self.repository.get_event(event_id)
        if not event:
            return False
        
        # 更新处理器列表
        if processor_name not in event.processors:
            event.processors.append(processor_name)
        
        # 更新状态
        if result.status == ProcessingStatus.SUCCESS:
            event.status = EventStatus.PROCESSED
            event.processed_at = datetime.utcnow()

            # Publish event.processed.success event
            if self.event_bus:
                try:
                    nats_event = NATSEvent(
                        event_type=EventType.EVENT_PROCESSED_SUCCESS,
                        source=ServiceSource.EVENT_SERVICE,
                        data={
                            "event_id": event.event_id,
                            "event_type": event.event_type,
                            "processor_name": processor_name,
                            "duration_ms": result.duration_ms,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    await self.event_bus.publish_event(nats_event)
                except Exception as e:
                    logger.error(f"Failed to publish event.processed.success event: {e}")

        elif result.status == ProcessingStatus.FAILED:
            event.status = EventStatus.FAILED
            event.error_message = result.message
            event.retry_count += 1

            # Publish event.processed.failed event
            if self.event_bus:
                try:
                    nats_event = NATSEvent(
                        event_type=EventType.EVENT_PROCESSED_FAILED,
                        source=ServiceSource.EVENT_SERVICE,
                        data={
                            "event_id": event.event_id,
                            "event_type": event.event_type,
                            "processor_name": processor_name,
                            "error_message": result.message,
                            "retry_count": event.retry_count,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    await self.event_bus.publish_event(nats_event)
                except Exception as e:
                    logger.error(f"Failed to publish event.processed.failed event: {e}")

        # 保存更新
        await self.repository.update_event(event)

        # 记录处理结果
        await self.repository.save_processing_result(result)

        return True
    
    async def retry_failed_events(self, max_retries: int = 3) -> int:
        """重试失败的事件"""
        failed_events = await self.repository.get_failed_events(max_retries)
        
        for event in failed_events:
            event.status = EventStatus.PENDING
            await self.repository.update_event(event)
            await self.processing_queue.put(event)
        
        return len(failed_events)
    
    # ==================== 事件重放 ====================
    
    async def replay_events(self, request: EventReplayRequest) -> Dict[str, Any]:
        """重放事件"""
        events = []

        if request.event_ids:
            # 按ID重放
            for event_id in request.event_ids:
                event = await self.repository.get_event(event_id)
                if event:
                    events.append(event)
        elif request.stream_id:
            # 按流重放
            events = await self.repository.get_event_stream(request.stream_id)
        elif request.start_time and request.end_time:
            # 按时间范围重放
            events = await self.repository.get_events_by_time_range(
                request.start_time,
                request.end_time
            )

        # Publish event.replay.started event
        if self.event_bus and not request.dry_run:
            try:
                nats_event = NATSEvent(
                    event_type=EventType.EVENT_REPLAY_STARTED,
                    source=ServiceSource.EVENT_SERVICE,
                    data={
                        "events_count": len(events),
                        "stream_id": request.stream_id,
                        "target_service": request.target_service,
                        "dry_run": request.dry_run,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                await self.event_bus.publish_event(nats_event)
            except Exception as e:
                logger.error(f"Failed to publish event.replay.started event: {e}")

        if request.dry_run:
            # 模拟运行
            return {
                "dry_run": True,
                "events_count": len(events),
                "events": [e.event_id for e in events]
            }

        # 实际重放
        replayed = 0
        failed = 0

        for event in events:
            try:
                # 重新发布事件
                await self._republish_event(event, request.target_service)
                replayed += 1
            except Exception as e:
                logger.error(f"Failed to replay event {event.event_id}: {e}")
                failed += 1

        return {
            "replayed": replayed,
            "failed": failed,
            "total": len(events)
        }
    
    # ==================== 事件投影 ====================
    
    async def create_projection(
        self,
        projection_name: str,
        entity_id: str,
        entity_type: str
    ) -> EventProjection:
        """创建事件投影"""
        projection = EventProjection(
            projection_name=projection_name,
            entity_id=entity_id,
            entity_type=entity_type
        )

        # 获取相关事件流
        stream_id = f"{entity_type}:{entity_id}"
        events = await self.repository.get_event_stream(stream_id)

        # 应用事件到投影
        for event in events:
            projection = await self._apply_event_to_projection(projection, event)

        # 保存投影
        await self.repository.save_projection(projection)
        self.projections[projection.projection_id] = projection

        # Publish event.projection.created event
        if self.event_bus:
            try:
                nats_event = NATSEvent(
                    event_type=EventType.EVENT_PROJECTION_CREATED,
                    source=ServiceSource.EVENT_SERVICE,
                    data={
                        "projection_id": projection.projection_id,
                        "projection_name": projection_name,
                        "entity_id": entity_id,
                        "entity_type": entity_type,
                        "events_count": len(events),
                        "version": projection.version,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                await self.event_bus.publish_event(nats_event)
            except Exception as e:
                logger.error(f"Failed to publish event.projection.created event: {e}")

        return projection
    
    async def get_projection(self, projection_id: str) -> Optional[EventProjection]:
        """获取事件投影"""
        if projection_id in self.projections:
            return self.projections[projection_id]
        
        return await self.repository.get_projection(projection_id)
    
    # ==================== 事件订阅 ====================
    
    async def create_subscription(self, subscription: EventSubscription) -> EventSubscription:
        """创建事件订阅"""
        # 保存订阅
        await self.repository.save_subscription(subscription)
        self.subscriptions[subscription.subscription_id] = subscription

        logger.info(f"Created subscription: {subscription.subscriber_name}")

        # Publish event.subscription.created event
        if self.event_bus:
            try:
                nats_event = NATSEvent(
                    event_type=EventType.EVENT_SUBSCRIPTION_CREATED,
                    source=ServiceSource.EVENT_SERVICE,
                    data={
                        "subscription_id": subscription.subscription_id,
                        "subscriber_name": subscription.subscriber_name,
                        "event_types": subscription.event_types,
                        "event_sources": [s.value if hasattr(s, 'value') else str(s) for s in subscription.event_sources] if subscription.event_sources else [],
                        "enabled": subscription.enabled,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                await self.event_bus.publish_event(nats_event)
            except Exception as e:
                logger.error(f"Failed to publish event.subscription.created event: {e}")

        return subscription
    
    async def list_subscriptions(self) -> List[EventSubscription]:
        """列出所有订阅"""
        # Return all subscriptions in memory
        # TODO: Load from repository if persistence is implemented
        return list(self.subscriptions.values())
    
    async def trigger_subscriptions(self, event: Event):
        """触发事件订阅"""
        for subscription in self.subscriptions.values():
            if not subscription.enabled:
                continue
            
            # 检查是否匹配订阅条件
            if not self._matches_subscription(event, subscription):
                continue
            
            # 触发订阅
            asyncio.create_task(self._deliver_to_subscriber(event, subscription))
    
    # ==================== 私有方法 ====================
    
    async def _process_event_queue(self):
        """处理事件队列"""
        self.is_processing = True
        
        while self.is_processing:
            try:
                # 从队列获取事件
                event = await asyncio.wait_for(
                    self.processing_queue.get(), 
                    timeout=1.0
                )
                
                # 处理事件
                await self._process_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event queue: {e}")
    
    async def process_event(self, event: Event):
        """处理单个事件（公共方法）"""
        try:
            await self._process_event(event)
            # 创建处理结果
            result = EventProcessingResult(
                event_id=event.event_id,
                processor_name="event_processor",
                status=ProcessingStatus.SUCCESS,
                message="Event processed successfully",
                processed_at=datetime.utcnow(),
                duration_ms=0
            )
            # 标记事件为已处理
            await self.mark_event_processed(event.event_id, "event_processor", result)
        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")
            # 创建失败处理结果
            result = EventProcessingResult(
                event_id=event.event_id,
                processor_name="event_processor",
                status=ProcessingStatus.FAILED,
                message=str(e),
                processed_at=datetime.utcnow(),
                duration_ms=0
            )
            await self.mark_event_processed(event.event_id, "event_processor", result)
    
    async def _process_event(self, event: Event):
        """处理单个事件（内部实现）"""
        try:
            # 更新投影
            await self._update_projections(event)
            
            # 触发订阅
            await self.trigger_subscriptions(event)
            
            # 执行处理器
            for processor in self.processors.values():
                if processor.enabled and self._matches_processor(event, processor):
                    await self._execute_processor(event, processor)
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")
    
    async def _trigger_realtime_processors(self, event: Event):
        """触发实时处理器"""
        # 这里可以触发需要立即处理的处理器
        pass
    
    async def _load_processors(self):
        """加载事件处理器"""
        # 从数据库或配置加载处理器
        processors = await self.repository.get_processors()
        for processor in processors:
            self.processors[processor.processor_id] = processor
    
    async def _load_subscriptions(self):
        """加载事件订阅"""
        # 从数据库加载订阅
        subscriptions = await self.repository.get_subscriptions()
        for subscription in subscriptions:
            self.subscriptions[subscription.subscription_id] = subscription
    
    def _categorize_rudderstack_event(self, event: RudderStackEvent) -> EventCategory:
        """分类 RudderStack 事件"""
        event_type = event.type.lower()
        
        if event_type == "page":
            return EventCategory.PAGE_VIEW
        elif event_type == "track":
            if "form" in event.event.lower():
                return EventCategory.FORM_SUBMIT
            elif "click" in event.event.lower():
                return EventCategory.CLICK
            else:
                return EventCategory.USER_ACTION
        else:
            return EventCategory.USER_ACTION
    
    def _categorize_nats_event(self, event: Dict[str, Any]) -> EventCategory:
        """分类 NATS 事件"""
        event_type = event.get("type", "").lower()
        
        if "user" in event_type:
            return EventCategory.USER_LIFECYCLE
        elif "payment" in event_type:
            return EventCategory.PAYMENT
        elif "order" in event_type:
            return EventCategory.ORDER
        elif "task" in event_type:
            return EventCategory.TASK
        elif "device" in event_type:
            return EventCategory.DEVICE_STATUS
        else:
            return EventCategory.SYSTEM
    
    def _matches_subscription(self, event: Event, subscription: EventSubscription) -> bool:
        """检查事件是否匹配订阅"""
        # 检查事件类型
        if subscription.event_types and event.event_type not in subscription.event_types:
            return False
        
        # 检查事件源
        if subscription.event_sources and event.event_source not in subscription.event_sources:
            return False
        
        # 检查事件分类
        if subscription.event_categories and event.event_category not in subscription.event_categories:
            return False
        
        return True
    
    def _matches_processor(self, event: Event, processor: EventProcessor) -> bool:
        """检查事件是否匹配处理器"""
        # 根据处理器的过滤条件判断
        filters = processor.filters
        
        if "event_type" in filters and event.event_type != filters["event_type"]:
            return False
        
        if "event_source" in filters and event.event_source != filters["event_source"]:
            return False
        
        return True
    
    async def _execute_processor(self, event: Event, processor: EventProcessor):
        """执行处理器"""
        try:
            # 这里应该根据处理器类型执行相应的处理逻辑
            result = EventProcessingResult(
                event_id=event.event_id,
                processor_name=processor.processor_name,
                status=ProcessingStatus.SUCCESS
            )
            
            await self.mark_event_processed(event.event_id, processor.processor_name, result)
            
        except Exception as e:
            logger.error(f"Processor {processor.processor_name} failed: {e}")
            
            result = EventProcessingResult(
                event_id=event.event_id,
                processor_name=processor.processor_name,
                status=ProcessingStatus.FAILED,
                message=str(e)
            )
            
            await self.mark_event_processed(event.event_id, processor.processor_name, result)
    
    async def _deliver_to_subscriber(self, event: Event, subscription: EventSubscription):
        """递送事件到订阅者"""
        if subscription.callback_url:
            # 通过 Webhook 递送
            # 这里应该实现 HTTP POST 请求
            pass
    
    async def _update_projections(self, event: Event):
        """更新相关投影"""
        # 查找相关投影
        stream_id = f"{event.event_category}:{event.user_id or 'system'}"
        
        for projection in self.projections.values():
            if projection.entity_id == event.user_id:
                projection = await self._apply_event_to_projection(projection, event)
                await self.repository.update_projection(projection)
    
    async def _apply_event_to_projection(
        self, 
        projection: EventProjection, 
        event: Event
    ) -> EventProjection:
        """应用事件到投影"""
        # 更新投影状态
        projection.state[event.event_type] = event.data
        projection.version += 1
        projection.last_event_id = event.event_id
        projection.updated_at = datetime.utcnow()
        
        return projection
    
    async def _republish_event(self, event: Event, target_service: Optional[str] = None):
        """重新发布事件"""
        # 这里应该实现事件重新发布逻辑
        # 可以发布到 NATS 或直接调用服务
        pass
    
    async def shutdown(self):
        """关闭服务"""
        self.is_processing = False
        await self.repository.close()