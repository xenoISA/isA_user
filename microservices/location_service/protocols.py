"""
Location Service Protocols (Interfaces)

Protocol definitions for dependency injection.
NO import-time I/O dependencies.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime


class LocationServiceError(Exception):
    """Base exception for location service errors"""
    pass


class LocationNotFoundError(Exception):
    """Location not found"""
    pass


class GeofenceNotFoundError(Exception):
    """Geofence not found"""
    pass


@runtime_checkable
class LocationRepositoryProtocol(Protocol):
    """Interface for Location Repository"""

    async def create_location(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    async def get_location_by_id(self, location_id: str) -> Optional[Dict[str, Any]]: ...

    async def get_device_latest_location(self, device_id: str) -> Optional[Dict[str, Any]]: ...

    async def get_device_location_history(
        self, device_id: str, start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None, limit: int = 100, offset: int = 0,
    ) -> List[Dict[str, Any]]: ...

    async def find_nearby_devices(
        self, latitude: float, longitude: float, radius_meters: float,
        user_id: str, time_window_minutes: int = 30,
        device_types: Optional[List[str]] = None, limit: int = 50,
    ) -> List[Dict[str, Any]]: ...

    async def create_geofence(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    async def get_geofence_by_id(self, geofence_id: str) -> Optional[Dict[str, Any]]: ...

    async def list_geofences(
        self, user_id: str, active_only: bool = False,
        limit: int = 100, offset: int = 0,
    ) -> List[Dict[str, Any]]: ...

    async def update_geofence(self, geofence_id: str, updates: Dict[str, Any]) -> bool: ...

    async def delete_geofence(self, geofence_id: str) -> bool: ...

    async def check_point_in_geofences(
        self, latitude: float, longitude: float, device_id: str, user_id: str,
    ) -> List[Dict[str, Any]]: ...

    async def create_place(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    async def get_place_by_id(self, place_id: str) -> Optional[Dict[str, Any]]: ...

    async def list_user_places(self, user_id: str) -> List[Dict[str, Any]]: ...

    async def update_place(self, place_id: str, updates: Dict[str, Any]) -> bool: ...

    async def delete_place(self, place_id: str) -> bool: ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Interface for Event Bus"""

    async def publish_event(self, event: Any) -> None: ...
