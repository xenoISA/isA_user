"""
Memory Service Event Publishers

Centralized functions for publishing events from Memory Service
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.nats_client import Event
from .models import (
    MemoryCreatedEvent,
    MemoryUpdatedEvent,
    MemoryDeletedEvent,
    FactualMemoryStoredEvent,
    EpisodicMemoryStoredEvent,
    ProceduralMemoryStoredEvent,
    SemanticMemoryStoredEvent,
    SessionMemoryDeactivatedEvent
)

logger = logging.getLogger(__name__)


async def publish_memory_created(
    event_bus,
    memory_id: str,
    memory_type: str,
    user_id: str,
    content: str,
    importance_score: Optional[float] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Publish memory.created event

    Args:
        event_bus: Event bus instance
        memory_id: Unique memory ID
        memory_type: Type of memory
        user_id: User ID
        content: Memory content
        importance_score: Importance score
        tags: Memory tags
        metadata: Additional metadata

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = MemoryCreatedEvent(
            memory_id=memory_id,
            memory_type=memory_type,
            user_id=user_id,
            content=content,
            importance_score=importance_score,
            tags=tags,
            metadata=metadata,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type="memory.created",
            source="memory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published memory.created event for memory {memory_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish memory.created event: {e}")
        return False


async def publish_memory_updated(
    event_bus,
    memory_id: str,
    memory_type: str,
    user_id: str,
    updated_fields: List[str]
) -> bool:
    """
    Publish memory.updated event

    Args:
        event_bus: Event bus instance
        memory_id: Unique memory ID
        memory_type: Type of memory
        user_id: User ID
        updated_fields: List of updated field names

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = MemoryUpdatedEvent(
            memory_id=memory_id,
            memory_type=memory_type,
            user_id=user_id,
            updated_fields=updated_fields,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type="memory.updated",
            source="memory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published memory.updated event for memory {memory_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish memory.updated event: {e}")
        return False


async def publish_memory_deleted(
    event_bus,
    memory_id: str,
    memory_type: str,
    user_id: str
) -> bool:
    """
    Publish memory.deleted event

    Args:
        event_bus: Event bus instance
        memory_id: Unique memory ID
        memory_type: Type of memory
        user_id: User ID

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = MemoryDeletedEvent(
            memory_id=memory_id,
            memory_type=memory_type,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type="memory.deleted",
            source="memory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published memory.deleted event for memory {memory_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish memory.deleted event: {e}")
        return False


async def publish_factual_memory_stored(
    event_bus,
    user_id: str,
    count: int,
    importance_score: float,
    source: str = "dialog"
) -> bool:
    """
    Publish factual_memory.stored event

    Args:
        event_bus: Event bus instance
        user_id: User ID
        count: Number of memories extracted
        importance_score: Average importance score
        source: Source of extraction

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = FactualMemoryStoredEvent(
            user_id=user_id,
            count=count,
            importance_score=importance_score,
            source=source,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type="memory.factual.stored",
            source="memory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published factual_memory.stored event for user {user_id}: {count} memories")
        return True

    except Exception as e:
        logger.error(f"Failed to publish factual_memory.stored event: {e}")
        return False


async def publish_episodic_memory_stored(
    event_bus,
    user_id: str,
    count: int,
    importance_score: float,
    source: str = "dialog"
) -> bool:
    """
    Publish episodic_memory.stored event

    Args:
        event_bus: Event bus instance
        user_id: User ID
        count: Number of memories extracted
        importance_score: Average importance score
        source: Source of extraction

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = EpisodicMemoryStoredEvent(
            user_id=user_id,
            count=count,
            importance_score=importance_score,
            source=source,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type="memory.episodic.stored",
            source="memory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published episodic_memory.stored event for user {user_id}: {count} memories")
        return True

    except Exception as e:
        logger.error(f"Failed to publish episodic_memory.stored event: {e}")
        return False


async def publish_procedural_memory_stored(
    event_bus,
    user_id: str,
    count: int,
    importance_score: float,
    source: str = "dialog"
) -> bool:
    """
    Publish procedural_memory.stored event

    Args:
        event_bus: Event bus instance
        user_id: User ID
        count: Number of memories extracted
        importance_score: Average importance score
        source: Source of extraction

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = ProceduralMemoryStoredEvent(
            user_id=user_id,
            count=count,
            importance_score=importance_score,
            source=source,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type="memory.procedural.stored",
            source="memory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published procedural_memory.stored event for user {user_id}: {count} memories")
        return True

    except Exception as e:
        logger.error(f"Failed to publish procedural_memory.stored event: {e}")
        return False


async def publish_semantic_memory_stored(
    event_bus,
    user_id: str,
    count: int,
    importance_score: float,
    source: str = "dialog"
) -> bool:
    """
    Publish semantic_memory.stored event

    Args:
        event_bus: Event bus instance
        user_id: User ID
        count: Number of memories extracted
        importance_score: Average importance score
        source: Source of extraction

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = SemanticMemoryStoredEvent(
            user_id=user_id,
            count=count,
            importance_score=importance_score,
            source=source,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type="memory.semantic.stored",
            source="memory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published semantic_memory.stored event for user {user_id}: {count} memories")
        return True

    except Exception as e:
        logger.error(f"Failed to publish semantic_memory.stored event: {e}")
        return False


async def publish_session_memory_deactivated(
    event_bus,
    user_id: str,
    session_id: str,
    duration_seconds: Optional[int] = None,
    message_count: Optional[int] = None
) -> bool:
    """
    Publish session_memory.deactivated event

    Args:
        event_bus: Event bus instance
        user_id: User ID
        session_id: Session ID
        duration_seconds: Session duration
        message_count: Number of messages

    Returns:
        bool: True if published successfully
    """
    try:
        event_data = SessionMemoryDeactivatedEvent(
            user_id=user_id,
            session_id=session_id,
            duration_seconds=duration_seconds,
            message_count=message_count,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        event = Event(
            event_type="memory.session.deactivated",
            source="memory_service",
            data=event_data.model_dump(mode='json')
        )

        await event_bus.publish_event(event)
        logger.info(f"Published session_memory.deactivated event for session {session_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish session_memory.deactivated event: {e}")
        return False
