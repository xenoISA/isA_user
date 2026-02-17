"""
Event Repository

事件数据存储层 - 使用 Supabase Client
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

# Add parent directories to path to import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.database.supabase_client import get_supabase_client
from .models import (
    Event, EventStatus, EventSource, EventCategory,
    EventStatistics, EventProcessingResult,
    EventProjection, EventProcessor, EventSubscription
)

logger = logging.getLogger(__name__)


class EventRepository:
    """事件存储库 - 使用 Supabase"""
    
    def __init__(self):
        """初始化仓库"""
        self.supabase = get_supabase_client()
        # 表名定义
        self.events_table = "events"
        self.event_streams_table = "event_streams"
        self.event_projections_table = "event_projections"
        self.event_processors_table = "event_processors"
        self.event_subscriptions_table = "event_subscriptions"
        self.processing_results_table = "processing_results"
    
    async def initialize(self):
        """初始化（与其他服务保持接口一致）"""
        logger.info("Event Repository initialized with Supabase client")
    
    async def save_event(self, event: Event) -> Event:
        """保存事件"""
        try:
            event_dict = {
                'event_id': event.event_id,
                'event_type': event.event_type,
                'event_source': event.event_source.value,
                'event_category': event.event_category.value,
                'user_id': event.user_id,
                'session_id': event.session_id,
                'organization_id': event.organization_id,
                'device_id': event.device_id,
                'correlation_id': event.correlation_id,
                'data': json.dumps(event.data),
                'metadata': json.dumps(event.metadata),
                'context': json.dumps(event.context) if event.context else None,
                'properties': json.dumps(event.properties) if event.properties else None,
                'status': event.status.value,
                'processed_at': event.processed_at.isoformat() if event.processed_at else None,
                'processors': event.processors,
                'error_message': event.error_message,
                'retry_count': event.retry_count,
                'timestamp': event.timestamp.isoformat(),
                'created_at': event.created_at.isoformat(),
                'updated_at': event.updated_at.isoformat(),
                'version': event.version,
                'schema_version': event.schema_version
            }
            
            result = self.supabase.table(self.events_table).insert(event_dict).execute()
            
            if result.data:
                logger.info(f"Event {event.event_id} saved successfully")
                return event
            else:
                raise Exception("Failed to save event")
                
        except Exception as e:
            logger.error(f"Error saving event {event.event_id}: {e}")
            raise
    
    async def get_event(self, event_id: str) -> Optional[Event]:
        """获取单个事件"""
        try:
            result = self.supabase.table(self.events_table).select('*').eq('event_id', event_id).single().execute()
            
            if result.data:
                return self._row_to_event(result.data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting event {event_id}: {e}")
            return None
    
    async def query_events(self, 
                          user_id: Optional[str] = None,
                          event_type: Optional[str] = None,
                          event_source: Optional[EventSource] = None,
                          event_category: Optional[EventCategory] = None,
                          status: Optional[EventStatus] = None,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          limit: int = 100,
                          offset: int = 0) -> Tuple[List[Event], int]:
        """查询事件"""
        try:
            # 构建查询条件
            query = self.supabase.table(self.events_table).select('*')
            count_query = self.supabase.table(self.events_table).select('*', count='exact')
            
            # 应用过滤条件
            if user_id:
                query = query.eq('user_id', user_id)
                count_query = count_query.eq('user_id', user_id)
            if event_type:
                query = query.eq('event_type', event_type)
                count_query = count_query.eq('event_type', event_type)
            if event_source:
                query = query.eq('event_source', event_source.value)
                count_query = count_query.eq('event_source', event_source.value)
            if event_category:
                query = query.eq('event_category', event_category.value)
                count_query = count_query.eq('event_category', event_category.value)
            if status:
                query = query.eq('status', status.value)
                count_query = count_query.eq('status', status.value)
            if start_time:
                query = query.gte('timestamp', start_time.isoformat())
                count_query = count_query.gte('timestamp', start_time.isoformat())
            if end_time:
                query = query.lte('timestamp', end_time.isoformat())
                count_query = count_query.lte('timestamp', end_time.isoformat())
            
            # 执行查询
            query = query.order('timestamp', desc=True).range(offset, offset + limit - 1)
            result = query.execute()
            count_result = count_query.execute()
            
            events = []
            if result.data:
                events = [self._row_to_event(row) for row in result.data]
            
            total = count_result.count if count_result.count is not None else 0
            return events, total
            
        except Exception as e:
            logger.error(f"Error querying events: {e}")
            return [], 0
    
    async def update_event_status(self, event_id: str, status: EventStatus, 
                                 error_message: Optional[str] = None) -> bool:
        """更新事件状态"""
        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if status == EventStatus.PROCESSED:
                update_data['processed_at'] = datetime.utcnow().isoformat()
            
            if error_message:
                update_data['error_message'] = error_message
            
            result = self.supabase.table(self.events_table).update(update_data).eq('event_id', event_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating event {event_id} status: {e}")
            return False
    
    async def update_event(self, event: Event) -> bool:
        """更新事件"""
        try:
            update_data = {
                'status': event.status.value,
                'processors': event.processors,
                'processed_at': event.processed_at.isoformat() if event.processed_at else None,
                'error_message': event.error_message,
                'retry_count': event.retry_count,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table(self.events_table).update(update_data).eq('event_id', event.event_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating event {event.event_id}: {e}")
            return False
    
    async def get_unprocessed_events(self, limit: int = 100) -> List[Event]:
        """获取未处理的事件"""
        try:
            query = self.supabase.table(self.events_table).select('*')
            query = query.eq('status', EventStatus.PENDING.value)
            query = query.order('timestamp', desc=False)  # 按时间顺序处理
            query = query.limit(limit)
            result = query.execute()
            
            if result.data:
                return [self._row_to_event(row) for row in result.data]
            return []
            
        except Exception as e:
            logger.error(f"Error getting unprocessed events: {e}")
            return []
    
    async def get_statistics(self, user_id: Optional[str] = None) -> EventStatistics:
        """获取事件统计"""
        try:
            # 基础查询
            query = self.supabase.table(self.events_table).select('*', count='exact')
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            # 获取总数
            total_result = query.execute()
            total_events = len(total_result.data) if total_result.data else 0
            
            # 获取各状态的事件数
            pending_query = self.supabase.table(self.events_table).select('*', count='exact').eq('status', EventStatus.PENDING.value)
            processed_query = self.supabase.table(self.events_table).select('*', count='exact').eq('status', EventStatus.PROCESSED.value)
            failed_query = self.supabase.table(self.events_table).select('*', count='exact').eq('status', EventStatus.FAILED.value)
            
            if user_id:
                pending_query = pending_query.eq('user_id', user_id)
                processed_query = processed_query.eq('user_id', user_id)
                failed_query = failed_query.eq('user_id', user_id)
            
            pending_events = len(pending_query.execute().data or [])
            processed_events = len(processed_query.execute().data or [])
            failed_events = len(failed_query.execute().data or [])
            
            # 获取今日事件数
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_query = self.supabase.table(self.events_table).select('*', count='exact').gte('timestamp', today_start.isoformat())
            
            if user_id:
                today_query = today_query.eq('user_id', user_id)
            
            events_today = len(today_query.execute().data or [])
            
            # 计算处理率和错误率
            processing_rate = (processed_events / total_events * 100) if total_events > 0 else 0
            error_rate = (failed_events / total_events * 100) if total_events > 0 else 0
            
            return EventStatistics(
                total_events=total_events,
                pending_events=pending_events,
                processed_events=processed_events,
                failed_events=failed_events,
                events_today=events_today,
                processing_rate=processing_rate,
                error_rate=error_rate,
                calculated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return EventStatistics(
                total_events=0,
                pending_events=0,
                processed_events=0,
                failed_events=0,
                events_today=0,
                processing_rate=0.0,
                error_rate=0.0,
                calculated_at=datetime.utcnow()
            )
    
    async def save_processing_result(self, result: EventProcessingResult):
        """保存处理结果"""
        try:
            result_dict = {
                'event_id': result.event_id,
                'processor_name': result.processor_name,
                'status': result.status.value,
                'message': result.message,
                'processed_at': result.processed_at.isoformat(),
                'duration_ms': result.duration_ms
            }
            
            self.supabase.table(self.processing_results_table).insert(result_dict).execute()
            
        except Exception as e:
            logger.error(f"Error saving processing result: {e}")
    
    async def get_event_stream(self, stream_id: str, 
                              from_version: Optional[int] = None) -> List[Event]:
        """获取事件流"""
        try:
            # 获取流信息
            stream_result = self.supabase.table(self.event_streams_table).select('*').eq('stream_id', stream_id).single().execute()
            
            if not stream_result.data:
                return []
            
            # 获取流中的事件
            events_data = json.loads(stream_result.data.get('events', '[]'))
            events = []
            
            for event_id in events_data:
                event = await self.get_event(event_id)
                if event:
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting event stream {stream_id}: {e}")
            return []
    
    async def save_projection(self, projection: EventProjection):
        """保存投影"""
        try:
            projection_dict = {
                'projection_id': projection.projection_id,
                'projection_name': projection.projection_name,
                'entity_id': projection.entity_id,
                'entity_type': projection.entity_type,
                'state': json.dumps(projection.state),
                'version': projection.version,
                'last_event_id': projection.last_event_id,
                'created_at': projection.created_at.isoformat(),
                'updated_at': projection.updated_at.isoformat()
            }
            
            # Upsert projection
            self.supabase.table(self.event_projections_table).upsert(projection_dict).execute()
            
        except Exception as e:
            logger.error(f"Error saving projection: {e}")
    
    async def get_projection(self, entity_type: str, entity_id: str) -> Optional[EventProjection]:
        """获取投影"""
        try:
            result = self.supabase.table(self.event_projections_table).select('*').eq('entity_type', entity_type).eq('entity_id', entity_id).single().execute()
            
            if result.data:
                return EventProjection(
                    projection_id=result.data['projection_id'],
                    projection_name=result.data['projection_name'],
                    entity_id=result.data['entity_id'],
                    entity_type=result.data['entity_type'],
                    state=json.loads(result.data['state']),
                    version=result.data['version'],
                    last_event_id=result.data.get('last_event_id'),
                    created_at=datetime.fromisoformat(result.data['created_at']),
                    updated_at=datetime.fromisoformat(result.data['updated_at'])
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting projection: {e}")
            return None
    
    async def save_processor(self, processor: EventProcessor):
        """保存处理器"""
        try:
            processor_dict = {
                'processor_id': processor.processor_id,
                'processor_name': processor.processor_name,
                'processor_type': processor.processor_type,
                'enabled': processor.enabled,
                'priority': processor.priority,
                'filters': json.dumps(processor.filters),
                'config': json.dumps(processor.config),
                'error_count': processor.error_count,
                'last_error': processor.last_error,
                'last_processed_at': processor.last_processed_at.isoformat() if processor.last_processed_at else None
            }
            
            self.supabase.table(self.event_processors_table).upsert(processor_dict).execute()
            
        except Exception as e:
            logger.error(f"Error saving processor: {e}")
    
    async def get_processors(self) -> List[EventProcessor]:
        """获取所有处理器"""
        try:
            result = self.supabase.table(self.event_processors_table).select('*').order('priority', desc=True).execute()
            
            if result.data:
                processors = []
                for row in result.data:
                    processors.append(EventProcessor(
                        processor_id=row['processor_id'],
                        processor_name=row['processor_name'],
                        processor_type=row['processor_type'],
                        enabled=row['enabled'],
                        priority=row['priority'],
                        filters=json.loads(row['filters']),
                        config=json.loads(row['config']),
                        error_count=row['error_count'],
                        last_error=row.get('last_error'),
                        last_processed_at=datetime.fromisoformat(row['last_processed_at']) if row.get('last_processed_at') else None
                    ))
                return processors
            return []
            
        except Exception as e:
            logger.error(f"Error getting processors: {e}")
            return []
    
    async def save_subscription(self, subscription: EventSubscription):
        """保存订阅"""
        try:
            subscription_dict = {
                'subscription_id': subscription.subscription_id,
                'subscriber_name': subscription.subscriber_name,
                'subscriber_type': subscription.subscriber_type,
                'event_types': subscription.event_types,
                'event_sources': [s.value for s in subscription.event_sources] if subscription.event_sources else None,
                'event_categories': [c.value for c in subscription.event_categories] if subscription.event_categories else None,
                'callback_url': subscription.callback_url,
                'webhook_secret': subscription.webhook_secret,
                'enabled': subscription.enabled,
                'retry_policy': json.dumps(subscription.retry_policy),
                'created_at': subscription.created_at.isoformat(),
                'updated_at': subscription.updated_at.isoformat()
            }
            
            self.supabase.table(self.event_subscriptions_table).upsert(subscription_dict).execute()
            
        except Exception as e:
            logger.error(f"Error saving subscription: {e}")
    
    async def get_subscriptions(self) -> List[EventSubscription]:
        """获取所有订阅"""
        try:
            result = self.supabase.table(self.event_subscriptions_table).select('*').execute()
            
            if result.data:
                subscriptions = []
                for row in result.data:
                    subscriptions.append(EventSubscription(
                        subscription_id=row['subscription_id'],
                        subscriber_name=row['subscriber_name'],
                        subscriber_type=row['subscriber_type'],
                        event_types=row['event_types'],
                        event_sources=[EventSource(s) for s in row['event_sources']] if row.get('event_sources') else None,
                        event_categories=[EventCategory(c) for c in row['event_categories']] if row.get('event_categories') else None,
                        callback_url=row.get('callback_url'),
                        webhook_secret=row.get('webhook_secret'),
                        enabled=row['enabled'],
                        retry_policy=json.loads(row['retry_policy']),
                        created_at=datetime.fromisoformat(row['created_at']),
                        updated_at=datetime.fromisoformat(row['updated_at'])
                    ))
                return subscriptions
            return []
            
        except Exception as e:
            logger.error(f"Error getting subscriptions: {e}")
            return []
    
    def _row_to_event(self, row: Dict) -> Event:
        """将数据库行转换为事件对象"""
        return Event(
            event_id=row['event_id'],
            event_type=row['event_type'],
            event_source=EventSource(row['event_source']),
            event_category=EventCategory(row['event_category']),
            user_id=row.get('user_id'),
            session_id=row.get('session_id'),
            organization_id=row.get('organization_id'),
            device_id=row.get('device_id'),
            correlation_id=row.get('correlation_id'),
            data=json.loads(row['data']) if row.get('data') else {},
            metadata=json.loads(row['metadata']) if row.get('metadata') else {},
            context=json.loads(row['context']) if row.get('context') else None,
            properties=json.loads(row['properties']) if row.get('properties') else None,
            status=EventStatus(row['status']),
            processed_at=datetime.fromisoformat(row['processed_at']) if row.get('processed_at') else None,
            processors=row.get('processors', []),
            error_message=row.get('error_message'),
            retry_count=row.get('retry_count', 0),
            timestamp=datetime.fromisoformat(row['timestamp']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            version=row.get('version', '1.0.0'),
            schema_version=row.get('schema_version', '1.0.0')
        )
    
    async def close(self):
        """关闭连接（Supabase client 不需要显式关闭）"""
        pass