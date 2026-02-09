"""
Memory Service Factory

Factory functions for creating service instances with real dependencies.
This is the ONLY place that imports I/O-dependent modules.

Usage:
    from .factory import create_memory_service
    service = create_memory_service(event_bus=event_bus)
"""
from typing import Optional

from .memory_service import MemoryService


def create_memory_service(
    consul_registry=None,
    event_bus=None,
) -> MemoryService:
    """
    Create MemoryService with real dependencies.

    This function imports the real sub-services (which have I/O dependencies).
    Use this in production, NOT in tests.

    Args:
        consul_registry: Consul registry for service discovery (deprecated)
        event_bus: Event bus for publishing events

    Returns:
        Configured MemoryService instance
    """
    # Import real sub-services here (not at module level)
    from .factual_service import FactualMemoryService
    from .procedural_service import ProceduralMemoryService
    from .episodic_service import EpisodicMemoryService
    from .semantic_service import SemanticMemoryService
    from .working_service import WorkingMemoryService
    from .session_service import SessionMemoryService

    return MemoryService(
        consul_registry=consul_registry,
        event_bus=event_bus,
        factual_service=FactualMemoryService(),
        procedural_service=ProceduralMemoryService(),
        episodic_service=EpisodicMemoryService(),
        semantic_service=SemanticMemoryService(),
        working_service=WorkingMemoryService(),
        session_service=SessionMemoryService(),
    )
