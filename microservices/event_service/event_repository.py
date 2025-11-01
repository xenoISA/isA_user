"""
Event Repository

Data access layer for event management using PostgresClient.
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from isa_common.postgres_client import PostgresClient
from .models import (
    Event, EventStatus, EventSource, EventCategory,
    EventStatistics, EventProcessingResult,
    EventProjection, EventProcessor, EventSubscription
)

logger = logging.getLogger(__name__)


class EventRepository:
    """Event Repository - using PostgresClient"""

    def __init__(self):
        """Initialize Event Repository with PostgresClient"""
        self.db = PostgresClient(
            host=os.getenv("POSTGRES_GRPC_HOST", "isa-postgres-grpc"),
            port=int(os.getenv("POSTGRES_GRPC_PORT", "50061")),
            user_id="event_service"
        )

        self.schema = "event"
        self.events_table = "events"
        self.event_streams_table = "event_streams"
        self.event_projections_table = "event_projections"
        self.event_processors_table = "event_processors"
        self.event_subscriptions_table = "event_subscriptions"
        self.processing_results_table = "processing_results"

        logger.info("EventRepository initialized with PostgresClient")

    async def initialize(self):
        """Initialize (for interface consistency with other services)"""
        logger.info("Event Repository initialized")

    async def save_event(self, event: Event) -> Event:
        """Save event"""
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
                'data': event.data or {},  # Direct dict, not json.dumps()
                'metadata': event.metadata or {},
                'context': event.context or {},
                'properties': event.properties or {},
                'status': event.status.value,
                'processed_at': event.processed_at.isoformat() if event.processed_at else None,
                'processors': event.processors or [],
                'error_message': event.error_message,
                'retry_count': event.retry_count,
                'timestamp': event.timestamp.isoformat(),
                'created_at': event.created_at.isoformat(),
                'updated_at': event.updated_at.isoformat(),
                'version': event.version,
                'schema_version': event.schema_version
            }

            with self.db:
                count = self.db.insert_into(self.events_table, [event_dict], schema=self.schema)

            if count is not None and count > 0:
                logger.info(f"Event {event.event_id} saved successfully")
                return event

            # Try to get event if insert returned None/0
            result = await self.get_event(event.event_id)
            if result:
                return result

            raise Exception("Failed to save event")

        except Exception as e:
            logger.error(f"Error saving event {event.event_id}: {e}")
            raise

    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get single event by ID"""
        try:
            query = f'SELECT * FROM {self.schema}.{self.events_table} WHERE event_id = $1'

            with self.db:
                result = self.db.query_row(query, [event_id], schema=self.schema)

            if result:
                return self._row_to_event(result)
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
                          correlation_id: Optional[str] = None,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None,
                          limit: int = 100,
                          offset: int = 0) -> Tuple[List[Event], int]:
        """Query events with filters"""
        try:
            conditions = []
            params = []
            param_count = 0

            if user_id:
                param_count += 1
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)

            if event_type:
                param_count += 1
                conditions.append(f"event_type = ${param_count}")
                params.append(event_type)

            if event_source:
                param_count += 1
                conditions.append(f"event_source = ${param_count}")
                params.append(event_source.value)

            if event_category:
                param_count += 1
                conditions.append(f"event_category = ${param_count}")
                params.append(event_category.value)

            if status:
                param_count += 1
                conditions.append(f"status = ${param_count}")
                params.append(status.value)

            if correlation_id:
                param_count += 1
                conditions.append(f"correlation_id = ${param_count}")
                params.append(correlation_id)

            if start_time:
                param_count += 1
                conditions.append(f"timestamp >= ${param_count}")
                params.append(start_time.isoformat())

            if end_time:
                param_count += 1
                conditions.append(f"timestamp <= ${param_count}")
                params.append(end_time.isoformat())

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            # Get total count
            count_query = f'SELECT COUNT(*) as count FROM {self.schema}.{self.events_table} WHERE {where_clause}'
            with self.db:
                count_result = self.db.query_row(count_query, params, schema=self.schema)
            total_count = int(count_result.get("count", 0)) if count_result else 0

            # Get events
            query = f'''
                SELECT * FROM {self.schema}.{self.events_table}
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT {limit} OFFSET {offset}
            '''

            with self.db:
                results = self.db.query(query, params, schema=self.schema)

            events = [self._row_to_event(row) for row in results] if results else []

            return events, total_count

        except Exception as e:
            logger.error(f"Error querying events: {e}")
            return [], 0

    async def update_event_status(self, event_id: str, status: EventStatus,
                                  error_message: Optional[str] = None,
                                  processed_at: Optional[datetime] = None) -> bool:
        """Update event status"""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if error_message:
                update_data["error_message"] = error_message

            if processed_at:
                update_data["processed_at"] = processed_at.isoformat()
            elif status == EventStatus.PROCESSED:
                update_data["processed_at"] = datetime.now(timezone.utc).isoformat()

            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(event_id)

            set_clause = ", ".join(set_clauses)
            query = f'''
                UPDATE {self.schema}.{self.events_table}
                SET {set_clause}
                WHERE event_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating event status {event_id}: {e}")
            return False

    async def update_event(self, event: Event) -> bool:
        """Update event"""
        try:
            update_data = {
                "data": event.data or {},
                "metadata": event.metadata or {},
                "context": event.context or {},
                "properties": event.properties or {},
                "status": event.status.value,
                "processed_at": event.processed_at.isoformat() if event.processed_at else None,
                "processors": event.processors or [],
                "error_message": event.error_message,
                "retry_count": event.retry_count,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            set_clauses = []
            params = []
            param_count = 0

            for key, value in update_data.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)

            param_count += 1
            params.append(event.event_id)

            set_clause = ", ".join(set_clauses)
            query = f'''
                UPDATE {self.schema}.{self.events_table}
                SET {set_clause}
                WHERE event_id = ${param_count}
            '''

            with self.db:
                count = self.db.execute(query, params, schema=self.schema)

            return count is not None and count > 0

        except Exception as e:
            logger.error(f"Error updating event {event.event_id}: {e}")
            return False

    async def get_unprocessed_events(self, limit: int = 100) -> List[Event]:
        """Get unprocessed events"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.events_table}
                WHERE status = $1
                ORDER BY timestamp ASC
                LIMIT {limit}
            '''

            with self.db:
                results = self.db.query(query, [EventStatus.PENDING.value], schema=self.schema)

            return [self._row_to_event(row) for row in results] if results else []

        except Exception as e:
            logger.error(f"Error getting unprocessed events: {e}")
            return []

    async def get_statistics(self, user_id: Optional[str] = None) -> EventStatistics:
        """Get event statistics"""
        try:
            conditions = []
            params = []

            if user_id:
                conditions.append("user_id = $1")
                params.append(user_id)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            # Get counts by status
            query = f'''
                SELECT
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_events,
                    COUNT(CASE WHEN status = 'processed' THEN 1 END) as processed_events,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_events,
                    COUNT(CASE WHEN timestamp >= CURRENT_DATE THEN 1 END) as events_today,
                    COUNT(CASE WHEN timestamp >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as events_week,
                    COUNT(CASE WHEN timestamp >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as events_month
                FROM {self.schema}.{self.events_table}
                WHERE {where_clause}
            '''

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            if result:
                return EventStatistics(
                    total_events=int(result.get("total_events", 0)),
                    pending_events=int(result.get("pending_events", 0)),
                    processed_events=int(result.get("processed_events", 0)),
                    failed_events=int(result.get("failed_events", 0)),
                    events_today=int(result.get("events_today", 0)),
                    events_this_week=int(result.get("events_week", 0)),
                    events_this_month=int(result.get("events_month", 0)),
                    events_by_type={},
                    events_by_source={},
                    events_by_category={}
                )

            # Return default statistics
            return EventStatistics(
                total_events=0,
                pending_events=0,
                processed_events=0,
                failed_events=0,
                events_today=0,
                events_this_week=0,
                events_this_month=0,
                events_by_type={},
                events_by_source={},
                events_by_category={}
            )

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return EventStatistics(
                total_events=0,
                pending_events=0,
                processed_events=0,
                failed_events=0,
                events_today=0,
                events_this_week=0,
                events_this_month=0,
                events_by_type={},
                events_by_source={},
                events_by_category={}
            )

    async def save_processing_result(self, result: EventProcessingResult):
        """Save processing result"""
        try:
            result_dict = {
                'event_id': result.event_id,
                'processor_name': result.processor_name,
                'status': result.status.value,
                'message': result.message,
                'processed_at': result.processed_at.isoformat() if result.processed_at else datetime.now(timezone.utc).isoformat(),
                'duration_ms': result.duration_ms
            }

            with self.db:
                count = self.db.insert_into(self.processing_results_table, [result_dict], schema=self.schema)

            if count is not None and count > 0:
                logger.info(f"Processing result for event {result.event_id} saved")

        except Exception as e:
            logger.error(f"Error saving processing result: {e}")
            raise

    async def get_event_stream(self, stream_id: str,
                              entity_type: Optional[str] = None,
                              entity_id: Optional[str] = None) -> Optional[Dict]:
        """Get event stream"""
        try:
            if stream_id:
                query = f'SELECT * FROM {self.schema}.{self.event_streams_table} WHERE stream_id = $1'
                params = [stream_id]
            elif entity_type and entity_id:
                query = f'SELECT * FROM {self.schema}.{self.event_streams_table} WHERE entity_type = $1 AND entity_id = $2'
                params = [entity_type, entity_id]
            else:
                return None

            with self.db:
                result = self.db.query_row(query, params, schema=self.schema)

            return result

        except Exception as e:
            logger.error(f"Error getting event stream: {e}")
            return None

    async def save_projection(self, projection: EventProjection):
        """Save event projection"""
        try:
            projection_dict = {
                'projection_id': projection.projection_id,
                'projection_name': projection.projection_name,
                'entity_id': projection.entity_id,
                'entity_type': projection.entity_type,
                'state': projection.state or {},
                'version': projection.version,
                'last_event_id': projection.last_event_id,
                'created_at': projection.created_at.isoformat(),
                'updated_at': projection.updated_at.isoformat()
            }

            with self.db:
                count = self.db.insert_into(self.event_projections_table, [projection_dict], schema=self.schema)

            if count is not None and count > 0:
                logger.info(f"Projection {projection.projection_id} saved")

        except Exception as e:
            logger.error(f"Error saving projection: {e}")
            raise

    async def get_projection(self, entity_type: str, entity_id: str,
                            projection_name: str = "default") -> Optional[EventProjection]:
        """Get event projection"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.event_projections_table}
                WHERE entity_type = $1 AND entity_id = $2 AND projection_name = $3
            '''

            with self.db:
                result = self.db.query_row(query, [entity_type, entity_id, projection_name], schema=self.schema)

            if result:
                return EventProjection(
                    projection_id=result['projection_id'],
                    projection_name=result['projection_name'],
                    entity_id=result['entity_id'],
                    entity_type=result['entity_type'],
                    state=result.get('state', {}),
                    version=result.get('version', 0),
                    last_event_id=result.get('last_event_id'),
                    created_at=datetime.fromisoformat(result['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(result['updated_at'].replace('Z', '+00:00'))
                )

            return None

        except Exception as e:
            logger.error(f"Error getting projection: {e}")
            return None

    async def save_processor(self, processor: EventProcessor):
        """Save event processor"""
        try:
            processor_dict = {
                'processor_id': processor.processor_id,
                'processor_name': processor.processor_name,
                'processor_type': processor.processor_type,
                'enabled': processor.enabled,
                'priority': processor.priority,
                'filters': processor.filters or {},
                'config': processor.config or {},
                'error_count': processor.error_count,
                'last_error': processor.last_error,
                'last_processed_at': processor.last_processed_at.isoformat() if processor.last_processed_at else None,
                'created_at': processor.created_at.isoformat(),
                'updated_at': processor.updated_at.isoformat()
            }

            with self.db:
                count = self.db.insert_into(self.event_processors_table, [processor_dict], schema=self.schema)

            if count is not None and count > 0:
                logger.info(f"Processor {processor.processor_id} saved")

        except Exception as e:
            logger.error(f"Error saving processor: {e}")
            raise

    async def get_processors(self) -> List[EventProcessor]:
        """Get all event processors"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.event_processors_table}
                WHERE enabled = TRUE
                ORDER BY priority DESC
            '''

            with self.db:
                results = self.db.query(query, [], schema=self.schema)

            processors = []
            if results:
                for row in results:
                    processors.append(EventProcessor(
                        processor_id=row['processor_id'],
                        processor_name=row['processor_name'],
                        processor_type=row['processor_type'],
                        enabled=row.get('enabled', True),
                        priority=row.get('priority', 0),
                        filters=row.get('filters', {}),
                        config=row.get('config', {}),
                        error_count=row.get('error_count', 0),
                        last_error=row.get('last_error'),
                        last_processed_at=datetime.fromisoformat(row['last_processed_at'].replace('Z', '+00:00')) if row.get('last_processed_at') else None,
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
                    ))

            return processors

        except Exception as e:
            logger.error(f"Error getting processors: {e}")
            return []

    async def save_subscription(self, subscription: EventSubscription):
        """Save event subscription"""
        try:
            subscription_dict = {
                'subscription_id': subscription.subscription_id,
                'subscriber_name': subscription.subscriber_name,
                'subscriber_type': subscription.subscriber_type,
                'event_types': subscription.event_types or [],
                'event_sources': subscription.event_sources or [],
                'event_categories': subscription.event_categories or [],
                'callback_url': subscription.callback_url,
                'webhook_secret': subscription.webhook_secret,
                'enabled': subscription.enabled,
                'retry_policy': subscription.retry_policy or {},
                'created_at': subscription.created_at.isoformat(),
                'updated_at': subscription.updated_at.isoformat()
            }

            with self.db:
                count = self.db.insert_into(self.event_subscriptions_table, [subscription_dict], schema=self.schema)

            if count is not None and count > 0:
                logger.info(f"Subscription {subscription.subscription_id} saved")
                return subscription

            return None

        except Exception as e:
            logger.error(f"Error saving subscription: {e}")
            raise

    async def get_subscriptions(self) -> List[EventSubscription]:
        """Get all event subscriptions"""
        try:
            query = f'''
                SELECT * FROM {self.schema}.{self.event_subscriptions_table}
                WHERE enabled = TRUE
                ORDER BY created_at DESC
            '''

            with self.db:
                results = self.db.query(query, [], schema=self.schema)

            subscriptions = []
            if results:
                for row in results:
                    subscriptions.append(EventSubscription(
                        subscription_id=row['subscription_id'],
                        subscriber_name=row['subscriber_name'],
                        subscriber_type=row['subscriber_type'],
                        event_types=row.get('event_types', []),
                        event_sources=row.get('event_sources', []),
                        event_categories=row.get('event_categories', []),
                        callback_url=row.get('callback_url'),
                        webhook_secret=row.get('webhook_secret'),
                        enabled=row.get('enabled', True),
                        retry_policy=row.get('retry_policy', {}),
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00'))
                    ))

            return subscriptions

        except Exception as e:
            logger.error(f"Error getting subscriptions: {e}")
            return []

    def _row_to_event(self, row: Dict) -> Event:
        """Convert database row to Event model"""
        # Handle JSONB fields
        data = row.get('data')
        if isinstance(data, str):
            import json
            data = json.loads(data)
        elif not isinstance(data, dict):
            data = {}

        metadata = row.get('metadata')
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)
        elif not isinstance(metadata, dict):
            metadata = {}

        context = row.get('context')
        if isinstance(context, str):
            import json
            context = json.loads(context)
        elif not isinstance(context, dict):
            context = {}

        properties = row.get('properties')
        if isinstance(properties, str):
            import json
            properties = json.loads(properties)
        elif not isinstance(properties, dict):
            properties = {}

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
            data=data,
            metadata=metadata,
            context=context,
            properties=properties,
            status=EventStatus(row['status']),
            processed_at=datetime.fromisoformat(row['processed_at'].replace('Z', '+00:00')) if row.get('processed_at') else None,
            processors=row.get('processors', []),
            error_message=row.get('error_message'),
            retry_count=row.get('retry_count', 0),
            timestamp=datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')),
            created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')),
            version=row.get('version', '1.0.0'),
            schema_version=row.get('schema_version', '1.0.0')
        )

    async def close(self):
        """Close repository (for interface consistency)"""
        logger.info("Event Repository closed")
