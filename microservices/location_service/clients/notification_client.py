"""
Notification Service Client

Client for location_service to interact with notification_service.
Used for sending location-related notifications to users.
"""

import os
import sys
from typing import Any, Dict, List, Optional

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from microservices.notification_service.client import NotificationServiceClient


class NotificationClient:
    """
    Wrapper client for Notification Service calls from Location Service.

    This wrapper provides location-specific convenience methods
    while delegating to the actual NotificationServiceClient.
    """

    def __init__(self, base_url: str = None, consul_registry=None):
        """
        Initialize Notification Service client

        Args:
            base_url: Notification service base URL (optional, uses service discovery)
            consul_registry: ConsulRegistry instance for service discovery
        """
        self._client = NotificationServiceClient(
            base_url=base_url, consul_registry=consul_registry
        )

    async def close(self):
        """Close HTTP client"""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =============================================================================
    # Location-Specific Notification Methods
    # =============================================================================

    async def send_geofence_alert(
        self,
        user_id: str,
        device_id: str,
        geofence_name: str,
        event_type: str,
        latitude: float,
        longitude: float,
    ) -> Dict[str, Any]:
        """
        Send geofence alert notification

        Args:
            user_id: User ID
            device_id: Device ID
            geofence_name: Geofence name
            event_type: Event type (entered, exited, dwell)
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Notification result
        """
        title = f"Geofence {event_type.capitalize()}: {geofence_name}"
        message = f"Device {device_id} has {event_type} geofence '{geofence_name}'"

        return await self._client.send_notification(
            user_id=user_id,
            notification_type="geofence_alert",
            title=title,
            message=message,
            data={
                "device_id": device_id,
                "geofence_name": geofence_name,
                "event_type": event_type,
                "latitude": latitude,
                "longitude": longitude,
            },
            channels=["push", "in_app"],
        )

    async def send_location_alert(
        self,
        user_id: str,
        device_id: str,
        alert_type: str,
        message: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send location-related alert

        Args:
            user_id: User ID
            device_id: Device ID
            alert_type: Alert type
            message: Alert message
            **kwargs: Additional data

        Returns:
            Notification result
        """
        return await self._client.send_notification(
            user_id=user_id,
            notification_type="location_alert",
            title=f"Location Alert: {alert_type}",
            message=message,
            data={"device_id": device_id, "alert_type": alert_type, **kwargs},
            channels=["push", "in_app"],
        )

    async def send_place_notification(
        self, user_id: str, place_name: str, event_type: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Send place-related notification

        Args:
            user_id: User ID
            place_name: Place name
            event_type: Event type (created, visited, left)
            **kwargs: Additional data

        Returns:
            Notification result
        """
        messages = {
            "created": f"Place '{place_name}' has been created",
            "visited": f"You have arrived at {place_name}",
            "left": f"You have left {place_name}",
        }

        message = messages.get(event_type, f"Place event: {event_type}")

        return await self._client.send_notification(
            user_id=user_id,
            notification_type="place_notification",
            title=f"Place {event_type.capitalize()}",
            message=message,
            data={"place_name": place_name, "event_type": event_type, **kwargs},
            channels=["push", "in_app"],
        )


__all__ = ["NotificationClient"]
