"""
Location Service Client

Client library for interacting with the Location Service
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from isa_common.service_client import ServiceClient

logger = logging.getLogger(__name__)


class LocationServiceClient(ServiceClient):
    """Client for Location Service"""

    def __init__(self, base_url: Optional[str] = None, consul_registry=None):
        """
        Initialize Location Service client

        Args:
            base_url: Base URL for location service (optional if using Consul)
            consul_registry: ConsulRegistry instance for service discovery
        """
        super().__init__(
            service_name="location_service",
            base_url=base_url,
            consul_registry=consul_registry,
            default_port=8224
        )

    # ==================== Location Operations ====================

    async def report_location(
        self,
        device_id: str,
        latitude: float,
        longitude: float,
        accuracy: float,
        altitude: Optional[float] = None,
        heading: Optional[float] = None,
        speed: Optional[float] = None,
        location_method: str = "gps",
        battery_level: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Report device location"""
        return await self._request(
            "POST",
            "/locations",
            json={
                "device_id": device_id,
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
                "altitude": altitude,
                "heading": heading,
                "speed": speed,
                "location_method": location_method,
                "battery_level": battery_level,
                "timestamp": timestamp.isoformat() if timestamp else None,
                "source": "device",
                "metadata": metadata or {}
            }
        )

    async def batch_report_locations(
        self,
        locations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Report multiple locations in batch"""
        return await self._request(
            "POST",
            "/locations/batch",
            json={"locations": locations}
        )

    async def get_device_latest_location(
        self,
        device_id: str
    ) -> Dict[str, Any]:
        """Get device's latest location"""
        return await self._request(
            "GET",
            f"/locations/device/{device_id}"
        )

    async def get_device_location_history(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get device location history"""
        params = {
            "limit": limit,
            "offset": offset
        }
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()

        return await self._request(
            "GET",
            f"/locations/device/{device_id}/history",
            params=params
        )

    async def get_user_devices_locations(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get latest locations for all user's devices"""
        return await self._request(
            "GET",
            f"/locations/user/{user_id}"
        )

    # ==================== Geofence Operations ====================

    async def create_geofence(
        self,
        name: str,
        shape_type: str,
        center_lat: float,
        center_lon: float,
        radius: Optional[float] = None,
        polygon_coordinates: Optional[List] = None,
        trigger_on_enter: bool = True,
        trigger_on_exit: bool = True,
        trigger_on_dwell: bool = False,
        dwell_time_seconds: Optional[int] = None,
        target_devices: Optional[List[str]] = None,
        target_groups: Optional[List[str]] = None,
        notification_channels: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new geofence"""
        data = {
            "name": name,
            "shape_type": shape_type,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "trigger_on_enter": trigger_on_enter,
            "trigger_on_exit": trigger_on_exit,
            "trigger_on_dwell": trigger_on_dwell,
            "target_devices": target_devices or [],
            "target_groups": target_groups or [],
            "notification_channels": notification_channels or []
        }

        if radius:
            data["radius"] = radius
        if polygon_coordinates:
            data["polygon_coordinates"] = polygon_coordinates
        if dwell_time_seconds:
            data["dwell_time_seconds"] = dwell_time_seconds

        data.update(kwargs)

        return await self._request(
            "POST",
            "/geofences",
            json=data
        )

    async def list_geofences(
        self,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List geofences"""
        return await self._request(
            "GET",
            "/geofences",
            params={
                "active_only": active_only,
                "limit": limit,
                "offset": offset
            }
        )

    async def get_geofence(
        self,
        geofence_id: str
    ) -> Dict[str, Any]:
        """Get geofence details"""
        return await self._request(
            "GET",
            f"/geofences/{geofence_id}"
        )

    async def update_geofence(
        self,
        geofence_id: str,
        **updates
    ) -> Dict[str, Any]:
        """Update geofence"""
        return await self._request(
            "PUT",
            f"/geofences/{geofence_id}",
            json=updates
        )

    async def delete_geofence(
        self,
        geofence_id: str
    ) -> Dict[str, Any]:
        """Delete geofence"""
        return await self._request(
            "DELETE",
            f"/geofences/{geofence_id}"
        )

    async def activate_geofence(
        self,
        geofence_id: str
    ) -> Dict[str, Any]:
        """Activate geofence"""
        return await self._request(
            "POST",
            f"/geofences/{geofence_id}/activate"
        )

    async def deactivate_geofence(
        self,
        geofence_id: str
    ) -> Dict[str, Any]:
        """Deactivate geofence"""
        return await self._request(
            "POST",
            f"/geofences/{geofence_id}/deactivate"
        )

    # ==================== Search Operations ====================

    async def find_nearby_devices(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float,
        device_types: Optional[List[str]] = None,
        time_window_minutes: int = 30,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Find devices near a location"""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius_meters": radius_meters,
            "time_window_minutes": time_window_minutes,
            "limit": limit
        }
        if device_types:
            params["device_types"] = ",".join(device_types)

        return await self._request(
            "GET",
            "/locations/nearby",
            params=params
        )

    async def search_radius(
        self,
        center_lat: float,
        center_lon: float,
        radius_meters: float,
        start_time: datetime,
        end_time: datetime,
        device_ids: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Search locations within a circular area"""
        return await self._request(
            "POST",
            "/locations/search/radius",
            json={
                "center_lat": center_lat,
                "center_lon": center_lon,
                "radius_meters": radius_meters,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "device_ids": device_ids,
                "limit": limit
            }
        )

    async def calculate_distance(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float
    ) -> Dict[str, Any]:
        """Calculate distance between two points"""
        return await self._request(
            "GET",
            "/locations/distance",
            params={
                "from_lat": from_lat,
                "from_lon": from_lon,
                "to_lat": to_lat,
                "to_lon": to_lon
            }
        )

    # ==================== Statistics ====================

    async def get_user_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get location statistics for a user"""
        return await self._request(
            "GET",
            f"/stats/user/{user_id}"
        )
